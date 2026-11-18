import { createConnection } from 'mysql2/promise';
import type { FastifyInstance } from 'fastify';
import { loadConfig, type Config } from '../src/config.js';
import { Databases } from '../src/db/connections.js';
import { localAuthenticator, hashPassword, type Authenticator } from '../src/auth/directory.js';
import { buildApp } from '../src/app.js';

/**
 * Les tests d'intégration utilisent un vrai serveur MariaDB/MySQL.
 * Variables : TEST_DB_HOST, TEST_DB_PORT, TEST_DB_USER, TEST_DB_PASSWORD.
 * Ils créent et suppriment des bases préfixées « sdl_test_ ».
 */
export function testConfig(): Config {
  return loadConfig({
    NODE_ENV: 'test',
    DB_HOST: process.env.TEST_DB_HOST ?? '127.0.0.1',
    DB_PORT: process.env.TEST_DB_PORT ?? '3306',
    DB_USER: process.env.TEST_DB_USER ?? 'sdl',
    DB_PASSWORD: process.env.TEST_DB_PASSWORD ?? 'sdl-dev',
    DB_GROUP_NAME: 'sdl_test_groupe',
    DB_TENANT_PREFIX: 'sdl_test_f_',
    SESSION_SECRET: 'secret-de-test-secret-de-test-0123456789',
    AUTH_MODE: 'local',
    LOGIN_RATE_LIMIT: '1000',
  });
}

export async function dropTestDatabases(cfg: Config) {
  const c = await createConnection({ host: cfg.DB_HOST, port: cfg.DB_PORT, user: cfg.DB_USER, password: cfg.DB_PASSWORD });
  const [rows] = await c.query("SHOW DATABASES LIKE 'sdl\\_test\\_%'");
  for (const r of rows as Array<Record<string, string>>) {
    const name = Object.values(r)[0]!;
    await c.query(`DROP DATABASE \`${name}\``);
  }
  await c.end();
}

export interface Harness {
  app: FastifyInstance;
  dbs: Databases;
  cfg: Config;
  /** Crée un utilisateur (mot de passe « motdepasse-123 ») et renvoie son id. */
  user(identifiant: string, role: string, filialeIds?: number[]): Promise<number>;
  /** Se connecte et renvoie l'en-tête Cookie de session. */
  login(identifiant: string, motDePasse?: string): Promise<string>;
  close(): Promise<void>;
}

export async function startHarness(authenticator: Authenticator = localAuthenticator()): Promise<Harness> {
  const cfg = testConfig();
  await dropTestDatabases(cfg);
  const dbs = await Databases.open(cfg);
  const app = await buildApp({ cfg, dbs, authenticator });
  const hash = await hashPassword('motdepasse-123');
  return {
    app,
    dbs,
    cfg,
    async user(identifiant, role, filialeIds = []) {
      const r = await dbs.group
        .insertInto('utilisateurs')
        .values({ identifiant, prenom: identifiant, nom: 'Test', email: null, role, mot_de_passe_hash: hash })
        .executeTakeFirstOrThrow();
      const id = Number(r.insertId);
      for (const filiale_id of filialeIds) await dbs.group.insertInto('utilisateur_filiales').values({ utilisateur_id: id, filiale_id }).execute();
      return id;
    },
    async login(identifiant, motDePasse = 'motdepasse-123') {
      const res = await app.inject({ method: 'POST', url: '/api/auth/login', payload: { identifiant, motDePasse } });
      if (res.statusCode !== 200) throw new Error(`Connexion refusée pour ${identifiant} : ${res.body}`);
      const c = res.cookies.find((x) => x.name === 'sdl_session');
      return `sdl_session=${c!.value}`;
    },
    async close() {
      await app.close();
      await dbs.close();
    },
  };
}
