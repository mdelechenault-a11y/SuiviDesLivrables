import { loadConfig } from './config.js';
import { Databases } from './db/connections.js';
import { ldapAuthenticator, localAuthenticator } from './auth/directory.js';
import { buildApp } from './app.js';
import { bootstrapAdmin } from './scripts/bootstrap.js';

const cfg = loadConfig();
const dbs = await Databases.open(cfg);
const authenticator = cfg.AUTH_MODE === 'ldap' ? ldapAuthenticator(cfg) : localAuthenticator();
await bootstrapAdmin(cfg, dbs);

const app = await buildApp({ cfg, dbs, authenticator });
const stop = async () => {
  await app.close();
  await dbs.close();
  process.exit(0);
};
process.on('SIGTERM', stop);
process.on('SIGINT', stop);

await app.listen({ port: cfg.PORT, host: cfg.HOST });
