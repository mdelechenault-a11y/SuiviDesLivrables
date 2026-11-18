import type { FastifyPluginAsync } from 'fastify';
import { sql } from 'kysely';
import { z } from 'zod';
import type { AppDeps } from '../../app.js';
import { HttpError, loadCurrentUser, mustUser, publicUser } from '../../security/context.js';

export const SESSION_COOKIE = 'sdl_session';

const LoginBody = z.object({
  identifiant: z.string().trim().min(1).max(100),
  motDePasse: z.string().min(1).max(256),
});

export const authRoutes: FastifyPluginAsync<AppDeps> = async (app, { cfg, dbs, authenticator }) => {
  app.post(
    '/login',
    { config: { rateLimit: { max: cfg.LOGIN_RATE_LIMIT, timeWindow: '1 minute' } } },
    async (req, reply) => {
      const { identifiant, motDePasse } = LoginBody.parse(req.body);
      // Un identifiant « DOMAINE\nom » ou « nom@domaine » est ramené à « nom ».
      const login = identifiant.replace(/^.*\\/, '').replace(/@.*$/, '');

      const row = await dbs.group
        .selectFrom('utilisateurs')
        .select(['id', 'actif', 'mot_de_passe_hash'])
        .where('identifiant', '=', login)
        .executeTakeFirst();

      const verified = await authenticator.verify(login, motDePasse, row?.mot_de_passe_hash ?? null);
      if (!verified) throw new HttpError(401, 'Identifiant ou mot de passe incorrect.');
      if (!row) throw new HttpError(403, "Votre compte n'est pas encore ouvert dans l'application. Demandez-le à un administrateur.");
      if (!row.actif) throw new HttpError(403, 'Votre compte est désactivé dans l\'application.');

      // Les nom, prénom et e-mail suivent l'annuaire quand il les fournit.
      await dbs.group
        .updateTable('utilisateurs')
        .set({
          derniere_connexion: sql<string>`CURRENT_TIMESTAMP`,
          ...(verified.prenom ? { prenom: verified.prenom } : {}),
          ...(verified.nom ? { nom: verified.nom } : {}),
          ...(verified.email ? { email: verified.email } : {}),
        })
        .where('id', '=', row.id)
        .execute();

      const user = await loadCurrentUser(dbs.group, row.id);
      if (!user) throw new HttpError(403, 'Compte indisponible.');
      const token = await reply.jwtSign({ uid: user.id }, { expiresIn: `${cfg.SESSION_HOURS}h` });
      reply.setCookie(SESSION_COOKIE, token, {
        path: '/',
        httpOnly: true,
        sameSite: 'strict',
        secure: cfg.COOKIE_SECURE,
        maxAge: cfg.SESSION_HOURS * 3600,
      });
      return { utilisateur: publicUser(user), modeConnexion: authenticator.mode };
    },
  );

  app.post('/logout', async (_req, reply) => {
    reply.clearCookie(SESSION_COOKIE, { path: '/' });
    return { ok: true };
  });

  app.get('/me', async (req) => ({ utilisateur: publicUser(mustUser(req)), modeConnexion: authenticator.mode }));
};
