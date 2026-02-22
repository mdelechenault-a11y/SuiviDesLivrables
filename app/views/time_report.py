import sys
import os
import csv
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView,
    QLabel, QHBoxLayout, QDateEdit, QComboBox, QPushButton,
    QFileDialog, QMessageBox, QDialog, QFormLayout, QDialogButtonBox
)
from PyQt6.QtCore import Qt, QDate
import qtawesome as qta
from app.controllers.project_controller import ProjectController
from app.controllers.user_controller import UserController

class NumericTableWidgetItem(QTableWidgetItem):
    """Widget-élément de tableau personnalisé pour le tri numérique."""
    def __lt__(self, other):
        try:
            # Tenter de comparer les données numériques stockées pour le tri
            return float(self.data(Qt.ItemDataRole.EditRole)) < float(other.data(Qt.ItemDataRole.EditRole))
        except (ValueError, TypeError, AttributeError):
            return super().__lt__(other)

class TimeReportFilterDialog(QDialog):
    """Dialogue pour sélectionner les filtres du rapport de temps."""
    def __init__(self, parent, current_filters, users, projects, activities):
        super().__init__(parent)
        self.setWindowTitle("Filtres du Rapport")
        self.setWindowIcon(qta.icon('fa5s.filter', color='white'))
        self.setMinimumWidth(400)

        layout = QFormLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        # Date editors
        self.start_date_edit = QDateEdit(calendarPopup=True)
        self.start_date_edit.setDate(current_filters.get('start_date', QDate.currentDate().addMonths(-1)))
        self.end_date_edit = QDateEdit(calendarPopup=True)
        self.end_date_edit.setDate(current_filters.get('end_date', QDate.currentDate()))
        layout.addRow("Du:", self.start_date_edit)
        layout.addRow("Au:", self.end_date_edit)

        # User combo
        self.user_combo = QComboBox()
        self.user_combo.addItem("Tous", userData=None)
        for user in users:
            self.user_combo.addItem(user['name'], userData=user['id'])
        if current_filters.get('user_id'):
            self.user_combo.setCurrentIndex(self.user_combo.findData(current_filters['user_id']))
        layout.addRow("Utilisateur:", self.user_combo)

        # Project combo
        self.project_combo = QComboBox()
        self.project_combo.addItem("Tous", userData=None)
        for project in projects:
            self.project_combo.addItem(f"{project['code']} - {project['nom']}", userData=project['id'])
        if current_filters.get('project_id'):
            self.project_combo.setCurrentIndex(self.project_combo.findData(current_filters['project_id']))
        layout.addRow("Projet:", self.project_combo)

        # Activity combo
        self.activity_combo = QComboBox()
        self.activity_combo.addItem("Toutes", userData=None)
        for activity in activities:
            self.activity_combo.addItem(activity['name'], userData=activity['id'])
        if current_filters.get('activity_type_id'):
            self.activity_combo.setCurrentIndex(self.activity_combo.findData(current_filters['activity_type_id']))
        layout.addRow("Activité:", self.activity_combo)

        # Buttons
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addRow(self.buttons)

    def get_filters(self):
        return {
            'start_date': self.start_date_edit.date(),
            'end_date': self.end_date_edit.date(),
            'user_id': self.user_combo.currentData(),
            'project_id': self.project_combo.currentData(),
            'activity_type_id': self.activity_combo.currentData()
        }

class TimeReportView(QWidget):
    """
    Vue pour afficher un rapport des temps pointés avec des filtres.
    """
    def __init__(self):
        super().__init__()
        self.project_controller = ProjectController()
        self.user_controller = UserController()

        # Filter state
        self.start_date = QDate.currentDate().addMonths(-1)
        self.end_date = QDate.currentDate()
        self.user_id = None
        self.project_id = None
        self.activity_type_id = None
        self.user_name_filter = "Tous"
        self.project_name_filter = "Tous"
        self.activity_name_filter = "Toutes"

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.layout.setSpacing(15)

        # --- Titre ---
        title_bar = QHBoxLayout()
        icon_label = QLabel()
        icon_label.setPixmap(qta.icon('fa5s.clock', color='white').pixmap(32, 32))
        title = QLabel("Rapport de Pointages")
        font = title.font()
        font.setPointSize(18)
        font.setBold(True)
        title.setFont(font)
        title_bar.addWidget(icon_label)
        title_bar.addSpacing(10)
        title_bar.addWidget(title)
        title_bar.addStretch()
        self.layout.addLayout(title_bar)

        # --- Tableau Principal ---
        self._setup_toolbar()
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["Date Réalisation", "Ressource", "Projet", "Tâche", "Type d'Activité", "Temps Déclaré"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSortingEnabled(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.layout.addWidget(self.table)

        # --- Pied de page ---
        footer_layout = QHBoxLayout()
        footer_layout.addStretch()
        self.total_hours_label = QLabel("Total des heures : 0.00")
        font = self.total_hours_label.font()
        font.setBold(True)
        self.total_hours_label.setFont(font)
        footer_layout.addWidget(self.total_hours_label)
        self.layout.addLayout(footer_layout)

        self.refresh_data()

    def _setup_toolbar(self):
        toolbar_layout = QHBoxLayout()
        toolbar_layout.setContentsMargins(0, 0, 0, 10)

        self.filter_button = QPushButton(qta.icon('fa5s.filter'), " Filtres")
        self.filter_button.clicked.connect(self._open_filter_dialog)
        toolbar_layout.addWidget(self.filter_button)

        self.active_filters_label = QLabel()
        self.active_filters_label.setStyleSheet("color: #aaa;")
        toolbar_layout.addWidget(self.active_filters_label)

        toolbar_layout.addStretch()

        self.export_button = QPushButton(qta.icon('fa5s.file-csv'), " Exporter en CSV")
        self.export_button.clicked.connect(self.export_to_csv)
        toolbar_layout.addWidget(self.export_button)

        self.layout.addLayout(toolbar_layout)

    def _open_filter_dialog(self):
        # Fetch fresh data for combos
        users = self.user_controller.get_all_users()
        projects = self.project_controller.get_all_projects()
        activities = self.project_controller.get_all_activity_types()

        current_filters = {
            'start_date': self.start_date,
            'end_date': self.end_date,
            'user_id': self.user_id,
            'project_id': self.project_id,
            'activity_type_id': self.activity_type_id,
        }

        dialog = TimeReportFilterDialog(self, current_filters, users, projects, activities)
        if dialog.exec():
            new_filters = dialog.get_filters()
            self.start_date = new_filters['start_date']
            self.end_date = new_filters['end_date']
            self.user_id = new_filters['user_id']
            self.project_id = new_filters['project_id']
            self.activity_type_id = new_filters['activity_type_id']
            
            self.user_name_filter = dialog.user_combo.currentText()
            self.project_name_filter = dialog.project_combo.currentText()
            self.activity_name_filter = dialog.activity_combo.currentText()

            self.apply_filters()

    def apply_filters(self):
        time_entries = self.project_controller.get_time_entries_report(
            self.start_date.toPyDate(), self.end_date.toPyDate(), self.user_id, self.project_id, self.activity_type_id
        )
        
        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)
        total_hours = 0.0

        for row, entry in enumerate(time_entries):
            self.table.insertRow(row)
            
            # Les dates au format YYYY-MM-DD se trient correctement comme du texte
            self.table.setItem(row, 0, QTableWidgetItem(entry['date_performed'].strftime('%Y-%m-%d')))
            self.table.setItem(row, 1, QTableWidgetItem(entry['user_name']))
            self.table.setItem(row, 2, QTableWidgetItem(entry['project_code']))
            self.table.setItem(row, 3, QTableWidgetItem(entry['task_name']))
            self.table.setItem(row, 4, QTableWidgetItem(entry['activity_type_name']))
            
            hours_spent = entry['hours_spent']
            hours_item = NumericTableWidgetItem(f"{hours_spent:.2f}")
            hours_item.setData(Qt.ItemDataRole.EditRole, hours_spent) # Stocker la valeur numérique pour le tri
            hours_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row, 5, hours_item)
            
            total_hours += hours_spent

        self.table.setSortingEnabled(True)
        self.table.sortByColumn(0, Qt.SortOrder.AscendingOrder)

        self.total_hours_label.setText(f"Total des heures : {total_hours:.2f}")
        self._update_active_filters_label()

    def _update_active_filters_label(self):
        filters = []
        filters.append(f"Période: {self.start_date.toString('dd/MM/yy')} au {self.end_date.toString('dd/MM/yy')}")
        
        if self.user_id:
            filters.append(f"Utilisateur: {self.user_name_filter}")
        
        if self.project_id:
            # Affiche seulement le code du projet pour la concision
            filters.append(f"Projet: {self.project_name_filter.split(' - ')[0]}")

        if self.activity_type_id:
            filters.append(f"Activité: {self.activity_name_filter}")

        self.active_filters_label.setText(f"Filtres actifs : {', '.join(filters)}")

    def refresh_data(self):
        """Applique les filtres pour recharger les données."""
        self.apply_filters()

    def export_to_csv(self):
        """Exporte les données actuellement filtrées dans un fichier CSV."""
        time_entries = self.project_controller.get_time_entries_report(
            self.start_date.toPyDate(), self.end_date.toPyDate(), self.user_id, self.project_id, self.activity_type_id
        )

        if not time_entries:
            QMessageBox.information(self, "Exportation", "Aucune donnée à exporter pour les filtres actuels.")
            return

        # Dialogue pour choisir le dossier et le nom du fichier
        default_path = os.path.join(os.path.expanduser("~"), "rapport_pointage.csv")
        file_path, _ = QFileDialog.getSaveFileName(self, "Enregistrer le rapport CSV", default_path, "Fichiers CSV (*.csv)")

        if not file_path:
            return

        # Logique d'incrémentation du nom de fichier
        base, ext = os.path.splitext(file_path)
        counter = 1
        while os.path.exists(file_path):
            file_path = f"{base}_{counter:03d}{ext}"
            counter += 1

        try:
            with open(file_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
                writer = csv.writer(csvfile, delimiter=';')
                
                # En-têtes
                headers = ["Date Réalisation", "Ressource", "Projet", "Tâche", "Type d'Activité", "Temps Déclaré"]
                writer.writerow(headers)
                
                # Données
                for entry in time_entries:
                    writer.writerow([entry['date_performed'], entry['user_name'], entry['project_code'], entry['task_name'], entry['activity_type_name'], f"{entry['hours_spent']:.2f}".replace('.', ',')])
            
            QMessageBox.information(self, "Exportation Réussie", f"Le rapport a été enregistré avec succès dans :\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Erreur d'Exportation", f"Une erreur est survenue lors de la création du fichier CSV :\n{e}")