import { z } from 'zod';

/**
 * Configuration lue dans les variables d'environnement.
 * Aucun identifiant n'est écrit dans le code : voir `.env.example` à la racine.
 */
const schema = z.object({
  NODE_ENV: z.enum(['development', 'production', 'test']).default('development'),
  PORT: z.coerce.number().int().default(3000),
  HOST: z.string().default('0.0.0.0'),

  // Serveur MySQL / MariaDB. Le compte doit pouvoir créer des bases (une par filiale).
  DB_HOST: z.string().default('localhost'),
  DB_PORT: z.coerce.number().int().default(3306),
  DB_USER: z.string().min(1),
  DB_PASSWORD: z.string().default(''),
  /** Base « groupe » : filiales, utilisateurs, droits. */
  DB_GROUP_NAME: z.string().regex(/^[a-z0-9_]+$/).default('sdl_groupe'),
  /** Préfixe des bases de filiale : sdl_f_<code>. */
  DB_TENANT_PREFIX: z.string().regex(/^[a-z0-9_]+$/).default('sdl_f_'),

  /** Secret de signature des sessions (32 caractères minimum). */
  SESSION_SECRET: z.string().min(32),
  SESSION_HOURS: z.coerce.number().positive().default(10),
  /** Tentatives de connexion autorisées par minute et par adresse IP. */
  LOGIN_RATE_LIMIT: z.coerce.number().int().positive().default(10),
  /** Cookie « Secure » : à activer dès que l'appli est servie en HTTPS. */
  COOKIE_SECURE: z.stringbool().default(false),

  /** ldap : comptes Active Directory. local : mots de passe gérés par l'appli (développement, tests). */
  AUTH_MODE: z.enum(['ldap', 'local']).default('ldap'),
  LDAP_URL: z.string().optional(),
  LDAP_BIND_DN: z.string().optional(),
  LDAP_BIND_PASSWORD: z.string().optional(),
  LDAP_BASE_DN: z.string().optional(),
  /** Attribut qui porte l'identifiant saisi à la connexion. */
  LDAP_USER_ATTRIBUTE: z.string().default('sAMAccountName'),
  /** Si renseigné, seuls les membres de ce groupe AD (DN complet) peuvent se connecter. */
  LDAP_REQUIRED_GROUP: z.string().optional(),
  LDAP_TLS_REJECT_UNAUTHORIZED: z.stringbool().default(true),

  /** Premier administrateur, créé au démarrage si aucun utilisateur n'existe. */
  BOOTSTRAP_ADMIN_USERNAME: z.string().optional(),
  /** Mot de passe du premier administrateur (mode local uniquement). */
  BOOTSTRAP_ADMIN_PASSWORD: z.string().optional(),

  /** Dossier des fichiers web compilés, servis par le même serveur. */
  WEB_DIST_DIR: z.string().optional(),
});

export type Config = z.infer<typeof schema>;

export function loadConfig(env: NodeJS.ProcessEnv = process.env): Config {
  const parsed = schema.safeParse(env);
  if (!parsed.success) {
    const details = parsed.error.issues.map((i) => `  - ${i.path.join('.')}: ${i.message}`).join('\n');
    throw new Error(`Configuration invalide :\n${details}`);
  }
  const cfg = parsed.data;
  if (cfg.AUTH_MODE === 'ldap') {
    const missing = (['LDAP_URL', 'LDAP_BIND_DN', 'LDAP_BIND_PASSWORD', 'LDAP_BASE_DN'] as const).filter((k) => !cfg[k]);
    if (missing.length) throw new Error(`AUTH_MODE=ldap : variables manquantes : ${missing.join(', ')}`);
  }
  if (cfg.NODE_ENV === 'production' && cfg.AUTH_MODE === 'local') {
    console.warn('[config] AUTH_MODE=local en production : les comptes ne passent pas par Active Directory.');
  }
  return cfg;
}
