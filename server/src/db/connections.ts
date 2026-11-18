import { createPool } from 'mysql2';
import { CompiledQuery, Kysely, MysqlDialect, sql } from 'kysely';
import { Migrator, type Migration, type MigrationProvider } from 'kysely/migration';
import type { Config } from '../config.js';
import type { GroupDatabase, TenantDatabase } from './types.js';
import * as groupe001 from './migrations/groupe/001_initial.js';
import * as filiale001 from './migrations/filiale/001_initial.js';

/** Migrations listées dans le code : rien à copier à côté des fichiers compilés. */
const GROUP_MIGRATIONS: Record<string, Migration> = { '001_initial': groupe001 };
const TENANT_MIGRATIONS: Record<string, Migration> = { '001_initial': filiale001 };

const provider = (m: Record<string, Migration>): MigrationProvider => ({ getMigrations: async () => m });

const SAFE_IDENT = /^[a-z0-9_]{1,64}$/;

function dialect(cfg: Config, database?: string) {
  return new MysqlDialect({
    pool: createPool({
      host: cfg.DB_HOST,
      port: cfg.DB_PORT,
      user: cfg.DB_USER,
      password: cfg.DB_PASSWORD,
      database,
      connectionLimit: 10,
      // Dates SQL renvoyées telles quelles ('AAAA-MM-JJ') : pas de décalage de fuseau.
      dateStrings: true,
      decimalNumbers: true,
      charset: 'utf8mb4',
      timezone: 'Z',
    }),
    // Horodatages en UTC, quel que soit le fuseau du serveur MySQL.
    onCreateConnection: async (conn) => {
      await conn.executeQuery(CompiledQuery.raw("SET time_zone = '+00:00'"));
    },
  });
}

async function runMigrations(db: Kysely<any>, migrations: Record<string, Migration>, label: string) {
  const migrator = new Migrator({ db, provider: provider(migrations) });
  const { error, results } = await migrator.migrateToLatest();
  for (const r of results ?? []) {
    if (r.status === 'Error') console.error(`[migrations ${label}] échec : ${r.migrationName}`);
  }
  if (error) throw error instanceof Error ? error : new Error(String(error));
}

async function ensureDatabase(cfg: Config, name: string) {
  if (!SAFE_IDENT.test(name)) throw new Error(`Nom de base invalide : ${name}`);
  const admin = new Kysely<any>({ dialect: dialect(cfg) });
  try {
    await sql`CREATE DATABASE IF NOT EXISTS ${sql.id(name)} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci`.execute(admin);
  } finally {
    await admin.destroy();
  }
}

export function tenantDbName(cfg: Config, code: string): string {
  return `${cfg.DB_TENANT_PREFIX}${code.toLowerCase()}`;
}

/**
 * Accès aux bases : une base « groupe » et une base par filiale.
 * Les connexions aux bases de filiale sont ouvertes à la demande puis gardées.
 */
export class Databases {
  readonly group: Kysely<GroupDatabase>;
  private tenants = new Map<string, Kysely<TenantDatabase>>();

  private constructor(readonly cfg: Config) {
    this.group = new Kysely<GroupDatabase>({ dialect: dialect(cfg, cfg.DB_GROUP_NAME) });
  }

  /** Crée la base groupe si besoin, applique ses migrations et celles de chaque filiale. */
  static async open(cfg: Config): Promise<Databases> {
    await ensureDatabase(cfg, cfg.DB_GROUP_NAME);
    const dbs = new Databases(cfg);
    await runMigrations(dbs.group, GROUP_MIGRATIONS, 'groupe');
    const filiales = await dbs.group.selectFrom('filiales').select('db_name').execute();
    for (const f of filiales) await runMigrations(dbs.tenant(f.db_name), TENANT_MIGRATIONS, f.db_name);
    return dbs;
  }

  /** Connexion à la base d'une filiale (nom de base issu de la table filiales). */
  tenant(dbName: string): Kysely<TenantDatabase> {
    if (!SAFE_IDENT.test(dbName)) throw new Error(`Nom de base invalide : ${dbName}`);
    let db = this.tenants.get(dbName);
    if (!db) {
      db = new Kysely<TenantDatabase>({ dialect: dialect(this.cfg, dbName) });
      this.tenants.set(dbName, db);
    }
    return db;
  }

  /** Crée et initialise la base d'une nouvelle filiale. */
  async createTenantDatabase(dbName: string): Promise<void> {
    await ensureDatabase(this.cfg, dbName);
    await runMigrations(this.tenant(dbName), TENANT_MIGRATIONS, dbName);
  }

  async close(): Promise<void> {
    await Promise.all([this.group.destroy(), ...[...this.tenants.values()].map((d) => d.destroy())]);
    this.tenants.clear();
  }
}
