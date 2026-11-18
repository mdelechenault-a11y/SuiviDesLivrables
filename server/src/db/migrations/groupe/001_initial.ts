import { sql, type Kysely } from 'kysely';
import { DEFAULT_ROLE_PERMISSIONS, ROLES } from '../../../security/permissions.js';

export async function up(db: Kysely<any>): Promise<void> {
  await db.schema
    .createTable('filiales')
    .addColumn('id', 'integer', (c) => c.primaryKey().autoIncrement())
    .addColumn('code', 'varchar(20)', (c) => c.notNull().unique())
    .addColumn('nom', 'varchar(255)', (c) => c.notNull())
    .addColumn('db_name', 'varchar(64)', (c) => c.notNull().unique())
    .addColumn('objectif_point_mort', sql`decimal(14,2)`, (c) => c.notNull().defaultTo(0))
    .addColumn('objectif_1', sql`decimal(14,2)`, (c) => c.notNull().defaultTo(0))
    .addColumn('objectif_2', sql`decimal(14,2)`, (c) => c.notNull().defaultTo(0))
    .addColumn('actif', 'boolean', (c) => c.notNull().defaultTo(true))
    .addColumn('cree_le', 'datetime', (c) => c.notNull().defaultTo(sql`CURRENT_TIMESTAMP`))
    .execute();

  await db.schema
    .createTable('utilisateurs')
    .addColumn('id', 'integer', (c) => c.primaryKey().autoIncrement())
    .addColumn('identifiant', 'varchar(100)', (c) => c.notNull().unique())
    .addColumn('prenom', 'varchar(100)', (c) => c.notNull())
    .addColumn('nom', 'varchar(100)', (c) => c.notNull())
    .addColumn('email', 'varchar(255)')
    .addColumn('role', 'varchar(30)', (c) => c.notNull())
    .addColumn('mot_de_passe_hash', 'varchar(100)')
    .addColumn('actif', 'boolean', (c) => c.notNull().defaultTo(true))
    .addColumn('derniere_connexion', 'datetime')
    .addColumn('cree_le', 'datetime', (c) => c.notNull().defaultTo(sql`CURRENT_TIMESTAMP`))
    .execute();

  await db.schema
    .createTable('utilisateur_filiales')
    .addColumn('utilisateur_id', 'integer', (c) => c.notNull().references('utilisateurs.id').onDelete('cascade'))
    .addColumn('filiale_id', 'integer', (c) => c.notNull().references('filiales.id').onDelete('cascade'))
    .addPrimaryKeyConstraint('pk_utilisateur_filiales', ['utilisateur_id', 'filiale_id'])
    .execute();

  await db.schema
    .createTable('role_permissions')
    .addColumn('role', 'varchar(30)', (c) => c.notNull())
    .addColumn('permission', 'varchar(60)', (c) => c.notNull())
    .addPrimaryKeyConstraint('pk_role_permissions', ['role', 'permission'])
    .execute();

  const rows = ROLES.flatMap((role) => DEFAULT_ROLE_PERMISSIONS[role].map((permission) => ({ role, permission })));
  await db.insertInto('role_permissions').values(rows).execute();
}

export async function down(db: Kysely<any>): Promise<void> {
  for (const t of ['role_permissions', 'utilisateur_filiales', 'utilisateurs', 'filiales']) {
    await db.schema.dropTable(t).ifExists().execute();
  }
}
