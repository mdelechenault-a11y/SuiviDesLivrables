# Suivi des Livrables

Application de suivi de projets et de livrables.

## Prérequis

- **Python 3.10+**
- **MySQL** (ou MariaDB) : L'application utilise une base de données MySQL par défaut. Vous devez avoir un serveur MySQL en cours d'exécution.

## Installation

1. **Cloner le dépôt (si ce n'est pas déjà fait) :**
   ```bash
   git clone <url_du_depot>
   cd SuiviDesLivrables
   ```

2. **Créer un environnement virtuel (recommandé) :**
   ```bash
   python -m venv venv
   ```

3. **Activer l'environnement virtuel :**
   - Sur Windows :
     ```bash
     venv\Scripts\activate
     ```
   - Sur macOS/Linux :
     ```bash
     source venv/bin/activate
     ```

4. **Installer les dépendances :**
   ```bash
   pip install -r requirements.txt
   ```

5. **Configuration de la base de données :**
   - Assurez-vous d'avoir un serveur MySQL accessible.
   - Par défaut, l'application s'attend à trouver une base de données nommée `suivi_livrables` sur `localhost:3306` avec l'utilisateur `root` (sans mot de passe).
   - **Important :** Modifiez les paramètres de connexion dans `config.py` selon votre environnement local (utilisateur, mot de passe, hôte, nom de la base de données).

## Initialisation et Lancement

1. **Synchronisation de la base de données :**
   L'application gère automatiquement la création des tables et l'initialisation des données de base au démarrage. Cependant, vous pouvez exécuter le script de synchronisation manuellement si besoin :
   ```bash
   python db_sync.py
   ```

2. **Lancer l'application :**
   ```bash
   python main.py
   ```

## Scripts Utilitaires

Plusieurs scripts sont disponibles à la racine du projet pour faciliter le développement et les tests :

- `seed_data.py` / `seed_advanced_data.py` : Scripts pour peupler la base de données avec des données de test (utilisateurs, projets, livrables, etc.).
- `manage_db.py` : Fonctions utilitaires pour la gestion de la base de données (initialisation des données de production de base comme les profils et l'administrateur).
- `migrate_sqlite_to_mysql.py` : Script pour migrer les données d'une ancienne base SQLite vers MySQL.

## Dépendances Principales

- **PyQt6** : Interface graphique.
- **SQLAlchemy** : ORM pour l'interaction avec la base de données.
- **PyMySQL** : Connecteur MySQL pour Python.
- **bcrypt** : Hachage des mots de passe.
- **pandas** / **matplotlib** : Traitement de données et génération de graphiques (pour les vues statistiques).
- **qt-material** / **qtawesome** : Thèmes et icônes pour l'interface utilisateur.
