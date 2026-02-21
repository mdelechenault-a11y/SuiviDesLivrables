import sys
from functools import partial
import datetime

from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QComboBox, 
    QPushButton, QVBoxLayout, QFormLayout, QMessageBox, QDateEdit, 
    QGroupBox, QHBoxLayout, QTableWidget, QHeaderView, QTableWidgetItem,
    QDialog, QDialogButtonBox, QDoubleSpinBox
)
from PyQt6.QtCore import Qt, QDate
import qtawesome as qta

from app.controllers.project_controller import ProjectController

class TimeLogDialog(QDialog):
    """Dialog to enter hours for a time entry."""
    def __init__(self, task_name, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Imputer du Temps pour: {task_name}")

        self.layout = QFormLayout(self)
        self.heures_input = QDoubleSpinBox()
        self.heures_input.setRange(0.25, 24.0)
        self.heures_input.setSingleStep(0.25)
        self.heures_input.setValue(1.0)

        self.date_input = QDateEdit(calendarPopup=True)
        self.date_input.setDate(QDate.currentDate())

        self.layout.addRow("Heures à imputer:", self.heures_input)
        self.layout.addRow("Date de réalisation:", self.date_input)

        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        self.layout.addRow(self.buttons)

    def get_data(self):
        return {
            "heures": self.heures_input.value(),
            "date": self.date_input.date().toPyDate()
        }

class UserDashboardWidget(QWidget):
    """
    Dashboard widget for a logged-in user.
    Shows assigned tasks and allows time logging.
    """
    def __init__(self, user, controller: ProjectController, parent=None):
        super().__init__(parent)
        self.user = user
        self.controller = controller
        
        self.layout = QVBoxLayout(self)
        
        title = QLabel(f"Tâches Affectées à {self.user.username}")
        font = self.font()
        font.setPointSize(14)
        font.setBold(True)
        title.setFont(font)
        
        self.tasks_table = QTableWidget()
        self.tasks_table.setColumnCount(5)
        self.tasks_table.setHorizontalHeaderLabels([
            "Projet", "Tâche", "Heures Allouées", "Temps Passé", "Action"
        ])
        self.tasks_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tasks_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.tasks_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        self.layout.addWidget(title)
        self.layout.addWidget(self.tasks_table)
        
        self.refresh_tasks_table()

    def refresh_tasks_table(self):
        """Fetches assigned tasks and populates the table."""
        self.tasks_table.setRowCount(0)
        tasks = self.controller.get_tasks_for_user(self.user.id)
        
        self.tasks_table.setRowCount(len(tasks))
        for row, task_data in enumerate(tasks):
            task_id = task_data['task_id']
            
            self.tasks_table.setItem(row, 0, QTableWidgetItem(task_data['project_name']))
            self.tasks_table.setItem(row, 1, QTableWidgetItem(task_data['task_name']))
            self.tasks_table.setItem(row, 2, QTableWidgetItem(str(task_data['temps_alloue'])))
            self.tasks_table.setItem(row, 3, QTableWidgetItem(str(task_data['temps_passe_total'])))
            
            # Pointage Button
            log_time_button = QPushButton(qta.icon('fa5s.stopwatch'), "")
            log_time_button.setToolTip("Imputer du temps sur cette tâche")
            handler = partial(self.open_time_log_dialog, task_id, task_data['task_name'])
            log_time_button.clicked.connect(handler)
            
            self.tasks_table.setCellWidget(row, 4, log_time_button)

    def open_time_log_dialog(self, task_id, task_name):
        """Opens the dialog to log time for a specific task."""
        dialog = TimeLogDialog(task_name, self)
        if dialog.exec():
            data = dialog.get_data()
            success, message = self.controller.log_time_for_task(
                user_id=self.user.id,
                task_id=task_id,
                heures=data["heures"],
                date_saisie=data["date"]
            )
            if success:
                QMessageBox.information(self, "Succès", "Temps imputé avec succès.")
                self.refresh_tasks_table()
            else:
                QMessageBox.critical(self, "Erreur", f"Impossible d'imputer le temps : {message}")

if __name__ == '__main__':
    from PyQt6.QtWidgets import QMainWindow
    # This is for testing the dashboard widget standalone
    app = QApplication(sys.argv)
    
    # Mock user and controller for testing
    class MockUser:
        id = 1
        username = 'testuser'
        prenom = 'Test'
        nom = 'User'
        
    class MockController(ProjectController):
        def get_tasks_for_user(self, user_id):
            return [
                {'task_id': 101, 'project_name': 'Projet Alpha', 'task_name': 'Développement UI', 'temps_alloue': 40, 'temps_passe_total': 15.5},
                {'task_id': 102, 'project_name': 'Projet Bêta', 'task_name': 'Tests unitaires', 'temps_alloue': 20, 'temps_passe_total': 8},
            ]
        def log_time_for_task(self, user_id, task_id, heures):
            print(f"Logging {heures}h for user {user_id} on task {task_id}")
            return True, "Success"

    # To test a widget, it's best to place it in a window
    main_window = QMainWindow()
    dashboard = UserDashboardWidget(MockUser(), MockController())
    main_window.setCentralWidget(dashboard)
    main_window.setWindowTitle("Dashboard Test")
    main_window.setGeometry(200, 200, 800, 500)
    main_window.show()
    
    sys.exit(app.exec())
