from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView,
    QLabel, QPushButton, QVBoxLayout, QSplitter, QLineEdit,
    QDialog, QFormLayout, QDoubleSpinBox, QDateEdit, QDialogButtonBox,
    QMessageBox, QAbstractItemView, QComboBox, QScrollArea, QFrame, QCheckBox
)
from PyQt6.QtGui import QFont, QColor, QBrush
from PyQt6.QtCore import Qt, QDate, QEvent
import qtawesome as qta

from app.controllers.deliverable_controller import DeliverableController
from app.controllers.company_controller import CompanyController
from app.views.financial_timeline import FinancialTimeline

class SortableTableWidgetItem(QTableWidgetItem):
    """
    A QTableWidgetItem that sorts based on data stored in a custom role,
    allowing the display text to be empty to prevent rendering conflicts
    when a cell widget is used.
    """
    def __lt__(self, other):
        # Sort using data from UserRole + 100.
        my_data = self.data(Qt.ItemDataRole.UserRole + 100)
        other_data = other.data(Qt.ItemDataRole.UserRole + 100)
        
        # Fallback to empty string if data is None, and sort case-insensitively
        my_data_str = str(my_data).lower() if my_data is not None else ""
        other_data_str = str(other_data).lower() if other_data is not None else ""
        
        return my_data_str < other_data_str

class DeliverablesFilterDialog(QDialog):
    def __init__(self, parent, current_year, current_month_index, current_company_id, show_ongoing, company_list):
        super().__init__(parent)
        self.setWindowTitle("Filtres d'Affichage")
        self.setWindowIcon(qta.icon('fa5s.filter', color='white'))
        self.setMinimumWidth(400)
        
        layout = QFormLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

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
        layout.addRow("", self.ongoing_only_checkbox)

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
        self.setWindowIcon(qta.icon('fa5s.plus', color='white'))
        self.setMinimumWidth(400)
        
        layout = QFormLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.nom_input = QLineEdit()
        self.montant_input = QDoubleSpinBox()
        self.montant_input.setRange(0.01, 9999999.0)
        self.montant_input.setSuffix(" €")
        self.montant_input.setGroupSeparatorShown(True)
        self.date_input = QDateEdit(calendarPopup=True)
        self.date_input.setDate(QDate.currentDate())
        self.date_input.setDisplayFormat("dd/MM/yyyy")

        layout.addRow("Nom du livrable:", self.nom_input)
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
        self.hover_color = QColor(80, 85, 107, 150) # #50556b with alpha, same as timeline

        # Cache de données pour le tri et le redessin
        self.visible_projects = []
        self.deliverables_data = {}
        self.monthly_totals = {}

        # Filter state variables
        self.filter_year = QDate.currentDate().year()
        self.filter_month_index = 0  # "Tous les mois"
        self.filter_company_id = None
        self.filter_ongoing_only = True

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # The project filter is moved here, outside the splitter, to ensure alignment
        # between the table and the timeline.
        self.project_filter_input = QLineEdit()
        self.project_filter_input.setPlaceholderText("Filtrer les projets par nom, code...")

        self._setup_title_bar()
        self._setup_totals_bar()

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(self.splitter)

        left_panel = self._create_left_panel()
        right_panel = self._create_right_panel()

        self.splitter.addWidget(left_panel)
        self.splitter.addWidget(right_panel)
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.setSizes([450, 800])

        # 1. Standardize Header Heights after both widgets are created.
        self.projects_table.horizontalHeader().setFixedHeight(self.timeline.header_height)

        self._connect_signals()
        self.refresh_data()

    def _setup_title_bar(self):
        title_bar = QHBoxLayout()

        icon_label = QLabel()
        icon_label.setPixmap(qta.icon('fa5s.file-invoice-dollar', color='white').pixmap(32, 32))
        title = QLabel("Suivi des Livrables")
        font = title.font()
        font.setPointSize(18)
        font.setBold(True)
        title.setFont(font)

        title_bar.addWidget(icon_label)
        title_bar.addSpacing(10)
        title_bar.addWidget(title)
        title_bar.addStretch()

        self.add_deliverable_button = QPushButton(qta.icon('fa5s.plus', color='white'), " Ajouter Livrable")
        self.add_deliverable_button.setEnabled(False)
        self.filter_button = QPushButton(qta.icon('fa5s.filter', color='white'), " Filtres")
        self.refresh_button = QPushButton(qta.icon('fa5s.sync-alt', color='white'), " Rafraîchir")

        title_bar.addWidget(self.add_deliverable_button)
        title_bar.addWidget(self.filter_button)
        title_bar.addWidget(self.refresh_button)
        self.layout().addLayout(title_bar)
    
    def _setup_totals_bar(self):
        totals_frame = QFrame()
        totals_frame.setObjectName("totalsFrame")
        totals_frame.setStyleSheet("#totalsFrame { border: 1px solid #4a5060; border-radius: 5px; }")
        totals_frame.setMaximumHeight(45)

        totals_layout = QHBoxLayout(totals_frame)
        totals_layout.setContentsMargins(15, 2, 15, 2)
        totals_layout.setSpacing(10)

        # --- Billed Total ---
        billed_layout = QHBoxLayout()
        billed_layout.setSpacing(10)
        billed_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        billed_title = QLabel("TOTAL FACTURÉ :")
        billed_title.setStyleSheet("font-size: 12px; color: #999; margin: 0px; padding: 0px;")
        
        self.total_billed_label = QLabel("0,00 €")
        self.total_billed_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #50FA7B; margin: 0px; padding: 0px;")
        
        billed_layout.addWidget(billed_title)
        billed_layout.addWidget(self.total_billed_label)

        # --- Planned Total ---
        planned_layout = QHBoxLayout()
        planned_layout.setSpacing(10)
        planned_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        planned_title = QLabel("TOTAL PRÉVU :")
        planned_title.setStyleSheet("font-size: 12px; color: #999; margin: 0px; padding: 0px;")

        self.total_planned_label = QLabel("0,00 €")
        self.total_planned_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #E0E0E0; margin: 0px; padding: 0px;")

        planned_layout.addWidget(planned_title)
        planned_layout.addWidget(self.total_planned_label)

        # --- Main Totals Layout ---
        totals_layout.addStretch()
        totals_layout.addLayout(billed_layout)
        totals_layout.addSpacing(50)
        totals_layout.addLayout(planned_layout)
        totals_layout.addStretch()

        self.layout().addWidget(totals_frame)

    def _create_left_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 5, 0) # Keep side margin
        layout.setSpacing(0) # No vertical spacing needed as there's only one widget

        self.projects_table = QTableWidget()
        self.projects_table.setColumnCount(4)
        # 5. Visual Polish: The header line will align if heights are identical.
        self.projects_table.setHorizontalHeaderLabels(["Code", "Projet", "Resp", "Total"])
        header = self.projects_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.projects_table.setColumnWidth(0, 90)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.projects_table.setColumnWidth(3, 90)
        self.projects_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.projects_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.projects_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.projects_table.setSortingEnabled(True)
        self.projects_table.setMouseTracking(True)
        self.projects_table.verticalHeader().setVisible(False)
        self.projects_table.setAlternatingRowColors(True)

        self.projects_table.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        # 2. Sync Row Heights: Ensure row heights are fixed and identical.
        self.projects_table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        self.projects_table.verticalHeader().setDefaultSectionSize(40)

        # 4. Scrollbar Synchronization Check: Match frame shape to avoid border offsets.
        self.projects_table.setFrameShape(QFrame.Shape.NoFrame)

        layout.addWidget(self.projects_table)
        return panel

    def _create_right_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(5, 0, 0, 0)

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
        self.projects_table.horizontalHeader().sortIndicatorChanged.connect(self._on_project_sort_changed)

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

        self.visible_projects = visible_projects
        self.last_hovered_row = -1 # Reset hover state
        self._populate_projects_table(self.visible_projects)

        self.deliverables_data = self.controller.get_yearly_deliverables_by_project(year, company_id=company_id)
        self.monthly_totals = self.controller.get_monthly_totals_for_year(year, company_id=company_id)

        # Update total labels
        planned_totals = self.monthly_totals.get('planned', {})
        billed_totals = self.monthly_totals.get('billed', {})
        total_planned_year = sum(planned_totals.values())
        total_billed_year = sum(billed_totals.values())
        self.total_planned_label.setText(f"{total_planned_year:,.2f} €".replace(",", " "))
        self.total_billed_label.setText(f"{total_billed_year:,.2f} €".replace(",", " "))

        self.timeline.set_data(self.visible_projects, self.deliverables_data, year, self.monthly_totals)

        # Par défaut, centrer la vue sur le début de l'année sélectionnée.
        # La timeline affiche 24 mois, commençant en Juillet de l'année N-1.
        # Janvier de l'année N est donc le 7ème mois, à l'index 6.
        scroll_position = 6 * self.timeline.month_width
        self.timeline_scroll_area.horizontalScrollBar().setValue(scroll_position)

    def _on_project_sort_changed(self):
        """
        Redessine la timeline pour correspondre au nouvel ordre de tri du tableau des projets.
        """
        if not self.visible_projects:
            return

        # Créer une map des projets actuellement affichés pour une recherche rapide.
        projects_map = {p['id']: p for p in self.visible_projects}
        
        # Obtenir le nouvel ordre des ID de projet directement à partir de la disposition visuelle du tableau.
        sorted_projects = []
        for row in range(self.projects_table.rowCount()):
            item = self.projects_table.item(row, 0)
            if item:
                project_id = item.data(Qt.ItemDataRole.UserRole)
                if project_id in projects_map:
                    sorted_projects.append(projects_map[project_id])

        # Mettre à jour la timeline avec la liste de projets réorganisée.
        # Les autres données (livrables, totaux, année) restent les mêmes que lors du dernier rafraîchissement.
        if sorted_projects:
            self.timeline.set_data(
                sorted_projects, 
                self.deliverables_data, 
                self.filter_year, 
                self.monthly_totals
            )

    def _populate_projects_table(self, projects):
        self.projects_table.setSortingEnabled(False)
        self.projects_table.setRowCount(0)
        self.projects_table.setRowCount(len(projects))

        # --- PROJECT ROWS ---
        for row_index, p in enumerate(projects):
            # 1. Utiliser SortableTableWidgetItem avec un texte vide pour l'affichage
            # et les données de tri dans un rôle personnalisé.
            code_item = SortableTableWidgetItem()
            code_item.setData(Qt.ItemDataRole.UserRole, p['id'])
            code_item.setData(Qt.ItemDataRole.UserRole + 100, p['code'])

            name_item = SortableTableWidgetItem()
            name_item.setData(Qt.ItemDataRole.UserRole + 100, p['name'])

            pm_item = SortableTableWidgetItem()
            pm_item.setData(Qt.ItemDataRole.UserRole + 100, p['project_manager'])
            
            self.projects_table.setItem(row_index, 0, code_item)
            self.projects_table.setItem(row_index, 1, name_item)
            self.projects_table.setItem(row_index, 2, pm_item)

            # 2. Définir des widgets QLabel pour l'affichage et un style fiable
            code_label = QLabel(p['code'])
            name_label = QLabel(p['name'])
            pm_label = QLabel(p['project_manager'])

            # Définir le tooltip
            tooltip_text = f"Projet: {p['name']}\nChef de projet: {p.get('project_manager_fullname', p['project_manager'])}"

            # Définir l'alignement
            code_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            name_label.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
            pm_label.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)

            # Stocker un style de base sur chaque widget. Le fond transparent
            # permet à la couleur de ligne alternée de l'item de transparaître.
            for label, padding in [(code_label, 0), (name_label, 5), (pm_label, 5)]:
                style = f"background-color: transparent; padding-left: {padding}px;"
                label.setStyleSheet(style)
                label.setProperty("base_style", style)
                label.setToolTip(tooltip_text)

            self.projects_table.setCellWidget(row_index, 0, code_label)
            self.projects_table.setCellWidget(row_index, 1, name_label)
            self.projects_table.setCellWidget(row_index, 2, pm_label)

            # 3. Add total amount column
            total_amount_item = SortableTableWidgetItem()
            total_amount_item.setData(Qt.ItemDataRole.UserRole + 100, p.get('total_amount', 0.0))
            self.projects_table.setItem(row_index, 3, total_amount_item)

            total_amount_label = QLabel(f"{p.get('total_amount', 0.0):,.0f} €".replace(",", " "))
            total_amount_label.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight)
            style = "background-color: transparent; padding-right: 5px;"
            total_amount_label.setStyleSheet(style)
            total_amount_label.setProperty("base_style", style)
            total_amount_label.setToolTip(tooltip_text)
            self.projects_table.setCellWidget(row_index, 3, total_amount_label)
        
        self.projects_table.setSortingEnabled(True)
        # The header height is now set once in __init__

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
            widget = self.projects_table.cellWidget(row, col)
            if widget:
                base_style = widget.property("base_style") or ""
                widget.setStyleSheet(base_style + f"background-color: {self.hover_color.name()};")

    def _clear_row_highlight(self, row):
        if row >= self.projects_table.rowCount(): return
        for col in range(self.projects_table.columnCount()):
            widget = self.projects_table.cellWidget(row, col)
            if widget:
                base_style = widget.property("base_style") or ""
                widget.setStyleSheet(base_style)

    def eventFilter(self, source, event):
        if (source is self.projects_table.viewport() or source is self.timeline) and event.type() == QEvent.Type.Leave:
            self._update_hover_row(-1)
        return super().eventFilter(source, event)