import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QStackedWidget, QWidget, QLabel
from PyQt6.QtGui import QAction
from PyQt6.QtCore import Qt
from qt_material import apply_stylesheet
import qtawesome as qta

from app.controllers.user_controller import UserController
from app.controllers.project_controller import ProjectController
from app.controllers.deliverable_controller import DeliverableController
from db_sync import synchronize_database
from manage_db import init_production_data
from app.views.login import LoginWindow
from app.views.user_dashboard import UserDashboardWidget
from app.views.project_management import ProjectManagementWidget
from app.views.load_project_dialog import LoadProjectDialog
from app.views.user_management import UserManagementWindow
from app.views.client_management import ClientManagementView
from app.views.global_dashboard import GlobalDashboardView
from app.views.time_report import TimeReportView
from app.views.weekly_pilotage import WeeklyPilotageView
from app.views.deliverables_tracking import DeliverablesTrackingView
from app.views.statistics_view import StatisticsView
from app.views.company_settings_view import CompanySettingsView

class MainWindow(QMainWindow):
    def __init__(self, user, controllers):
        super().__init__()
        self.user = user
        self.user_controller, self.project_controller, self.deliverable_controller = controllers
        
        company_name = f" - {self.user.company.name}" if self.user.company else ""
        self.setWindowTitle(f"Suivi des Livrables - Connecté : {self.user.prenom} {self.user.nom}{company_name}")
        self.setGeometry(100, 100, 1200, 800)

        self.setup_ui()
        self.setup_menus()

        # Set initial view to dashboard
        self.show_dashboard()

    def setup_ui(self):
        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)

        # Dashboard Widget
        self.dashboard_widget = UserDashboardWidget(self.user, self.project_controller)
        self.stacked_widget.addWidget(self.dashboard_widget)

        # Project Management Widget
        self.project_management_widget = ProjectManagementWidget()
        self.stacked_widget.addWidget(self.project_management_widget)

        # User Management Widget
        self.user_management_widget = UserManagementWindow()
        self.stacked_widget.addWidget(self.user_management_widget)

        # Client Management Widget
        self.client_management_widget = ClientManagementView()
        self.stacked_widget.addWidget(self.client_management_widget)

        # Global Dashboard Widget
        self.global_dashboard_widget = GlobalDashboardView()
        self.global_dashboard_widget.project_double_clicked.connect(self.open_project_from_dashboard)
        self.stacked_widget.addWidget(self.global_dashboard_widget)

        # Time Report Widget
        self.time_report_widget = TimeReportView()
        self.stacked_widget.addWidget(self.time_report_widget)

        # Weekly Pilotage View
        self.weekly_pilotage_widget = WeeklyPilotageView(self.user)
        self.stacked_widget.addWidget(self.weekly_pilotage_widget)

        # Deliverables Tracking View
        self.deliverables_tracking_widget = DeliverablesTrackingView()
        self.stacked_widget.addWidget(self.deliverables_tracking_widget)

        # Statistics View (pass user to get company objectives)
        self.statistics_widget = StatisticsView(self.user)
        self.stacked_widget.addWidget(self.statistics_widget)

        # Company Settings View
        self.company_settings_widget = CompanySettingsView()
        self.stacked_widget.addWidget(self.company_settings_widget)

    def setup_menus(self):
        menu_bar = self.menuBar()

        # File Menu
        file_menu = menu_bar.addMenu("Fichier")
        exit_action = QAction(qta.icon('fa5s.sign-out-alt', color='white'), "Quitter", self)
        client_action = QAction(qta.icon('fa5s.users', color='white'), "Clients", self)
        client_action.triggered.connect(self.show_client_management)
        file_menu.addAction(client_action)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # --- New Pilotage Menu ---
        pilotage_menu = menu_bar.addMenu("Pilotage")
        dashboard_action = QAction(qta.icon('fa5s.user-clock', color='white'), "Mon Tableau de bord", self)
        dashboard_action.triggered.connect(self.show_dashboard)
        pilotage_menu.addAction(dashboard_action)
        weekly_analysis_action = QAction(qta.icon('fa5s.calendar-week', color='white'), "Analyse Hebdomadaire", self)
        weekly_analysis_action.triggered.connect(self.show_weekly_pilotage)
        pilotage_menu.addAction(weekly_analysis_action)

        # --- Statistics ---
        stats_action = QAction(qta.icon('fa5s.chart-bar', color='white'), "Statistiques", self)
        stats_action.triggered.connect(self.show_statistics)
        pilotage_menu.addAction(stats_action)

        # --- Suivi des Livrables ---
        deliverables_action = QAction(qta.icon('fa5s.file-invoice-dollar', color='white'), "Suivi des Livrables", self)
        deliverables_action.triggered.connect(self.show_deliverables_tracking)
        pilotage_menu.addAction(deliverables_action)

        # --- Temps Menu (was Rapport) ---
        time_menu = menu_bar.addMenu("Temps")
        time_report_action = QAction(qta.icon('fa5s.clock', color='white'), "Détail des temps", self)
        time_report_action.triggered.connect(self.show_time_report)
        time_menu.addAction(time_report_action)

        # Show admin-level menus based on user profile
        if self.user.profil.nom in ["Admin", "Chef de projet"]:
            global_dashboard_action = QAction(qta.icon('fa5s.chart-pie', color='white'), "Vue d'ensemble Projets", self)
            global_dashboard_action.triggered.connect(self.show_global_dashboard)
            pilotage_menu.addAction(global_dashboard_action)
            # Projects Menu
            project_menu = menu_bar.addMenu("Projets")

            new_project_action = QAction(qta.icon('fa5s.project-diagram', color='white'), "Nouveau projet", self)
            new_project_action.triggered.connect(self.show_new_project_view)
            project_menu.addAction(new_project_action)
            
            load_project_action = QAction(qta.icon('fa5s.folder-open', color='white'), "Charger un projet", self)
            load_project_action.triggered.connect(self.open_project_loader)
            project_menu.addAction(load_project_action)

        if self.user.profil.nom == "Admin":
            # Company/Users Menu
            company_menu = menu_bar.addMenu("Sociétés")
            
            user_management_action = QAction(qta.icon('fa5s.user-cog', color='white'), "Gestion des Utilisateurs", self)
            user_management_action.triggered.connect(self.show_user_management)
            company_menu.addAction(user_management_action)

            company_settings_action = QAction(qta.icon('fa5s.building', color='white'), "Paramètres Sociétés", self)
            company_settings_action.triggered.connect(self.show_company_settings)
            company_menu.addAction(company_settings_action)

    def show_dashboard(self):
        self.dashboard_widget.refresh_tasks_table()
        self.stacked_widget.setCurrentWidget(self.dashboard_widget)

    def show_new_project_view(self):
        self.project_management_widget.reset_view()
        self.stacked_widget.setCurrentWidget(self.project_management_widget)

    def open_project_loader(self):
        dialog = LoadProjectDialog(self)
        if dialog.exec():
            project_id = dialog.get_selected_project_id()
            if project_id:
                self.open_project_from_dashboard(project_id)
    
    def show_user_management(self):
        self.user_management_widget.refresh_user_table()
        self.stacked_widget.setCurrentWidget(self.user_management_widget)

    def show_client_management(self):
        self.client_management_widget.refresh_client_table()
        self.stacked_widget.setCurrentWidget(self.client_management_widget)

    def show_global_dashboard(self):
        self.global_dashboard_widget.refresh_data()
        self.stacked_widget.setCurrentWidget(self.global_dashboard_widget)

    def show_time_report(self):
        self.time_report_widget.refresh_data()
        self.stacked_widget.setCurrentWidget(self.time_report_widget)

    def show_weekly_pilotage(self):
        self.weekly_pilotage_widget.refresh_data()
        self.stacked_widget.setCurrentWidget(self.weekly_pilotage_widget)

    def show_statistics(self):
        self.statistics_widget.refresh_data()
        self.stacked_widget.setCurrentWidget(self.statistics_widget)

    def show_deliverables_tracking(self):
        self.deliverables_tracking_widget.refresh_data()
        self.stacked_widget.setCurrentWidget(self.deliverables_tracking_widget)

    def open_project_from_dashboard(self, project_id):
        """Charge un projet dans la vue de gestion et affiche cette vue."""
        self.project_management_widget.load_project(project_id)
        self.stacked_widget.setCurrentWidget(self.project_management_widget)

    def show_company_settings(self):
        self.company_settings_widget.refresh_table()
        self.stacked_widget.setCurrentWidget(self.company_settings_widget)


class Application:
    def __init__(self, app):
        self.app = app
        
        # 1. S'assurer que le schéma de la BDD est à jour (crée les tables et applique les migrations simples)
        synchronize_database()
        # 2. S'assurer que les données essentielles (profils, admin) existent, sans être verbeux
        init_production_data(verbose=False)

        self.user_controller = UserController()
        self.project_controller = ProjectController()
        self.deliverable_controller = DeliverableController()
        
        self.login_window = None
        self.main_window = None

    def start(self):
        self.login_window = LoginWindow(self.user_controller)
        self.login_window.login_successful.connect(self.show_main_window)
        self.login_window.show()

    def show_main_window(self, user):
        controllers = (self.user_controller, self.project_controller, self.deliverable_controller)
        self.main_window = MainWindow(user, controllers)
        self.main_window.show()

def main():
    app = QApplication(sys.argv)
    apply_stylesheet(app, theme='dark_blue.xml')
    
    app_manager = Application(app)
    app_manager.start()
    
    sys.exit(app.exec())

if __name__ == '__main__':
    main()