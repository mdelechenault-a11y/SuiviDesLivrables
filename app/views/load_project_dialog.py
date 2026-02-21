import sys
from PyQt6.QtWidgets import (
    QDialog, QLineEdit, QPushButton, QVBoxLayout, QTableWidget, 
    QTableWidgetItem, QHeaderView, QAbstractItemView
)
from PyQt6.QtCore import Qt
from app.controllers.project_controller import ProjectController

class LoadProjectDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Charger un Projet")
        self.setMinimumSize(600, 400)
        self.selected_project_id = None
        self.controller = ProjectController()

        # --- Layouts ---
        self.layout = QVBoxLayout(self)
        
        # --- Widgets ---
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Rechercher par code ou nom...")
        
        self.project_table = QTableWidget()
        self.project_table.setColumnCount(4)
        self.project_table.setHorizontalHeaderLabels(["Code", "Nom", "Client", "Chef de Projet"])
        self.project_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.project_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.project_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.project_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        self.validate_button = QPushButton("Valider")
        self.cancel_button = QPushButton("Annuler")

        # --- Add widgets to layout ---
        self.layout.addWidget(self.search_input)
        self.layout.addWidget(self.project_table)
        self.layout.addWidget(self.validate_button)
        self.layout.addWidget(self.cancel_button)
        
        # --- Connections ---
        self.search_input.textChanged.connect(self.populate_projects)
        self.project_table.itemSelectionChanged.connect(self.handle_selection)
        self.validate_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)

        # --- Initial Population ---
        self.populate_projects()
        self.validate_button.setEnabled(False)

    def populate_projects(self):
        search_term = self.search_input.text()
        projects = self.controller.get_all_projects(search_term)
        
        self.project_table.setRowCount(0)
        for row, project in enumerate(projects):
            self.project_table.insertRow(row)
            # Store ID in the first item's data
            id_item = QTableWidgetItem(project["code"])
            id_item.setData(Qt.ItemDataRole.UserRole, project["id"])
            
            self.project_table.setItem(row, 0, id_item)
            self.project_table.setItem(row, 1, QTableWidgetItem(project["nom"]))
            self.project_table.setItem(row, 2, QTableWidgetItem(project["client_name"]))
            self.project_table.setItem(row, 3, QTableWidgetItem(project["pm_username"]))

    def handle_selection(self):
        selected_items = self.project_table.selectedItems()
        if selected_items:
            self.validate_button.setEnabled(True)
            # Get ID from the first column item
            self.selected_project_id = selected_items[0].data(Qt.ItemDataRole.UserRole)
        else:
            self.validate_button.setEnabled(False)
            self.selected_project_id = None
            
    def get_selected_project_id(self):
        return self.selected_project_id

if __name__ == '__main__':
    from PyQt6.QtWidgets import QApplication
    from qt_material import apply_stylesheet
    
    # This is just for testing the dialog
    app = QApplication(sys.argv)
    apply_stylesheet(app, theme='dark_blue.xml')
    dialog = LoadProjectDialog()
    if dialog.exec():
        print(f"Project selected: {dialog.get_selected_project_id()}")
    sys.exit()
