import sys
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QPushButton, 
    QHBoxLayout, QHeaderView, QMessageBox, QDialog, QFormLayout, 
    QLineEdit, QComboBox, QDialogButtonBox, QLabel, QAbstractItemView
)
from PyQt6.QtCore import Qt
import qtawesome as qta
from app.controllers.user_controller import UserController

class UserEditDialog(QDialog):
    """Dialogue pour ajouter ou modifier un utilisateur."""
    def __init__(self, controller: UserController, user=None, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.user = user
        self.is_edit_mode = user is not None

        title = "Modifier l'Utilisateur" if self.is_edit_mode else "Ajouter un Utilisateur"
        icon = 'fa5s.user-edit' if self.is_edit_mode else 'fa5s.user-plus'
        self.setWindowTitle(title)
        self.setWindowIcon(qta.icon(icon, color='white'))
        self.setMinimumWidth(400)

        layout = QFormLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        
        self.username_input = QLineEdit(user.username if user else "")
        self.prenom_input = QLineEdit(user.prenom if user else "")
        self.nom_input = QLineEdit(user.nom if user else "")
        self.email_input = QLineEdit(user.email if user else "")
        
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Laisser vide pour ne pas changer" if self.is_edit_mode else "Mot de passe requis")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)

        self.profil_combo = QComboBox()
        self.company_combo = QComboBox()
        
        layout.addRow("Nom d'utilisateur:", self.username_input)
        layout.addRow("Prénom:", self.prenom_input)
        layout.addRow("Nom:", self.nom_input)
        layout.addRow("Email:", self.email_input)
        layout.addRow("Mot de passe:", self.password_input)
        layout.addRow("Rôle:", self.profil_combo)
        layout.addRow("Société:", self.company_combo)

        self.populate_profils()
        self.populate_companies()

        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addRow(self.buttons)

    def populate_profils(self):
        profils = self.controller.get_all_profils() 
        for p in profils:
            self.profil_combo.addItem(p.nom, userData=p.id)
        
        if self.is_edit_mode and self.user.profil:
            index = self.profil_combo.findText(self.user.profil.nom)
            if index != -1:
                self.profil_combo.setCurrentIndex(index)

    def populate_companies(self):
        """Remplit la liste déroulante des sociétés."""
        companies = self.controller.get_all_companies()
        self.company_combo.addItem("Aucune", userData=None)
        for c in companies:
            self.company_combo.addItem(c.name, userData=c.id)
        
        if self.is_edit_mode and self.user.company:
            index = self.company_combo.findData(self.user.company.id)
            if index != -1:
                self.company_combo.setCurrentIndex(index)

    def get_data(self):
        """Retourne les données du formulaire sous forme de dictionnaire."""
        return {
            "username": self.username_input.text(),
            "prenom": self.prenom_input.text(),
            "nom": self.nom_input.text(),
            "email": self.email_input.text(),
            "password": self.password_input.text(),
            "profil_nom": self.profil_combo.currentText(),
            "company_id": self.company_combo.currentData()
        }

class UserManagementWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.controller = UserController()
        
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(15)

        # --- Barre de Titre ---
        title_bar = QHBoxLayout()
        icon_label = QLabel()
        icon_label.setPixmap(qta.icon('fa5s.user-cog', color='white').pixmap(32, 32))
        title = QLabel("Gestion des Utilisateurs")
        font = title.font()
        font.setPointSize(18)
        font.setBold(True)
        title.setFont(font)

        title_bar.addWidget(icon_label)
        title_bar.addSpacing(10)
        title_bar.addWidget(title)
        title_bar.addStretch()
        
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

        # --- Tableau des Utilisateurs ---
        self.user_table = QTableWidget()
        self.user_table.setColumnCount(5)
        self.user_table.setHorizontalHeaderLabels(["ID", "Nom", "Email", "Rôle", "Société"])
        self.user_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.user_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.user_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.user_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.user_table.hideColumn(0)
        self.user_table.setAlternatingRowColors(True)
        self.user_table.verticalHeader().setVisible(False)
        
        self.main_layout.addWidget(self.user_table)

        # --- Connexions ---
        self.add_button.clicked.connect(self.add_user)
        self.edit_button.clicked.connect(self.edit_user)
        self.delete_button.clicked.connect(self.delete_user)
        self.refresh_button.clicked.connect(self.refresh_user_table)

        self.refresh_user_table()

    def refresh_user_table(self):
        try:
            users = self.controller.get_all_users_full() 
            self.user_table.setRowCount(len(users))

            for row, user in enumerate(users):
                self.user_table.setItem(row, 0, QTableWidgetItem(str(user.id)))
                self.user_table.setItem(row, 1, QTableWidgetItem(f"{user.prenom} {user.nom}"))
                self.user_table.setItem(row, 2, QTableWidgetItem(user.email))
                self.user_table.setItem(row, 3, QTableWidgetItem(user.profil.nom if user.profil else "N/A"))
                self.user_table.setItem(row, 4, QTableWidgetItem(user.company.name if user.company else "N/A"))
        except Exception as e:
            QMessageBox.critical(self, "Erreur de chargement", f"Impossible de charger les utilisateurs: {e}")

    def get_selected_user_id(self):
        selected_rows = self.user_table.selectionModel().selectedRows()
        if not selected_rows:
            return None
        return int(self.user_table.item(selected_rows[0].row(), 0).text())

    def add_user(self):
        dialog = UserEditDialog(self.controller, parent=self)
        if dialog.exec():
            data = dialog.get_data()
            if not all([data['username'], data['password'], data['prenom'], data['nom'], data['email']]):
                QMessageBox.warning(self, "Champs requis", "Tous les champs (y compris le mot de passe) sont requis pour un nouvel utilisateur.")
                return
            
            success, message = self.controller.add_user(
                username=data['username'], prenom=data['prenom'], nom=data['nom'],
                email=data['email'], password=data['password'], profil_nom=data['profil_nom'],
                company_id=data['company_id']
            )
            if success:
                QMessageBox.information(self, "Succès", message)
                self.refresh_user_table()
            else:
                QMessageBox.critical(self, "Erreur", message)

    def edit_user(self):
        user_id = self.get_selected_user_id()
        if user_id is None:
            QMessageBox.warning(self, "Aucune sélection", "Veuillez sélectionner un utilisateur à modifier.")
            return

        all_users = self.controller.get_all_users_full()
        user_to_edit = next((u for u in all_users if u.id == user_id), None)

        if not user_to_edit:
            QMessageBox.critical(self, "Erreur", "Utilisateur non trouvé.")
            return

        dialog = UserEditDialog(self.controller, user=user_to_edit, parent=self)
        if dialog.exec():
            data = dialog.get_data()
            success, message = self.controller.update_user(user_id, data)
            if success:
                QMessageBox.information(self, "Succès", message)
                self.refresh_user_table()
            else:
                QMessageBox.critical(self, "Erreur", message)

    def delete_user(self):
        user_id = self.get_selected_user_id()
        if user_id is None:
            QMessageBox.warning(self, "Aucune sélection", "Veuillez sélectionner un utilisateur à supprimer.")
            return
        
        reply = QMessageBox.question(self, "Confirmation de suppression",
                                     "Êtes-vous sûr de vouloir supprimer cet utilisateur ?\nCette action est irréversible.",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            success, message = self.controller.delete_user(user_id)
            if success:
                QMessageBox.information(self, "Succès", message)
                self.refresh_user_table()
            else:
                QMessageBox.critical(self, "Erreur de suppression", message)
