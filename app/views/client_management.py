import sys
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QPushButton,
    QHBoxLayout, QHeaderView, QMessageBox, QDialog, QFormLayout,
    QLineEdit, QTextEdit, QDialogButtonBox, QAbstractItemView
)
from PyQt6.QtCore import Qt
import qtawesome as qta
from app.controllers.project_controller import ProjectController

class ClientEditDialog(QDialog):
    """Dialogue pour ajouter ou modifier un client."""
    def __init__(self, controller: ProjectController, client_id=None, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.client_id = client_id
        self.is_edit_mode = client_id is not None

        self.setWindowTitle("Modifier le Client" if self.is_edit_mode else "Ajouter un Client")
        self.setMinimumWidth(400)

        layout = QFormLayout(self)
        
        self.name_input = QLineEdit()
        self.contact_info_input = QTextEdit()
        self.contact_info_input.setPlaceholderText("Adresse, email, téléphone, etc.")
        
        layout.addRow("Nom:", self.name_input)
        layout.addRow("Informations de contact:", self.contact_info_input)

        if self.is_edit_mode:
            details = self.controller.get_client_details(self.client_id)
            if details:
                self.name_input.setText(details.get('name', ''))
                self.contact_info_input.setText(details.get('contact_info', ''))

        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addRow(self.buttons)

    def get_data(self):
        """Retourne les données du formulaire sous forme de dictionnaire."""
        return {
            "name": self.name_input.text(),
            "contact_info": self.contact_info_input.toPlainText(),
        }

class ClientManagementView(QWidget):
    def __init__(self):
        super().__init__()
        self.controller = ProjectController()
        
        self.main_layout = QVBoxLayout(self)

        self.client_table = QTableWidget()
        self.client_table.setColumnCount(3)
        self.client_table.setHorizontalHeaderLabels(["ID", "Nom", "Informations de Contact"])
        self.client_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.client_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.client_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.client_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.client_table.hideColumn(0)

        buttons_layout = QHBoxLayout()
        self.add_button = QPushButton(qta.icon('fa5s.plus'), "Ajouter un Client")
        self.edit_button = QPushButton(qta.icon('fa5s.edit'), "Modifier le Client")
        self.delete_button = QPushButton(qta.icon('fa5s.trash-alt'), "Supprimer le Client")
        
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.add_button)
        buttons_layout.addWidget(self.edit_button)
        buttons_layout.addWidget(self.delete_button)

        self.main_layout.addWidget(self.client_table)
        self.main_layout.addLayout(buttons_layout)

        self.add_button.clicked.connect(self.add_client)
        self.edit_button.clicked.connect(self.edit_client)
        self.delete_button.clicked.connect(self.delete_client)
        self.client_table.doubleClicked.connect(self.edit_client)

        self.refresh_client_table()

    def refresh_client_table(self):
        try:
            clients = self.controller.get_all_clients() 
            self.client_table.setRowCount(len(clients))

            for row, client in enumerate(clients):
                self.client_table.setItem(row, 0, QTableWidgetItem(str(client["id"])))
                self.client_table.setItem(row, 1, QTableWidgetItem(client["name"]))
                self.client_table.setItem(row, 2, QTableWidgetItem(client.get("contact_info", "")))

        except Exception as e:
            QMessageBox.critical(self, "Erreur de chargement", f"Impossible de charger les clients: {e}")

    def get_selected_client_id(self):
        selected_rows = self.client_table.selectionModel().selectedRows()
        if not selected_rows:
            return None
        return int(self.client_table.item(selected_rows[0].row(), 0).text())

    def add_client(self):
        dialog = ClientEditDialog(self.controller, parent=self)
        if dialog.exec():
            data = dialog.get_data()
            if not data['name']:
                QMessageBox.warning(self, "Champs requis", "Le nom du client est requis.")
                return
            
            success, message = self.controller.add_client(data)
            if success:
                QMessageBox.information(self, "Succès", message)
                self.refresh_client_table()
            else:
                QMessageBox.critical(self, "Erreur", message)

    def edit_client(self):
        client_id = self.get_selected_client_id()
        if client_id is None:
            QMessageBox.warning(self, "Aucune sélection", "Veuillez sélectionner un client à modifier.")
            return

        dialog = ClientEditDialog(self.controller, client_id=client_id, parent=self)
        if dialog.exec():
            data = dialog.get_data()
            if not data['name']:
                QMessageBox.warning(self, "Champs requis", "Le nom du client est requis.")
                return
            success, message = self.controller.update_client(client_id, data)
            if success:
                QMessageBox.information(self, "Succès", message)
                self.refresh_client_table()
            else:
                QMessageBox.critical(self, "Erreur", message)

    def delete_client(self):
        client_id = self.get_selected_client_id()
        if client_id is None:
            QMessageBox.warning(self, "Aucune sélection", "Veuillez sélectionner un client à supprimer.")
            return
        
        reply = QMessageBox.question(self, "Confirmation de suppression",
                                     "Êtes-vous sûr de vouloir retirer ce client de la liste ?\nSes données seront conservées pour l'historique.",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            success, message = self.controller.soft_delete_client(client_id)
            if success:
                QMessageBox.information(self, "Succès", message)
                self.refresh_client_table()
            else:
                QMessageBox.critical(self, "Erreur de suppression", message)