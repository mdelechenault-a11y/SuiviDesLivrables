import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QStackedWidget, QWidget,
                             QLabel, QToolButton, QMenu, QLineEdit, QHBoxLayout,
                             QVBoxLayout)
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
from app.views.kpi_view import KPIView
from app.views.calendar_view import CalendarView

class MainWindow(QMainWindow):
    def __init__(self, user, controllers):
        super().__init__()
        self.user = user
        self.user_controller, self.project_controller, self.deliverable_controller = controllers

        company_name = f" - {self.user.company.name}" if self.user.company else ""
        self.setWindowTitle(f"Suivi des Livrables - Connecté : {self.user.prenom} {self.user.nom}{company_name}")
        self.setGeometry(100, 100, 1400, 900)

        self.setup_ui()
        self.setup_header()

    def setup_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)

        self.main_layout = QVBoxLayout(main_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # Header
        self.header = QWidget()
        self.header_layout = QHBoxLayout(self.header)
        self.main_layout.addWidget(self.header)

        # Content
        self.stacked_widget = QStackedWidget()
        self.main_layout.addWidget(self.stacked_widget)

        # --- Add Views to StackedWidget ---
        self.dashboard_widget = UserDashboardWidget(self.user, self.project_controller)
        self.stacked_widget.addWidget(self.dashboard_widget)

        self.project_management_widget = ProjectManagementWidget()
        self.stacked_widget.addWidget(self.project_management_widget)

        self.user_management_widget = UserManagementWindow()
        self.stacked_widget.addWidget(self.user_management_widget)

        self.client_management_widget = ClientManagementView()
        self.stacked_widget.addWidget(self.client_management_widget)

        self.global_dashboard_widget = GlobalDashboardView()
        self.global_dashboard_widget.project_double_clicked.connect(self.open_project_from_dashboard)
        self.stacked_widget.addWidget(self.global_dashboard_widget)

        self.time_report_widget = TimeReportView()
        self.stacked_widget.addWidget(self.time_report_widget)

        self.weekly_pilotage_widget = WeeklyPilotageView(self.user)
        self.stacked_widget.addWidget(self.weekly_pilotage_widget)

        self.deliverables_tracking_widget = DeliverablesTrackingView()
        self.stacked_widget.addWidget(self.deliverables_tracking_widget)

        self.statistics_widget = StatisticsView(self.user)
        self.stacked_widget.addWidget(self.statistics_widget)

        self.company_settings_widget = CompanySettingsView()
        self.stacked_widget.addWidget(self.company_settings_widget)

        self.kpi_widget = KPIView(self.user)
        self.stacked_widget.addWidget(self.kpi_widget)

        self.calendar_widget = CalendarView(self.project_controller)
        self.stacked_widget.addWidget(self.calendar_widget)

    def setup_header(self):
        self.header.setFixedHeight(50)

        title = QLabel(f"Suivi des Livrables")
        font = title.font()
        font.setPointSize(12)
        font.setBold(True)
        title.setFont(font)
        self.header_layout.addWidget(title)

        self.header_layout.addSpacing(20)
        self.setup_top_menu()

        self.header_layout.addStretch()

        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Rechercher...")
        self.search_bar.setMaximumWidth(200)
        # self.search_bar.returnPressed.connect(self._on_global_search) # TODO
        self.header_layout.addWidget(self.search_bar)

        self.notification_button = QToolButton(self)
        self.notification_button.setIcon(qta.icon('fa5s.bell', color='white'))
        self.notification_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.notification_menu = QMenu(self)
        self.notification_button.setMenu(self.notification_menu)
        # self.notification_button.clicked.connect(self.refresh_notifications) # TODO
        self.header_layout.addWidget(self.notification_button)

        # self.refresh_notifications() # TODO

    def setup_top_menu(self):
        menu_items = [
            {'icon': 'fa5s.tachometer-alt', 'text': "Tableaux de bord", 'item_id': None, 'children': [
                {'icon': 'fa5s.user-clock', 'text': "Mon Tableau de bord", 'item_id': "dashboard"},
                {'icon': 'fa5s.chart-pie', 'text': "Vue d'ensemble Projets", 'item_id': "global_dashboard", 'profiles': ["Admin", "Chef de projet"]},
            ]},
            {'icon': 'fa5s.chart-bar', 'text': "Analyse", 'item_id': None, 'children': [
                {'icon': 'fa5s.calendar-alt', 'text': "Calendrier", 'item_id': "calendar"},
                {'icon': 'fa5s.calendar-week', 'text': "Analyse Hebdomadaire", 'item_id': "weekly_pilotage"},
                {'icon': 'fa5s.chart-line', 'text': "Statistiques", 'item_id': "statistics"},
                {'icon': 'fa5s.tachometer-alt', 'text': "KPI", 'item_id': "kpi"},
            ]},
            {'icon': 'fa5s.tasks', 'text': "Suivi", 'item_id': None, 'children': [
                {'icon': 'fa5s.file-invoice-dollar', 'text': "Suivi des Livrables", 'item_id': "deliverables_tracking"},
                {'icon': 'fa5s.clock', 'text': "Détail des temps", 'item_id': "time_report"},
            ]},
            {'icon': 'fa5s.project-diagram', 'text': "Gestion", 'item_id': None, 'profiles': ["Admin", "Chef de projet"], 'children': [
                {'icon': 'fa5s.plus-circle', 'text': "Nouveau projet", 'item_id': "new_project"},
                {'icon': 'fa5s.folder-open', 'text': "Charger un projet", 'item_id': "load_project"},
            ]},
            {'icon': 'fa5s.cogs', 'text': "Administration", 'item_id': None, 'profiles': ["Admin"], 'children': [
                {'icon': 'fa5s.users', 'text': "Clients", 'item_id': "client_management"},
                {'icon': 'fa5s.user-cog', 'text': "Utilisateurs", 'item_id': "user_management"},
                {'icon': 'fa5s.building', 'text': "Sociétés", 'item_id': "company_settings"},
            ]},
            {'icon': 'fa5s.sign-out-alt', 'text': "Quitter", 'item_id': "exit"},
        ]

        for item_data in menu_items:
            if 'profiles' in item_data and self.user.profil.nom not in item_data['profiles']:
                continue

            btn = QToolButton(self)
            btn.setText(item_data['text'])
            btn.setIcon(qta.icon(item_data['icon'], color='white'))
            btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
            btn.setStyleSheet("QToolButton { border: none; padding: 5px; color: white; } QToolButton:hover { background-color: #34495e; border-radius: 4px; }")
            btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)

            if 'children' in item_data and item_data['children']:
                menu = QMenu(self)
                for child_data in item_data['children']:
                    if 'profiles' in child_data and self.user.profil.nom not in child_data['profiles']:
                        continue
                    action = menu.addAction(qta.icon(child_data['icon'], color='white'), child_data['text'])
                    action.triggered.connect(lambda checked=False, item_id=child_data['item_id']: self.switch_view(item_id))
                btn.setMenu(menu)
            else:
                if item_data.get('item_id'):
                    btn.clicked.connect(lambda checked=False, item_id=item_data['item_id']: self.switch_view(item_id))

            self.header_layout.addWidget(btn)
        
        self.switch_view("dashboard")

    def switch_view(self, item_id):
        view_map = {
            "dashboard": self.show_dashboard,
            "calendar": self.show_calendar_view,
            "weekly_pilotage": self.show_weekly_pilotage,
            "statistics": self.show_statistics,
            "deliverables_tracking": self.show_deliverables_tracking,
            "kpi": self.show_kpi,
            "time_report": self.show_time_report,
            "global_dashboard": self.show_global_dashboard,
            "new_project": self.show_new_project_view,
            "load_project": self.open_project_loader,
            "client_management": self.show_client_management,
            "user_management": self.show_user_management,
            "company_settings": self.show_company_settings,
            "exit": self.close
        }
        action = view_map.get(item_id)
        if action:
            action()


    def show_dashboard(self):
        self.dashboard_widget.refresh_tasks_table()
        self.stacked_widget.setCurrentWidget(self.dashboard_widget)

    def show_calendar_view(self):
        self.calendar_widget.refresh_data()
        self.stacked_widget.setCurrentWidget(self.calendar_widget)

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

    def show_kpi(self):
        self.kpi_widget.refresh_data()
        self.stacked_widget.setCurrentWidget(self.kpi_widget)

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
    try:
        app = QApplication(sys.argv)
        apply_stylesheet(app, theme='dark_blue.xml')
        
        app_manager = Application(app)
        app_manager.start()
        
        sys.exit(app.exec())
    except Exception as e:
        with open("C:\\Users\\Mathieu\\.gemini\\tmp\\b8782745c3130a80ef4837c807fb37f35693595f68a2d55ca096fb90914b6a0f\\crash.log", "w") as f:
            import traceback
            f.write(f"An error occurred: {e}\n")
            f.write(traceback.format_exc())
        sys.exit(1)

if __name__ == '__main__':
    main()