import datetime
from collections import defaultdict
from sqlalchemy.orm import sessionmaker, joinedload
from sqlalchemy import func, select, case, and_
from app.models.base import engine
from app.models.schema import Project, Livrable, ProjectStatus, LivrableComment, User, Company, ActivityType, Task, Client

Session = sessionmaker(bind=engine)

class DeliverableController:
    def get_ongoing_projects(self, year, month=None, company_id=None):
        """Récupère les projets 'En cours' avec le nom du chef de projet et le montant total des livrables."""
        session = Session()
        try:
            # Subquery to calculate the total amount for each project
            total_amount_subquery = (
                select(
                    Livrable.project_id,
                    func.sum(Livrable.montant).label("total_amount")
                )
                .group_by(Livrable.project_id)
                .subquery()
            )

            query = session.query(
                Project,
                func.coalesce(total_amount_subquery.c.total_amount, 0).label("total_amount")
            ).outerjoin(
                total_amount_subquery, Project.id == total_amount_subquery.c.project_id
            ).options(joinedload(Project.chef_de_projet)).filter(Project.statut == ProjectStatus.EN_COURS)
            
            if company_id:
                query = query.filter(Project.company_id == company_id)

            if month:
                query = query.join(Livrable).filter(
                    func.extract('year', Livrable.date_prevue) == year,
                    func.extract('month', Livrable.date_prevue) == month
                ).distinct()

            projects_with_totals = query.order_by(Project.nom).all()
            result = []
            for p, total_amount in projects_with_totals:
                pm_fullname = f"{p.chef_de_projet.prenom} {p.chef_de_projet.nom}" if p.chef_de_projet else "N/A"
                pm_username = p.chef_de_projet.username if p.chef_de_projet else "N/A"
                result.append({
                    "id": p.id,
                    "code": p.code,
                    "name": p.nom,
                    "project_manager": pm_username,
                    "project_manager_fullname": pm_fullname,
                    "total_amount": total_amount or 0.0
                })
            return result
        finally:
            session.close()

    def get_all_projects_summary(self, year, month=None, company_id=None):
        """Récupère tous les projets avec le nom du chef de projet et le montant total des livrables."""
        session = Session()
        try:
            # Subquery to calculate the total amount for each project
            total_amount_subquery = (
                select(
                    Livrable.project_id,
                    func.sum(Livrable.montant).label("total_amount")
                )
                .group_by(Livrable.project_id)
                .subquery()
            )

            query = session.query(
                Project,
                func.coalesce(total_amount_subquery.c.total_amount, 0).label("total_amount")
            ).outerjoin(
                total_amount_subquery, Project.id == total_amount_subquery.c.project_id
            ).options(joinedload(Project.chef_de_projet))
            
            if company_id:
                query = query.filter(Project.company_id == company_id)

            if month:
                query = query.join(Livrable).filter(
                    func.extract('year', Livrable.date_prevue) == year,
                    func.extract('month', Livrable.date_prevue) == month
                ).distinct()

            projects_with_totals = query.order_by(Project.nom).all()
            result = []
            for p, total_amount in projects_with_totals:
                pm_fullname = f"{p.chef_de_projet.prenom} {p.chef_de_projet.nom}" if p.chef_de_projet else "N/A"
                pm_username = p.chef_de_projet.username if p.chef_de_projet else "N/A"
                result.append({
                    "id": p.id,
                    "code": p.code,
                    "name": p.nom,
                    "project_manager": pm_username,
                    "project_manager_fullname": pm_fullname,
                    "total_amount": total_amount or 0.0
                })
            return result
        finally:
            session.close()

    def add_deliverable(self, project_id, data):
        """Crée un livrable (nom, montant, date)."""
        session = Session()
        try:
            new_livrable = Livrable(
                project_id=project_id,
                nom=data['nom'],
                montant=data['montant'],
                date_prevue=data['date_prevue'],
                date_initiale=data['date_prevue']
            )
            session.add(new_livrable)
            session.commit()
            return True, "Livrable ajouté avec succès."
        except Exception as e:
            session.rollback()
            return False, str(e)
        finally:
            session.close()

    def add_comment(self, livrable_id, content):
        """Ajoute un commentaire à un livrable."""
        session = Session()
        try:
            comment = LivrableComment(livrable_id=livrable_id, contenu=content)
            session.add(comment)
            session.commit()
            return True, "Commentaire ajouté."
        except Exception as e:
            session.rollback()
            return False, str(e)
        finally:
            session.close()

    def get_deliverable_comments(self, livrable_id):
        """Récupère l'historique chronologique des commentaires pour un livrable."""
        session = Session()
        try:
            comments = session.query(LivrableComment).filter_by(livrable_id=livrable_id).order_by(LivrableComment.date_creation.asc()).all()
            return [{
                'contenu': c.contenu,
                'date_creation': c.date_creation
            } for c in comments]
        finally:
            session.close()

    def get_comments(self, livrable_id):
        """Récupère les commentaires pour un livrable."""
        session = Session()
        try:
            comments = session.query(LivrableComment).filter_by(livrable_id=livrable_id).order_by(LivrableComment.date_creation.desc()).all()
            return [{
                'id': c.id,
                'contenu': c.contenu,
                'date_creation': c.date_creation
            } for c in comments]
        finally:
            session.close()

    def delete_deliverable(self, deliverable_id):
        """Supprime un livrable."""
        session = Session()
        try:
            livrable = session.query(Livrable).get(deliverable_id)
            if not livrable:
                return False, "Livrable non trouvé."
            session.delete(livrable)
            session.commit()
            return True, "Livrable supprimé."
        except Exception as e:
            session.rollback()
            return False, str(e)
        finally:
            session.close()

    def get_project_deliverables(self, project_id):
        """Récupère la liste des livrables d'un projet."""
        session = Session()
        try:
            livrables = session.query(Livrable).filter(Livrable.project_id == project_id).order_by(Livrable.date_prevue).all()
            return [{
                "id": l.id,
                "nom": l.nom,
                "montant": l.montant,
                "date_prevue": l.date_prevue,
                "est_facture": l.est_facture,
                "date_initiale": l.date_initiale,
                "responsabilite_retard": l.responsabilite_retard
            } for l in livrables]
        finally:
            session.close()

    def get_yearly_forecast(self, year, company_id=None):
        """Retourne une structure de données pour le tableau de droite (prévisions).
        Ne somme que les livrables NON facturés."""
        session = Session()
        try:
            query = session.query(Livrable).join(Project).filter(
                func.extract('year', Livrable.date_prevue) == year,
                Project.statut == ProjectStatus.EN_COURS,
                Livrable.est_facture == False
            )
            if company_id:
                query = query.filter(Project.company_id == company_id)
            livrables = query.options(joinedload(Livrable.project)).all()

            forecast_data = defaultdict(lambda: {
                'name': '',
                'monthly_totals': [0.0] * 12
            })
            
            monthly_grand_totals = [0.0] * 12
            yearly_grand_total = 0.0

            for l in livrables:
                month_index = l.date_prevue.month - 1
                project_data = forecast_data[l.project_id]
                project_data['name'] = f"{l.project.code} - {l.project.nom}"
                project_data['monthly_totals'][month_index] += l.montant
                
                monthly_grand_totals[month_index] += l.montant
                yearly_grand_total += l.montant

            project_forecasts = [
                {'project_id': pid, 'project_name': data['name'], 'monthly_totals': data['monthly_totals']}
                for pid, data in forecast_data.items()
            ]

            return {
                'project_forecasts': sorted(project_forecasts, key=lambda x: x['project_name']),
                'monthly_grand_totals': monthly_grand_totals,
                'yearly_grand_total': yearly_grand_total
            }
        finally:
            session.close()

    def toggle_deliverable_invoiced_status(self, deliverable_id):
        """Bascule le statut 'facturé' d'un livrable."""
        session = Session()
        try:
            livrable = session.query(Livrable).get(deliverable_id)
            if not livrable:
                return False, "Livrable non trouvé."
            
            livrable.est_facture = not livrable.est_facture
            session.commit()
            status_text = "facturé" if livrable.est_facture else "non facturé"
            return True, f"Livrable marqué comme {status_text}."
        except Exception as e:
            session.rollback()
            return False, str(e)
        finally:
            session.close()

    def shift_deliverable(self, deliverable_id, new_date, responsabilite):
        """Met à jour la date prévue d'un livrable et la responsabilité du décalage."""
        session = Session()
        try:
            livrable = session.query(Livrable).get(deliverable_id)
            if not livrable:
                return False, "Livrable non trouvé."
            
            if livrable.date_initiale is None:
                livrable.date_initiale = livrable.date_prevue
            
            livrable.date_prevue = new_date
            livrable.responsabilite_retard = responsabilite
            session.commit()
            return True, "Date du livrable mise à jour."
        except Exception as e:
            session.rollback()
            return False, str(e)
        finally:
            session.close()

    def get_monthly_totals_for_year(self, year, company_id=None):
        """Calcule les totaux mensuels planifiés (tous) et facturés sur une période de 24 mois autour de l'année donnée."""
        session = Session()
        try:
            start_date = datetime.date(year - 1, 7, 1)
            end_date = datetime.date(year + 1, 6, 30)

            # Base queries
            planned_query = session.query(
                func.extract('year', Livrable.date_prevue),
                func.extract('month', Livrable.date_prevue),
                func.sum(Livrable.montant)
            ).filter(Livrable.date_prevue.between(start_date, end_date))

            billed_query = session.query(
                func.extract('year', Livrable.date_prevue),
                func.extract('month', Livrable.date_prevue),
                func.sum(Livrable.montant)
            ).filter(
                Livrable.date_prevue.between(start_date, end_date),
                Livrable.est_facture == True
            )

            if company_id:
                planned_query = planned_query.join(Project).filter(Project.company_id == company_id)
                billed_query = billed_query.join(Project).filter(Project.company_id == company_id)

            # 1. Total planifié
            planned_results = planned_query.group_by(func.extract('year', Livrable.date_prevue), func.extract('month', Livrable.date_prevue)).all()

            total_planned = defaultdict(float)
            for res_year, res_month, total in planned_results:
                if res_year is not None and res_month is not None and total is not None:
                    total_planned[(int(res_year), int(res_month))] = float(total)

            # 2. Total facturé
            billed_results = billed_query.group_by(func.extract('year', Livrable.date_prevue), func.extract('month', Livrable.date_prevue)).all()

            total_billed = defaultdict(float)
            for res_year, res_month, total in billed_results:
                if res_year is not None and res_month is not None and total is not None:
                    total_billed[(int(res_year), int(res_month))] = float(total)
            
            return {
                "planned": total_planned,
                "billed": total_billed
            }
        finally:
            session.close()

    def get_yearly_deliverables_by_project(self, year, company_id=None):
        """Récupère tous les livrables sur une période de 24 mois, groupés par projet."""
        session = Session()
        try:
            start_date = datetime.date(year - 1, 7, 1)
            end_date = datetime.date(year + 1, 6, 30)
            query = session.query(Livrable).join(Project).filter(
                Livrable.date_prevue.between(start_date, end_date),
                Project.statut == ProjectStatus.EN_COURS
            )
            if company_id:
                query = query.filter(Project.company_id == company_id)
            livrables = query.options(joinedload(Livrable.project)).order_by(Project.nom, Livrable.date_prevue).all()

            projects_data = defaultdict(lambda: {
                'project_id': None,
                'project_name': '',
                'project_code': '',
                'deliverables': []
            })

            for l in livrables:
                p_data = projects_data[l.project_id]
                p_data['project_id'] = l.project.id
                p_data['project_name'] = l.project.nom
                p_data['project_code'] = l.project.code

                # Récupérer le dernier commentaire pour ce livrable
                last_comment_obj = session.query(LivrableComment).filter(LivrableComment.livrable_id == l.id).order_by(LivrableComment.date_creation.desc()).first()
                last_comment = last_comment_obj.contenu if last_comment_obj else None

                p_data['deliverables'].append({
                    'id': l.id, 'nom': l.nom, 'montant': l.montant,
                    'date_prevue': l.date_prevue, 'date_initiale': l.date_initiale,
                    'est_facture': l.est_facture,
                    'responsabilite_retard': l.responsabilite_retard,
                    'last_comment': last_comment
                })
            
            return sorted(projects_data.values(), key=lambda p: p['project_name'])
        finally:
            session.close()

    def get_available_years(self, company_id=None):
        """Returns a sorted list of unique years found in deliverables for a given company."""
        session = Session()
        try:
            query = session.query(func.extract('year', Livrable.date_prevue)).distinct()

            if company_id:
                query = query.join(Project).filter(Project.company_id == company_id)

            years = [year[0] for year in query.all() if year[0] is not None]
            # Return sorted in descending order for better UX
            return sorted(list(set(years)), reverse=True)
        finally:
            session.close()

    def get_financial_stats(self, year, user_id=None, company_id=None):
        """Calcule les statistiques financières pour une année donnée, en utilisant les objectifs de la société de l'utilisateur."""
        session = Session()
        try:
            # 1. Récupérer les objectifs de la société
            if company_id:
                # Objectifs pour une seule société
                company = session.query(Company).get(company_id)
                if company:
                    objectives = {
                        'objective_point_mort': company.objective_point_mort or 0.0,
                        'objective_1': company.objective_1 or 0.0,
                        'objective_2': company.objective_2 or 0.0
                    }
                else:
                    objectives = {'objective_point_mort': 0.0, 'objective_1': 0.0, 'objective_2': 0.0}
            else:
                # Objectifs pour "Toutes les sociétés" : on somme les objectifs de toutes les sociétés
                total_objectives = session.query(
                    func.sum(Company.objective_point_mort),
                    func.sum(Company.objective_1),
                    func.sum(Company.objective_2)
                ).one()
                objectives = {
                    'objective_point_mort': total_objectives[0] or 0.0,
                    'objective_1': total_objectives[1] or 0.0,
                    'objective_2': total_objectives[2] or 0.0
                }

            # --- New Queries for KPI View ---
            # 6. Activity Distribution (based on planned hours in relevant projects)
            project_ids_in_year_query = session.query(Project.id).join(Livrable).filter(func.extract('year', Livrable.date_prevue) == year)
            if company_id:
                project_ids_in_year_query = project_ids_in_year_query.filter(Project.company_id == company_id)
            project_ids_in_year = [p[0] for p in project_ids_in_year_query.distinct().all()]

            activity_distribution = {}
            if project_ids_in_year:
                activity_dist_query = session.query(
                    ActivityType.nom,
                    func.sum(Task.heures_prevues)
                ).join(Task, ActivityType.id == Task.activity_type_id)\
                    .filter(Task.project_id.in_(project_ids_in_year))\
                    .group_by(ActivityType.nom)
                activity_distribution = {name: hours for name, hours in activity_dist_query.all() if hours and hours > 0}

            # 7. Top 10 Clients by planned deliverable amount
            top_clients_query = session.query(
                Client.name,
                func.sum(Livrable.montant).label('total_amount')
            ).join(Project, Client.id == Project.client_id)\
                .join(Livrable, Project.id == Livrable.project_id)\
                .filter(func.extract('year', Livrable.date_prevue) == year)

            if company_id:
                top_clients_query = top_clients_query.filter(Project.company_id == company_id)

            top_clients_query = top_clients_query.group_by(Client.name)\
                                                    .order_by(func.sum(Livrable.montant).desc())\
                                                    .limit(10)

            top_clients = [{'name': name, 'amount': amount} for name, amount in top_clients_query.all()]
            # --- End of New Queries ---

            # 5. Delay statistics
            delay_query = session.query(
                func.extract('month', Livrable.date_prevue),
                func.sum(case((Livrable.est_facture == True, 1), else_=0)),  # "OK" count
                # Count of all delayed deliverables ("NOK" column)
                func.sum(case((and_(Livrable.date_initiale != None, Livrable.date_prevue != Livrable.date_initiale), 1), else_=0)),
                # Total delayed amount (non-client responsibility)
                func.sum(case((and_(Livrable.date_initiale != None, Livrable.date_prevue != Livrable.date_initiale, Livrable.responsabilite_retard != 'Client'), Livrable.montant), else_=0.0)),
                # Total delayed amount (client responsibility)
                func.sum(case((and_(Livrable.date_initiale != None, Livrable.date_prevue != Livrable.date_initiale, Livrable.responsabilite_retard == 'Client'), Livrable.montant), else_=0.0))
            ).join(Project).filter(func.extract('year', Livrable.date_prevue) == year)

            if company_id:
                delay_query = delay_query.filter(Project.company_id == company_id)

            delay_results = delay_query.group_by(func.extract('month', Livrable.date_prevue)).all()

            delay_stats_by_month = [
                {'invoiced': 0, 'delayed_count': 0, 'delayed_amount_non_client': 0.0, 'delayed_amount_client': 0.0} for _ in range(12)
            ]
            for res in delay_results:
                month, invoiced_count, delayed_count, delayed_amount_non_client, delayed_amount_client = res
                if month is not None:
                    month_idx = int(month) - 1
                    delay_stats_by_month[month_idx] = {
                        'invoiced': invoiced_count or 0,
                        'delayed_count': delayed_count or 0,
                        'delayed_amount_non_client': delayed_amount_non_client or 0.0,
                        'delayed_amount_client': delayed_amount_client or 0.0
                    }

            # Base queries
            planned_query = session.query(
                func.extract('month', Livrable.date_prevue),
                func.sum(Livrable.montant)
            ).join(Project).filter(func.extract('year', Livrable.date_prevue) == year)

            billed_query = session.query(
                func.extract('month', Livrable.date_prevue),
                func.sum(Livrable.montant)
            ).join(Project).filter(
                func.extract('year', Livrable.date_prevue) == year,
                Livrable.est_facture == True
            )

            if company_id:
                planned_query = planned_query.filter(Project.company_id == company_id)
                billed_query = billed_query.filter(Project.company_id == company_id)

            # 2. Total planifié par mois
            planned_results = planned_query.group_by(func.extract('month', Livrable.date_prevue)).all()

            monthly_planned = [0.0] * 12
            for month, total in planned_results:
                if month is not None and total is not None:
                    monthly_planned[int(month) - 1] = float(total)

            # 3. Total facturé par mois
            billed_results = billed_query.group_by(func.extract('month', Livrable.date_prevue)).all()

            monthly_billed = [0.0] * 12
            for month, total in billed_results:
                if month is not None and total is not None:
                    monthly_billed[int(month) - 1] = float(total)
            
            # 4. Cumul planifié
            cumulative_planned = []
            current_sum = 0.0
            for monthly_total in monthly_planned:
                current_sum += monthly_total
                cumulative_planned.append(current_sum)

            return {
                "monthly_planned": monthly_planned,
                "monthly_billed": monthly_billed,
                "cumulative_planned": cumulative_planned,
                "objectives": objectives,
                "delay_stats": delay_stats_by_month,
                "activity_distribution": activity_distribution,
                "top_clients": top_clients
            }
        finally:
            session.close()