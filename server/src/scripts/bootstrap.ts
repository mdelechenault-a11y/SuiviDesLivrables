import type { Config } from '../config.js';
import type { Databases } from '../db/connections.js';
import { hashPassword } from '../auth/directory.js';

/**
 * Crée le premier administrateur si la base groupe ne contient aucun utilisateur.
 * En mode Active Directory, BOOTSTRAP_ADMIN_USERNAME est son identifiant Windows.
 */
export async function bootstrapAdmin(cfg: Config, dbs: Databases): Promise<void> {
  const any = await dbs.group.selectFrom('utilisateurs').select('id').limit(1).executeTakeFirst();
  if (any) return;
  if (!cfg.BOOTSTRAP_ADMIN_USERNAME) {
    console.warn('[démarrage] Aucun utilisateur : renseignez BOOTSTRAP_ADMIN_USERNAME pour créer le premier administrateur.');
    return;
  }
  if (cfg.AUTH_MODE === 'local' && !cfg.BOOTSTRAP_ADMIN_PASSWORD) {
    throw new Error('AUTH_MODE=local : BOOTSTRAP_ADMIN_PASSWORD est requis pour créer le premier administrateur.');
  }
  await dbs.group
    .insertInto('utilisateurs')
    .values({
      identifiant: cfg.BOOTSTRAP_ADMIN_USERNAME,
      prenom: 'Administrateur',
      nom: cfg.BOOTSTRAP_ADMIN_USERNAME,
      email: null,
      role: 'Admin',
      mot_de_passe_hash: cfg.AUTH_MODE === 'local' ? await hashPassword(cfg.BOOTSTRAP_ADMIN_PASSWORD!) : null,
    })
    .execute();
  console.info(`[démarrage] Premier administrateur créé : ${cfg.BOOTSTRAP_ADMIN_USERNAME}`);
}
