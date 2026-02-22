from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QPushButton,
    QHBoxLayout, QHeaderView, QMessageBox, QInputDialog, QAbstractItemView,
    QDialog, QFormLayout, QLineEdit, QDialogButtonBox, QLabel
)
from PyQt6.QtCore import Qt
import qtawesome as qta
from app.controllers.company_controller import CompanyController

class NumericTableWidgetItem(QTableWidgetItem):
    """Widget-item de tableau personnalisé pour le tri numérique."""
    def __lt__(self, other):
        try:
            return float(self.data(Qt.ItemDataRole.EditRole)) < float(other.data(Qt.ItemDataRole.EditRole))
        except (ValueError, TypeError):
            return super().__lt__(other)

class CompanyAddDialog(QDialog):
    """Dialogue pour ajouter une nouvelle société."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Ajouter une Société")
        self.setWindowIcon(qta.icon('fa5s.plus', color='white'))
        self.setMinimumWidth(350)
        
        layout = QFormLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Nom de la nouvelle société")
        layout.addRow("Nom:", self.name_input)

        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addRow(self.buttons)

    def get_name(self):
        return self.name_input.text()

class CompanySettingsView(QWidget):
    def __init__(self):
        super().__init__()
        self.controller = CompanyController()
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.layout.setSpacing(15)

        # --- Barre de Titre ---
        title_bar = QHBoxLayout()
        icon_label = QLabel()
        icon_label.setPixmap(qta.icon('fa5s.building', color='white').pixmap(32, 32))
        title = QLabel("Paramètres des Sociétés")
        font = title.font()
        font.setPointSize(18)
        font.setBold(True)
        title.setFont(font)

        title_bar.addWidget(icon_label)
        title_bar.addSpacing(10)
        title_bar.addWidget(title)
        title_bar.addStretch()

        self.add_button = QPushButton(qta.icon('fa5s.plus', color='white'), " Ajouter")
        self.delete_button = QPushButton(qta.icon('fa5s.trash-alt', color='white'), " Supprimer")
        self.refresh_button = QPushButton(qta.icon('fa5s.sync-alt', color='white'), " Rafraîchir")
        self.save_button = QPushButton(qta.icon('fa5s.save', color='white'), " Enregistrer")
        
        title_bar.addWidget(self.add_button)
        title_bar.addWidget(self.delete_button)
        title_bar.addSpacing(20)
        title_bar.addWidget(self.refresh_button)
        title_bar.addWidget(self.save_button)
        self.layout.addLayout(title_bar)
        
        # --- Table ---
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["ID", "Nom de la Société", "Obj. Point Mort (€)", "Obj. 1 (€)", "Obj. 2 (€)"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.hideColumn(0)
        self.table.setSortingEnabled(True)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.layout.addWidget(self.table)
        
        # --- Connexions ---
        self.add_button.clicked.connect(self.add_company)
        self.delete_button.clicked.connect(self.delete_company)
        self.save_button.clicked.connect(self.save_changes)
        self.refresh_button.clicked.connect(self.refresh_table)
        
        self.refresh_table()

    def refresh_table(self):
        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)
        companies = self.controller.get_all_companies()
        
        self.table.setRowCount(len(companies))
        for row, company in enumerate(companies):
            # ID
            id_item = QTableWidgetItem(str(company.id))
            id_item.setFlags(id_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 0, id_item)
            
            # Name
            name_item = QTableWidgetItem(company.name)
            self.table.setItem(row, 1, name_item) # Allow editing name
            
            # Objectives
            self._set_numeric_item(row, 2, company.objective_point_mort)
            self._set_numeric_item(row, 3, company.objective_1)
            self._set_numeric_item(row, 4, company.objective_2)
            
        self.table.setSortingEnabled(True)

    def _set_numeric_item(self, row, col, value):
        # Format with space as thousand separator and comma for decimal
        text_value = f"{value:,.2f}".replace(",", " ").replace(".", ",")
        item = NumericTableWidgetItem(text_value)
        item.setData(Qt.ItemDataRole.EditRole, value)
        item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.table.setItem(row, col, item)

    def add_company(self):
        dialog = CompanyAddDialog(self)
        if dialog.exec():
            name = dialog.get_name()
            if name:
                success, message = self.controller.create_company(name)
                if success:
                    QMessageBox.information(self, "Succès", message)
                    self.refresh_table()
                else:
                    QMessageBox.critical(self, "Erreur", message)

    def delete_company(self):
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "Aucune sélection", "Veuillez sélectionner une société à supprimer.")
            return
        
        company_id = int(self.table.item(selected_rows[0].row(), 0).text())
        company_name = self.table.item(selected_rows[0].row(), 1).text()
        
        reply = QMessageBox.question(self, "Confirmation", f"Êtes-vous sûr de vouloir supprimer la société '{company_name}' ?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            success, message = self.controller.delete_company(company_id)
            if success:
                QMessageBox.information(self, "Succès", message)
                self.refresh_table()
            else:
                QMessageBox.critical(self, "Erreur", message)

    def save_changes(self):
        updates = []
        for row in range(self.table.rowCount()):
            try:
                # Correctly parse the locale-formatted string back to a float
                def parse_float(text):
                    return float(text.replace(" ", "").replace(",", "."))

                updates.append({
                    'id': int(self.table.item(row, 0).text()),
                    'name': self.table.item(row, 1).text(), # Also save name changes
                    'objective_point_mort': parse_float(self.table.item(row, 2).text()),
                    'objective_1': parse_float(self.table.item(row, 3).text()),
                    'objective_2': parse_float(self.table.item(row, 4).text())
                })
            except (ValueError, AttributeError) as e:
                QMessageBox.warning(self, "Données invalides", f"Veuillez vérifier les valeurs à la ligne {row + 1}.\nErreur: {e}")
                return
        
        if updates:
            success, message = self.controller.bulk_update_objectives(updates)
            if success:
                QMessageBox.information(self, "Succès", message)
                self.refresh_table()
            else:
                QMessageBox.critical(self, "Erreur", message)
