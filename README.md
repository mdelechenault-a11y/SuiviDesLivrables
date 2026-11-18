# Suivi des Livrables

Application web de pilotage des projets, des heures et des livrables, pour un groupe de plusieurs filiales.
Elle remplace l'ancienne application de bureau Python/PyQt, archivée dans [`legacy/python-pyqt`](legacy/python-pyqt).

- **Accès** : depuis un navigateur, sur le réseau interne ou par VPN. Rien à installer sur les postes.
- **Connexion** : comptes Windows (Active Directory).
- **Une base de données par filiale**, plus une base « groupe » pour les filiales, les utilisateurs et les droits.
- **Droits vérifiés par le serveur** à chaque action, paramétrables par rôle depuis l'écran *Droits*.

Le fonctionnement détaillé est décrit dans [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Avancement

| Étape | Contenu | État |
| --- | --- | --- |
| 1. Socle | Connexion AD, filiales et bases séparées, rôles et droits, pointage des heures, administration, installation Docker | Fait |
| 2. Reprise de l'existant | Projets et Gantt, livrables et facturation, prévisionnel, KPI, calendrier, analyse hebdomadaire, clients, documents | À faire |
| 3. Nouveaux modules | CRM (opportunités, leads en tickets), achats et réceptions, bilans des affaires, bilans financiers et simulation | À faire |

## Installation sur une VM interne

Prérequis : Docker et Docker Compose sur la VM.

```bash
git clone https://github.com/mdelechenault-a11y/SuiviDesLivrables.git
cd SuiviDesLivrables
cp .env.example .env      # puis remplir le fichier (mots de passe, Active Directory, premier admin)
docker compose up -d --build
```

L'appli répond sur `http://<vm>:3000`. Pour l'HTTPS, placez-la derrière le reverse proxy habituel (IIS, Nginx…) et passez `COOKIE_SECURE=true`.

Au premier démarrage, l'appli crée la base groupe et le compte administrateur indiqué par `BOOTSTRAP_ADMIN_USERNAME` (son identifiant Windows). Cet administrateur crée ensuite les filiales (chacune reçoit sa base), puis les utilisateurs en choisissant leur rôle et leur filiale.

**Active Directory.** Il faut un compte de service en lecture seule sur l'annuaire (`LDAP_BIND_DN`, `LDAP_BIND_PASSWORD`). Préférez `ldaps://` (port 636) : le mot de passe des utilisateurs transite vers le contrôleur de domaine. `LDAP_REQUIRED_GROUP` permet de réserver l'accès à un groupe AD. Un utilisateur doit aussi avoir été créé dans l'appli pour pouvoir se connecter.

**Sauvegardes.** Toutes les données sont dans le volume Docker `db-data`. Sauvegardez chaque base `sdl_*` (par exemple avec `mariadb-dump --databases`) selon votre politique habituelle.

## Développement

Prérequis : Node.js 22 et un serveur MariaDB ou MySQL local.

```bash
npm install
# Fichier d'environnement de développement (mode local, sans Active Directory)
cat > server/.env.local <<'EOF'
DB_USER=sdl
DB_PASSWORD=...
SESSION_SECRET=une-chaine-de-32-caracteres-minimum-ici
AUTH_MODE=local
BOOTSTRAP_ADMIN_USERNAME=admin
BOOTSTRAP_ADMIN_PASSWORD=admin-admin-123
EOF
cd server && set -a && . ./.env.local && set +a
npm run seed:demo          # filiale DEMO + comptes demo.* (mot de passe demo-demo-demo)
npm run dev                # API sur http://localhost:3000
# dans un autre terminal
npm run dev:web            # interface sur http://localhost:5173
```

Commandes utiles, depuis la racine :

- `npm test` : tests du serveur (il faut un MariaDB accessible ; voir `server/test/helpers.ts` pour les variables `TEST_DB_*`).
- `npm run typecheck` : vérification des types du serveur et de l'interface.
- `npm run build` : compilation de production.

## Organisation du code

```
server/            API Node.js (Fastify, TypeScript)
  src/modules/     un dossier par module métier (auth, admin, temps, puis projets, livrables, crm…)
  src/db/          connexions, types et migrations (base groupe / base de filiale)
  src/security/    rôles, permissions, contrôle d'accès
web/               interface (Vue 3, TypeScript)
legacy/            ancienne application Python, conservée pour référence
```
