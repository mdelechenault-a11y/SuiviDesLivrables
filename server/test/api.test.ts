import { afterAll, beforeAll, describe, expect, it } from 'vitest';
import { sql } from 'kysely';
import { startHarness, type Harness } from './helpers.js';
import type { Authenticator } from '../src/auth/directory.js';

let h: Harness;
let adminCookie: string;
let filialeA: { id: number; code: string };
let filialeB: { id: number; code: string };
let tacheId: number;
const ids: Record<string, number> = {};

async function api(method: 'GET' | 'POST' | 'PATCH' | 'PUT' | 'DELETE', url: string, cookie?: string, payload?: unknown) {
  const res = await h.app.inject({ method, url, payload: payload as object, headers: cookie ? { cookie } : {} });
  return { status: res.statusCode, body: res.body ? JSON.parse(res.body) : null };
}

beforeAll(async () => {
  h = await startHarness();
  ids.admin = await h.user('admin', 'Admin');
  adminCookie = await h.login('admin');

  // Création de deux filiales par l'API : chacune reçoit sa propre base.
  const a = await api('POST', '/api/admin/filiales', adminCookie, { code: 'nord', nom: 'Filiale Nord' });
  const b = await api('POST', '/api/admin/filiales', adminCookie, { code: 'SUD', nom: 'Filiale Sud' });
  expect(a.status).toBe(201);
  expect(b.status).toBe(201);
  filialeA = { id: a.body.id, code: a.body.code };
  filialeB = { id: b.body.id, code: b.body.code };

  ids.salarie = await h.user('salarie', 'Utilisateur', [filialeA.id]);
  ids.collegue = await h.user('collegue', 'Utilisateur', [filialeA.id]);
  ids.manager = await h.user('manager', 'Manager', [filialeA.id]);

  // Un projet et une tâche dans la base de la filiale Nord.
  const db = h.dbs.tenant('sdl_test_f_nord');
  const c = await db.insertInto('clients').values({ nom: 'Client' }).executeTakeFirstOrThrow();
  const p = await db.insertInto('projets').values({ code: 'P1', nom: 'Projet', client_id: Number(c.insertId), chef_de_projet_id: null, date_debut: '2026-01-05', statut: 'En cours' }).executeTakeFirstOrThrow();
  const t = await db.insertInto('taches').values({ projet_id: Number(p.insertId), nom: 'Réalisation', type_activite_id: null, parente_id: null, date_debut: null, date_fin: null }).executeTakeFirstOrThrow();
  tacheId = Number(t.insertId);
  for (const who of ['salarie', 'collegue']) await db.insertInto('affectations').values({ tache_id: tacheId, utilisateur_id: ids[who]!, heures_allouees: 40 }).execute();
});

afterAll(async () => {
  await h?.close();
});

describe('connexion', () => {
  it('refuse un mauvais mot de passe sans dire si le compte existe', async () => {
    const r1 = await api('POST', '/api/auth/login', undefined, { identifiant: 'salarie', motDePasse: 'faux-faux-faux' });
    const r2 = await api('POST', '/api/auth/login', undefined, { identifiant: 'inconnu', motDePasse: 'faux-faux-faux' });
    expect(r1.status).toBe(401);
    expect(r2.body.erreur).toBe(r1.body.erreur);
  });

  it('accepte un identifiant saisi avec le domaine Windows', async () => {
    const r = await api('POST', '/api/auth/login', undefined, { identifiant: 'GROUPE\\salarie', motDePasse: 'motdepasse-123' });
    expect(r.status).toBe(200);
    expect(r.body.utilisateur.identifiant).toBe('salarie');
  });

  it("exige une session pour toutes les routes de l'API", async () => {
    expect((await api('GET', '/api/auth/me')).status).toBe(401);
    expect((await api('GET', '/api/admin/utilisateurs')).status).toBe(401);
    expect((await api('GET', '/api/auth/me', 'sdl_session=jeton-falsifie')).status).toBe(401);
  });

  it('refuse un compte désactivé, même avec une session encore valide', async () => {
    const id = await h.user('parti', 'Utilisateur', [filialeA.id]);
    const cookie = await h.login('parti');
    expect((await api('PATCH', `/api/admin/utilisateurs/${id}`, adminCookie, { actif: false })).status).toBe(200);
    expect((await api('GET', '/api/auth/me', cookie)).status).toBe(401);
  });
});

describe('filiales', () => {
  it('crée une base SQL par filiale', async () => {
    const r = await sql<{ n: number }>`SELECT COUNT(*) AS n FROM information_schema.tables WHERE table_schema = 'sdl_test_f_sud' AND table_name = 'pointages'`.execute(h.dbs.group);
    expect(Number(r.rows[0]!.n)).toBe(1);
  });

  it("refuse l'accès à une filiale non attribuée", async () => {
    const cookie = await h.login('salarie');
    expect((await api('GET', `/api/f/${filialeB.code}/mes-taches`, cookie)).status).toBe(403);
    expect((await api('GET', `/api/f/${filialeA.code}/mes-taches`, cookie)).status).toBe(200);
  });

  it("ne liste que les filiales de l'utilisateur", async () => {
    const me = await api('GET', '/api/auth/me', await h.login('salarie'));
    expect(me.body.utilisateur.filiales.map((f: { code: string }) => f.code)).toEqual(['NORD']);
  });
});

describe('heures', () => {
  it('permet à chacun de pointer sur ses tâches et de voir ses heures', async () => {
    const cookie = await h.login('salarie');
    const post = await api('POST', `/api/f/NORD/pointages`, cookie, { tache_id: tacheId, date: '2026-03-02', heures: 7.5 });
    expect(post.status).toBe(201);
    const mine = await api('GET', `/api/f/NORD/mes-pointages?du=2026-03-01&au=2026-03-31`, cookie);
    expect(mine.body).toHaveLength(1);
    expect(mine.body[0].heures).toBe(7.5);
    const taches = await api('GET', `/api/f/NORD/mes-taches`, cookie);
    expect(taches.body[0].heures_pointees).toBe(7.5);
  });

  it("refuse de pointer sur une tâche où l'on n'est pas affecté", async () => {
    const cookie = await h.login('manager');
    const r = await api('POST', `/api/f/NORD/pointages`, cookie, { tache_id: tacheId, date: '2026-03-02', heures: 2 });
    expect(r.status).toBe(403);
  });

  it('refuse plus de 24 heures sur une journée', async () => {
    const cookie = await h.login('salarie');
    const r = await api('POST', `/api/f/NORD/pointages`, cookie, { tache_id: tacheId, date: '2026-03-02', heures: 17 });
    expect(r.status).toBe(400);
  });

  it("n'autorise pas un salarié à voir ni supprimer les heures d'un collègue", async () => {
    const collegue = await h.login('collegue');
    const created = await api('POST', `/api/f/NORD/pointages`, collegue, { tache_id: tacheId, date: '2026-03-03', heures: 4 });
    const salarie = await h.login('salarie');
    expect((await api('GET', `/api/f/NORD/pointages?du=2026-03-01&au=2026-03-31`, salarie)).status).toBe(403);
    expect((await api('DELETE', `/api/f/NORD/pointages/${created.body.id}`, salarie)).status).toBe(404);
  });

  it("permet au manager de voir les heures de l'équipe, avec les noms", async () => {
    const r = await api('GET', `/api/f/NORD/pointages?du=2026-03-01&au=2026-03-31`, await h.login('manager'));
    expect(r.status).toBe(200);
    expect(r.body.map((x: { utilisateur: string }) => x.utilisateur).sort()).toEqual(['collegue Test', 'salarie Test']);
  });
});

describe('administration', () => {
  it("réserve la gestion des utilisateurs à l'administration", async () => {
    const r = await api('POST', '/api/admin/utilisateurs', await h.login('manager'), { identifiant: 'x', prenom: 'X', nom: 'X', role: 'Admin', filiales: [] });
    expect(r.status).toBe(403);
  });

  it('crée un utilisateur rattaché à une filiale', async () => {
    const r = await api('POST', '/api/admin/utilisateurs', adminCookie, {
      identifiant: 'jdupont', prenom: 'Jeanne', nom: 'Dupont', email: 'jeanne.dupont@exemple.fr', role: 'Chef de projet', filiales: [filialeB.id], motDePasse: 'un-mot-de-passe-long',
    });
    expect(r.status).toBe(201);
    const me = await api('GET', '/api/auth/me', await h.login('jdupont', 'un-mot-de-passe-long'));
    expect(me.body.utilisateur.filiales.map((f: { code: string }) => f.code)).toEqual(['SUD']);
    expect(me.body.utilisateur.permissions).toContain('projets.gerer');
  });

  it("empêche de retirer à l'administrateur le droit de gérer les droits", async () => {
    const r = await api('PUT', '/api/admin/droits', adminCookie, { matrice: { Admin: [], Manager: ['temps.saisir'] } });
    expect(r.status).toBe(200);
    const d = await api('GET', '/api/admin/droits', adminCookie);
    expect(d.body.matrice.Admin).toContain('admin.droits');
    expect(d.body.matrice.Manager).toEqual(['temps.saisir']);
    // Le changement s'applique tout de suite : le manager ne voit plus les heures de l'équipe.
    expect((await api('GET', `/api/f/NORD/pointages?du=2026-03-01&au=2026-03-31`, await h.login('manager'))).status).toBe(403);
  });

  it("empêche un administrateur de se désactiver lui-même", async () => {
    expect((await api('PATCH', `/api/admin/utilisateurs/${ids.admin}`, adminCookie, { actif: false })).status).toBe(400);
  });
});

describe('connexion Active Directory', () => {
  it("met à jour nom, prénom et e-mail depuis l'annuaire et refuse un compte non ouvert dans l'appli", async () => {
    const fakeAd: Authenticator = {
      mode: 'ldap',
      async verify(identifiant, motDePasse) {
        return motDePasse === 'mot-de-passe-ad' ? { identifiant, prenom: 'Lucie', nom: 'Annuaire', email: 'lucie@exemple.fr' } : null;
      },
    };
    const { buildApp } = await import('../src/app.js');
    const app = await buildApp({ cfg: h.cfg, dbs: h.dbs, authenticator: fakeAd });
    const ok = await app.inject({ method: 'POST', url: '/api/auth/login', payload: { identifiant: 'salarie', motDePasse: 'mot-de-passe-ad' } });
    expect(ok.statusCode).toBe(200);
    expect(JSON.parse(ok.body).utilisateur).toMatchObject({ prenom: 'Lucie', nom: 'Annuaire', email: 'lucie@exemple.fr' });
    const absent = await app.inject({ method: 'POST', url: '/api/auth/login', payload: { identifiant: 'nouveau', motDePasse: 'mot-de-passe-ad' } });
    expect(absent.statusCode).toBe(403);
    await app.close();
  });
});

describe('protection contre les essais de mot de passe', () => {
  it('bloque une adresse après trop de tentatives', async () => {
    const { buildApp } = await import('../src/app.js');
    const app = await buildApp({ cfg: { ...h.cfg, LOGIN_RATE_LIMIT: 3 }, dbs: h.dbs, authenticator: (await import('../src/auth/directory.js')).localAuthenticator() });
    const codes: number[] = [];
    for (let i = 0; i < 4; i++) {
      const r = await app.inject({ method: 'POST', url: '/api/auth/login', payload: { identifiant: 'salarie', motDePasse: 'faux-faux-faux' } });
      codes.push(r.statusCode);
    }
    expect(codes).toEqual([401, 401, 401, 429]);
    await app.close();
  });
});
