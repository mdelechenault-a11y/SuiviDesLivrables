import sys
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QPushButton, QLabel,
    QHBoxLayout, QHeaderView, QMessageBox, QDialog, QFormLayout,
    QLineEdit, QTextEdit, QDialogButtonBox, QAbstractItemView, QLabel
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

        title = "Modifier le Client" if self.is_edit_mode else "Ajouter un Client"
        icon_name = 'fa5s.building'  # Icône pour une société/client
        self.setWindowTitle(title)
        self.setWindowIcon(qta.icon(icon_name, color='white'))
        self.setMinimumWidth(450)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(10)

        # --- En-tête avec icône ---
        title_bar = QHBoxLayout()
        icon_label = QLabel()
        icon_label.setPixmap(qta.icon(icon_name, color='#3498db').pixmap(32, 32))
        title_label = QLabel(title)
        font = title_label.font()
        font.setPointSize(16)
        font.setBold(True)
        title_label.setFont(font)
        title_bar.addWidget(icon_label)
        title_bar.addSpacing(10)
        title_bar.addWidget(title_label)
        title_bar.addStretch()
        main_layout.addLayout(title_bar)
        
        # --- Formulaire ---
        form_layout = QFormLayout()
        form_layout.setSpacing(15)
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.name_input = QLineEdit()
        self.code_input = QLineEdit()
        self.code_input.setInputMask(">AAA")
        self.address_input = QTextEdit()
        self.address_input.setMinimumHeight(40)
        self.phone_input = QLineEdit()
        self.website_input = QLineEdit()
        self.contact_info_input = QTextEdit()
        self.contact_info_input.setPlaceholderText("Commentaires généraux...")
        self.contact_info_input.setMinimumHeight(80)
        
        form_layout.addRow("Nom (Raison Sociale):", self.name_input)
        form_layout.addRow("Code (3 lettres):", self.code_input)
        form_layout.addRow("Adresse:", self.address_input)
        form_layout.addRow("Téléphone:", self.phone_input)
        form_layout.addRow("Site web:", self.website_input)
        form_layout.addRow("Commentaires:", self.contact_info_input)

        main_layout.addLayout(form_layout)

        if self.is_edit_mode:
            details = self.controller.get_client_details(self.client_id)
            if details:
                self.name_input.setText(details.get('name', ''))
                self.code_input.setText(details.get('code', ''))
                self.address_input.setText(details.get('address', ''))
                self.phone_input.setText(details.get('phone', ''))
                self.website_input.setText(details.get('website', ''))
                self.contact_info_input.setText(details.get('contact_info', ''))

        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.accepted.connect(self.validate_and_accept)
        self.buttons.rejected.connect(self.reject)
        form_layout.addRow(self.buttons)

    def validate_and_accept(self):
        """Valide les champs avant de fermer le dialogue."""
        if not self.name_input.text().strip():
            QMessageBox.warning(self, "Champ Requis", "Le nom du client (Raison Sociale) est requis.")
            self.name_input.setFocus()
            return

        if not self.code_input.hasAcceptableInput():
            QMessageBox.warning(self, "Format Invalide", "Le champ 'Code' doit contenir exactement 3 lettres.")
            self.code_input.setFocus()
            return
        
        super().accept()

    def get_data(self):
        """Retourne les données du formulaire sous forme de dictionnaire."""
        return {
            "name": self.name_input.text(),
            "code": self.code_input.text(),
            "address": self.address_input.toPlainText(),
            "phone": self.phone_input.text(),
            "website": self.website_input.text(),
            "contact_info": self.contact_info_input.toPlainText(),
        }

class ClientManagementView(QWidget):
    def __init__(self):
        super().__init__()
        self.controller = ProjectController()
        
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(15)

        # --- Barre de Titre ---
        title_bar = QHBoxLayout()
        icon_label = QLabel()
        icon_label.setPixmap(qta.icon('fa5s.users', color='white').pixmap(32, 32))
        title = QLabel("Gestion des Clients")
        font = title.font()
        font.setPointSize(18)
        font.setBold(True)
        title.setFont(font)

        title_bar.addWidget(icon_label)
        title_bar.addSpacing(10)
        title_bar.addWidget(title)
        title_bar.addStretch()

        # --- Search Bar ---
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Rechercher par nom ou code...")
        self.search_input.setMaximumWidth(250)
        title_bar.addWidget(self.search_input)
        title_bar.addSpacing(10)
        
        self.add_button = QPushButton(qta.icon('fa5s.plus', color='white'), " Ajouter")
        self.edit_button = QPushButton(qta.icon('fa5s.edit', color='white'), " Modifier")
        self.delete_button = QPushButton(qta.icon('fa5s.trash-alt', color='white'), " Supprimer")
        self.refresh_button = QPushButton(qta.icon('fa5s.sync-alt', color='white'), " Rafraîchir")

        title_bar.addWidget(self.add_button)
        title_bar.addWidget(self.edit_button)
        title_bar.addWidget(self.delete_button)
        title_bar.addSpacing(20)
        title_bar.addWidget(self.refresh_button)

        self.main_layout.addLayout(title_bar)

        # --- Tableau des Clients ---
        self.client_table = QTableWidget()
        self.client_table.setColumnCount(4)
        self.client_table.setHorizontalHeaderLabels(["ID", "Nom", "Code", "Commentaires"])
        header = self.client_table.horizontalHeader()
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        self.client_table.setColumnWidth(1, 250) # Largeur initiale pour le nom
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.client_table.setColumnWidth(2, 80)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)  # Commentaires
        self.client_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.client_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.client_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.client_table.hideColumn(0)
        self.client_table.setAlternatingRowColors(True)
        self.client_table.verticalHeader().setVisible(False)
        self.client_table.setSortingEnabled(True)
        
        self.main_layout.addWidget(self.client_table)

        # --- Connexions ---
        self.add_button.clicked.connect(self.add_client)
        self.edit_button.clicked.connect(self.edit_client)
        self.delete_button.clicked.connect(self.delete_client)
        self.refresh_button.clicked.connect(self.refresh_client_table)
        self.search_input.textChanged.connect(self.refresh_client_table)
        self.client_table.doubleClicked.connect(self.edit_client)

        self.refresh_client_table()

    def refresh_client_table(self):
        # Disable sorting to improve performance during population
        self.client_table.setSortingEnabled(False)
        try:
            all_clients = self.controller.get_all_clients() 
            search_text = self.search_input.text().lower()

            if search_text:
                clients_to_display = []
                for client in all_clients:
                    # Ensure code exists and is a string before checking
                    code = client.get("code") or ""
                    if search_text in client["name"].lower() or search_text in code.lower():
                        clients_to_display.append(client)
            else:
                clients_to_display = all_clients

            self.client_table.setRowCount(len(clients_to_display))

            for row, client in enumerate(clients_to_display):
                self.client_table.setItem(row, 0, QTableWidgetItem(str(client["id"])))
                self.client_table.setItem(row, 1, QTableWidgetItem(client["name"]))

                code_item = QTableWidgetItem(client.get("code", ""))
                code_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.client_table.setItem(row, 2, code_item)

                self.client_table.setItem(row, 3, QTableWidgetItem(client.get("contact_info", "")))

        except Exception as e:
            QMessageBox.critical(self, "Erreur de chargement", f"Impossible de charger les clients: {e}")
        finally:
            # Re-enable sorting after the table is populated
            self.client_table.setSortingEnabled(True)

    def get_selected_client_id(self):
        selected_rows = self.client_table.selectionModel().selectedRows()
        if not selected_rows:
            return None
        return int(self.client_table.item(selected_rows[0].row(), 0).text())

    def add_client(self):
        dialog = ClientEditDialog(self.controller, parent=self)
        if dialog.exec():
            data = dialog.get_data()
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