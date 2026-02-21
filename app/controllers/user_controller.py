import bcrypt
from sqlalchemy.orm import sessionmaker, joinedload
from sqlalchemy.exc import IntegrityError
from app.models.base import engine
from app.models.schema import User, Profil, TaskAssignment, TimeEntry, Company

Session = sessionmaker(bind=engine)

class UserController:
    @staticmethod
    def set_password(password):
        """Hashes a password for storing."""
        salt = bcrypt.gensalt()
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed_password.decode('utf-8')

    @staticmethod
    def check_password(hashed_password, password):
        """Checks a password against a stored hash."""
        return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))

    def authenticate_user(self, username, password):
        """Authenticates a user and returns the user object if successful."""
        session = Session()
        try:
            user = session.query(User).options(joinedload(User.profil), joinedload(User.company)).filter_by(username=username).one_or_none()
            if user and self.check_password(user.password_hash, password):
                return user
            return None
        finally:
            session.close()

    def get_all_profil_names(self):
        session = Session()
        try:
            profils = session.query(Profil.nom).all()
            return [p[0] for p in profils]
        finally:
            session.close()

    def get_all_profils(self):
        session = Session()
        try:
            return session.query(Profil).all()
        finally:
            session.close()

    def get_all_companies(self):
        """Récupère toutes les sociétés."""
        session = Session()
        try:
            return session.query(Company).order_by(Company.name).all()
        finally:
            session.close()

    def get_all_users(self):
        """Retourne une simple liste d'utilisateurs pour les listes déroulantes."""
        session = Session()
        try:
            users = session.query(User.id, User.prenom, User.nom, User.username).all()
            return [{"id": u.id, "name": f"{u.prenom} {u.nom}", "username": u.username} for u in users]
        finally:
            session.close()

    def get_all_users_full(self):
        """Retourne une liste d'objets User avec Profil et Company chargés pour la vue de gestion."""
        session = Session()
        users = session.query(User).options(joinedload(User.profil), joinedload(User.company)).order_by(User.nom).all()
        session.expunge_all() # Détache de la session
        return users

    def add_user(self, username, email, password, prenom, nom, profil_nom, company_id=None):
        session = Session()
        try:
            profil = session.query(Profil).filter_by(nom=profil_nom).first()
            if not profil:
                return False, f"Profil '{profil_nom}' not found."

            hashed_password = self.set_password(password)

            new_user = User(
                username=username,
                email=email,
                password_hash=hashed_password,
                prenom=prenom,
                nom=nom,
                profil=profil,
                company_id=company_id
            )
            session.add(new_user)
            session.commit()
            return True, "Utilisateur ajouté avec succès."
        except IntegrityError as e:
            session.rollback()
            # This can happen if username or email already exists
            return False, "Le nom d'utilisateur ou l'email existe déjà."
        except Exception as e:
            session.rollback()
            return False, f"An unexpected error occurred: {str(e)}"
        finally:
            session.close()

    def update_user(self, user_id, data):
        session = Session()
        try:
            user = session.query(User).get(user_id)
            if not user:
                return False, "Utilisateur non trouvé."

            if 'profil_nom' in data:
                profil = session.query(Profil).filter_by(nom=data.pop('profil_nom')).first()
                if profil:
                    user.profil_id = profil.id
            
            if 'password' in data and data['password']:
                user.password_hash = self.set_password(data.pop('password'))
            
            if 'company_id' in data:
                user.company_id = data.pop('company_id')

            for key, value in data.items():
                if hasattr(user, key) and value is not None and key != 'password':
                    setattr(user, key, value)

            session.commit()
            return True, "Utilisateur mis à jour avec succès."
        except IntegrityError:
            session.rollback()
            return False, "Le nom d'utilisateur ou l'email existe déjà."
        except Exception as e:
            session.rollback()
            return False, str(e)
        finally:
            session.close()

    def delete_user(self, user_id):
        session = Session()
        try:
            user = session.query(User).options(joinedload(User.task_assignments), joinedload(User.time_entries)).get(user_id)
            if not user:
                return False, "Utilisateur non trouvé."

            if user.task_assignments or user.time_entries:
                return False, "Impossible de supprimer : l'utilisateur a des tâches ou des heures affectées."

            session.delete(user)
            session.commit()
            return True, "Utilisateur supprimé avec succès."
        except Exception as e:
            session.rollback()
            return False, f"Erreur lors de la suppression : {str(e)}"
        finally:
            session.close()

    def ensure_profils_exist(self, profil_names):
        """Ensures a list of profile names exist in the database, creating any that are missing."""
        session = Session()
        try:
            existing_profils = {p.nom for p in session.query(Profil).all()}
            missing_profils = [name for name in profil_names if name not in existing_profils]
            
            if missing_profils:
                for name in missing_profils:
                    session.add(Profil(nom=name))
                session.commit()
            return True, "Profils checked and created if necessary."
        except Exception as e:
            session.rollback()
            return False, str(e)
        finally:
            session.close()
