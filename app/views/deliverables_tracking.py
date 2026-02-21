from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView,
    QLabel, QPushButton, QVBoxLayout, QSplitter, QLineEdit,
    QDialog, QFormLayout, QDoubleSpinBox, QDateEdit, QDialogButtonBox, QRadioButton,
    QMessageBox, QAbstractItemView, QComboBox, QScrollArea, QFrame, QCheckBox
)
from PyQt6.QtGui import QFont, QColor, QBrush
from PyQt6.QtCore import Qt, QDate, QEvent
import qtawesome as qta

from app.controllers.deliverable_controller import DeliverableController
from app.controllers.company_controller import CompanyController
from app.views.financial_timeline import FinancialTimeline

class DeliverablesFilterDialog(QDialog):
    def __init__(self, parent, current_year, current_month_index, current_company_id, show_ongoing, company_list):
        super().__init__(parent)
        self.setWindowTitle("Filtres d'affichage")
        layout = QFormLayout(self)

        # Year selector
        self.year_selector = QComboBox()
        start_year = QDate.currentDate().year()
        for year in range(start_year - 2, start_year + 3):
            self.year_selector.addItem(str(year))
        self.year_selector.setCurrentText(str(current_year))
        layout.addRow("Année:", self.year_selector)

        # Month selector
        self.month_selector = QComboBox()
        self.month_selector.addItem("Tous les mois")
        months = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
        self.month_selector.addItems(months)
        self.month_selector.setCurrentIndex(current_month_index)
        layout.addRow("Mois:", self.month_selector)

        # Company selector
        self.company_selector = QComboBox()
        self.company_selector.addItem("Toutes les sociétés", userData=None)
        for company in company_list:
            self.company_selector.addItem(company['name'], userData=company['id'])
        company_index = self.company_selector.findData(current_company_id)
        if company_index != -1:
            self.company_selector.setCurrentIndex(company_index)
        layout.addRow("Société:", self.company_selector)

        # Ongoing projects filter
        self.ongoing_only_checkbox = QCheckBox("Afficher uniquement les projets 'En cours'")
        self.ongoing_only_checkbox.setChecked(show_ongoing)
        layout.addRow(self.ongoing_only_checkbox)

        # Buttons
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addRow(self.buttons)

    def get_filters(self):
        return {
            'year': int(self.year_selector.currentText()),
            'month_index': self.month_selector.currentIndex(),
            'company_id': self.company_selector.currentData(),
            'ongoing_only': self.ongoing_only_checkbox.isChecked()
        }

class AddDeliverableDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Ajouter un Livrable")
        layout = QFormLayout(self)
        self.nom_input = QLineEdit()
        self.montant_input = QDoubleSpinBox()
        self.montant_input.setRange(0.01, 9999999.0)
        self.montant_input.setSuffix(" €")
        self.date_input = QDateEdit(calendarPopup=True)
        self.date_input.setDate(QDate.currentDate())
        layout.addRow("Nom:", self.nom_input)
        layout.addRow("Montant:", self.montant_input)
        layout.addRow("Date prévue:", self.date_input)
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addRow(self.buttons)

    def get_data(self):
        if not self.nom_input.text() or self.montant_input.value() <= 0:
            return None
        return {
            'nom': self.nom_input.text(),
            'montant': self.montant_input.value(),
            'date_prevue': self.date_input.date().toPyDate()
        }

class DeliverablesTrackingView(QWidget):
    def __init__(self):
        super().__init__()
        self.controller = DeliverableController()
        self.company_controller = CompanyController()
        self.current_project_id = None
        self.last_hovered_row = -1
        self.hover_color = QColor("#50556b")

        # Filter state variables
        self.filter_year = QDate.currentDate().year()
        self.filter_month_index = 0  # "Tous les mois"
        self.filter_company_id = None
        self.filter_ongoing_only = True

        main_layout = QHBoxLayout(self)
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(self.splitter)

        left_panel = self._create_left_panel()
        right_panel = self._create_right_panel()
        left_panel.setMinimumWidth(0)
        right_panel.setMinimumWidth(0)

        self.splitter.addWidget(left_panel)
        self.splitter.addWidget(right_panel)
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.setSizes([400, 800])

        self._connect_signals()
        self.refresh_data()

    def _create_left_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 5, 5, 5)

        top_bar_layout = QHBoxLayout()
        self.add_deliverable_button = QPushButton(qta.icon('fa5s.plus'), " Ajouter un Livrable")
        self.add_deliverable_button.setEnabled(False)
        top_bar_layout.addWidget(self.add_deliverable_button)

        # Séparateur vertical
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.VLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        top_bar_layout.addWidget(separator)
        top_bar_layout.addSpacing(10)
        
        self.filter_button = QPushButton(qta.icon('fa5s.filter'), " Filtres")
        top_bar_layout.addWidget(self.filter_button)
        top_bar_layout.addStretch()
        layout.addLayout(top_bar_layout)

        self.project_filter_input = QLineEdit()
        self.project_filter_input.setPlaceholderText("Filtrer les projets...")
        layout.addWidget(self.project_filter_input)

        self.projects_table = QTableWidget()
        self.projects_table.setColumnCount(3)
        self.projects_table.setHorizontalHeaderLabels(["Code", "Nom du Projet", "Chef de Projet"])
        header = self.projects_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.projects_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.projects_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.projects_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.projects_table.setSortingEnabled(True)
        self.projects_table.setMouseTracking(True)
        self.projects_table.verticalHeader().setVisible(False)

        # Configuration pour la synchronisation du scroll au pixel près
        self.projects_table.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.projects_table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        self.projects_table.verticalHeader().setDefaultSectionSize(40) # Doit correspondre à timeline.row_height

        layout.addWidget(self.projects_table)

        return panel

    def _create_right_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(5, 5, 0, 5)

        top_layout = QHBoxLayout()
        
        # Pousse les totaux vers la droite
        top_layout.addStretch()

        # Intégration des totaux dans la barre supérieure
        self.total_billed_label = QLabel("0,00 €")
        self.total_billed_label.setStyleSheet("font-size: 40px; font-weight: bold; color: #2ecc71; margin: 10px;")
        top_layout.addWidget(self.total_billed_label)

        top_layout.addSpacing(20)

        self.total_planned_label = QLabel("0,00 €")
        self.total_planned_label.setStyleSheet("font-size: 40px; font-weight: bold; color: #BDC3C7; margin: 10px;")
        top_layout.addWidget(self.total_planned_label)

        layout.addLayout(top_layout)

        self.timeline_scroll_area = QScrollArea()
        self.timeline = FinancialTimeline(self.controller)
        self.timeline_scroll_area.setWidget(self.timeline)
        self.timeline_scroll_area.setWidgetResizable(True)
        self.timeline_scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        layout.addWidget(self.timeline_scroll_area)

        return panel

    def _connect_signals(self):
        self.add_deliverable_button.clicked.connect(self._open_add_deliverable_dialog)
        self.project_filter_input.textChanged.connect(self.refresh_data)
        self.projects_table.itemSelectionChanged.connect(self._on_project_selected)
        self.timeline.data_changed.connect(self.refresh_data)
        self.timeline.row_hovered.connect(self._update_hover_row)
        self.projects_table.cellEntered.connect(self._update_hover_row)
        self.filter_button.clicked.connect(self._open_filter_dialog)

        # Synchronize scroll bars
        self.projects_table.verticalScrollBar().valueChanged.connect(self.timeline_scroll_area.verticalScrollBar().setValue)
        self.timeline_scroll_area.verticalScrollBar().valueChanged.connect(self.projects_table.verticalScrollBar().setValue)

        self.projects_table.viewport().installEventFilter(self)
        self.timeline.installEventFilter(self)

    def _open_filter_dialog(self):
        companies = self.company_controller.get_all_companies_for_filter()
        dialog = DeliverablesFilterDialog(
            parent=self,
            current_year=self.filter_year,
            current_month_index=self.filter_month_index,
            current_company_id=self.filter_company_id,
            show_ongoing=self.filter_ongoing_only,
            company_list=companies
        )
        if dialog.exec():
            filters = dialog.get_filters()
            self.filter_year = filters['year']
            self.filter_month_index = filters['month_index']
            self.filter_company_id = filters['company_id']
            self.filter_ongoing_only = filters['ongoing_only']
            self.refresh_data()

    def refresh_data(self):
        year = self.filter_year
        month = self.filter_month_index if self.filter_month_index > 0 else None
        company_id = self.filter_company_id

        # Choisir la source des projets en fonction du filtre radio
        if self.filter_ongoing_only:
            all_projects = self.controller.get_ongoing_projects(year=year, month=month, company_id=company_id)
        else:
            all_projects = self.controller.get_all_projects_summary(year=year, month=month, company_id=company_id)

        filter_text = self.project_filter_input.text().lower()

        if filter_text:
            visible_projects = [
                p for p in all_projects 
                if filter_text in p['code'].lower()
                or filter_text in p['name'].lower() 
                or filter_text in p['project_manager'].lower()
            ]
        else:
            visible_projects = all_projects

        self.last_hovered_row = -1 # Reset hover state
        self._populate_projects_table(visible_projects)

        deliverables_data = self.controller.get_yearly_deliverables_by_project(year, company_id=company_id)
        monthly_totals = self.controller.get_monthly_totals_for_year(year, company_id=company_id)

        # Update total labels
        planned_totals = monthly_totals.get('planned', {})
        billed_totals = monthly_totals.get('billed', {})
        total_planned_year = sum(planned_totals.values())
        total_billed_year = sum(billed_totals.values())
        self.total_planned_label.setText(f"{total_planned_year:,.2f} €".replace(",", " "))
        self.total_billed_label.setText(f"{total_billed_year:,.2f} €".replace(",", " "))

        self.timeline.set_data(visible_projects, deliverables_data, year, monthly_totals)

    def _populate_projects_table(self, projects):
        self.projects_table.setSortingEnabled(False)
        self.projects_table.setRowCount(0)
        self.projects_table.setRowCount(len(projects))

        # --- PROJECT ROWS ---
        for i, p in enumerate(projects):
            row_index = i
            code_item = QTableWidgetItem(p['code'])
            code_item.setData(Qt.ItemDataRole.UserRole, p['id'])

            name_item = QTableWidgetItem(p['name'])
            pm_item = QTableWidgetItem(p['project_manager'])

            self.projects_table.setItem(row_index, 0, code_item)
            self.projects_table.setItem(row_index, 1, name_item)
            self.projects_table.setItem(row_index, 2, pm_item)
        
        self.projects_table.setSortingEnabled(True)
        self.projects_table.horizontalHeader().setFixedHeight(self.timeline.header_height)

    def _on_project_selected(self):
        selected_items = self.projects_table.selectedItems()
        if not selected_items:
            self.current_project_id = None
            self.add_deliverable_button.setEnabled(False)
            return

        selected_row = self.projects_table.row(selected_items[0])
        
        project_id_item = self.projects_table.item(selected_row, 0)
        self.current_project_id = project_id_item.data(Qt.ItemDataRole.UserRole)
        self.add_deliverable_button.setEnabled(True)

    def _open_add_deliverable_dialog(self):
        if not self.current_project_id:
            QMessageBox.warning(self, "Aucun Projet", "Veuillez sélectionner un projet pour y ajouter un livrable.")
            return

        dialog = AddDeliverableDialog(self)
        if dialog.exec():
            data = dialog.get_data()
            if data:
                success, message = self.controller.add_deliverable(self.current_project_id, data)
                if success:
                    self.refresh_data()
                else:
                    QMessageBox.critical(self, "Erreur", message)
            else:
                QMessageBox.warning(self, "Données Invalides", "Le nom et un montant positif sont requis.")

    def _update_hover_row(self, row, column=-1):
        if self.last_hovered_row == row:
            return

        # Clear old highlight if it exists
        if self.last_hovered_row != -1:
            self._clear_row_highlight(self.last_hovered_row)

        # Apply new highlight
        if row != -1:
            self._apply_row_highlight(row)

        # Sync with timeline
        self.timeline.set_hovered_row(row)

        self.last_hovered_row = row

    def _apply_row_highlight(self, row):
        if row >= self.projects_table.rowCount(): return
        for col in range(self.projects_table.columnCount()):
            item = self.projects_table.item(row, col)
            if item:
                # Store original background if not already stored
                if item.data(Qt.ItemDataRole.UserRole + 1) is None:
                    item.setData(Qt.ItemDataRole.UserRole + 1, item.data(Qt.ItemDataRole.BackgroundRole))
                item.setData(Qt.ItemDataRole.BackgroundRole, QBrush(self.hover_color))

    def _clear_row_highlight(self, row):
        if row >= self.projects_table.rowCount(): return
        for col in range(self.projects_table.columnCount()):
            item = self.projects_table.item(row, col)
            if item:
                original_bg = item.data(Qt.ItemDataRole.UserRole + 1)
                if original_bg is not None:
                    item.setData(Qt.ItemDataRole.BackgroundRole, original_bg)
                    item.setData(Qt.ItemDataRole.UserRole + 1, None)

    def eventFilter(self, source, event):
        if (source is self.projects_table.viewport() or source is self.timeline) and event.type() == QEvent.Type.Leave:
            self._update_hover_row(-1)
        return super().eventFilter(source, event)