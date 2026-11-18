import { sql, type Kysely } from 'kysely';

/**
 * Schéma métier d'une filiale, repris de l'ancienne appli Python
 * (clients, projets, tâches, affectations, pointages, livrables, commentaires, documents).
 * Changements : montants et heures en DECIMAL exact, commentaires signés,
 * utilisateurs référencés par leur identifiant de la base groupe.
 */
export async function up(db: Kysely<any>): Promise<void> {
  const now = sql`CURRENT_TIMESTAMP`;

  await db.schema
    .createTable('clients')
    .addColumn('id', 'integer', (c) => c.primaryKey().autoIncrement())
    .addColumn('nom', 'varchar(255)', (c) => c.notNull().unique())
    .addColumn('code', 'varchar(10)')
    .addColumn('adresse', 'text')
    .addColumn('telephone', 'varchar(50)')
    .addColumn('site_web', 'varchar(255)')
    .addColumn('contact', 'text')
    .addColumn('visible', 'boolean', (c) => c.notNull().defaultTo(true))
    .execute();

  await db.schema
    .createTable('types_activite')
    .addColumn('id', 'integer', (c) => c.primaryKey().autoIncrement())
    .addColumn('nom', 'varchar(100)', (c) => c.notNull().unique())
    .execute();

  await db.schema
    .createTable('projets')
    .addColumn('id', 'integer', (c) => c.primaryKey().autoIncrement())
    .addColumn('code', 'varchar(50)', (c) => c.notNull().unique())
    .addColumn('nom', 'varchar(255)', (c) => c.notNull())
    .addColumn('client_id', 'integer', (c) => c.notNull().references('clients.id'))
    .addColumn('chef_de_projet_id', 'integer')
    .addColumn('date_debut', 'date', (c) => c.notNull())
    .addColumn('statut', 'varchar(20)', (c) => c.notNull().defaultTo('Chiffrage'))
    .addColumn('budget_materiel_prevu', sql`decimal(14,2)`, (c) => c.notNull().defaultTo(0))
    .addColumn('budget_materiel_depense', sql`decimal(14,2)`, (c) => c.notNull().defaultTo(0))
    .addColumn('cree_le', 'datetime', (c) => c.notNull().defaultTo(now))
    .execute();

  await db.schema
    .createTable('taches')
    .addColumn('id', 'integer', (c) => c.primaryKey().autoIncrement())
    .addColumn('projet_id', 'integer', (c) => c.notNull().references('projets.id').onDelete('cascade'))
    .addColumn('nom', 'varchar(255)', (c) => c.notNull())
    .addColumn('type_activite_id', 'integer', (c) => c.references('types_activite.id').onDelete('set null'))
    .addColumn('parente_id', 'integer', (c) => c.references('taches.id').onDelete('set null'))
    .addColumn('position', 'integer', (c) => c.notNull().defaultTo(0))
    .addColumn('duree_jours', 'integer', (c) => c.notNull().defaultTo(1))
    .addColumn('decalage_jours', 'integer', (c) => c.notNull().defaultTo(0))
    .addColumn('heures_prevues', sql`decimal(8,2)`, (c) => c.notNull().defaultTo(0))
    .addColumn('date_debut', 'date')
    .addColumn('date_fin', 'date')
    .addColumn('jalon', 'boolean', (c) => c.notNull().defaultTo(false))
    .execute();
  await db.schema.createIndex('idx_taches_projet').on('taches').column('projet_id').execute();

  await db.schema
    .createTable('affectations')
    .addColumn('id', 'integer', (c) => c.primaryKey().autoIncrement())
    .addColumn('tache_id', 'integer', (c) => c.notNull().references('taches.id').onDelete('cascade'))
    .addColumn('utilisateur_id', 'integer', (c) => c.notNull())
    .addColumn('heures_allouees', sql`decimal(8,2)`, (c) => c.notNull().defaultTo(0))
    .addUniqueConstraint('uq_affectation', ['tache_id', 'utilisateur_id'])
    .execute();
  await db.schema.createIndex('idx_affectations_utilisateur').on('affectations').column('utilisateur_id').execute();

  await db.schema
    .createTable('pointages')
    .addColumn('id', 'integer', (c) => c.primaryKey().autoIncrement())
    .addColumn('utilisateur_id', 'integer', (c) => c.notNull())
    .addColumn('tache_id', 'integer', (c) => c.notNull().references('taches.id'))
    .addColumn('projet_id', 'integer', (c) => c.notNull().references('projets.id'))
    .addColumn('date', 'date', (c) => c.notNull())
    .addColumn('heures', sql`decimal(5,2)`, (c) => c.notNull())
    .addColumn('commentaire', 'varchar(500)')
    .addColumn('cree_le', 'datetime', (c) => c.notNull().defaultTo(now))
    .execute();
  await db.schema.createIndex('idx_pointages_utilisateur_date').on('pointages').columns(['utilisateur_id', 'date']).execute();
  await db.schema.createIndex('idx_pointages_projet').on('pointages').column('projet_id').execute();

  await db.schema
    .createTable('livrables')
    .addColumn('id', 'integer', (c) => c.primaryKey().autoIncrement())
    .addColumn('projet_id', 'integer', (c) => c.notNull().references('projets.id').onDelete('cascade'))
    .addColumn('nom', 'varchar(255)', (c) => c.notNull())
    .addColumn('montant', sql`decimal(14,2)`, (c) => c.notNull())
    .addColumn('date_prevue', 'date', (c) => c.notNull())
    .addColumn('date_initiale', 'date')
    .addColumn('responsabilite_retard', 'varchar(20)')
    .addColumn('facture', 'boolean', (c) => c.notNull().defaultTo(false))
    .execute();
  await db.schema.createIndex('idx_livrables_date').on('livrables').column('date_prevue').execute();

  await db.schema
    .createTable('commentaires_livrables')
    .addColumn('id', 'integer', (c) => c.primaryKey().autoIncrement())
    .addColumn('livrable_id', 'integer', (c) => c.notNull().references('livrables.id').onDelete('cascade'))
    .addColumn('auteur_id', 'integer', (c) => c.notNull())
    .addColumn('contenu', 'text', (c) => c.notNull())
    .addColumn('cree_le', 'datetime', (c) => c.notNull().defaultTo(now))
    .execute();

  await db.schema
    .createTable('documents')
    .addColumn('id', 'integer', (c) => c.primaryKey().autoIncrement())
    .addColumn('objet_type', 'varchar(20)', (c) => c.notNull())
    .addColumn('objet_id', 'integer', (c) => c.notNull())
    .addColumn('nom_fichier', 'varchar(255)', (c) => c.notNull())
    .addColumn('chemin_stockage', 'varchar(500)', (c) => c.notNull())
    .addColumn('taille_octets', 'integer', (c) => c.notNull())
    .addColumn('depose_par', 'integer', (c) => c.notNull())
    .addColumn('cree_le', 'datetime', (c) => c.notNull().defaultTo(now))
    .execute();
  await db.schema.createIndex('idx_documents_objet').on('documents').columns(['objet_type', 'objet_id']).execute();

  await db
    .insertInto('types_activite')
    .values(['Gestion de projet', 'Études', 'Développement', 'Tests', 'Déploiement'].map((nom) => ({ nom })))
    .execute();
}

export async function down(db: Kysely<any>): Promise<void> {
  for (const t of ['documents', 'commentaires_livrables', 'livrables', 'pointages', 'affectations', 'taches', 'projets', 'types_activite', 'clients']) {
    await db.schema.dropTable(t).ifExists().execute();
  }
}
