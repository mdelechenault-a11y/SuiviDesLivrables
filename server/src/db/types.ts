import type { ColumnType, Generated } from 'kysely';

/** Date SQL lue et écrite sous forme 'AAAA-MM-JJ' (option dateStrings du pilote). */
type DateStr = string;
/** Horodatage géré par la base. */
type CreatedAt = ColumnType<string, never, never>;

/* ---------- Base groupe : filiales, utilisateurs, droits ---------- */

export interface FilialeTable {
  id: Generated<number>;
  code: string;
  nom: string;
  db_name: string;
  objectif_point_mort: ColumnType<number, number | undefined, number>;
  objectif_1: ColumnType<number, number | undefined, number>;
  objectif_2: ColumnType<number, number | undefined, number>;
  actif: ColumnType<number, number | undefined, number>;
  cree_le: CreatedAt;
}

export interface UtilisateurTable {
  id: Generated<number>;
  identifiant: string;
  prenom: string;
  nom: string;
  email: string | null;
  role: string;
  mot_de_passe_hash: string | null;
  actif: ColumnType<number, number | undefined, number>;
  derniere_connexion: string | null;
  cree_le: CreatedAt;
}

export interface UtilisateurFilialeTable {
  utilisateur_id: number;
  filiale_id: number;
}

export interface RolePermissionTable {
  role: string;
  permission: string;
}

export interface GroupDatabase {
  filiales: FilialeTable;
  utilisateurs: UtilisateurTable;
  utilisateur_filiales: UtilisateurFilialeTable;
  role_permissions: RolePermissionTable;
}

/* ---------- Base de filiale : données métier ---------- */

export interface ClientTable {
  id: Generated<number>;
  nom: string;
  code: string | null;
  adresse: string | null;
  telephone: string | null;
  site_web: string | null;
  contact: string | null;
  visible: ColumnType<number, number | undefined, number>;
}

export interface TypeActiviteTable {
  id: Generated<number>;
  nom: string;
}

export type StatutProjet = 'Chiffrage' | 'En cours' | 'Terminé';

export interface ProjetTable {
  id: Generated<number>;
  code: string;
  nom: string;
  client_id: number;
  /** Identifiant d'utilisateur de la base groupe. */
  chef_de_projet_id: number | null;
  date_debut: DateStr;
  statut: StatutProjet;
  budget_materiel_prevu: ColumnType<number, number | undefined, number>;
  budget_materiel_depense: ColumnType<number, number | undefined, number>;
  cree_le: CreatedAt;
}

export interface TacheTable {
  id: Generated<number>;
  projet_id: number;
  nom: string;
  type_activite_id: number | null;
  parente_id: number | null;
  position: ColumnType<number, number | undefined, number>;
  duree_jours: ColumnType<number, number | undefined, number>;
  decalage_jours: ColumnType<number, number | undefined, number>;
  heures_prevues: ColumnType<number, number | undefined, number>;
  date_debut: DateStr | null;
  date_fin: DateStr | null;
  jalon: ColumnType<number, number | undefined, number>;
}

export interface AffectationTable {
  id: Generated<number>;
  tache_id: number;
  utilisateur_id: number;
  heures_allouees: number;
}

export interface PointageTable {
  id: Generated<number>;
  utilisateur_id: number;
  tache_id: number;
  projet_id: number;
  date: DateStr;
  heures: number;
  commentaire: string | null;
  cree_le: CreatedAt;
}

export interface LivrableTable {
  id: Generated<number>;
  projet_id: number;
  nom: string;
  montant: number;
  date_prevue: DateStr;
  date_initiale: DateStr | null;
  responsabilite_retard: 'Client' | 'Interne' | null;
  facture: ColumnType<number, number | undefined, number>;
}

export interface CommentaireLivrableTable {
  id: Generated<number>;
  livrable_id: number;
  auteur_id: number;
  contenu: string;
  cree_le: CreatedAt;
}

export interface DocumentTable {
  id: Generated<number>;
  objet_type: 'projet' | 'tache' | 'client';
  objet_id: number;
  nom_fichier: string;
  chemin_stockage: string;
  taille_octets: number;
  depose_par: number;
  cree_le: CreatedAt;
}

export interface TenantDatabase {
  clients: ClientTable;
  types_activite: TypeActiviteTable;
  projets: ProjetTable;
  taches: TacheTable;
  affectations: AffectationTable;
  pointages: PointageTable;
  livrables: LivrableTable;
  commentaires_livrables: CommentaireLivrableTable;
  documents: DocumentTable;
}
