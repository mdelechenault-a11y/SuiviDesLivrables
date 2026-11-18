import sys
from functools import partial
import datetime

from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QComboBox, 
    QPushButton, QVBoxLayout, QFormLayout, QMessageBox, QDateEdit, 
    QGroupBox, QHBoxLayout, QTableWidget, QHeaderView, QTableWidgetItem, QMenu,
    QDialog, QDialogButtonBox, QDoubleSpinBox, QSpacerItem, QSizePolicy
)
from PyQt6.QtGui import QColor, QBrush
from PyQt6.QtCore import Qt, QDate, QEvent
import qtawesome as qta

from app.controllers.project_controller import ProjectController

class TimeLogDialog(QDialog):
    """Dialog to enter hours for a time entry."""
    def __init__(self, task_name, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Imputer du Temps")
        self.setWindowIcon(qta.icon('fa5s.stopwatch', color='white'))
        self.setMinimumWidth(350)

        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(15)

        # Information label
        info_label = QLabel(f"Tâche : <b>{task_name}</b>")
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(info_label)

        form_layout = QFormLayout()
        self.heures_input = QDoubleSpinBox()
        self.heures_input.setRange(0.25, 24.0)
        self.heures_input.setSingleStep(0.25)
        self.heures_input.setValue(1.0)
        self.heures_input.setSuffix(" h")

        self.date_input = QDateEdit(calendarPopup=True)
        self.date_input.setDate(QDate.currentDate())
        self.date_input.setDisplayFormat("dd/MM/yyyy")

        form_layout.addRow("Heures à imputer:", self.heures_input)
        form_layout.addRow("Date de réalisation:", self.date_input)
        self.layout.addLayout(form_layout)

        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        self.layout.addWidget(self.buttons)

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
        self.last_hovered_row = -1
        self.hover_color = QColor("#50556b")
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.layout.setSpacing(15)

        # --- Title Bar ---
        title_bar_layout = QHBoxLayout()
        
        icon_label = QLabel()
        icon_label.setPixmap(qta.icon('fa5s.user-clock', color='white').pixmap(32, 32))
        
        title = QLabel(f"Mon Tableau de Bord ({self.user.prenom} {self.user.nom})")
        font = self.font()
        font.setPointSize(18)
        font.setBold(True)
        title.setFont(font)
        
        title_bar_layout.addWidget(icon_label)
        title_bar_layout.addSpacing(10)
        title_bar_layout.addWidget(title)
        title_bar_layout.addStretch()

        self.refresh_button = QPushButton(qta.icon('fa5s.sync-alt', color='white'), "Rafraîchir")
        self.refresh_button.clicked.connect(self.refresh_tasks_table)
        title_bar_layout.addWidget(self.refresh_button)
        
        self.layout.addLayout(title_bar_layout)

        # --- Tasks Table ---
        self.tasks_table = QTableWidget()
        self.tasks_table.setColumnCount(6)
        self.tasks_table.setHorizontalHeaderLabels([
            "Projet", "Tâche", "Prévu", "Pointé", "Restant", "Action"
        ])
        self.tasks_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tasks_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.tasks_table.verticalHeader().setVisible(False)
        self.tasks_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tasks_table.setAlternatingRowColors(True)

        # Enable row highlighting and selection
        self.tasks_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tasks_table.setMouseTracking(True)
        self.tasks_table.viewport().installEventFilter(self)
        self.tasks_table.cellEntered.connect(self._handle_row_hover)

        self.tasks_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tasks_table.customContextMenuRequested.connect(self._show_context_menu)

        self.layout.addWidget(self.tasks_table)
        
        self.refresh_tasks_table()

    def refresh_tasks_table(self):
        """Fetches assigned tasks and populates the table."""
        self.tasks_table.setRowCount(0)
        try:
            tasks = self.controller.get_tasks_for_user(self.user.id)
        except Exception as e:
            QMessageBox.critical(self, "Erreur de Connexion", f"Impossible de charger les tâches: {e}")
            tasks = []
            
        self.tasks_table.setRowCount(len(tasks))
        for row, task_data in enumerate(tasks):
            task_id = task_data['task_id']
            
            # --- Column 0: Project Name ---
            project_name_label = QLabel(task_data['project_name'])
            project_name_label.setProperty("base_style", "border: none; padding-left: 5px;")
            project_name_label.setStyleSheet("border: none; padding-left: 5px; background-color: transparent;")
            # Store task_id in the widget of the first column for context menu access
            project_name_label.setProperty("task_id", task_id)
            self.tasks_table.setCellWidget(row, 0, project_name_label)

            # --- Column 1: Task Name ---
            task_name_label = QLabel(task_data['task_name'])
            task_name_label.setProperty("base_style", "border: none; padding-left: 5px;")
            task_name_label.setStyleSheet("border: none; padding-left: 5px; background-color: transparent;")
            self.tasks_table.setCellWidget(row, 1, task_name_label)
            
            temps_alloue = task_data['temps_alloue']
            temps_passe = task_data['temps_passe_total']
            restant = temps_alloue - temps_passe

            # --- Column 2: Prévu ---
            prevu_label = QLabel(f"{temps_alloue:.1f} h")
            prevu_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            prevu_label.setProperty("base_style", "border: none;")
            prevu_label.setStyleSheet("border: none; background-color: transparent;")
            self.tasks_table.setCellWidget(row, 2, prevu_label)

            # --- Column 3: Pointé ---
            pointe_label = QLabel(f"{temps_passe:.1f} h")
            pointe_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            pointe_label.setProperty("base_style", "border: none;")
            pointe_label.setStyleSheet("border: none; background-color: transparent;")
            self.tasks_table.setCellWidget(row, 3, pointe_label)

            # --- Column 4: Restant ---
            restant_label = QLabel(f"{restant:.1f} h")
            restant_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            color = "#e74c3c" if restant < 0 else "#2ecc71"
            base_style = f"color: {color}; font-weight: bold; border: none;"
            restant_label.setProperty("base_style", base_style)
            restant_label.setStyleSheet(base_style + " background-color: transparent;")
            self.tasks_table.setCellWidget(row, 4, restant_label)

            # --- Column 5: Action ---
            log_time_button = QPushButton(qta.icon('fa5s.stopwatch', color='white'), "")
            log_time_button.setToolTip("Imputer du temps sur cette tâche")
            log_time_button.clicked.connect(partial(self.open_time_log_dialog, task_id, task_data['task_name']))
            
            cell_widget = QWidget()
            # Revert to default border for the button's container
            base_widget_style = ""
            cell_widget.setProperty("base_style", base_widget_style)
            cell_widget.setStyleSheet(base_widget_style + " background-color: transparent;")
            cell_layout = QHBoxLayout(cell_widget)
            cell_layout.addWidget(log_time_button)
            cell_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cell_layout.setContentsMargins(0, 0, 0, 0)
            
            self.tasks_table.setCellWidget(row, 5, cell_widget)

    def open_time_log_dialog(self, task_id, task_name):
        """Opens the dialog to log time for a specific task."""
        dialog = TimeLogDialog(task_name, self)
        if dialog.exec():
            data = dialog.get_data()
            try:
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
            except Exception as e:
                QMessageBox.critical(self, "Erreur de Connexion", f"Une erreur est survenue: {e}")

    def _show_context_menu(self, point):
        row = self.tasks_table.rowAt(point.y())
        if row < 0:
            return

        # Retrieve widgets from the clicked row
        project_widget = self.tasks_table.cellWidget(row, 0)
        task_widget = self.tasks_table.cellWidget(row, 1)
        if not project_widget or not task_widget:
            return
        
        task_id = project_widget.property("task_id")
        task_name = task_widget.text()

        menu = QMenu(self)
        complete_action = menu.addAction(qta.icon('fa5s.check-circle', color='#2ecc71'), f"Marquer '{task_name}' comme terminée")
        
        action = menu.exec(self.tasks_table.viewport().mapToGlobal(point))

        if action == complete_action:
            self._mark_task_completed(task_id)

    def _mark_task_completed(self, task_id):
        """Marks a task as completed and refreshes the view."""
        try:
            success, message = self.controller.update_task(task_id, {'status': 'Terminée'})
            if success:
                QMessageBox.information(self, "Succès", "Tâche marquée comme terminée.")
                self.refresh_tasks_table()
            else:
                QMessageBox.warning(self, "Erreur", f"Impossible de mettre à jour la tâche : {message}")
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Une erreur inattendue est survenue : {e}")

    def eventFilter(self, source, event):
        if source is self.tasks_table.viewport() and event.type() == QEvent.Type.Leave:
            self._clear_row_highlight(self.last_hovered_row)
            self.last_hovered_row = -1
        return super().eventFilter(source, event)

    def _handle_row_hover(self, row, column):
        if self.last_hovered_row != row:
            self._clear_row_highlight(self.last_hovered_row)
            self._apply_row_highlight(row)
            self.last_hovered_row = row

    def _apply_row_highlight(self, row):
        if row < 0 or row >= self.tasks_table.rowCount(): return
        for col in range(self.tasks_table.columnCount()):
            widget = self.tasks_table.cellWidget(row, col)
            if widget:
                base_style = widget.property("base_style") or ""
                widget.setStyleSheet(base_style + f" background-color: {self.hover_color.name()};")
            else:
                item = self.tasks_table.item(row, col)
                if item:
                    item.setBackground(self.hover_color)

    def _clear_row_highlight(self, row):
        if row < 0 or row >= self.tasks_table.rowCount(): return
        for col in range(self.tasks_table.columnCount()):
            widget = self.tasks_table.cellWidget(row, col)
            if widget:
                base_style = widget.property("base_style") or ""
                widget.setStyleSheet(base_style + " background-color: transparent;")
            else:
                item = self.tasks_table.item(row, col)
                if item:
                    item.setBackground(QBrush())

if __name__ == '__main__':
    from PyQt6.QtWidgets import QMainWindow
    from qt_material import apply_stylesheet
    
    app = QApplication(sys.argv)
    apply_stylesheet(app, theme='dark_blue.xml')
    
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
                {'task_id': 102, 'project_name': 'Projet Bêta', 'task_name': 'Tests unitaires', 'temps_alloue': 20, 'temps_passe_total': 8.75},
                {'task_id': 103, 'project_name': 'Projet Gamma', 'task_name': 'Rédaction de la documentation', 'temps_alloue': 16, 'temps_passe_total': 0},
            ]
        def log_time_for_task(self, user_id, task_id, heures, date_saisie):
            print(f"Logging {heures}h for user {user_id} on task {task_id} for date {date_saisie}")
            return True, "Success"

    main_window = QMainWindow()
    dashboard = UserDashboardWidget(MockUser(), MockController())
    main_window.setCentralWidget(dashboard)
    main_window.setWindowTitle("Dashboard Test")
    main_window.setGeometry(200, 200, 900, 600)
    main_window.show()
    
    sys.exit(app.exec())
