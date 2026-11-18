/**
 * Rôles et permissions.
 *
 * Les droits sont vérifiés par le serveur sur chaque requête : masquer un menu
 * dans l'interface ne suffit jamais. La matrice rôle × permission est stockée
 * dans la base groupe et modifiable par un administrateur ; les valeurs
 * ci-dessous servent de point de départ.
 */

export const ROLES = ['Admin', 'Directeur', 'Manager', 'Chef de projet', 'Utilisateur'] as const;
export type Role = (typeof ROLES)[number];

export const PERMISSIONS = {
  'temps.saisir': 'Pointer ses propres heures',
  'temps.voir_equipe': 'Voir les heures des autres salariés',
  'projets.voir': 'Consulter les projets',
  'projets.gerer': 'Créer et modifier les projets, tâches et affectations',
  'livrables.voir': 'Consulter les livrables',
  'livrables.gerer': 'Créer, décaler et facturer les livrables',
  'finance.voir': 'Voir les montants, le prévisionnel et les KPI financiers',
  'admin.utilisateurs': 'Gérer les utilisateurs et leurs filiales',
  'admin.filiales': 'Créer les filiales et régler leurs objectifs',
  'admin.droits': 'Modifier cette matrice de droits',
} as const;
export type Permission = keyof typeof PERMISSIONS;
export const ALL_PERMISSIONS = Object.keys(PERMISSIONS) as Permission[];

export function isRole(value: unknown): value is Role {
  return typeof value === 'string' && (ROLES as readonly string[]).includes(value);
}
export function isPermission(value: unknown): value is Permission {
  return typeof value === 'string' && value in PERMISSIONS;
}

/** Valeurs par défaut, posées à la création de la base groupe. */
export const DEFAULT_ROLE_PERMISSIONS: Record<Role, Permission[]> = {
  Admin: [...ALL_PERMISSIONS],
  Directeur: ['temps.saisir', 'temps.voir_equipe', 'projets.voir', 'projets.gerer', 'livrables.voir', 'livrables.gerer', 'finance.voir'],
  Manager: ['temps.saisir', 'temps.voir_equipe', 'projets.voir', 'livrables.voir', 'finance.voir'],
  'Chef de projet': ['temps.saisir', 'projets.voir', 'projets.gerer', 'livrables.voir', 'livrables.gerer'],
  Utilisateur: ['temps.saisir'],
};

/**
 * Permissions que l'on ne peut pas retirer, pour ne jamais se retrouver sans
 * personne capable d'administrer l'appli, et pour que chacun puisse pointer.
 */
export const LOCKED: Array<{ role: Role; permission: Permission }> = [
  { role: 'Admin', permission: 'admin.droits' },
  { role: 'Admin', permission: 'admin.utilisateurs' },
  ...ROLES.map((role) => ({ role, permission: 'temps.saisir' as Permission })),
];

export function isLocked(role: Role, permission: Permission): boolean {
  return LOCKED.some((l) => l.role === role && l.permission === permission);
}
