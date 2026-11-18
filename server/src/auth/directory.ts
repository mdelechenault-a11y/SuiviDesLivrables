import { Client, EqualityFilter, AndFilter } from 'ldapts';
import bcrypt from 'bcryptjs';
import type { Config } from '../config.js';

/** Informations lues dans l'annuaire après une connexion réussie. */
export interface DirectoryUser {
  identifiant: string;
  prenom?: string;
  nom?: string;
  email?: string;
}

/** Vérifie un couple identifiant / mot de passe. Renvoie null si refusé. */
export interface Authenticator {
  readonly mode: 'ldap' | 'local';
  verify(identifiant: string, motDePasse: string, storedHash: string | null): Promise<DirectoryUser | null>;
}

const first = (v: unknown): string | undefined => {
  if (Array.isArray(v)) return first(v[0]);
  if (Buffer.isBuffer(v)) return v.toString('utf8');
  return typeof v === 'string' && v ? v : undefined;
};
const list = (v: unknown): string[] => (Array.isArray(v) ? v.map((x) => first(x) ?? '') : first(v) ? [first(v)!] : []);

/**
 * Connexion Active Directory : un compte de service cherche l'utilisateur,
 * puis on tente une connexion LDAP avec son propre mot de passe.
 * Le mot de passe n'est jamais stocké par l'appli.
 */
export function ldapAuthenticator(cfg: Config): Authenticator {
  const clientFor = () =>
    new Client({
      url: cfg.LDAP_URL!,
      timeout: 8000,
      connectTimeout: 8000,
      tlsOptions: { rejectUnauthorized: cfg.LDAP_TLS_REJECT_UNAUTHORIZED },
    });

  return {
    mode: 'ldap',
    async verify(identifiant, motDePasse) {
      // Un mot de passe vide ferait une connexion « anonyme » acceptée par certains annuaires.
      if (!identifiant || !motDePasse) return null;
      const service = clientFor();
      let dn: string;
      let entry: Record<string, unknown>;
      try {
        await service.bind(cfg.LDAP_BIND_DN!, cfg.LDAP_BIND_PASSWORD!);
        const filter = new AndFilter({
          filters: [
            new EqualityFilter({ attribute: 'objectClass', value: 'user' }),
            new EqualityFilter({ attribute: cfg.LDAP_USER_ATTRIBUTE, value: identifiant }),
          ],
        });
        const { searchEntries } = await service.search(cfg.LDAP_BASE_DN!, {
          scope: 'sub',
          filter,
          sizeLimit: 2,
          attributes: ['dn', 'givenName', 'sn', 'mail', 'memberOf', cfg.LDAP_USER_ATTRIBUTE],
        });
        if (searchEntries.length !== 1) return null;
        entry = searchEntries[0]!;
        dn = String(entry.dn);
      } finally {
        await service.unbind().catch(() => undefined);
      }

      if (cfg.LDAP_REQUIRED_GROUP) {
        const groups = list(entry.memberOf).map((g) => g.toLowerCase());
        if (!groups.includes(cfg.LDAP_REQUIRED_GROUP.toLowerCase())) return null;
      }

      const userClient = clientFor();
      try {
        await userClient.bind(dn, motDePasse);
      } catch {
        return null;
      } finally {
        await userClient.unbind().catch(() => undefined);
      }
      return { identifiant, prenom: first(entry.givenName), nom: first(entry.sn), email: first(entry.mail) };
    },
  };
}

/** Mode local (développement, tests) : mot de passe haché avec bcrypt dans la base groupe. */
export function localAuthenticator(): Authenticator {
  return {
    mode: 'local',
    async verify(identifiant, motDePasse, storedHash) {
      if (!storedHash || !motDePasse) return null;
      return (await bcrypt.compare(motDePasse, storedHash)) ? { identifiant } : null;
    },
  };
}

export const hashPassword = (pwd: string) => bcrypt.hash(pwd, 12);
