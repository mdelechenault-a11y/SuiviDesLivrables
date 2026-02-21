from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QPushButton,
    QHBoxLayout, QHeaderView, QMessageBox, QInputDialog, QAbstractItemView
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

class CompanySettingsView(QWidget):
    def __init__(self):
        super().__init__()
        self.controller = CompanyController()
        self.setWindowTitle("Paramètres des Sociétés")
        
        self.layout = QVBoxLayout(self)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["ID", "Nom de la Société", "Obj. Point Mort (€)", "Obj. 1 (€)", "Obj. 2 (€)"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.hideColumn(0)
        self.table.setSortingEnabled(True)
        self.layout.addWidget(self.table)
        
        # Buttons
        buttons_layout = QHBoxLayout()
        self.add_button = QPushButton(qta.icon('fa5s.plus'), " Ajouter une Société")
        self.delete_button = QPushButton(qta.icon('fa5s.trash-alt'), " Supprimer la Société")
        self.save_button = QPushButton(qta.icon('fa5s.save'), " Enregistrer les modifications")
        
        buttons_layout.addWidget(self.add_button)
        buttons_layout.addWidget(self.delete_button)
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.save_button)
        self.layout.addLayout(buttons_layout)
        
        # Connections
        self.add_button.clicked.connect(self.add_company)
        self.delete_button.clicked.connect(self.delete_company)
        self.save_button.clicked.connect(self.save_changes)
        
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
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 1, name_item)
            
            # Objectives
            self._set_numeric_item(row, 2, company.objective_point_mort)
            self._set_numeric_item(row, 3, company.objective_1)
            self._set_numeric_item(row, 4, company.objective_2)
            
        self.table.setSortingEnabled(True)

    def _set_numeric_item(self, row, col, value):
        item = NumericTableWidgetItem(f"{value:,.2f}".replace(",", " "))
        item.setData(Qt.ItemDataRole.EditRole, value)
        item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.table.setItem(row, col, item)

    def add_company(self):
        name, ok = QInputDialog.getText(self, "Ajouter une Société", "Nom de la nouvelle société:")
        if ok and name:
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
                updates.append({
                    'id': int(self.table.item(row, 0).text()),
                    'objective_point_mort': float(self.table.item(row, 2).text().replace(" ", "").replace(",", ".")),
                    'objective_1': float(self.table.item(row, 3).text().replace(" ", "").replace(",", ".")),
                    'objective_2': float(self.table.item(row, 4).text().replace(" ", "").replace(",", "."))
                })
            except (ValueError, AttributeError):
                QMessageBox.warning(self, "Données invalides", f"Veuillez vérifier les valeurs numériques à la ligne {row + 1}.")
                return
        
        if updates:
            success, message = self.controller.bulk_update_objectives(updates)
            if success:
                QMessageBox.information(self, "Succès", message)
                self.refresh_table()
            else:
                QMessageBox.critical(self, "Erreur", message)