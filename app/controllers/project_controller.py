import csv
import os
import datetime
from collections import defaultdict
from sqlalchemy.orm import sessionmaker, joinedload
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func
from app.models.base import engine
from app.models.schema import Project, Task, ActivityType, User, Client, TaskAssignment, ProjectStatus, TimeEntry, Profil, Company

Session = sessionmaker(bind=engine)

class ProjectController:

    def ensure_activity_types_exist(self, type_names):
        session = Session()
        try:
            existing_types = {t.nom for t in session.query(ActivityType).all()}
            missing_types = [name for name in type_names if name not in existing_types]
            if missing_types:
                for name in missing_types:
                    session.add(ActivityType(nom=name))
                session.commit()
            return True, "Activity types checked and created if necessary."
        except Exception as e:
            session.rollback()
            return False, str(e)
        finally:
            session.close()

    def get_all_clients(self):
        session = Session()
        try:
            clients = session.query(Client).filter(Client.is_visible == True).order_by(Client.name).all()
            return [{"id": c.id, "name": c.name, "code": c.code, "contact_info": c.contact_info} for c in clients]
        finally:
            session.close()

    def get_client_details(self, client_id):
        session = Session()
        try:
            client = session.query(Client).get(client_id)
            if not client: return None
            return {
                "id": client.id, "name": client.name, "code": client.code,
                "address": client.address, "phone": client.phone, "website": client.website,
                "contact_info": client.contact_info
            }
        finally:
            session.close()

    def add_client(self, data):
        session = Session()
        try:
            new_client = Client(
                name=data['name'], code=data.get('code'), address=data.get('address'),
                phone=data.get('phone'), website=data.get('website'),
                contact_info=data.get('contact_info')
            )
            session.add(new_client)
            session.commit()
            return True, "Client added successfully."
        except IntegrityError:
            session.rollback()
            return False, "Client name already exists."
        finally:
            session.close()

    def update_client(self, client_id, data):
        session = Session()
        try:
            client = session.query(Client).get(client_id)
            if not client: return False, "Client not found."
            client.name = data['name']
            client.code = data.get('code')
            client.address = data.get('address')
            client.phone = data.get('phone')
            client.website = data.get('website')
            client.contact_info = data.get('contact_info')
            session.commit()
            return True, "Client updated successfully."
        except IntegrityError:
            session.rollback()
            return False, "Another client with this name already exists."
        finally:
            session.close()

    def get_all_activity_type_names(self):
        session = Session()
        try:
            types = session.query(ActivityType.nom).all()
            return [t[0] for t in types]
        finally:
            session.close()

    def get_all_activity_types(self):
        session = Session()
        try:
            types = session.query(ActivityType.id, ActivityType.nom).order_by(ActivityType.nom).all()
            return [{"id": t.id, "name": t.nom} for t in types]
        finally:
            session.close()

    def get_project_managers(self):
        """Récupère les utilisateurs avec le profil 'Chef de projet'."""
        session = Session()
        try:
            users = session.query(User).join(Profil).filter(Profil.nom == "Chef de projet").order_by(User.nom).all()
            return [{"id": u.id, "name": f"{u.prenom} {u.nom}"} for u in users]
        finally:
            session.close()

    def get_all_project_managers(self):
        """Récupère les noms uniques des chefs de projet qui sont assignés à au moins un projet."""
        session = Session()
        try:
            # Utilise une sous-requête pour obtenir les ID uniques des chefs de projet à partir des projets
            pm_ids = session.query(Project.chef_de_projet_id).distinct().subquery()
            users = session.query(User).filter(User.id.in_(pm_ids)).order_by(User.nom, User.prenom).all()
            return [f"{u.prenom} {u.nom}" for u in users]
        finally:
            session.close()

    def get_all_users(self):
        session = Session()
        try:
            users = session.query(User.id, User.prenom, User.nom, User.username).all()
            return [{"id": u.id, "name": f"{u.prenom} {u.nom}", "username": u.username} for u in users]
        finally:
            session.close()

    def get_all_companies(self):
        session = Session()
        try:
            companies = session.query(Company).order_by(Company.name).all()
            return [{"id": c.id, "name": c.name} for c in companies]
        finally:
            session.close()

    def get_all_projects(self, search_term=""):
        session = Session()
        try:
            query = session.query(
                Project.id, Project.code, Project.nom,
                Client.name.label("client_name"), User.username.label("pm_username")
            ).join(Client).join(User)
            if search_term:
                search_filter = f"%{search_term}%"
                query = query.filter((Project.nom.like(search_filter)) | (Project.code.like(search_filter)))
            projects = query.all()
            return [dict(p._mapping) for p in projects]
        finally:
            session.close()

    def soft_delete_client(self, client_id):
        session = Session()
        try:
            client = session.query(Client).get(client_id)
            if not client: return False, "Client not found."
            client.is_visible = False
            session.commit()
            return True, "Le client a été retiré de la liste, mais ses données sont conservées pour l'historique des projets."
        except Exception as e:
            session.rollback()
            return False, f"An error occurred: {str(e)}"
        finally:
            session.close()

    def get_project_details(self, project_id):
        session = Session()
        try:
            project = session.query(Project).filter(Project.id == project_id).options(
                joinedload(Project.client), 
                joinedload(Project.chef_de_projet),
                joinedload(Project.company)
            ).one_or_none()
            if not project: return None
            return {
                "id": project.id, "code": project.code, "nom": project.nom,
                "client_id": project.client_id, "chef_de_projet_id": project.chef_de_projet_id, "date_debut": project.date_debut, 
                "statut": project.statut, "budget_material_planned": project.budget_material_planned,
                "company_id": project.company_id
            }
        finally:
            session.close()

    def create_project(self, data):
        session = Session()
        try:
            statut_value = data.get('statut')
            if isinstance(statut_value, str):
                statut_enum = ProjectStatus(statut_value)
            else:
                statut_enum = statut_value

            new_project = Project(
                code=data['code'],
                nom=data['nom'],
                chef_de_projet_id=data.get('chef_de_projet_id'),
                client_id=data.get('client_id'),
                company_id=data.get('company_id'),
                statut=statut_enum,
                date_debut=datetime.date.today(),
                budget_material_planned=data.get('budget_material_planned', 0.0)
            )
            
            session.add(new_project)
            session.commit()
            
            return True, new_project.id
        except IntegrityError:
            session.rollback()
            return False, f"Le code projet '{data.get('code')}' existe déjà."
        except Exception as e:
            session.rollback()
            return False, f"Une erreur inattendue est survenue : {str(e)}"
        finally:
            session.close()

    def update_project(self, project_id, data):
        session = Session()
        try:
            project = session.query(Project).filter_by(id=project_id).one_or_none()
            if not project:
                return False, "Projet non trouvé."
            for key, value in data.items():
                if key == "statut":
                    value = ProjectStatus(value)
                setattr(project, key, value)
            session.commit()
            return True, "Projet mis à jour avec succès."
        except Exception as e:
            session.rollback()
            return False, f"Une erreur est survenue : {str(e)}"
        finally:
            session.close()

    def get_project_tasks(self, project_id):
        session = Session()
        try:
            tasks = session.query(Task.id, Task.nom).filter_by(project_id=project_id).order_by(Task.position).all()
            return [{"id": t.id, "name": t.nom} for t in tasks]
        finally:
            session.close()

    def get_project_tasks_for_display(self, project_id):
        session = Session()
        try:
            tasks = session.query(Task).options(joinedload(Task.activity_type)).filter(Task.project_id == project_id).order_by(Task.position).all()
            if not tasks:
                return []

            # --- CPM Calculation ---
            task_map = {t.id: t for t in tasks}
            
            # 1. Forward Pass is assumed to be correct from _recalculate_task_and_dependents
            # Find project end date (max Early Finish)
            project_end_date = max((t.date_fin for t in tasks if t.date_fin), default=None)
            if not project_end_date:
                project = session.query(Project).get(project_id)
                project_end_date = project.date_debut if project else datetime.date.today()

            # 2. Backward Pass
            # Initialize Latest Start (LS) and Latest Finish (LF)
            cpm_data = {t.id: {'ls': None, 'lf': None} for t in tasks}
            
            # Identify children for each task
            children_map = defaultdict(list)
            for task in tasks:
                if task.parente_id:
                    children_map[task.parente_id].append(task)

            # Start backward pass from tasks with no children
            for task in reversed(tasks):
                if not children_map.get(task.id):
                    # This is a terminal task (or has no children in the current set)
                    cpm_data[task.id]['lf'] = project_end_date
                else:
                    # LF is the minimum of the LS of its direct children, considering lag
                    child_latest_starts = [
                        (cpm_data[child.id]['ls'] - datetime.timedelta(days=child.lag_days or 0))
                        for child in children_map[task.id] if cpm_data[child.id]['ls'] is not None
                    ]
                    if child_latest_starts:
                        min_ls = min(child_latest_starts)
                        cpm_data[task.id]['lf'] = min_ls - datetime.timedelta(days=1)
                    else:
                        # If no processed children are found, treat as a terminal task for this pass.
                        cpm_data[task.id]['lf'] = project_end_date
                
                duration = task.duree_jours or 1
                cpm_data[task.id]['ls'] = cpm_data[task.id]['lf'] - datetime.timedelta(days=duration - 1)

            # 3. Calculate Float (Total Slack) and determine critical path
            for task in tasks:
                if task.date_debut_calculee and cpm_data[task.id].get('ls'):
                    early_start = task.date_debut_calculee
                    latest_start = cpm_data[task.id]['ls']
                    float_days = (latest_start - early_start).days
                    cpm_data[task.id]['is_critical'] = float_days <= 0
                else:
                    cpm_data[task.id]['is_critical'] = False

            # 4. Format output
            return [{
                "id": t.id, "nom": t.nom, "activity_type": t.activity_type.nom,
                "date_debut_calculee": t.date_debut_calculee, "heures_prevues": t.heures_prevues,
                "duree_jours": t.duree_jours, "date_fin": t.date_fin, "parente_id": t.parente_id, "lag_days": t.lag_days,
                "position": t.position,
                "is_critical": cpm_data[t.id].get('is_critical', False)
            } for t in tasks]
        finally:
            session.close()

    def get_task_details(self, task_id):
        session = Session()
        try:
            task = session.query(Task).options(
                joinedload(Task.user_assignments).joinedload(TaskAssignment.user), 
                joinedload(Task.activity_type)
            ).filter(Task.id == task_id).one_or_none()
            if not task: return None

            # Get all time entries for this task at once for efficiency
            time_entries_by_user = defaultdict(float)
            time_entries = session.query(
                TimeEntry.user_id, func.sum(TimeEntry.hours_spent)
            ).filter(TimeEntry.task_id == task_id).group_by(TimeEntry.user_id).all()
            for user_id, total_hours in time_entries:
                time_entries_by_user[user_id] = total_hours

            assignments_data = []
            for a in task.user_assignments:
                assignments_data.append({
                    "user_id": a.user_id,
                    "temps_alloue": a.temps_alloue,
                    "temps_pointe": time_entries_by_user.get(a.user_id, 0.0)
                })

            return {
                "id": task.id, "nom": task.nom, "activity_type_name": task.activity_type.nom,
                "heures_prevues": task.heures_prevues, "duree_jours": task.duree_jours,
                "parente_id": task.parente_id, "date_debut_calculee": task.date_debut_calculee, "lag_days": task.lag_days,
                "assignments": assignments_data
            }
        finally:
            session.close()

    def add_task(self, project_id, data):
        session = Session()
        try:
            activity_type = session.query(ActivityType).filter_by(nom=data["activity_type_name"]).first()
            if not activity_type: return False, f"Type d'activité '{data['activity_type_name']}' non trouvé."
            
            last_task = session.query(Task).filter_by(project_id=project_id).order_by(Task.position.desc()).first()
            new_position = (last_task.position + 1) if last_task and last_task.position is not None else 0
            
            new_task = Task(
                project_id=project_id,
                nom=data["nom"],
                heures_prevues=data["heures_prevues"],
                duree_jours=data["duree_jours"],
                position=new_position,
                date_debut_calculee=data["date_debut"],
                lag_days=data.get("lag_days", 0),
                activity_type_id=activity_type.id,
                parente_id=data["parente_id"]
            )
            session.add(new_task)
            session.flush()

            if "assignments" in data:
                for assign_data in data.get("assignments", []):
                    if assign_data.get("user_id") and assign_data.get("temps_alloue") is not None:
                        session.add(TaskAssignment(task_id=new_task.id, user_id=assign_data["user_id"], temps_alloue=assign_data["temps_alloue"]))
            
            self._recalculate_task_and_dependents(new_task, session)
            session.commit()
            return True, "Tâche ajoutée avec succès."
        except Exception as e:
            session.rollback()
            return False, f"Erreur inattendue : {str(e)}"
        finally:
            session.close()

    def update_task(self, task_id, new_data):
        session = Session()
        try:
            task = session.query(Task).options(joinedload(Task.user_assignments)).filter(Task.id == task_id).one_or_none()
            if not task: return False, "Tâche non trouvée."

            if "activity_type_name" in new_data:
                activity_type = session.query(ActivityType).filter_by(nom=new_data.pop("activity_type_name")).first()
                if activity_type: task.activity_type_id = activity_type.id
            
            if "assignments" in new_data:
                # Clear existing assignments
                for old_assignment in task.user_assignments:
                    session.delete(old_assignment)
                session.flush()
                # Add new ones
                for assign_data in new_data.pop("assignments"):
                    if assign_data.get("user_id") and assign_data.get("temps_alloue") is not None:
                        session.add(TaskAssignment(task_id=task.id, user_id=assign_data["user_id"], temps_alloue=assign_data["temps_alloue"]))

            if "date_debut" in new_data:
                task.date_debut_calculee = new_data.pop("date_debut")

            for key, value in new_data.items():
                setattr(task, key, value)
            
            self._recalculate_task_and_dependents(task, session)
            session.commit()
            return True, "Tâche mise à jour avec succès."
        except Exception as e:
            session.rollback()
            return False, f"Erreur inattendue : {str(e)}"
        finally:
            session.close()

    def update_task_assignments(self, task_id, assignments_data):
        session = Session()
        try:
            task = session.query(Task).options(joinedload(Task.user_assignments)).filter(Task.id == task_id).one_or_none()
            if not task:
                return False, "Tâche non trouvée."

            # Clear existing assignments
            for old_assignment in task.user_assignments:
                session.delete(old_assignment)
            session.flush()

            # Add new ones
            for assign_data in assignments_data:
                if assign_data.get("user_id") and assign_data.get("temps_alloue") is not None:
                    session.add(TaskAssignment(task_id=task.id, user_id=assign_data["user_id"], temps_alloue=assign_data["temps_alloue"]))
            
            session.commit()
            return True, "Affectations mises à jour avec succès."
        except Exception as e:
            session.rollback()
            return False, f"Erreur lors de la mise à jour des affectations : {str(e)}"
        finally:
            session.close()

    def update_task_order(self, project_id, ordered_task_ids):
        session = Session()
        try:
            tasks = session.query(Task).filter(Task.project_id == project_id).all()
            task_map = {task.id: task for task in tasks}
            
            for index, task_id in enumerate(ordered_task_ids):
                if task_id in task_map:
                    task_map[task_id].position = index
            
            session.commit()
            return True, "Task order updated successfully."
        except Exception as e:
            session.rollback()
            return False, f"Failed to update task order: {str(e)}"
        finally:
            session.close()

    def _recalculate_task_and_dependents(self, task, session):
        date_debut = task.date_debut_calculee
        if task.parente_id:
            parente_task = session.query(Task).get(task.parente_id)
            if parente_task and parente_task.date_fin:
                date_debut = parente_task.date_fin + datetime.timedelta(days=1 + (task.lag_days or 0))
        
        # Fallback for root tasks or orphans without a start date
        if date_debut is None:
            project = session.query(Project).get(task.project_id)
            date_debut = project.date_debut

        duree = task.duree_jours or 1
        task.date_debut_calculee = date_debut
        task.date_fin = date_debut + datetime.timedelta(days=duree - 1) if duree > 0 else date_debut
        
        # Recurse for children, ensuring they are processed in a defined order
        children = session.query(Task).filter(Task.parente_id == task.id).order_by(Task.position).all()
        for child in children:
            self._recalculate_task_and_dependents(child, session)

    def get_matrix_dashboard_data(self, company_id=None, year=None, project_manager_name=None, ongoing_only=True):
        session = Session()
        try:            
            # 1. Récupérer tous les projets et leurs chefs de projet.
            project_query = session.query(Project).options(joinedload(Project.chef_de_projet))

            if company_id:
                project_query = project_query.filter(Project.company_id == company_id)

            if project_manager_name:
                # Jointure explicite nécessaire pour le filtrage
                project_query = project_query.join(User, Project.chef_de_projet_id == User.id)\
                                             .filter(func.concat(User.prenom, ' ', User.nom) == project_manager_name)

            if ongoing_only:
                project_query = project_query.filter(Project.statut != ProjectStatus.TERMINE)

            if year:
                start_of_year = datetime.date(year, 1, 1)
                end_of_year = datetime.date(year, 12, 31)
                # Filtre les projets ayant au moins une tâche qui chevauche l'année sélectionnée.
                # .any() génère une sous-requête EXISTS efficace.
                project_query = project_query.filter(
                    Project.tasks.any(
                        (Task.date_debut_calculee <= end_of_year) & (Task.date_fin >= start_of_year)
                    )
                )

            projects = project_query.all()
            if not projects:
                return []

            project_map = {p.id: p for p in projects}
            project_ids = list(project_map.keys())

            # 2. Exécuter une seule requête pour agréger les données de tâches pour tous les projets.
            # Cela remplace les boucles Python par un traitement SQL beaucoup plus rapide.
            task_aggregates = session.query(
                Task.project_id,
                ActivityType.nom.label('activity_name'),
                func.sum(Task.heures_prevues).label('planned'),
                func.sum(Task.temps_passe_total).label('logged')
            ).join(Task.activity_type)\
             .filter(Task.project_id.in_(project_ids))\
             .group_by(Task.project_id, ActivityType.nom)\
             .all()

            # 3. Construire la structure de données finale en Python à partir des résultats pré-agrégés.
            summary_data = {
                pid: {
                    'project_id': p.id, 'project_name': p.nom, 'project_code': p.code,
                    'project_manager': f"{p.chef_de_projet.prenom} {p.chef_de_projet.nom}" if p.chef_de_projet else "N/A",
                    'project_status': p.statut.value,
                    'total_planned': 0.0, 'total_logged': 0.0,
                    'budget_material_planned': p.budget_material_planned or 0.0,
                    'budget_material_spent': p.budget_material_spent or 0.0,
                    'activities': defaultdict(lambda: {'planned': 0.0, 'logged': 0.0})
                } for pid, p in project_map.items()
            }

            for agg in task_aggregates:
                p_data = summary_data.get(agg.project_id)
                if not p_data: continue

                planned_hours = agg.planned or 0.0
                logged_hours = agg.logged or 0.0
                
                p_data['activities'][agg.activity_name]['planned'] += planned_hours
                p_data['activities'][agg.activity_name]['logged'] += logged_hours
                p_data['total_planned'] += planned_hours
                p_data['total_logged'] += logged_hours

            return list(summary_data.values())
        finally:
            session.close()

    def get_weekly_time_summary(self, start_date, end_date, user_id, project_filter=None):
        session = Session()
        try:
            query = session.query(
                TimeEntry.date_performed,
                TimeEntry.hours_spent,
                Project.id.label('project_id'),
                Project.code.label('project_code'),
                Project.nom.label('project_name'),
                Task.nom.label('task_name')
            ).join(Project, TimeEntry.project_id == Project.id)\
             .join(Task, TimeEntry.task_id == Task.id)

            # Filter by date range
            query = query.filter(TimeEntry.date_performed.between(start_date, end_date))

            # Filter by user if specified
            if user_id:
                query = query.filter(TimeEntry.user_id == user_id)
            # Add project filter if provided
            if project_filter:
                search_pattern = f"%{project_filter}%"
                query = query.filter(
                    (Project.code.like(search_pattern)) | (Project.nom.like(search_pattern))
                )

            all_entries = query.all()

            # Process data in Python
            # structure: { (year, week_num): {project_id: {'code': ..., 'name': ..., 'tasks': {task_name: [mon, tue, ...]}}}}
            weekly_data = defaultdict(lambda: defaultdict(lambda: {
                'code': '',
                'name': '',
                'tasks': defaultdict(lambda: [0.0] * 7)
            }))

            for entry in all_entries:
                iso_year, week_num, day_of_week = entry.date_performed.isocalendar()

                week_key = (iso_year, week_num)
                project_id = entry.project_id
                project_data = weekly_data[week_key][project_id]
                project_data['code'] = entry.project_code
                project_data['name'] = entry.project_name
                project_data['tasks'][entry.task_name][day_of_week - 1] += entry.hours_spent
            
            # Convert to a more structured list for the view
            result = []
            # Sort by year, then week number, descending
            for (year, week_num), projects_data in sorted(weekly_data.items(), key=lambda item: item[0], reverse=True):
                week_projects = []
                week_total = 0.0
                for project_id, project_details in projects_data.items():
                    project_tasks = []
                    project_total = 0.0
                    for task_name, hours_by_day in project_details['tasks'].items():
                        task_total = sum(hours_by_day)
                        project_tasks.append({'name': task_name, 'hours': hours_by_day, 'total': task_total})
                        project_total += task_total
                    
                    week_projects.append({
                        'code': project_details['code'],
                        'name': project_details['name'],
                        'tasks': sorted(project_tasks, key=lambda x: x['name']),
                        'total': project_total
                    })
                    week_total += project_total
                
                result.append({
                    'week_num': week_num, 
                    'year': year, 
                    'projects': sorted(week_projects, key=lambda x: x['name']), 
                    'total': week_total
                })

            return result
        finally:
            session.close()

    def get_global_project_summary(self):
        session = Session()
        try:
            # Single query to get all projects and their aggregated task data
            task_aggregates = session.query(
                Project.id.label('project_id'),
                Project.nom.label('project_name'),
                Project.code.label('project_code'),
                ActivityType.nom.label('activity_name'),
                func.sum(Task.heures_prevues).label('planned'),
                func.sum(Task.temps_passe_total).label('logged')
            ).join(Task, Project.tasks) \
             .join(ActivityType, Task.activity_type) \
             .group_by(Project.id, Project.nom, Project.code, ActivityType.nom) \
             .all()

            # Process the aggregated data in Python
            summary_data = defaultdict(lambda: {
                'total_planned': 0.0,
                'total_logged': 0.0,
                'activity_summary': defaultdict(lambda: {'planned': 0.0, 'logged': 0.0})
            })

            for agg in task_aggregates:
                project_data = summary_data[agg.project_id]
                project_data['project_id'] = agg.project_id
                project_data['project_name'] = agg.project_name
                project_data['project_code'] = agg.project_code
                
                planned_hours = agg.planned or 0.0
                logged_hours = agg.logged or 0.0
                
                project_data['activity_summary'][agg.activity_name]['planned'] += planned_hours
                project_data['activity_summary'][agg.activity_name]['logged'] += logged_hours
                project_data['total_planned'] += planned_hours
                project_data['total_logged'] += logged_hours
            
            # Convert the defaultdict to a list of dictionaries
            summary_list = []
            for project_id, data in summary_data.items():
                data['activity_summary'] = [
                    {'activity_name': name, 'planned': d['planned'], 'logged': d['logged']}
                    for name, d in sorted(data['activity_summary'].items())
                ]
                summary_list.append(data)

            return sorted(summary_list, key=lambda x: x['project_name'])
        finally:
            session.close()
    
    def get_tasks_for_user(self, user_id):
        session = Session()
        try:
            # Query specific columns to avoid loading the full Task object,
            # which prevents crashing if the 'position' column is missing from the DB.
            assignments = session.query(TaskAssignment).join(Task).join(Project).filter(
                TaskAssignment.user_id == user_id,
                Project.statut == ProjectStatus.EN_COURS
            ).options(
                joinedload(TaskAssignment.task).joinedload(Task.project)
            ).all()
            
            task_list = []
            for assignment in assignments:
                task = assignment.task
                if not task: continue

                # Recalculate spent time for the specific user on that task
                logged_by_user = session.query(func.sum(TimeEntry.hours_spent)).filter(
                    TimeEntry.task_id == task.id,
                    TimeEntry.user_id == user_id
                ).scalar() or 0.0

                task_list.append({
                    "task_id": task.id,
                    "task_name": task.nom,
                    "project_name": task.project.nom,
                    "temps_alloue": assignment.temps_alloue,
                    "temps_passe_total": logged_by_user, # Show time logged by user, not total on task
                })
            return task_list
        finally:
            session.close()
    def log_time_for_task(self, user_id, task_id, heures, date_saisie):
        session = Session()
        try:
            task = session.query(Task).filter_by(id=task_id).one_or_none()
            if not task:
                return False, "Tâche non trouvée."

            new_entry = TimeEntry(
                user_id=user_id,
                task_id=task_id,
                project_id=task.project_id,
                date_performed=date_saisie,
                hours_spent=heures
            )
            session.add(new_entry)

            if task.temps_passe_total is None:
                task.temps_passe_total = 0.0
            task.temps_passe_total += heures
            
            session.commit()
            return True, "Temps imputé avec succès."
        except Exception as e:
            session.rollback()
            return False, f"Une erreur est survenue : {str(e)}"
        finally:
            session.close()

    def get_time_entries_report(self, start_date, end_date, user_id=None, project_id=None, activity_type_id=None):
        session = Session()
        try:
            query = session.query(
                TimeEntry.date_performed,
                TimeEntry.hours_spent,
                User.prenom,
                User.nom,
                Project.code,
                Task.nom,
                ActivityType.nom.label('activity_type_name')
            ).join(User, TimeEntry.user_id == User.id)\
             .join(Project, TimeEntry.project_id == Project.id)\
             .join(Task, TimeEntry.task_id == Task.id)\
             .join(ActivityType, Task.activity_type_id == ActivityType.id)

            query = query.filter(TimeEntry.date_performed.between(start_date, end_date))

            if user_id:
                query = query.filter(TimeEntry.user_id == user_id)
            
            if project_id:
                query = query.filter(TimeEntry.project_id == project_id)

            if activity_type_id:
                query = query.filter(Task.activity_type_id == activity_type_id)

            results = query.order_by(TimeEntry.date_performed).all()

            return [{
                'date_performed': date,
                'user_name': f"{user_prenom} {user_nom}",
                'project_code': project_code,
                'task_name': task_name,
                'activity_type_name': activity_type_name,
                'hours_spent': hours
            } for date, hours, user_prenom, user_nom, project_code, task_name, activity_type_name in results]
        finally:
            session.close()

    def update_assignment_hours(self, task_id, user_id, hours):
        session = Session()
        try:
            assignment = session.query(TaskAssignment).filter_by(
                task_id=task_id, 
                user_id=user_id
            ).one_or_none()

            if assignment:
                assignment.temps_alloue = hours
                session.commit()
                return True, "Heures allouées mises à jour."
            else:
                return False, "Affectation non trouvée."
        except Exception as e:
            session.rollback()
            return False, f"Erreur lors de la mise à jour : {str(e)}"
        finally:
            session.close()
			
    def get_all_deliverables_and_milestones(self):
        session = Session()
        try:
            from app.models.schema import Livrable
            events = []
            
            # Récupérer les tâches jalons
            milestones = session.query(Task, Project.nom.label("project_name")) \
                                .join(Project, Task.project_id == Project.id) \
                                .filter(Task.is_milestone == True).all()
            for task, project_name in milestones:
                if task.date_fin:
                    events.append({
                        "name": task.nom,
                        "date": task.date_fin.isoformat(),
                        "type": "Jalon",
                        "project_name": project_name
                    })

            # Récupérer les livrables
            livrables = session.query(Livrable, Project.nom.label("project_name")) \
                                  .join(Project, Livrable.project_id == Project.id) \
                                  .all()
            for livrable, project_name in livrables:
                if livrable.date_prevue:
                    events.append({
                        "name": livrable.nom,
                        "date": livrable.date_prevue.isoformat(),
                        "type": "Livrable",
                        "project_name": project_name
                    })

            return events
        finally:
            session.close()

    def export_project_to_csv(self, project_id):
        session = Session()
        try:
            project = session.query(Project).options(
                joinedload(Project.tasks).joinedload(Task.user_assignments).joinedload(TaskAssignment.user)
            ).filter(Project.id == project_id).one_or_none()

            if not project:
                return False, "Project not found."

            export_dir = "export"
            os.makedirs(export_dir, exist_ok=True)
            safe_project_name = "".join(c for c in project.nom if c.isalnum() or c in (' ', '_')).rstrip()
            filepath = os.path.join(export_dir, f"export_{safe_project_name}_{datetime.date.today()}.csv")

            with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['Nom Projet', 'Nom Tâche', 'Utilisateur', 'Heures Prévues', 'Heures Pointées'])
                
                for task in project.tasks:
                    if not task.user_assignments:
                        writer.writerow([project.nom, task.nom, "Non assignée", task.heures_prevues, 0])
                    else:
                        for assignment in task.user_assignments:
                            user = assignment.user
                            writer.writerow([
                                project.nom, task.nom, 
                                f"{user.prenom} {user.nom}", 
                                assignment.temps_alloue, 
                                assignment.temps_pointe
                            ])
            return True, os.path.abspath(filepath)
        except Exception as e:
            return False, f"An error occurred during CSV export: {str(e)}"
        finally:
            session.close()
