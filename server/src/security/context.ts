import type { FastifyReply, FastifyRequest } from 'fastify';
import type { Kysely } from 'kysely';
import type { GroupDatabase, TenantDatabase } from '../db/types.js';
import { isPermission, type Permission } from './permissions.js';

export interface FilialeRef {
  id: number;
  code: string;
  nom: string;
}

/** Utilisateur connecté, rechargé depuis la base groupe à chaque requête. */
export interface CurrentUser {
  id: number;
  identifiant: string;
  prenom: string;
  nom: string;
  email: string | null;
  role: string;
  permissions: Set<Permission>;
  filiales: FilialeRef[];
}

export interface TenantContext {
  filiale: FilialeRef & { db_name: string };
  db: Kysely<TenantDatabase>;
}

declare module 'fastify' {
  interface FastifyRequest {
    auth: CurrentUser | null;
    tenant: TenantContext | null;
  }
}

export class HttpError extends Error {
  constructor(
    public statusCode: number,
    message: string,
  ) {
    super(message);
  }
}

export async function loadCurrentUser(group: Kysely<GroupDatabase>, id: number): Promise<CurrentUser | null> {
  const u = await group
    .selectFrom('utilisateurs')
    .select(['id', 'identifiant', 'prenom', 'nom', 'email', 'role', 'actif'])
    .where('id', '=', id)
    .executeTakeFirst();
  if (!u || !u.actif) return null;

  const perms = await group.selectFrom('role_permissions').select('permission').where('role', '=', u.role).execute();
  // Un administrateur accède à toutes les filiales ; les autres à celles qui leur sont attribuées.
  let q = group.selectFrom('filiales').select(['filiales.id', 'filiales.code', 'filiales.nom']).where('filiales.actif', '=', 1);
  if (u.role !== 'Admin') {
    q = q.innerJoin('utilisateur_filiales as uf', 'uf.filiale_id', 'filiales.id').where('uf.utilisateur_id', '=', u.id);
  }
  const filiales = await q.orderBy('filiales.nom').execute();

  return {
    id: u.id,
    identifiant: u.identifiant,
    prenom: u.prenom,
    nom: u.nom,
    email: u.email,
    role: u.role,
    permissions: new Set(perms.map((p) => p.permission).filter(isPermission)),
    filiales,
  };
}

export function publicUser(u: CurrentUser) {
  return {
    id: u.id,
    identifiant: u.identifiant,
    prenom: u.prenom,
    nom: u.nom,
    email: u.email,
    role: u.role,
    permissions: [...u.permissions].sort(),
    filiales: u.filiales,
  };
}

/** À placer en preHandler : refuse la requête si la permission manque. */
export function requirePermission(...perms: Permission[]) {
  return async (req: FastifyRequest, _reply: FastifyReply) => {
    if (!req.auth) throw new HttpError(401, 'Connexion requise.');
    if (!perms.some((p) => req.auth!.permissions.has(p))) {
      throw new HttpError(403, "Vous n'avez pas les droits pour cette action.");
    }
  };
}

export function mustUser(req: FastifyRequest): CurrentUser {
  if (!req.auth) throw new HttpError(401, 'Connexion requise.');
  return req.auth;
}

export function mustTenant(req: FastifyRequest): TenantContext {
  if (!req.tenant) throw new HttpError(500, 'Filiale non résolue.');
  return req.tenant;
}
