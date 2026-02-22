import sys
import os
import random
import datetime
from faker import Faker
import argparse

# Ajout de la racine du projet au PYTHONPATH pour les imports absolus
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from sqlalchemy.orm import sessionmaker, joinedload
from app.models.base import engine
from app.models.schema import (Profil, User, Client, Project, ActivityType,
                               Task, TimeEntry, TaskAssignment, ProjectStatus, Livrable,
                               LivrableComment, Company)
from app.controllers.user_controller import UserController
from app.controllers.project_controller import ProjectController
from db_sync import synchronize_database

# Initialisation de Faker pour des données en français
fake = Faker('fr_FR')

# Création d'une session SQLAlchemy
Session = sessionmaker(bind=engine)

# --- Fonctions de base ---

def clear_data():
    """Nettoie les tables pertinentes pour éviter les conflits."""
    session = Session()
    print("Nettoyage des données de l'application...")
    try:
        # L'ordre est important à cause des clés étrangères
        session.query(TimeEntry).delete()
        session.query(TaskAssignment).delete()
        session.query(LivrableComment).delete()
        session.query(Livrable).delete()
        session.query(Task).delete()
        session.query(Project).delete()
        session.query(User).delete()
        session.query(Client).delete()
        session.query(Profil).delete()
        session.query(ActivityType).delete()
        session.query(Company).delete()
        session.commit()
        print("Données nettoyées avec succès.")
    except Exception as e:
        session.rollback()
        print(f"Erreur lors du nettoyage des données : {e}")
    finally:
        session.close()

# --- Commandes principales ---

def init_production_data(verbose=True):
    """
    Assure que les données essentielles (profils, admin) existent pour une utilisation en production.
    Ne supprime aucune donnée existante.
    Le paramètre `verbose` contrôle l'affichage des messages dans la console.
    """
    def log(message):
        if verbose:
            print(message)

    log("Initialisation de la base de données pour la production...")
    controller = UserController()
    
    # 1. S'assurer que les profils de base existent
    profiles_to_ensure = ["Admin", "Chef de projet", "Utilisateur"]
    log(f"Vérification de l'existence des profils : {', '.join(profiles_to_ensure)}")
    controller.ensure_profils_exist(profiles_to_ensure)

    # 2. S'assurer qu'il y a au moins un utilisateur admin
    if not controller.get_all_users():
        log("Aucun utilisateur trouvé. Création de l'utilisateur admin par défaut (admin/admin)...")
        controller.add_user(
            username="admin",
            email="admin@local.host",
            password="admin",
            prenom="Admin",
            nom="User",
            profil_nom="Admin"
        )
        log("Utilisateur admin créé.")
    else:
        log("Des utilisateurs existent déjà, aucune création n'est nécessaire.")
    
    log("Initialisation terminée.")

def seed_basic_data():
    """
    Nettoie la base de données et la peuple avec un jeu de données minimal.
    (Remplace l'ancien seed_data.py)
    """
    print("Lancement du peuplement de base...")
    clear_data()
    
    session = Session()
    try:
        # Créer les profils
        print("Création des profils de base...")
        profil_rh = Profil(nom='RH')
        profil_dev = Profil(nom='Développeur')
        profil_cp = Profil(nom='Chef de projet')
        session.add_all([profil_rh, profil_dev, profil_cp])
        session.commit()

        # Créer les utilisateurs
        print("Création des utilisateurs de base...")
        user_rh = User(username='test_rh', email='rh@example.com', prenom="Test", nom="RH", password_hash=UserController.set_password('password_rh'), profil=profil_rh)
        user_dev = User(username='test_dev', email='dev@example.com', prenom="Test", nom="Dev", password_hash=UserController.set_password('password_dev'), profil=profil_dev)
        user_cp = User(username='test_cp', email='cp@example.com', prenom="Test", nom="CP", password_hash=UserController.set_password('password_cp'), profil=profil_cp)
        session.add_all([user_rh, user_dev, user_cp])
        session.commit()
        
        print("Peuplement de base terminé avec succès.")
    except Exception as e:
        session.rollback()
        print(f"Une erreur est survenue durant le peuplement de base : {e}")
    finally:
        session.close()

def seed_full_data(nb_users, nb_clients, nb_projects, tasks_per_project, entries_per_task):
    """
    Nettoie la base de données et la peuple avec un jeu de données complet et réaliste.
    (Remplace l'ancien seed_advanced_data.py)
    """
    print("Lancement du peuplement complet...")
    clear_data()
    
    profils, activity_types, companies = _seed_base_dependencies()
    if profils and activity_types and companies:
        users = _create_users(profils, companies, count=nb_users)
        clients = _create_clients(count=nb_clients)
        if users and clients:
            _create_projects_and_tasks(users, clients, activity_types, companies, 
                                       project_count=nb_projects, 
                                       tasks_per_project=tasks_per_project,
                                       entries_per_task=entries_per_task)
    print("\nPeuplement complet de la base de données terminé avec succès !")

# --- Fonctions de support pour le peuplement complet ---

def _seed_base_dependencies():
    """Crée les données de base nécessaires comme les profils et les types d'activités."""
    session = Session()
    print("Création des données de base (Profils, Types d'activités, Sociétés)...")
    try:
        profil_names = ["Admin", "Chef de projet", "Développeur", "Dessinateur", "Électricien"]
        for name in profil_names:
            if not session.query(Profil).filter_by(nom=name).first():
                session.add(Profil(nom=name))

        activity_type_names = [
            "Développement Logiciel", "Conception Mécanique", "Étude Électrique",
            "Montage Mécanique", "Câblage Électrique", "Documentation", "Gestion de Projet",
            "SAV", "Expertise", "Autres"
        ]
        for name in activity_type_names:
            if not session.query(ActivityType).filter_by(nom=name).first():
                session.add(ActivityType(nom=name))
        
        company_names = ["INGENIERIE", "BIOTECH", "ENERGY", "AIR AND SECURITY", "MANAGEMENT"]
        for name in company_names:
            if not session.query(Company).filter_by(name=name).first():
                session.add(Company(name=name))
        
        session.commit()
        print("Données de base créées.")
        return session.query(Profil).all(), session.query(ActivityType).all(), session.query(Company).all()
    finally:
        session.close()

def _create_users(profils, companies, count):
    """Crée un nombre défini d'utilisateurs de test."""
    session = Session()
    print(f"Création de {count} utilisateurs...")
    try:
        admin_profil = next((p for p in profils if p.nom == "Admin"), None)
        admin_company = next((c for c in companies if c.name == "MANAGEMENT"), None)
        admin_user = User(
            username="admin", email="admin@test.com", password_hash=UserController.set_password("admin"),
            prenom="Admin", nom="Istrateur", profil=admin_profil, company=admin_company
        )
        session.add(admin_user)

        for i in range(count - 1):
            prenom = fake.first_name()
            nom = fake.last_name()
            user_company = random.choice(companies) if companies else None
            session.add(User(
                username=f"{prenom.lower()}.{nom.lower()}{i}",
                email=f"{prenom.lower()}.{nom.lower()}{i}@fake.com",
                password_hash=UserController.set_password("password"),
                prenom=prenom, nom=nom,
                profil=random.choice(profils),
                company=user_company
            ))
        session.commit()
        users = session.query(User).options(joinedload(User.profil)).all()
        print(f"{len(users)} utilisateurs créés.")
        return users
    except Exception as e:
        session.rollback()
        print(f"Erreur lors de la création des utilisateurs : {e}")
        return []
    finally:
        session.close()

def _create_clients(count):
    """Crée un nombre défini de clients de test."""
    session = Session()
    print(f"Création de {count} clients...")
    try:
        client_names = set()
        while len(client_names) < count:
            client_names.add(fake.company())

        for name in client_names:
            session.add(Client(name=name))

        session.commit()
        clients = session.query(Client).all()
        print(f"{len(clients)} clients créés.")
        return clients
    finally:
        session.close()

def _create_projects_and_tasks(users, clients, activity_types, companies, project_count, tasks_per_project, entries_per_task):
    """Crée les projets, les tâches, et simule le pointage d'heures."""
    session = Session()
    controller = ProjectController()
    print(f"Création de {project_count} projets avec {tasks_per_project} tâches chacun...")
    try:
        chefs_de_projet = [u for u in users if u.profil.nom == "Chef de projet"]
        if not chefs_de_projet: chefs_de_projet = users

        for i in range(project_count):
            start_date = fake.date_between(start_date='-1y', end_date='today')
            project = Project(
                code=f"P{datetime.date.today().year}-{i+1:03d}",
                nom=fake.catch_phrase(),
                client=random.choice(clients),
                chef_de_projet=random.choice(chefs_de_projet),
                statut=random.choice(list(ProjectStatus)),
                date_debut=start_date,
                budget_material_planned=round(random.uniform(500.0, 20000.0), 2),
                company=random.choice(companies) if companies else None
            )
            project.budget_material_spent = round(project.budget_material_planned * random.uniform(0.7, 1.2), 2)
            session.add(project)
            session.flush()

            project_year = project.date_debut.year
            months = random.sample(range(1, 13), 5)
            for k, month in enumerate(months):
                day = random.randint(1, 28)
                date_prevue = datetime.date(project_year, month, day)
                livrable = Livrable(
                    nom=f"Jalon de facturation {k+1}",
                    montant=round(random.uniform(1000.0, 50000.0), 2),
                    date_prevue=date_prevue,
                    date_initiale=date_prevue,
                    project_id=project.id,
                    est_facture=random.random() < 0.2
                )
                if random.random() < 0.3:
                    shift_days = random.randint(-30, 60)
                    livrable.date_prevue = date_prevue + datetime.timedelta(days=shift_days)
                    livrable.responsabilite_retard = random.choice(['Client', 'Entreprise'])
                    comment = LivrableComment(
                        contenu=f"Décalage de {shift_days} jours. Raison: {fake.sentence(nb_words=6)}",
                        livrable=livrable
                    )
                    session.add(comment)
                session.add(livrable)

            project_budget_factor = random.uniform(0.8, 1.3)
            created_tasks_in_project = []
            last_task_in_chain = None
            chain_length_remaining = 0
            for j in range(tasks_per_project):
                # Start a new chain if the previous one is finished or it's the first task
                if chain_length_remaining <= 0:
                    parente_task = None
                    chain_length_remaining = random.randint(3, 5)
                else:
                    parente_task = last_task_in_chain

                heures_prevues = round(random.uniform(4.0, 100.0), 2)
                duree_jours = max(1, int(heures_prevues / 8) + random.randint(-1, 2))
                initial_date_debut = fake.date_between(start_date=project.date_debut, end_date=project.date_debut + datetime.timedelta(days=30)) if not parente_task else None
                
                task = Task(
                    project=project, nom=fake.bs(), heures_prevues=heures_prevues,
                    duree_jours=duree_jours, position=j,
                    date_debut_calculee=initial_date_debut,
                    activity_type=random.choice(activity_types),
                    parente_id=parente_task.id if parente_task else None,
                    lag_days=random.randint(0, 3) if parente_task else 0
                )
                session.add(task)
                session.flush() # Flush to get ID for the next task in the chain
                
                created_tasks_in_project.append(task)
                last_task_in_chain = task
                chain_length_remaining -= 1
            
            session.flush()
            root_tasks = [t for t in created_tasks_in_project if t.parente_id is None]
            for root_task in root_tasks:
                controller._recalculate_task_and_dependents(root_task, session)

            for task in created_tasks_in_project:
                num_to_assign = min(2, len(users))
                assigned_users = random.sample(users, num_to_assign) if num_to_assign > 0 else []
                for user in assigned_users:
                    assignment = TaskAssignment(user=user, task=task, temps_alloue=heures_prevues / 2)
                    session.add(assignment)
                    total_logged_for_user = 0
                    target_hours = (heures_prevues / 2) * project_budget_factor
                    for _ in range(random.randint(1, entries_per_task + 2)):
                        if total_logged_for_user >= target_hours: break
                        logged_chunk = round(random.uniform(0.5, 8.0) * 2) / 2
                        if total_logged_for_user + logged_chunk > target_hours * 1.2:
                            logged_chunk = max(0, target_hours - total_logged_for_user)
                        if logged_chunk < 0.25 or not task.date_debut_calculee or task.date_debut_calculee > datetime.date.today(): continue
                        end_date_for_log = min(datetime.date.today(), task.date_fin if task.date_fin else datetime.date.today())
                        if task.date_debut_calculee > end_date_for_log: continue
                        log_date = fake.date_between(start_date=task.date_debut_calculee, end_date=end_date_for_log)
                        session.add(TimeEntry(user=user, task=task, project_id=project.id, date_performed=log_date, hours_spent=logged_chunk))
                        total_logged_for_user += logged_chunk
                    assignment.temps_pointe = total_logged_for_user
                    task.temps_passe_total += total_logged_for_user

        session.commit()
        print(f"{project_count} projets créés avec leurs tâches, affectations et pointages.")
    finally:
        session.close()

def main():
    """Fonction principale pour exécuter le processus de gestion de la BDD."""
    parser = argparse.ArgumentParser(
        description="Script de gestion et de peuplement de la base de données.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        '--sync-only', 
        action='store_true', 
        help="Exécute uniquement la synchronisation du schéma de la BDD (création/màj des tables) et quitte."
    )

    subparsers = parser.add_subparsers(dest='command', help='Commandes disponibles')

    subparsers.add_parser('init', help="Initialise la BDD pour la production (crée profils/admin si vide). Ne supprime rien.")
    subparsers.add_parser('clear', help="Supprime toutes les données des tables de l'application.")
    parser_seed = subparsers.add_parser('seed', help="Supprime les données et peuple la BDD avec des données de test.")
    seed_subparsers = parser_seed.add_subparsers(dest='level', required=True, help='Niveau de peuplement')
    
    seed_subparsers.add_parser('basic', help='Jeu de données minimal (3 utilisateurs/profils).')
    
    parser_full = seed_subparsers.add_parser('full', help='Jeu de données complet et réaliste.')
    parser_full.add_argument('--users', type=int, default=10, help='Nombre d\'utilisateurs à créer (défaut: 10).')
    parser_full.add_argument('--clients', type=int, default=20, help='Nombre de clients à créer (défaut: 20).')
    parser_full.add_argument('--projects', type=int, default=50, help='Nombre de projets à créer (défaut: 50).')
    parser_full.add_argument('--tasks', type=int, default=10, help='Nombre de tâches par projet (défaut: 10).')
    parser_full.add_argument('--entries', type=int, default=50, help='Nombre moyen de pointages par tâche (défaut: 50).')

    args = parser.parse_args()

    print("--- Étape 1: Synchronisation du schéma de la base de données ---")
    synchronize_database()
    print("--- Schéma de la base de données à jour. ---\n")

    if args.sync_only:
        print("Opération 'sync-only' terminée.")
        return

    if not args.command:
        print("Aucune commande spécifiée. Utilisez -h pour voir l'aide.")
        parser.print_help()
        return

    print(f"--- Étape 2: Exécution de la commande '{args.command}' ---")
    if args.command == 'init':
        init_production_data(verbose=True)
    elif args.command == 'clear':
        clear_data()
    elif args.command == 'seed':
        print(f"Niveau de peuplement : {args.level}")
        if args.level == 'basic':
            seed_basic_data()
        elif args.level == 'full':
            seed_full_data(
                nb_users=args.users,
                nb_clients=args.clients,
                nb_projects=args.projects,
                tasks_per_project=args.tasks,
                entries_per_task=args.entries
            )

if __name__ == "__main__":
    main()