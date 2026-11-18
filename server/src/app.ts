import Fastify, { type FastifyInstance } from 'fastify';
import cookie from '@fastify/cookie';
import jwt from '@fastify/jwt';
import rateLimit from '@fastify/rate-limit';
import fastifyStatic from '@fastify/static';
import { existsSync } from 'node:fs';
import path from 'node:path';
import { ZodError } from 'zod';
import type { Config } from './config.js';
import type { Databases } from './db/connections.js';
import type { Authenticator } from './auth/directory.js';
import { HttpError, loadCurrentUser } from './security/context.js';
import { authRoutes, SESSION_COOKIE } from './modules/auth/routes.js';
import { adminRoutes } from './modules/admin/routes.js';
import { tempsRoutes } from './modules/temps/routes.js';

export interface AppDeps {
  cfg: Config;
  dbs: Databases;
  authenticator: Authenticator;
}

/** Routes accessibles sans être connecté. */
const PUBLIC_ROUTES = new Set(['/api/auth/login', '/api/auth/logout', '/api/sante']);

export async function buildApp({ cfg, dbs, authenticator }: AppDeps): Promise<FastifyInstance> {
  const app = Fastify({
    logger: cfg.NODE_ENV === 'test' ? false : { level: 'info', redact: ['req.headers.cookie', 'req.body.motDePasse'] },
    trustProxy: true,
  });

  await app.register(cookie);
  await app.register(jwt, { secret: cfg.SESSION_SECRET, cookie: { cookieName: SESSION_COOKIE, signed: false } });
  await app.register(rateLimit, { global: false });

  app.decorateRequest('auth', null);
  app.decorateRequest('tenant', null);

  // Toute route /api, sauf la connexion, exige une session valide.
  app.addHook('onRequest', async (req) => {
    const url = req.url.split('?')[0]!;
    if (!url.startsWith('/api/') || PUBLIC_ROUTES.has(url)) return;
    let payload: { uid?: number };
    try {
      payload = await req.jwtVerify<{ uid: number }>();
    } catch {
      throw new HttpError(401, 'Session absente ou expirée. Reconnectez-vous.');
    }
    const user = typeof payload.uid === 'number' ? await loadCurrentUser(dbs.group, payload.uid) : null;
    if (!user) throw new HttpError(401, 'Compte inconnu ou désactivé.');
    req.auth = user;
  });

  app.setErrorHandler((err, req, reply) => {
    if (err instanceof HttpError) return reply.status(err.statusCode).send({ erreur: err.message });
    if (err instanceof ZodError) {
      return reply.status(400).send({ erreur: 'Données invalides.', details: err.issues.map((i) => `${i.path.join('.')}: ${i.message}`) });
    }
    const e = err as { statusCode?: number; message?: string };
    if (e.statusCode === 429) return reply.status(429).send({ erreur: 'Trop de tentatives. Réessayez dans une minute.' });
    if (e.statusCode && e.statusCode < 500) return reply.status(e.statusCode).send({ erreur: e.message });
    req.log.error(err);
    return reply.status(500).send({ erreur: 'Erreur interne du serveur.' });
  });

  app.get('/api/sante', async () => ({ ok: true }));
  await app.register(authRoutes, { prefix: '/api/auth', cfg, dbs, authenticator });
  await app.register(adminRoutes, { prefix: '/api/admin', cfg, dbs, authenticator });

  // Routes d'une filiale : /api/f/<code>/...
  await app.register(
    async (f) => {
      f.addHook('preHandler', async (req) => {
        const code = (req.params as { filiale?: string }).filiale ?? '';
        const user = req.auth;
        if (!user) throw new HttpError(401, 'Connexion requise.');
        const ref = user.filiales.find((x) => x.code.toLowerCase() === code.toLowerCase());
        if (!ref) throw new HttpError(403, "Vous n'avez pas accès à cette filiale.");
        const row = await dbs.group.selectFrom('filiales').select('db_name').where('id', '=', ref.id).executeTakeFirstOrThrow();
        req.tenant = { filiale: { ...ref, db_name: row.db_name }, db: dbs.tenant(row.db_name) };
      });
      await f.register(tempsRoutes, { dbs });
    },
    { prefix: '/api/f/:filiale' },
  );

  app.all('/api/*', async () => {
    throw new HttpError(404, 'Route inconnue.');
  });

  // Interface web compilée (Vue), servie par le même serveur.
  const webDir = cfg.WEB_DIST_DIR ? path.resolve(cfg.WEB_DIST_DIR) : null;
  if (webDir && existsSync(webDir)) {
    await app.register(fastifyStatic, { root: webDir, wildcard: false });
    app.setNotFoundHandler((req, reply) => {
      if (req.method === 'GET' && !req.url.startsWith('/api/')) return reply.sendFile('index.html');
      return reply.status(404).send({ erreur: 'Introuvable.' });
    });
  }

  return app;
}
