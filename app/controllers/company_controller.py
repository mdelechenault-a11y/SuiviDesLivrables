from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
from app.models.base import engine
from app.models.schema import Company, User

Session = sessionmaker(bind=engine)

class CompanyController:
    def get_all_companies(self):
        """Retourne toutes les sociétés, triées par nom."""
        session = Session()
        try:
            companies = session.query(Company).order_by(Company.name).all()
            return companies
        finally:
            session.close()

    def get_all_companies_for_filter(self):
        """Retourne une liste de dictionnaires {id, name} pour les filtres."""
        session = Session()
        try:
            companies = session.query(Company.id, Company.name).order_by(Company.name).all()
            return [{"id": c.id, "name": c.name} for c in companies]
        finally:
            session.close()

    def create_company(self, name):
        """Crée une nouvelle société."""
        session = Session()
        try:
            if not name:
                return False, "Le nom de la société ne peut pas être vide."
            new_company = Company(name=name)
            session.add(new_company)
            session.commit()
            return True, "Société ajoutée avec succès."
        except IntegrityError:
            session.rollback()
            return False, "Une société avec ce nom existe déjà."
        except Exception as e:
            session.rollback()
            return False, f"Une erreur est survenue : {str(e)}"
        finally:
            session.close()

    def delete_company(self, company_id):
        """Supprime une société si elle n'est pas utilisée."""
        session = Session()
        try:
            company = session.query(Company).get(company_id)
            if not company:
                return False, "Société non trouvée."
            
            user_count = session.query(User).filter_by(company_id=company_id).count()
            if user_count > 0:
                return False, f"Impossible de supprimer : {user_count} utilisateur(s) sont liés à cette société."

            session.delete(company)
            session.commit()
            return True, "Société supprimée avec succès."
        except Exception as e:
            session.rollback()
            return False, f"Erreur lors de la suppression : {str(e)}"
        finally:
            session.close()

    def update_company_objectives(self, company_id, pm, obj1, obj2):
        """Met à jour les objectifs pour une seule société."""
        session = Session()
        try:
            company = session.query(Company).get(company_id)
            if not company:
                return False, "Société non trouvée."
            
            company.objective_point_mort = pm
            company.objective_1 = obj1
            company.objective_2 = obj2
            
            session.commit()
            return True, "Objectifs mis à jour avec succès."
        except Exception as e:
            session.rollback()
            return False, f"Erreur lors de la mise à jour : {str(e)}"
        finally:
            session.close()

    def bulk_update_objectives(self, updates):
        """Met à jour les objectifs pour plusieurs sociétés en une seule transaction."""
        session = Session()
        try:
            session.bulk_update_mappings(Company, updates)
            session.commit()
            return True, "Toutes les modifications ont été enregistrées."
        except Exception as e:
            session.rollback()
            return False, f"Une erreur est survenue lors de l'enregistrement : {e}"
        finally:
            session.close()