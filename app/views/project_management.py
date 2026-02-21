import sys
from functools import partial
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QComboBox, 
    QPushButton, QVBoxLayout, QFormLayout, QMessageBox, QDateEdit, 
    QGroupBox, QHBoxLayout, QTableWidget, QHeaderView, QTableWidgetItem, QSpinBox,
    QAbstractItemView, QScrollArea, QDialog, QDialogButtonBox, QDoubleSpinBox,
    QCheckBox, QSplitter
)
import datetime
from PyQt6.QtCore import QDate, Qt, pyqtSignal
import qtawesome as qta

from app.controllers.project_controller import ProjectController
from app.views.gantt_chart import GanttChart
from app.views.add_client_dialog import AddClientDialog
from app.views.widgets.loading_dialog import LoadingDialog
from app.models.schema import ProjectStatus

class TaskTableWidget(QTableWidget):
    """
    Tableau personnalisé pour gérer le glisser-déposer des tâches de manière robuste.
    Émet un signal avec la nouvelle liste d'ID de tâches après un drop.
    """
    rows_reordered = pyqtSignal(list)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setDragDropOverwriteMode(False)
        self.setDropIndicatorShown(True)

    def dropEvent(self, event: 'QDropEvent'):
        if event.source() is not self or not (event.dropAction() == Qt.DropAction.MoveAction):
            super().dropEvent(event)
            return

        try:
            source_row = self.currentRow()
            target_item = self.itemAt(event.position().toPoint())
            target_row = self.row(target_item) if target_item else self.rowCount()

            if source_row == -1 or source_row == target_row:
                event.ignore()
                return

            # Construire la liste des ID dans leur ordre actuel
            all_ids = [self.item(r, 0).data(Qt.ItemDataRole.UserRole) for r in range(self.rowCount())]
            
            # Effectuer le déplacement dans la liste
            moved_id = all_ids.pop(source_row)
            
            # Ajuster la cible si on déplace un élément vers le bas
            if source_row < target_row:
                target_row -= 1

            all_ids.insert(target_row, moved_id)
            
            # Émettre le signal avec le nouvel ordre et laisser la vue principale gérer la mise à jour
            self.rows_reordered.emit(all_ids)
            event.accept()
        except Exception as e:
            print(f"Erreur lors du glisser-déposer : {e}")
            event.ignore()

class UserAssignmentDialog(QDialog):
    def __init__(self, controller, parent=None, assignments=None):
        super().__init__(parent)
        self.setWindowTitle("Affecter des Utilisateurs et leurs Heures")
        self.controller = controller
        self.assignments = assignments or {}
        self.layout = QVBoxLayout(self)
        self.layout.addWidget(QLabel("Cochez les utilisateurs à affecter et définissez les heures allouées :"))
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Utilisateur", "Affecté", "Heures Allouées"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.layout.addWidget(self.table)
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        self.layout.addWidget(self.buttons)
        self.populate_users()

    def populate_users(self):
        all_users = self.controller.get_all_users()
        self.table.setRowCount(len(all_users))
        for row, user in enumerate(all_users):
            user_id = user['id']
            is_assigned = user_id in self.assignments
            name_item = QTableWidgetItem(f"{user['name']} ({user['username']})")
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 0, name_item)
            checkbox = QCheckBox()
            checkbox.setChecked(is_assigned)
            checkbox_widget = QWidget()
            chk_layout = QHBoxLayout(checkbox_widget)
            chk_layout.addWidget(checkbox)
            chk_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            chk_layout.setContentsMargins(0,0,0,0)
            self.table.setCellWidget(row, 1, checkbox_widget)
            heures_spinbox = QDoubleSpinBox()
            heures_spinbox.setRange(0.0, 1000.0)
            heures_spinbox.setValue(self.assignments.get(user_id, 8.0))
            heures_spinbox.setEnabled(is_assigned)
            self.table.setCellWidget(row, 2, heures_spinbox)
            checkbox.stateChanged.connect(heures_spinbox.setEnabled)

    def get_assignments(self):
        new_assignments = {}
        for row in range(self.table.rowCount()):
            checkbox = self.table.cellWidget(row, 1).findChild(QCheckBox)
            if checkbox and checkbox.isChecked():
                user_id = self.controller.get_all_users()[row]['id']
                heures_spinbox = self.table.cellWidget(row, 2)
                new_assignments[user_id] = heures_spinbox.value()
        return new_assignments

class ProjectInfoDialog(QDialog):
    def __init__(self, project_details, controller, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Modifier les Informations du Projet")
        self.controller = controller
        self.details = project_details

        self.layout = QFormLayout(self)
        
        self.code_input = QLineEdit(self.details.get('code', ''))
        self.code_input.setInputMask("99-999-AAA;#")
        self.nom_input = QLineEdit(self.details.get('nom', ''))
        self.budget_material_input = QDoubleSpinBox()
        self.budget_material_input.setRange(0.0, 1_000_000.0)
        self.budget_material_input.setSuffix(" €")
        self.budget_material_input.setValue(self.details.get('budget_material_planned', 0.0))
        self.pm_combo = QComboBox()
        self.client_combo = QComboBox()
        self.company_combo = QComboBox()
        self.status_combo = QComboBox()
        self.status_combo.addItems([s.value for s in ProjectStatus])
        
        self.populate_pms()
        self.populate_clients()
        self.populate_companies()
        
        self.layout.addRow("Code Projet:", self.code_input)
        self.layout.addRow("Nom Projet:", self.nom_input)
        self.layout.addRow("Budget Matériel Prévu:", self.budget_material_input)
        self.layout.addRow("Chef de Projet:", self.pm_combo)
        self.layout.addRow("Client:", self.client_combo)
        self.layout.addRow("Société:", self.company_combo)
        self.layout.addRow("Statut:", self.status_combo)

        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.accepted.connect(self.validate_and_accept)
        self.buttons.rejected.connect(self.reject)
        self.layout.addRow(self.buttons)

    def populate_pms(self):
        """Populates the Project Manager combo box with users having the correct role."""
        pms = self.controller.get_project_managers()
        for pm in pms:
            self.pm_combo.addItem(pm["name"], userData=pm["id"])
        
        pm_index = self.pm_combo.findData(self.details.get("chef_de_projet_id"))
        if pm_index != -1:
            self.pm_combo.setCurrentIndex(pm_index)

    def populate_clients(self):
        clients = self.controller.get_all_clients()
        for client in clients:
            self.client_combo.addItem(client["name"], userData=client["id"])
        
        client_index = self.client_combo.findData(self.details.get("client_id"))
        if client_index != -1:
            self.client_combo.setCurrentIndex(client_index)

    def populate_companies(self):
        """Populates the Company combo box."""
        companies = self.controller.get_all_companies()
        self.company_combo.addItem("Aucune", userData=None)
        for company in companies:
            self.company_combo.addItem(company["name"], userData=company["id"])
        company_index = self.company_combo.findData(self.details.get("company_id"))
        if company_index != -1:
            self.company_combo.setCurrentIndex(company_index)

        status_value = self.details.get("statut")
        if isinstance(status_value, ProjectStatus):
            status_value = status_value.value

        status_index = self.status_combo.findText(status_value or "")
        if status_index != -1:
            self.status_combo.setCurrentIndex(status_index)
            
    def validate_and_accept(self):
        """Vérifie la validité du masque avant de fermer la boîte de dialogue."""
        if not self.code_input.hasAcceptableInput():
            QMessageBox.warning(self, "Format Invalide", "Le format du Code Projet est incorrect ou incomplet.\nIl doit être de la forme 12-345-ABC.")
            return
        self.accept()

    def get_data(self):
        return {
            "code": self.code_input.text(),
            "nom": self.nom_input.text(),
            "budget_material_planned": self.budget_material_input.value(),
            "chef_de_projet_id": self.pm_combo.currentData(),
            "client_id": self.client_combo.currentData(),
            "statut": self.status_combo.currentText(),
            "company_id": self.company_combo.currentData()
        }

class ProjectManagementWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.controller = ProjectController()
        self.current_project_id = None
        self.current_task_id = None
        self.project_start_date = None
        self.task_assignments = {}
        self.project_tasks_data = []

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(5, 5, 5, 5)

        self.top_bar = QHBoxLayout()
        self.project_title_label = QLabel("Aucun projet chargé")
        font = self.project_title_label.font()
        font.setPointSize(12)
        font.setBold(True)
        self.project_title_label.setFont(font)
        
        self.edit_project_button = QPushButton(qta.icon('fa5s.pencil-alt'), " Modifier les infos du projet")
        self.export_csv_button = QPushButton(qta.icon('fa5s.file-csv'), " Export CSV")
        
        self.top_bar.addWidget(self.project_title_label)
        self.top_bar.addStretch()
        self.top_bar.addWidget(self.edit_project_button)
        self.top_bar.addWidget(self.export_csv_button)
        self.main_layout.addLayout(self.top_bar)

        self.content_layout = QHBoxLayout()
        self.left_panel = QWidget()
        self.left_panel_layout = QVBoxLayout(self.left_panel)
        self.left_panel_layout.setSpacing(5)
        self.left_panel_layout.setContentsMargins(0, 0, 0, 0)

        self.task_form_group = QGroupBox("Ajouter / Modifier une Tâche")
        task_form_layout = QHBoxLayout() # Changed to Horizontal for 2 columns
        self.task_form_group.setLayout(task_form_layout)

        # --- Left Column (Inputs) ---
        left_inputs_layout = QVBoxLayout()
        
        # Ligne 1: Nom de la Tâche
        label_width = 80
        name_layout = QHBoxLayout()
        nom_label = QLabel("Nom :")
        nom_label.setFixedWidth(label_width)
        name_layout.addWidget(nom_label)
        self.task_nom_input = QLineEdit()
        self.task_nom_input.setPlaceholderText("Nom de la tâche")
        name_layout.addWidget(self.task_nom_input)
        left_inputs_layout.addLayout(name_layout)

        # Ligne 2: Métriques Temporelles (3 éléments côte à côte)
        metrics_layout = QHBoxLayout()
        duree_label = QLabel("Durée :")
        duree_label.setFixedWidth(label_width)
        metrics_layout.addWidget(duree_label)
        self.task_duree_jours_input = QSpinBox()
        self.task_duree_jours_input.setRange(1, 999)
        self.task_duree_jours_input.setFixedWidth(60)
        metrics_layout.addWidget(self.task_duree_jours_input)
        metrics_layout.addSpacing(15)
        metrics_layout.addWidget(QLabel("Heures :"))
        self.task_heures_input = QSpinBox()
        self.task_heures_input.setRange(1, 9999)
        self.task_heures_input.setFixedWidth(70)
        metrics_layout.addWidget(self.task_heures_input)
        metrics_layout.addSpacing(15)
        metrics_layout.addWidget(QLabel("Début :"))
        self.task_date_debut_input = QDateEdit(calendarPopup=True)
        self.task_date_debut_input.setDate(QDate.currentDate())
        metrics_layout.addWidget(self.task_date_debut_input)
        metrics_layout.addStretch()
        left_inputs_layout.addLayout(metrics_layout)

        # Ligne 3: Tâche Parente
        parent_layout = QHBoxLayout()
        parent_label = QLabel("Parent :")
        parent_label.setFixedWidth(label_width)
        parent_layout.addWidget(parent_label)
        self.task_parente_combo = QComboBox()
        parent_layout.addWidget(self.task_parente_combo)
        left_inputs_layout.addLayout(parent_layout)

        # Ligne 4: Type d'Activité
        activity_layout = QHBoxLayout()
        activite_label = QLabel("Activité :")
        activite_label.setFixedWidth(label_width)
        activity_layout.addWidget(activite_label)
        self.task_type_combo = QComboBox()
        activity_layout.addWidget(self.task_type_combo)
        left_inputs_layout.addLayout(activity_layout)
        
        left_inputs_layout.addStretch()

        # --- Right Column (Actions) ---
        right_actions_layout = QVBoxLayout()

        self.assign_users_button = QPushButton("Affecter / Gérer les Heures")
        self.add_task_button = QPushButton("Ajouter Tâche")
        self.modify_task_button = QPushButton("Modifier Tâche")
        self.clear_selection_button = QPushButton("Désélectionner")
        
        right_actions_layout.addWidget(self.assign_users_button)
        right_actions_layout.addWidget(self.add_task_button)
        right_actions_layout.addWidget(self.modify_task_button)
        right_actions_layout.addWidget(self.clear_selection_button)
        right_actions_layout.addStretch()
        
        self.modify_task_button.hide()

        task_form_layout.addLayout(left_inputs_layout, stretch=2)
        task_form_layout.addLayout(right_actions_layout, stretch=1)

        self.assigned_users_label = QLabel("Utilisateurs Affectés à la Tâche Sélectionnée:")
        self.assigned_users_label.setContentsMargins(0, 0, 0, 2) # Reduce bottom margin

        self.assigned_users_table = QTableWidget()
        self.assigned_users_table.setColumnCount(4)
        self.assigned_users_table.setHorizontalHeaderLabels(["ID", "Utilisateur", "Heures Allouées", "Heures Réelles"])
        self.assigned_users_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.assigned_users_table.hideColumn(0)
        self.assigned_users_table.setShowGrid(False)
        self.assigned_users_table.verticalHeader().setVisible(False)
        self.assigned_users_table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #4a5060;
                border-radius: 4px;
            }
            QHeaderView::section {
                background-color: transparent; border: none; padding: 4px;
            }""")
        self.assigned_users_table.setMinimumHeight(150)

        self.task_table = TaskTableWidget()
        self.task_table.setColumnCount(7)
        self.task_table.setHorizontalHeaderLabels(["ID", "Nom", "Début", "Fin", "Durée (j)", "Heures Prév.", "Parente ID"])
        header = self.task_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        self.task_table.setColumnWidth(1, 350)
        self.task_table.hideColumn(0)
        self.task_table.viewport().installEventFilter(self)

        # --- NEW Splitter Implementation for Left Panel ---
        # Container for Users (Bottom)
        users_container = QWidget()
        users_layout = QVBoxLayout(users_container)
        users_layout.setContentsMargins(0,0,0,0)
        users_layout.addWidget(self.assigned_users_label)
        users_layout.addWidget(self.assigned_users_table)
        
        # Bottom splitter for tasks and assigned users
        bottom_splitter = QSplitter(Qt.Orientation.Vertical)
        bottom_splitter.addWidget(self.task_table)
        bottom_splitter.addWidget(users_container)

        # Main splitter for the left panel
        left_panel_splitter = QSplitter(Qt.Orientation.Vertical)
        left_panel_splitter.addWidget(self.task_form_group)
        left_panel_splitter.addWidget(bottom_splitter)
        left_panel_splitter.setSizes([250, 750]) # Give more space to tables (approx 30/70)
        self.left_panel_layout.addWidget(left_panel_splitter)

        self.gantt_scroll_area = QScrollArea()
        self.gantt_chart = GanttChart()
        self.gantt_scroll_area.setWidget(self.gantt_chart)
        self.gantt_scroll_area.setWidgetResizable(True)
        self.left_panel.setMinimumWidth(0)
        self.gantt_scroll_area.setMinimumWidth(0)
        
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.left_panel)
        splitter.addWidget(self.gantt_scroll_area)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([300, 700])
        
        self.content_layout.addWidget(splitter)
        self.main_layout.addLayout(self.content_layout)
        
        self.set_project_loaded(False)

        self.gantt_chart.task_clicked.connect(self.on_gantt_task_clicked)
        self.gantt_chart.task_duration_changed.connect(self.on_task_duration_changed)
        self.gantt_chart.task_lag_changed.connect(self.on_task_lag_changed)
        self.edit_project_button.clicked.connect(self.open_edit_project_dialog)
        self.add_task_button.clicked.connect(self.add_task)
        self.modify_task_button.clicked.connect(self.update_task)
        self.clear_selection_button.clicked.connect(self.reset_task_form)
        self.assign_users_button.clicked.connect(self.open_user_assignment_dialog)
        self.task_table.itemSelectionChanged.connect(self.on_task_selected)
        self.export_csv_button.clicked.connect(self.export_project_to_csv)
        self.task_table.rows_reordered.connect(self.on_tasks_reordered)

        self.populate_activity_types()
    
    def eventFilter(self, source, event):
        if (event.type() == event.Type.MouseButtonPress and
            source is self.task_table.viewport()):
            item = self.task_table.itemAt(event.pos())
            if item is None:
                self.reset_task_form()
        return super().eventFilter(source, event)
    
    def set_project_loaded(self, loaded):
        self.left_panel.setVisible(loaded)
        self.gantt_scroll_area.setVisible(loaded)
        self.edit_project_button.setVisible(loaded)
        self.export_csv_button.setVisible(loaded)
        if not loaded:
            self.project_title_label.setText("Chargez un projet pour commencer")

    def load_project(self, project_id):
        loading_dialog = LoadingDialog(f"Chargement du projet...", self)
        loading_dialog.show()
        QApplication.processEvents()

        try:
            details = self.controller.get_project_details(project_id)
            if not details:
                QMessageBox.critical(self, "Erreur", "Impossible de charger les détails du projet.")
                return

            self.current_project_id = project_id
            self.project_start_date = details['date_debut']
            self.project_title_label.setText(f"Projet: {details['nom']} ({details['code']})")
            
            self.populate_parent_tasks()
            self.refresh_task_table()
            self.reset_task_form()
            self.set_project_loaded(True)
        finally:
            loading_dialog.accept()
        
    def open_edit_project_dialog(self):
        if not self.current_project_id: return
        details = self.controller.get_project_details(self.current_project_id)
        if not details: return

        dialog = ProjectInfoDialog(details, self.controller, self)
        if dialog.exec():
            new_data = dialog.get_data()
            success, message = self.controller.update_project(self.current_project_id, new_data)
            if success:
                self.load_project(self.current_project_id)
            else:
                QMessageBox.critical(self, "Erreur", message)

    def on_task_selected(self):
        selected_items = self.task_table.selectedItems()
        if not selected_items:
            self.reset_task_form()
            return
        
        task_id = self.task_table.item(self.task_table.currentRow(), 0).data(Qt.ItemDataRole.UserRole)
        task_details = self.controller.get_task_details(task_id)

        if task_details:
            self.current_task_id = task_details["id"]
            self.task_nom_input.setText(task_details["nom"])
            self.task_duree_jours_input.setValue(int(task_details["duree_jours"] or 0))
            self.task_heures_input.setValue(int(task_details["heures_prevues"] or 0))
            self.task_date_debut_input.setDate(QDate(task_details["date_debut_calculee"]))
            
            type_index = self.task_type_combo.findText(task_details["activity_type_name"])
            self.task_type_combo.setCurrentIndex(type_index)

            parent_index = self.task_parente_combo.findData(task_details.get("parente_id"))
            self.task_parente_combo.setCurrentIndex(parent_index if parent_index != -1 else 0)

            self.task_assignments = {
                a['user_id']: {'temps_alloue': a['temps_alloue'], 'temps_pointe': a.get('temps_pointe', 0.0)}
                for a in task_details.get('assignments', [])
            }
            self.update_assigned_users_table()
            
            self.add_task_button.hide()
            self.modify_task_button.show()

    def on_task_duration_changed(self, task_id, new_duration):
        """Appelé lorsque la durée d'une tâche est modifiée depuis le Gantt."""
        success, message = self.controller.update_task(task_id, {'duree_jours': new_duration})
        if success:
            # Rafraîchir pour voir les changements et recalculer les dépendances
            self.refresh_task_table()
        else:
            QMessageBox.critical(self, "Erreur de mise à jour", f"Impossible de modifier la durée de la tâche:\n{message}")

    def on_task_lag_changed(self, task_id, new_lag):
        """Appelé lorsque le décalage (lag) d'une tâche est modifié depuis le Gantt."""
        success, message = self.controller.update_task(task_id, {'lag_days': new_lag})
        if success:
            # Rafraîchir pour voir les changements et recalculer les dépendances
            self.refresh_task_table()
        else:
            QMessageBox.critical(self, "Erreur de mise à jour", f"Impossible de modifier le décalage de la tâche:\n{message}")

    def on_gantt_task_clicked(self, task_id):
        """Sélectionne la tâche correspondante dans le tableau lorsqu'elle est cliquée dans le diagramme de Gantt."""
        for row in range(self.task_table.rowCount()):
            # L'ID est stocké dans la colonne 0
            item = self.task_table.item(row, 0)
            if item and item.data(Qt.ItemDataRole.UserRole) == task_id:
                self.task_table.selectRow(row)
                # S'assurer que la ligne sélectionnée est visible
                self.task_table.scrollToItem(item, QAbstractItemView.ScrollHint.PositionAtCenter)
                return

    def _get_task_data_from_form(self):
        task_data = {
            "nom": self.task_nom_input.text(),
            "duree_jours": self.task_duree_jours_input.value(),
            "heures_prevues": self.task_heures_input.value(),
            "activity_type_name": self.task_type_combo.currentText(),
            "parente_id": self.task_parente_combo.currentData(),
            "date_debut": self.task_date_debut_input.date().toPyDate(),
            "assignments": [{'user_id': uid, 'temps_alloue': data['temps_alloue']} 
                            for uid, data in self.task_assignments.items()]
        }
        if not all([task_data["nom"], task_data["duree_jours"] > 0, task_data["heures_prevues"] > 0]):
            QMessageBox.warning(self, "Erreur de saisie", "Nom, durée (>0) et heures prévues (>0) sont requis.")
            return None
        return task_data

    def add_task(self):
        if not self.current_project_id: return
        
        task_data = self._get_task_data_from_form()
        if task_data is None: return

        # Ensure we are not accidentally updating a task
        self.current_task_id = None 
        
        success, message = self.controller.add_task(self.current_project_id, task_data)

        if success:
            self.populate_parent_tasks()
            self.refresh_task_table()
            self.reset_task_form()
        else:
            QMessageBox.critical(self, "Erreur", message)

    def update_task(self):
        if not self.current_project_id or not self.current_task_id:
            return

        task_data = self._get_task_data_from_form()
        if task_data is None: return

        success, message = self.controller.update_task(self.current_task_id, task_data)

        if success:
            self.populate_parent_tasks()
            self.refresh_task_table()
            self.reset_task_form()
        else:
            QMessageBox.critical(self, "Erreur", message)

    def reset_task_form(self):
        self.current_task_id = None
        self.task_nom_input.clear()
        self.task_duree_jours_input.setValue(1)
        self.task_heures_input.setValue(8)
        self.task_date_debut_input.setDate(QDate.currentDate())
        self.task_type_combo.setCurrentIndex(0)
        self.task_parente_combo.setCurrentIndex(0)
        self.task_table.clearSelection()
        self.task_assignments = {}
        self.update_assigned_users_table()
        self.add_task_button.show()
        self.modify_task_button.hide()
        
    def reset_view(self):
        default_details = {
            "code": "",
            "nom": "",
            "client_id": None,
            "statut": ProjectStatus.CHiffrage.value
        }

        dialog = ProjectInfoDialog(default_details, self.controller, self)
        if dialog.exec():
            project_data = dialog.get_data()
            
            if not project_data.get("nom") or not project_data.get("code"):
                QMessageBox.warning(self, "Données Incomplètes", "Le nom et le code du projet sont obligatoires.")
                return

            # Note: Assuming create_project exists in the controller
            success, result = self.controller.create_project(project_data)

            if success:
                new_project_id = result
                self.load_project(new_project_id)
            else:
                QMessageBox.critical(self, "Erreur de Création", str(result))

    def populate_activity_types(self):
        self.task_type_combo.clear()
        desired_types = [
            "Développement Logiciel", "Conception Mécanique", "Étude Électrique", 
            "Montage Mécanique", "Câblage Électrique", "Documentation", "Gestion de Projet",
            "SAV", "Expertise", "Autres", "Conception Électronique", "Commande Matériel"
        ]
        self.controller.ensure_activity_types_exist(desired_types)
        all_types = self.controller.get_all_activity_type_names()
        self.task_type_combo.addItems(all_types)

    def populate_parent_tasks(self):
        self.task_parente_combo.clear()
        self.task_parente_combo.addItem("Aucune", userData=None)
        if self.current_project_id:
            tasks = self.controller.get_project_tasks(self.current_project_id)
            for task in tasks:
                if self.current_task_id and task["id"] == self.current_task_id:
                    continue
                self.task_parente_combo.addItem(task["name"], userData=task["id"])

    def refresh_task_table(self):
        self.task_table.setRowCount(0)
        if self.current_project_id:
            self.task_table.blockSignals(True)
            tasks = self.controller.get_project_tasks_for_display(self.current_project_id)
            self.project_tasks_data = tasks
            self.task_table.setRowCount(len(tasks))
            for row, task in enumerate(tasks):
                id_item = QTableWidgetItem(str(task["id"]))
                id_item.setData(Qt.ItemDataRole.UserRole, task["id"])
                self.task_table.setItem(row, 0, id_item)
                self.task_table.setItem(row, 1, QTableWidgetItem(task["nom"]))
                self.task_table.setItem(row, 2, QTableWidgetItem(task["date_debut_calculee"].strftime('%Y-%m-%d') if task["date_debut_calculee"] else "N/A"))
                self.task_table.setItem(row, 3, QTableWidgetItem(task["date_fin"].strftime('%Y-%m-%d') if task["date_fin"] else "N/A"))
                self.task_table.setItem(row, 4, QTableWidgetItem(str(task["duree_jours"])))
                self.task_table.setItem(row, 5, QTableWidgetItem(str(task["heures_prevues"])))
                self.task_table.setItem(row, 6, QTableWidgetItem(str(task["parente_id"]) if task["parente_id"] else ""))
            self.task_table.blockSignals(False)
            self.gantt_chart.set_data(tasks, self.project_start_date)

    def on_tasks_reordered(self, new_id_order):
        """
        Appelé après un glisser-déposer réussi. Met à jour la base de données
        et rafraîchit la vue pour garantir la cohérence.
        """
        # Persist the new order to the database
        if self.current_project_id:
            success, message = self.controller.update_task_order(self.current_project_id, new_id_order)
            if not success:
                QMessageBox.critical(self, "Erreur de Sauvegarde", f"Impossible de sauvegarder le nouvel ordre des tâches:\n{message}")
            
            # Toujours rafraîchir depuis la base de données pour garantir la cohérence
            self.refresh_task_table()

    def open_user_assignment_dialog(self):
        if self.current_task_id is None:
            QMessageBox.warning(self, "Aucune Tâche Sélectionnée", "Veuillez d'abord sélectionner une tâche.")
            return
        
        allocated_hours = {uid: data['temps_alloue'] for uid, data in self.task_assignments.items()}
        dialog = UserAssignmentDialog(self.controller, self, allocated_hours)
        
        if dialog.exec():
            new_allocations = dialog.get_assignments()
            
            # Rebuild self.task_assignments, preserving temps_pointe for existing users
            # and removing users that were de-selected.
            current_assignments = {}
            for user_id, hours in new_allocations.items():
                if user_id in self.task_assignments:
                    # Preserve existing temps_pointe
                    current_assignments[user_id] = {
                        'temps_alloue': hours,
                        'temps_pointe': self.task_assignments[user_id]['temps_pointe']
                    }
                else:
                    # New user, temps_pointe is 0
                    current_assignments[user_id] = {'temps_alloue': hours, 'temps_pointe': 0.0}
            self.task_assignments = current_assignments
            self.update_assigned_users_table()

            # Persist these changes to the database
            assignments_to_save = [{'user_id': uid, 'temps_alloue': data['temps_alloue']} for uid, data in self.task_assignments.items()]
            success, message = self.controller.update_task_assignments(self.current_task_id, assignments_to_save)
            if not success:
                QMessageBox.critical(self, "Erreur de sauvegarde", f"Impossible de sauvegarder les affectations : {message}")
    
    def on_assignment_hours_finished(self, user_id, spinbox):
        """
        Se déclenche lorsque l'édition des heures est terminée (perte de focus ou Entrée).
        """
        new_hours = spinbox.value()
        if self.current_task_id is None: return
        
        if user_id in self.task_assignments:
            self.task_assignments[user_id]['temps_alloue'] = new_hours
        success, message = self.controller.update_assignment_hours(self.current_task_id, user_id, new_hours)

    def update_assigned_users_table(self):
        self.assigned_users_table.blockSignals(True)
        self.assigned_users_table.setRowCount(0)
        self.assigned_users_table.setRowCount(len(self.task_assignments))
        all_users = {u['id']: u for u in self.controller.get_all_users()}
        for row, user_id in enumerate(self.task_assignments.keys()):
            user_info = all_users.get(user_id)
            if not user_info: continue

            assignment_data = self.task_assignments[user_id]

            id_item = QTableWidgetItem(str(user_id))
            id_item.setData(Qt.ItemDataRole.UserRole, user_id)
            self.assigned_users_table.setItem(row, 0, id_item)

            name_item = QTableWidgetItem(user_info['name'])
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.assigned_users_table.setItem(row, 1, name_item)

            # Heures Allouées (editable spinbox)
            heures_spinbox = QDoubleSpinBox()
            heures_spinbox.setRange(0.0, 1000.0)
            heures_spinbox.setValue(assignment_data.get('temps_alloue', 0.0))
            handler = partial(self.on_assignment_hours_finished, user_id, heures_spinbox)
            heures_spinbox.editingFinished.connect(handler)
            self.assigned_users_table.setCellWidget(row, 2, heures_spinbox)

            # Heures Réelles (read-only item)
            temps_pointe = assignment_data.get('temps_pointe', 0.0)
            heures_reelles_item = QTableWidgetItem(f"{temps_pointe:.2f}")
            heures_reelles_item.setFlags(heures_reelles_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            heures_reelles_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.assigned_users_table.setItem(row, 3, heures_reelles_item)
        self.assigned_users_table.blockSignals(False)

    def export_project_to_csv(self):
        if not self.current_project_id: return
        success, message = self.controller.export_project_to_csv(self.current_project_id)
        if success:
            QMessageBox.information(self, "Exportation Réussie", f"Le projet a été exporté avec succès dans:\n{message}")
        else:
            QMessageBox.critical(self, "Erreur d'Exportation", message)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    apply_stylesheet(app, theme='dark_blue.xml')
    from PyQt6.QtWidgets import QMainWindow
    window = QMainWindow()
    pm_widget = ProjectManagementWidget()
    window.setCentralWidget(pm_widget)
    window.show()
    sys.exit(app.exec())