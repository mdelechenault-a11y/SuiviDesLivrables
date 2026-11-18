# Architecture

## Vue d'ensemble

```
Navigateur (Vue 3)  ──HTTPS / VPN──►  Serveur Node.js (Fastify)  ──►  MariaDB
                                         │                            ├─ sdl_groupe     filiales, utilisateurs, droits
                                         │                            ├─ sdl_f_nord     données de la filiale Nord
                                         └──► Active Directory (LDAP) └─ sdl_f_sud      données de la filiale Sud
```

Le navigateur ne parle qu'au serveur. Seul le serveur connaît les identifiants de la base et de l'annuaire, et il vérifie les droits à chaque requête. C'est la principale différence avec l'ancienne appli, où chaque poste se connectait directement à MySQL.

## Bases de données

- **Base groupe** (`DB_GROUP_NAME`, par défaut `sdl_groupe`) : `filiales` (code, nom, nom de la base, objectifs financiers), `utilisateurs`, `utilisateur_filiales`, `role_permissions`.
- **Une base par filiale** (`sdl_f_<code>`) : clients, types d'activité, projets, tâches, affectations, pointages, livrables, commentaires, documents. Le schéma reprend celui de l'ancienne appli, avec des montants et des heures en décimal exact et des commentaires signés.
- Les utilisateurs sont communs au groupe : une base de filiale référence un utilisateur par son identifiant de la base groupe.
- Créer une filiale depuis l'écran *Filiales* crée sa base et y applique les migrations.
- Les migrations (`server/src/db/migrations/`) s'appliquent au démarrage, sur la base groupe puis sur chaque base de filiale. Pour faire évoluer le schéma, on ajoute un fichier de migration et on l'inscrit dans `connections.ts`.
- **Consolidation groupe** (bilans à venir) : le serveur lira chaque base de filiale et additionnera les résultats. Les tables gardent la même structure dans toutes les filiales pour que ce soit simple.

## Connexion

- `AUTH_MODE=ldap` : le serveur cherche l'utilisateur dans l'AD avec un compte de service, puis tente une connexion avec son mot de passe. Le mot de passe n'est jamais stocké. Nom, prénom et e-mail sont recopiés depuis l'annuaire.
- `AUTH_MODE=local` : mots de passe hachés (bcrypt) dans la base groupe. Réservé au développement et aux tests.
- Dans les deux cas, l'utilisateur doit exister dans l'appli et être actif : c'est là qu'on choisit son rôle et ses filiales.
- La session est un jeton signé dans un cookie `httpOnly` et `SameSite=Strict`, valable `SESSION_HOURS` heures. Le compte est relu à chaque requête : un compte désactivé ou un droit retiré s'applique immédiatement.
- Les tentatives de connexion sont limitées (`LOGIN_RATE_LIMIT` par minute et par adresse).

## Rôles et droits

Rôles : Admin, Directeur, Manager, Chef de projet, Utilisateur. Chaque route de l'API déclare la permission qu'elle exige (`requirePermission(...)`). La matrice rôle × permission est modifiable dans l'écran *Droits*.

Règles fixes :

- chacun peut pointer et voir ses propres heures (`temps.saisir`) ;
- seuls les rôles qui ont `temps.voir_equipe` (par défaut Manager, Directeur, Admin) voient les heures des autres ;
- l'administrateur garde toujours la gestion des utilisateurs et des droits ;
- un utilisateur n'accède qu'aux filiales qui lui sont attribuées ; l'administrateur les voit toutes.

## Ajouter un module

1. Créer `server/src/modules/<module>/routes.ts` et l'enregistrer dans `app.ts` (dans le bloc `/api/f/:filiale` s'il travaille sur les données d'une filiale).
2. Déclarer ses permissions dans `security/permissions.ts`.
3. Ajouter ses tables par une nouvelle migration de filiale.
4. Ajouter ses écrans dans `web/src/views/` et ses liens dans `components/AppLayout.vue`.
5. Écrire ses tests dans `server/test/`.
