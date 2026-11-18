/** Applique les migrations de la base groupe et de toutes les bases de filiale, puis s'arrête. */
import { loadConfig } from '../config.js';
import { Databases } from '../db/connections.js';

const dbs = await Databases.open(loadConfig());
console.info('Migrations appliquées.');
await dbs.close();
