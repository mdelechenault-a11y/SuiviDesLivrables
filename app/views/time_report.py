import sys
import os
import csv
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView,
    QLabel, QHBoxLayout, QGroupBox, QDateEdit, QComboBox, QPushButton,
    QFileDialog, QMessageBox
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

class TimeReportView(QWidget):
    """
    Vue pour afficher un rapport des temps pointés avec des filtres.
    """
    def __init__(self):
        super().__init__()
        self.project_controller = ProjectController()
        self.user_controller = UserController()

        self.layout = QVBoxLayout(self)

        # --- Titre ---
        title = QLabel("Rapport de Pointages")
        font = title.font()
        font.setPointSize(16)
        font.setBold(True)
        title.setFont(font)
        self.layout.addWidget(title)

        # --- Barre de Filtres ---
        self._setup_filters()

        # --- Tableau Principal ---
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

    def _setup_filters(self):
        filter_group = QGroupBox("Filtres")
        filter_layout = QHBoxLayout()

        self.start_date_edit = QDateEdit(calendarPopup=True)
        self.start_date_edit.setDate(QDate.currentDate().addMonths(-1))
        self.end_date_edit = QDateEdit(calendarPopup=True)
        self.end_date_edit.setDate(QDate.currentDate())
        
        self.user_combo = QComboBox()
        self.project_combo = QComboBox()
        self.activity_combo = QComboBox()
        
        self.filter_button = QPushButton("Appliquer")
        self.filter_button.clicked.connect(self.apply_filters)

        filter_layout.addWidget(QLabel("Du:"))
        filter_layout.addWidget(self.start_date_edit)
        filter_layout.addWidget(QLabel("Au:"))
        filter_layout.addWidget(self.end_date_edit)
        filter_layout.addWidget(QLabel("Utilisateur:"))
        filter_layout.addWidget(self.user_combo)
        filter_layout.addWidget(QLabel("Projet:"))
        filter_layout.addWidget(self.project_combo)
        filter_layout.addWidget(QLabel("Activité:"))
        filter_layout.addWidget(self.activity_combo)
        filter_layout.addStretch()
        filter_layout.addWidget(self.filter_button)

        self.export_button = QPushButton(qta.icon('fa5s.file-csv'), " Exporter en CSV")
        self.export_button.clicked.connect(self.export_to_csv)
        filter_layout.addWidget(self.export_button)

        filter_group.setLayout(filter_layout)
        self.layout.addWidget(filter_group)

    def populate_filters(self):
        # Utilisateurs
        self.user_combo.clear()
        self.user_combo.addItem("Tous", userData=None)
        users = self.user_controller.get_all_users()
        for user in users:
            self.user_combo.addItem(user['name'], userData=user['id'])

        # Projets
        self.project_combo.clear()
        self.project_combo.addItem("Tous", userData=None)
        projects = self.project_controller.get_all_projects()
        for project in projects:
            self.project_combo.addItem(f"{project['code']} - {project['nom']}", userData=project['id'])

        # Types d'activités
        self.activity_combo.clear()
        self.activity_combo.addItem("Toutes", userData=None)
        activities = self.project_controller.get_all_activity_types()
        for activity in activities:
            self.activity_combo.addItem(activity['name'], userData=activity['id'])

    def apply_filters(self):
        start_date = self.start_date_edit.date().toPyDate()
        end_date = self.end_date_edit.date().toPyDate()
        user_id = self.user_combo.currentData()
        project_id = self.project_combo.currentData()
        activity_type_id = self.activity_combo.currentData()

        time_entries = self.project_controller.get_time_entries_report(start_date, end_date, user_id, project_id, activity_type_id)
        
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

    def refresh_data(self):
        """Rafraîchit les filtres et applique les filtres pour recharger les données."""
        self.populate_filters()
        self.apply_filters()

    def export_to_csv(self):
        """Exporte les données actuellement filtrées dans un fichier CSV."""
        start_date = self.start_date_edit.date().toPyDate()
        end_date = self.end_date_edit.date().toPyDate()
        user_id = self.user_combo.currentData()
        project_id = self.project_combo.currentData()
        activity_type_id = self.activity_combo.currentData()

        time_entries = self.project_controller.get_time_entries_report(
            start_date, end_date, user_id, project_id, activity_type_id
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