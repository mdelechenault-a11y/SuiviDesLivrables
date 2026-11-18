import type { FastifyPluginAsync } from 'fastify';
import { sql } from 'kysely';
import { z } from 'zod';
import type { Databases } from '../../db/connections.js';
import { HttpError, mustTenant, mustUser, requirePermission } from '../../security/context.js';

const DateStr = z.string().regex(/^\d{4}-\d{2}-\d{2}$/, 'Date au format AAAA-MM-JJ');
const Periode = z.object({ du: DateStr, au: DateStr }).refine((p) => p.du <= p.au, 'La date de début doit précéder la date de fin.');
const PeriodeEquipe = z.intersection(
  Periode,
  z.object({
    utilisateur_id: z.coerce.number().int().positive().optional(),
    projet_id: z.coerce.number().int().positive().optional(),
  }),
);
const PointageBody = z.object({
  tache_id: z.number().int().positive(),
  date: DateStr,
  heures: z.number().gt(0).max(24).multipleOf(0.25, 'Par quarts d\'heure (0,25)'),
  commentaire: z.string().trim().max(500).optional(),
});

/** Pointage des heures. Chacun pointe et voit ses heures ; les heures des autres exigent temps.voir_equipe. */
export const tempsRoutes: FastifyPluginAsync<{ dbs: Databases }> = async (app, { dbs }) => {
  app.get('/mes-taches', { preHandler: requirePermission('temps.saisir') }, async (req) => {
    const me = mustUser(req);
    const { db } = mustTenant(req);
    const rows = await db
      .selectFrom('affectations as a')
      .innerJoin('taches as t', 't.id', 'a.tache_id')
      .innerJoin('projets as p', 'p.id', 't.projet_id')
      .select([
        't.id as tache_id',
        't.nom as tache',
        't.date_debut',
        't.date_fin',
        'p.id as projet_id',
        'p.code as projet_code',
        'p.nom as projet',
        'a.heures_allouees',
        (eb) =>
          eb
            .selectFrom('pointages as x')
            .select(sql<number>`COALESCE(SUM(x.heures), 0)`.as('s'))
            .whereRef('x.tache_id', '=', 't.id')
            .where('x.utilisateur_id', '=', me.id)
            .as('heures_pointees'),
      ])
      .where('a.utilisateur_id', '=', me.id)
      .where('p.statut', '=', 'En cours')
      .orderBy('p.code')
      .orderBy('t.position')
      .execute();
    return rows.map((r) => ({ ...r, heures_pointees: Number(r.heures_pointees ?? 0) }));
  });

  app.get('/mes-pointages', { preHandler: requirePermission('temps.saisir') }, async (req) => {
    const me = mustUser(req);
    const { db } = mustTenant(req);
    const { du, au } = Periode.parse(req.query);
    return db
      .selectFrom('pointages as x')
      .innerJoin('taches as t', 't.id', 'x.tache_id')
      .innerJoin('projets as p', 'p.id', 'x.projet_id')
      .select(['x.id', 'x.date', 'x.heures', 'x.commentaire', 't.nom as tache', 'p.code as projet_code', 'p.nom as projet'])
      .where('x.utilisateur_id', '=', me.id)
      .where('x.date', '>=', du)
      .where('x.date', '<=', au)
      .orderBy('x.date', 'desc')
      .orderBy('x.id', 'desc')
      .execute();
  });

  app.post('/pointages', { preHandler: requirePermission('temps.saisir') }, async (req, reply) => {
    const me = mustUser(req);
    const { db } = mustTenant(req);
    const body = PointageBody.parse(req.body);
    const tache = await db
      .selectFrom('taches as t')
      .innerJoin('affectations as a', (j) => j.onRef('a.tache_id', '=', 't.id').on('a.utilisateur_id', '=', me.id))
      .select(['t.id', 't.projet_id'])
      .where('t.id', '=', body.tache_id)
      .executeTakeFirst();
    if (!tache) throw new HttpError(403, "Vous n'êtes pas affecté à cette tâche.");

    const jour = await db
      .selectFrom('pointages')
      .select(sql<number>`COALESCE(SUM(heures), 0)`.as('total'))
      .where('utilisateur_id', '=', me.id)
      .where('date', '=', body.date)
      .executeTakeFirstOrThrow();
    if (Number(jour.total) + body.heures > 24) throw new HttpError(400, 'Plus de 24 heures pointées sur cette journée.');

    const r = await db
      .insertInto('pointages')
      .values({
        utilisateur_id: me.id,
        tache_id: tache.id,
        projet_id: tache.projet_id,
        date: body.date,
        heures: body.heures,
        commentaire: body.commentaire || null,
      })
      .executeTakeFirstOrThrow();
    reply.status(201);
    return { id: Number(r.insertId) };
  });

  app.delete('/pointages/:id', { preHandler: requirePermission('temps.saisir') }, async (req) => {
    const me = mustUser(req);
    const { db } = mustTenant(req);
    const id = z.coerce.number().int().positive().parse((req.params as { id: string }).id);
    const r = await db.deleteFrom('pointages').where('id', '=', id).where('utilisateur_id', '=', me.id).executeTakeFirst();
    if (!Number(r.numDeletedRows)) throw new HttpError(404, 'Pointage introuvable parmi les vôtres.');
    return { ok: true };
  });

  app.get('/pointages', { preHandler: requirePermission('temps.voir_equipe') }, async (req) => {
    const { db } = mustTenant(req);
    const q = PeriodeEquipe.parse(req.query);
    let query = db
      .selectFrom('pointages as x')
      .innerJoin('taches as t', 't.id', 'x.tache_id')
      .innerJoin('projets as p', 'p.id', 'x.projet_id')
      .leftJoin('types_activite as ta', 'ta.id', 't.type_activite_id')
      .select(['x.id', 'x.date', 'x.heures', 'x.utilisateur_id', 't.nom as tache', 'ta.nom as activite', 'p.code as projet_code', 'p.nom as projet'])
      .where('x.date', '>=', q.du)
      .where('x.date', '<=', q.au);
    if (q.utilisateur_id) query = query.where('x.utilisateur_id', '=', q.utilisateur_id);
    if (q.projet_id) query = query.where('x.projet_id', '=', q.projet_id);
    const rows = await query.orderBy('x.date', 'desc').limit(5000).execute();

    // Les noms viennent de la base groupe (les utilisateurs sont communs aux filiales).
    const ids = [...new Set(rows.map((r) => r.utilisateur_id))];
    const users = ids.length ? await dbs.group.selectFrom('utilisateurs').select(['id', 'prenom', 'nom']).where('id', 'in', ids).execute() : [];
    const name = new Map(users.map((u) => [u.id, `${u.prenom} ${u.nom}`]));
    return rows.map((r) => ({ ...r, utilisateur: name.get(r.utilisateur_id) ?? `#${r.utilisateur_id}` }));
  });
};
