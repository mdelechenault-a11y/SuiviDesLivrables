import type { FastifyPluginAsync } from 'fastify';
import { z } from 'zod';
import type { AppDeps } from '../../app.js';
import { tenantDbName } from '../../db/connections.js';
import { hashPassword } from '../../auth/directory.js';
import { HttpError, mustUser, requirePermission } from '../../security/context.js';
import { ALL_PERMISSIONS, isLocked, isPermission, LOCKED, PERMISSIONS, ROLES, type Role } from '../../security/permissions.js';

const Id = z.coerce.number().int().positive();
const Montant = z.number().min(0).max(1e12);

const FilialeCreate = z.object({
  code: z.string().trim().regex(/^[A-Za-z0-9_]{2,20}$/, 'Code de 2 à 20 caractères : lettres, chiffres ou _'),
  nom: z.string().trim().min(1).max(255),
});
const FilialeUpdate = z.object({
  nom: z.string().trim().min(1).max(255).optional(),
  objectif_point_mort: Montant.optional(),
  objectif_1: Montant.optional(),
  objectif_2: Montant.optional(),
  actif: z.boolean().optional(),
});

const UserBase = {
  prenom: z.string().trim().min(1).max(100),
  nom: z.string().trim().min(1).max(100),
  email: z.email().max(255).nullable().optional(),
  role: z.enum(ROLES),
  filiales: z.array(z.number().int().positive()).max(100),
  motDePasse: z.string().min(10, 'Mot de passe de 10 caractères minimum').max(256).optional(),
};
const UserCreate = z.object({ identifiant: z.string().trim().regex(/^[A-Za-z0-9._-]{2,100}$/, 'Identifiant Windows sans domaine, ex. jdupont'), ...UserBase });
const UserUpdate = z.object({ ...UserBase, actif: z.boolean() }).partial();

const DroitsBody = z.object({ matrice: z.record(z.string(), z.array(z.string())) });

export const adminRoutes: FastifyPluginAsync<AppDeps> = async (app, { dbs, authenticator }) => {
  const g = dbs.group;

  /* ---------- Filiales ---------- */

  app.get('/filiales', { preHandler: requirePermission('admin.filiales', 'admin.utilisateurs') }, async () => {
    const rows = await g.selectFrom('filiales').selectAll().orderBy('nom').execute();
    return rows.map((f) => ({ ...f, actif: !!f.actif }));
  });

  app.post('/filiales', { preHandler: requirePermission('admin.filiales') }, async (req, reply) => {
    const body = FilialeCreate.parse(req.body);
    const code = body.code.toUpperCase();
    const exists = await g.selectFrom('filiales').select('id').where('code', '=', code).executeTakeFirst();
    if (exists) throw new HttpError(409, `Une filiale porte déjà le code ${code}.`);
    const db_name = tenantDbName(dbs.cfg, code);
    // La base est créée avant la ligne : si la création échoue, rien n'est enregistré.
    await dbs.createTenantDatabase(db_name);
    const res = await g.insertInto('filiales').values({ code, nom: body.nom, db_name }).executeTakeFirstOrThrow();
    reply.status(201);
    return { id: Number(res.insertId), code, nom: body.nom, db_name };
  });

  app.patch('/filiales/:id', { preHandler: requirePermission('admin.filiales') }, async (req) => {
    const id = Id.parse((req.params as { id: string }).id);
    const body = FilialeUpdate.parse(req.body);
    const { actif, ...rest } = body;
    const set = { ...rest, ...(actif === undefined ? {} : { actif: actif ? 1 : 0 }) };
    if (Object.keys(set).length) {
      const r = await g.updateTable('filiales').set(set).where('id', '=', id).executeTakeFirst();
      if (!Number(r.numUpdatedRows)) throw new HttpError(404, 'Filiale introuvable.');
    }
    return { ok: true };
  });

  /* ---------- Utilisateurs ---------- */

  app.get('/utilisateurs', { preHandler: requirePermission('admin.utilisateurs') }, async () => {
    const users = await g
      .selectFrom('utilisateurs')
      .select(['id', 'identifiant', 'prenom', 'nom', 'email', 'role', 'actif', 'derniere_connexion'])
      .orderBy('nom')
      .orderBy('prenom')
      .execute();
    const links = await g.selectFrom('utilisateur_filiales').selectAll().execute();
    return users.map((u) => ({
      ...u,
      actif: !!u.actif,
      filiales: links.filter((l) => l.utilisateur_id === u.id).map((l) => l.filiale_id),
    }));
  });

  async function checkFiliales(ids: number[]) {
    if (!ids.length) return;
    const found = await g.selectFrom('filiales').select('id').where('id', 'in', ids).execute();
    if (found.length !== new Set(ids).size) throw new HttpError(400, 'Filiale inconnue dans la liste.');
  }

  app.post('/utilisateurs', { preHandler: requirePermission('admin.utilisateurs') }, async (req, reply) => {
    const body = UserCreate.parse(req.body);
    if (body.role !== 'Admin' && !body.filiales.length) throw new HttpError(400, 'Choisissez au moins une filiale.');
    await checkFiliales(body.filiales);
    if (authenticator.mode === 'local' && !body.motDePasse) throw new HttpError(400, 'Mot de passe requis en mode local.');
    const dup = await g.selectFrom('utilisateurs').select('id').where('identifiant', '=', body.identifiant).executeTakeFirst();
    if (dup) throw new HttpError(409, `L'identifiant ${body.identifiant} existe déjà.`);

    const id = await g.transaction().execute(async (trx) => {
      const r = await trx
        .insertInto('utilisateurs')
        .values({
          identifiant: body.identifiant,
          prenom: body.prenom,
          nom: body.nom,
          email: body.email ?? null,
          role: body.role,
          mot_de_passe_hash: authenticator.mode === 'local' && body.motDePasse ? await hashPassword(body.motDePasse) : null,
        })
        .executeTakeFirstOrThrow();
      const uid = Number(r.insertId);
      if (body.filiales.length) {
        await trx.insertInto('utilisateur_filiales').values([...new Set(body.filiales)].map((filiale_id) => ({ utilisateur_id: uid, filiale_id }))).execute();
      }
      return uid;
    });
    reply.status(201);
    return { id };
  });

  app.patch('/utilisateurs/:id', { preHandler: requirePermission('admin.utilisateurs') }, async (req) => {
    const me = mustUser(req);
    const id = Id.parse((req.params as { id: string }).id);
    const body = UserUpdate.parse(req.body);
    if (id === me.id && body.actif === false) throw new HttpError(400, 'Vous ne pouvez pas désactiver votre propre compte.');
    if (id === me.id && body.role && body.role !== me.role) throw new HttpError(400, 'Vous ne pouvez pas changer votre propre rôle.');
    if (body.filiales) await checkFiliales(body.filiales);
    const current = await g.selectFrom('utilisateurs').select('id').where('id', '=', id).executeTakeFirst();
    if (!current) throw new HttpError(404, 'Utilisateur introuvable.');

    await g.transaction().execute(async (trx) => {
      const set: Record<string, unknown> = {};
      for (const k of ['prenom', 'nom', 'email', 'role'] as const) if (body[k] !== undefined) set[k] = body[k];
      if (body.actif !== undefined) set.actif = body.actif ? 1 : 0;
      if (body.motDePasse && authenticator.mode === 'local') set.mot_de_passe_hash = await hashPassword(body.motDePasse);
      if (Object.keys(set).length) await trx.updateTable('utilisateurs').set(set).where('id', '=', id).execute();
      if (body.filiales) {
        await trx.deleteFrom('utilisateur_filiales').where('utilisateur_id', '=', id).execute();
        if (body.filiales.length) {
          await trx.insertInto('utilisateur_filiales').values([...new Set(body.filiales)].map((filiale_id) => ({ utilisateur_id: id, filiale_id }))).execute();
        }
      }
    });
    return { ok: true };
  });

  /* ---------- Droits ---------- */

  app.get('/droits', { preHandler: requirePermission('admin.droits') }, async () => {
    const rows = await g.selectFrom('role_permissions').selectAll().execute();
    const matrice = Object.fromEntries(ROLES.map((r) => [r, rows.filter((x) => x.role === r).map((x) => x.permission).filter(isPermission)]));
    return { roles: ROLES, permissions: PERMISSIONS, matrice, verrouillees: LOCKED };
  });

  app.put('/droits', { preHandler: requirePermission('admin.droits') }, async (req) => {
    const { matrice } = DroitsBody.parse(req.body);
    const rows: Array<{ role: Role; permission: string }> = [];
    for (const role of ROLES) {
      const wanted = new Set((matrice[role] ?? []).filter(isPermission));
      for (const p of ALL_PERMISSIONS) if (isLocked(role, p)) wanted.add(p);
      for (const permission of wanted) rows.push({ role, permission });
    }
    await g.transaction().execute(async (trx) => {
      await trx.deleteFrom('role_permissions').execute();
      await trx.insertInto('role_permissions').values(rows).execute();
    });
    return { ok: true };
  });
};
