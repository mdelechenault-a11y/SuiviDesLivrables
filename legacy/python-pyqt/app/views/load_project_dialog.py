import sys
from PyQt6.QtWidgets import (
    QDialog, QLineEdit, QPushButton, QVBoxLayout, QTableWidget, 
    QTableWidgetItem, QHeaderView, QAbstractItemView, QDialogButtonBox,
    QLabel, QHBoxLayout
)
from PyQt6.QtCore import Qt
import qtawesome as qta
from app.controllers.project_controller import ProjectController

class LoadProjectDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Charger un Projet")
        self.resize(800, 600)
        self.selected_project_id = None
        self.controller = ProjectController()

        # --- Layout ---
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.layout.setSpacing(15)
        
        # --- Header ---
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 10)

        icon_label = QLabel()
        icon = qta.icon('fa5s.folder-open', color='#3498db')
        icon_label.setPixmap(icon.pixmap(48, 48))

        title_label = QLabel("Sélectionner un projet")
        font = title_label.font()
        font.setPointSize(18)
        font.setBold(True)
        title_label.setFont(font)

        header_layout.addWidget(icon_label)
        header_layout.addSpacing(15)
        header_layout.addWidget(title_label)
        header_layout.addStretch()

        self.layout.addLayout(header_layout)

        # --- Widgets ---
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Rechercher par code, nom, client...")
        
        self.project_table = QTableWidget()
        self.project_table.setColumnCount(4)
        self.project_table.setHorizontalHeaderLabels(["Code", "Nom", "Client", "Chef de Projet"])
        
        header = self.project_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)

        self.project_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.project_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.project_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.project_table.setAlternatingRowColors(True)
        self.project_table.verticalHeader().setVisible(False)

        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.validate_button = self.button_box.button(QDialogButtonBox.StandardButton.Ok)
        self.validate_button.setText("Valider")
        
        # --- Add widgets to layout ---
        self.layout.addWidget(self.search_input)
        self.layout.addWidget(self.project_table)
        self.layout.addWidget(self.button_box)
        
        # --- Connections ---
        self.search_input.textChanged.connect(self.populate_projects)
        self.project_table.itemSelectionChanged.connect(self.handle_selection)
        self.project_table.doubleClicked.connect(self.accept)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        # --- Initial Population ---
        self.populate_projects()
        self.validate_button.setEnabled(False)

    def populate_projects(self):
        search_term = self.search_input.text()
        # Assuming the controller method can handle an empty search term
        projects = self.controller.get_all_projects(search_term)
        
        self.project_table.setRowCount(0)
        self.project_table.setSortingEnabled(False)
        for row, project in enumerate(projects):
            self.project_table.insertRow(row)
            # Store ID in the first item's data
            id_item = QTableWidgetItem(project["code"])
            id_item.setData(Qt.ItemDataRole.UserRole, project["id"])
            
            self.project_table.setItem(row, 0, id_item)
            self.project_table.setItem(row, 1, QTableWidgetItem(project["nom"]))
            self.project_table.setItem(row, 2, QTableWidgetItem(project["client_name"]))
            self.project_table.setItem(row, 3, QTableWidgetItem(project["pm_username"]))
        self.project_table.setSortingEnabled(True)

    def handle_selection(self):
        selected_items = self.project_table.selectedItems()
        if selected_items:
            self.validate_button.setEnabled(True)
            # Get ID from the first column item of the selected row
            row = self.project_table.row(selected_items[0])
            self.selected_project_id = self.project_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        else:
            self.validate_button.setEnabled(False)
            self.selected_project_id = None
            
    def get_selected_project_id(self):
        # Ensure ID is up-to-date on accept
        self.handle_selection()
        return self.selected_project_id

if __name__ == '__main__':
    from PyQt6.QtWidgets import QApplication
    from qt_material import apply_stylesheet
    
    app = QApplication(sys.argv)
    apply_stylesheet(app, theme='dark_blue.xml')
    dialog = LoadProjectDialog()
    if dialog.exec():
        print(f"Project selected: {dialog.get_selected_project_id()}")
    sys.exit()
