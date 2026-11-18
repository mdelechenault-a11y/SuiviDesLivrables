/**
 * Données d'exemple pour essayer l'appli : une filiale DEMO, quelques comptes
 * (mode local uniquement), un client, un projet en cours, ses tâches et affectations.
 * Usage : npm run seed:demo
 */
import { loadConfig } from '../config.js';
import { Databases, tenantDbName } from '../db/connections.js';
import { hashPassword } from '../auth/directory.js';

const cfg = loadConfig();
const dbs = await Databases.open(cfg);
const g = dbs.group;

let filiale = await g.selectFrom('filiales').selectAll().where('code', '=', 'DEMO').executeTakeFirst();
if (!filiale) {
  const db_name = tenantDbName(cfg, 'DEMO');
  await dbs.createTenantDatabase(db_name);
  await g.insertInto('filiales').values({ code: 'DEMO', nom: 'Filiale de démonstration', db_name, objectif_point_mort: 300000, objectif_1: 380000, objectif_2: 450000 }).execute();
  filiale = await g.selectFrom('filiales').selectAll().where('code', '=', 'DEMO').executeTakeFirstOrThrow();
}

const comptes = [
  { identifiant: 'demo.directeur', prenom: 'Diane', nom: 'Directrice', role: 'Directeur' },
  { identifiant: 'demo.manager', prenom: 'Marc', nom: 'Manager', role: 'Manager' },
  { identifiant: 'demo.cdp', prenom: 'Claire', nom: 'Cheffe de projet', role: 'Chef de projet' },
  { identifiant: 'demo.salarie', prenom: 'Sami', nom: 'Salarié', role: 'Utilisateur' },
];
const ids: Record<string, number> = {};
for (const c of comptes) {
  let u = await g.selectFrom('utilisateurs').select('id').where('identifiant', '=', c.identifiant).executeTakeFirst();
  if (!u) {
    const r = await g
      .insertInto('utilisateurs')
      .values({ ...c, email: null, mot_de_passe_hash: cfg.AUTH_MODE === 'local' ? await hashPassword('demo-demo-demo') : null })
      .executeTakeFirstOrThrow();
    u = { id: Number(r.insertId) };
    await g.insertInto('utilisateur_filiales').values({ utilisateur_id: u.id, filiale_id: filiale.id }).execute();
  }
  ids[c.identifiant] = u.id;
}

const db = dbs.tenant(filiale.db_name);
const has = await db.selectFrom('projets').select('id').where('code', '=', 'DEMO-01').executeTakeFirst();
if (!has) {
  const client = await db.insertInto('clients').values({ nom: 'Client exemple', code: 'CEX' }).executeTakeFirstOrThrow();
  const today = new Date();
  const iso = (d: Date) => d.toISOString().slice(0, 10);
  const add = (n: number) => iso(new Date(today.getTime() + n * 864e5));
  const p = await db
    .insertInto('projets')
    .values({ code: 'DEMO-01', nom: 'Projet de démonstration', client_id: Number(client.insertId), chef_de_projet_id: ids['demo.cdp']!, date_debut: add(-30), statut: 'En cours' })
    .executeTakeFirstOrThrow();
  const projet_id = Number(p.insertId);
  const types = await db.selectFrom('types_activite').selectAll().execute();
  const type = (nom: string) => types.find((t) => t.nom === nom)?.id ?? null;
  const taches: Array<[string, string, number, number, number]> = [
    ['Cadrage', 'Gestion de projet', -30, 10, 30],
    ['Conception', 'Études', -19, 20, 80],
    ['Réalisation', 'Développement', 2, 40, 240],
  ];
  let parente_id: number | null = null;
  for (const [i, [nom, t, debut, duree, heures]] of taches.entries()) {
    const r = await db
      .insertInto('taches')
      .values({ projet_id, nom, type_activite_id: type(t), parente_id, position: i, duree_jours: duree, heures_prevues: heures, date_debut: add(debut), date_fin: add(debut + duree - 1) })
      .executeTakeFirstOrThrow();
    parente_id = Number(r.insertId);
    for (const who of ['demo.cdp', 'demo.salarie']) {
      await db.insertInto('affectations').values({ tache_id: parente_id, utilisateur_id: ids[who]!, heures_allouees: heures / 2 }).execute();
    }
  }
  await db.insertInto('livrables').values([
    { projet_id, nom: 'Spécifications validées', montant: 12000, date_prevue: add(-5) },
    { projet_id, nom: 'Mise en production', montant: 36000, date_prevue: add(45) },
  ]).execute();
}

console.info('Données de démonstration prêtes. Comptes (mode local) : demo.directeur, demo.manager, demo.cdp, demo.salarie — mot de passe : demo-demo-demo');
await dbs.close();
