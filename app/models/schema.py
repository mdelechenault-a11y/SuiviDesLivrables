import enum
import datetime
from sqlalchemy import (create_engine, Column, Integer, String, Date, Boolean, 
                        ForeignKey, Float, Enum, DateTime, Text)
from sqlalchemy.orm import relationship
from .base import Base

class Company(Base):
    __tablename__ = 'companies'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    objective_point_mort = Column(Float, default=0.0)
    objective_1 = Column(Float, default=0.0)
    objective_2 = Column(Float, default=0.0)

    users = relationship("User", back_populates="company")
    projects = relationship("Project", back_populates="company")

    def __repr__(self):
        return f"<Company(name='{self.name}')>"

class Livrable(Base):
    __tablename__ = 'livrables'

    id = Column(Integer, primary_key=True, index=True)
    nom = Column(String, nullable=False)
    montant = Column(Float, nullable=False)
    date_prevue = Column(Date, nullable=False)
    date_initiale = Column(Date, nullable=True)
    responsabilite_retard = Column(String, nullable=True)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False)
    est_facture = Column(Boolean, default=False, nullable=False)
    project = relationship("Project", back_populates="livrables")
    comments = relationship("LivrableComment", back_populates="livrable", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Livrable(nom='{self.nom}', montant='{self.montant}')>"

class LivrableComment(Base):
    __tablename__ = 'livrable_comments'

    id = Column(Integer, primary_key=True, index=True)
    contenu = Column(Text, nullable=False)
    date_creation = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    livrable_id = Column(Integer, ForeignKey('livrables.id'), nullable=False)
    
    livrable = relationship("Livrable", back_populates="comments")

    def __repr__(self):
        return f"<LivrableComment(livrable_id='{self.livrable_id}', date='{self.date_creation}')>"

class Profil(Base):
    __tablename__ = 'profils'

    id = Column(Integer, primary_key=True)
    nom = Column(String, unique=True, nullable=False)
    users = relationship("User", back_populates="profil")

    def __repr__(self):
        return f"<Profil(nom='{self.nom}')>"

class TaskAssignment(Base):
    __tablename__ = 'task_assignments'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    task_id = Column(Integer, ForeignKey('tasks.id'), nullable=False)
    temps_alloue = Column(Float, nullable=False)
    temps_pointe = Column(Float, default=0.0)
    
    user = relationship("User", back_populates="task_assignments")
    task = relationship("Task", back_populates="user_assignments")

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, nullable=False)
    prenom = Column(String, nullable=False)
    nom = Column(String, nullable=False)
    password_hash = Column(String, nullable=False)
    profil_id = Column(Integer, ForeignKey('profils.id'))
    company_id = Column(Integer, ForeignKey('companies.id'), nullable=True)
    
    profil = relationship("Profil", back_populates="users")
    company = relationship("Company", back_populates="users")
    managed_projects = relationship("Project", back_populates="chef_de_projet")
    task_assignments = relationship("TaskAssignment", back_populates="user", cascade="all, delete-orphan")
    time_entries = relationship("TimeEntry", back_populates="user", cascade="all, delete-orphan")


    def __repr__(self):
        return f"<User(username='{self.username}')>"

class Client(Base):
    __tablename__ = 'clients'

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    contact_info = Column(String)
    is_visible = Column(Boolean, default=True, nullable=False)
    projects = relationship("Project", back_populates="client")

    def __repr__(self):
        return f"<Client(name='{self.name}')>"

class ProjectStatus(enum.Enum):
    CHiffrage = "Chiffrage"
    EN_COURS = "En cours"
    TERMINE = "Terminé"

class Project(Base):
    __tablename__ = 'projects'

    id = Column(Integer, primary_key=True)
    code = Column(String, unique=True, nullable=False)
    nom = Column(String, nullable=False)
    date_debut = Column(Date, nullable=False)
    statut = Column(Enum(ProjectStatus), nullable=False, default=ProjectStatus.CHiffrage)
    budget_material_planned = Column(Float, default=0.0)
    budget_material_spent = Column(Float, default=0.0)
    
    chef_de_projet_id = Column(Integer, ForeignKey('users.id'))
    client_id = Column(Integer, ForeignKey('clients.id'))
    company_id = Column(Integer, ForeignKey('companies.id'), nullable=True)

    chef_de_projet = relationship("User", back_populates="managed_projects")
    client = relationship("Client", back_populates="projects")
    company = relationship("Company", back_populates="projects")
    tasks = relationship("Task", back_populates="project", cascade="all, delete-orphan")
    livrables = relationship("Livrable", back_populates="project", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Project(nom='{self.nom}')>"

class ActivityType(Base):
    __tablename__ = 'activity_types'

    id = Column(Integer, primary_key=True)
    nom = Column(String, unique=True, nullable=False)
    tasks = relationship("Task", back_populates="activity_type")

    def __repr__(self):
        return f"<ActivityType(nom='{self.nom}')>"

class Task(Base):
    __tablename__ = 'tasks'

    id = Column(Integer, primary_key=True)
    nom = Column(String, nullable=False)
    heures_prevues = Column(Float, nullable=False)
    temps_passe_total = Column(Float, default=0.0, nullable=False)
    duree_jours = Column(Float)
    position = Column(Integer, default=0)
    lag_days = Column(Integer, default=0, nullable=False)
    date_debut_calculee = Column(Date)
    date_fin = Column(Date)
    
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False, index=True)
    activity_type_id = Column(Integer, ForeignKey('activity_types.id'))
    parente_id = Column(Integer, ForeignKey('tasks.id'), nullable=True)

    project = relationship("Project", back_populates="tasks")
    activity_type = relationship("ActivityType", back_populates="tasks")
    
    # Adjacency list for parent/child relationship
    parente = relationship("Task", remote_side=[id], back_populates="enfants")
    enfants = relationship("Task", back_populates="parente", cascade="all, delete-orphan")
    
    user_assignments = relationship("TaskAssignment", back_populates="task", cascade="all, delete-orphan")
    assigned_users = relationship("User", secondary="task_assignments", viewonly=True)
    time_entries = relationship("TimeEntry", back_populates="task")


    def __repr__(self):
        return f"<Task(nom='{self.nom}')>"

class TimeEntry(Base):
    __tablename__ = 'time_entries'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False, index=True)
    task_id = Column(Integer, ForeignKey('tasks.id'), nullable=False, index=True)
    date_performed = Column(Date, nullable=False)
    hours_spent = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="time_entries")
    task = relationship("Task", back_populates="time_entries")
    project = relationship("Project")

    def __repr__(self):
        return f"<TimeEntry(user_id={self.user_id}, task_id={self.task_id}, hours={self.hours_spent})>"
