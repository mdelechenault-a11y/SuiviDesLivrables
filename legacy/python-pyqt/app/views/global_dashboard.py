import sys
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView, 
    QLabel, QCheckBox, QHBoxLayout, QFrame, QAbstractItemView, QSplitter, QMessageBox,
    QLineEdit, QSizePolicy, QApplication, QComboBox, QDialog, QFormLayout,
    QDialogButtonBox, QPushButton
)
from PyQt6.QtGui import QColor, QBrush, QFont
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QDate
from app.controllers.project_controller import ProjectController
from app.models.schema import ProjectStatus
from app.views.widgets.loading_dialog import LoadingDialog
import qtawesome as qta

class DashboardFilterDialog(QDialog):
    def __init__(self, parent, current_filters, companies, pms):
        super().__init__(parent)
        self.setWindowTitle("Filtres Avancés")
        self.setWindowIcon(qta.icon('fa5s.filter', color='white'))
        self.setMinimumWidth(400)

        layout = QFormLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        # Year
        self.year_selector = QComboBox()
        self.year_selector.addItem("Toutes les années", userData=None)
        current_year = QDate.currentDate().year()
        for year in range(current_year - 2, current_year + 3):
            self.year_selector.addItem(str(year), userData=year)
        if current_filters.get('year'):
            self.year_selector.setCurrentText(str(current_filters['year']))
        layout.addRow("Filtrer par Année:", self.year_selector)

        # Company
        self.company_selector = QComboBox()
        self.company_selector.addItem("Toutes les sociétés", userData=None)
        for company in companies:
            self.company_selector.addItem(company['name'], userData=company['id'])
        if current_filters.get('company_id'):
            # Find the index for the company_id and set it
            index = self.company_selector.findData(current_filters.get('company_id'))
            if index != -1:
                self.company_selector.setCurrentIndex(index)
        layout.addRow("Filtrer par Société:", self.company_selector)

        # Project Manager
        self.pm_selector = QComboBox()
        self.pm_selector.addItem("Tous les chefs de projet", userData=None)
        for pm in pms:
             self.pm_selector.addItem(pm) # Assuming pms is a list of strings
        self.pm_selector.setCurrentText(current_filters.get('pm_name') or "Tous les chefs de projet")
        layout.addRow("Filtrer par Chef de Projet:", self.pm_selector)

        # Status
        self.ongoing_only_cb = QCheckBox("Afficher uniquement les projets non-terminés")
        self.ongoing_only_cb.setChecked(current_filters.get('ongoing_only', True))
        layout.addRow("", self.ongoing_only_cb)

        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addRow(self.buttons)

    def get_filters(self):
        pm_text = self.pm_selector.currentText()
        return {
            'year': self.year_selector.currentData(),
            'company_id': self.company_selector.currentData(),
            'pm_name': pm_text if pm_text != "Tous les chefs de projet" else None,
            'ongoing_only': self.ongoing_only_cb.isChecked()
        }

class NumericTableWidgetItem(QTableWidgetItem):
    """Widget-élément de tableau personnalisé pour le tri numérique."""
    def __lt__(self, other):
        try:
            # Tenter de comparer les données numériques stockées pour le tri
            return float(self.data(Qt.ItemDataRole.EditRole)) < float(other.data(Qt.ItemDataRole.EditRole))
        except (ValueError, TypeError, AttributeError):
            # Fallback to default string comparison if data is not numeric
            return super().__lt__(other)


class GlobalDashboardView(QWidget):
    # Signal pour la navigation par double-clic
    project_double_clicked = pyqtSignal(int)

    # Constantes pour les types d'activités, garantissant la cohérence
    MAIN_ACTIVITIES = [
        "Développement Logiciel", "Conception Mécanique", "Étude Électrique", 
        "Montage Mécanique", "Câblage Électrique", "Documentation", "Gestion de Projet"
    ]
    SECONDARY_ACTIVITIES = ["SAV", "Expertise", "Autres"]

    def __init__(self):
        super().__init__()
        self.controller = ProjectController()
        self.column_map = {}
        self.is_syncing_selection = False # Flag pour éviter la récursion des signaux
        self.last_hovered_row = -1
        self.hover_color = QColor("#50556b") # Couleur de survol plus visible sur thème sombre
        base_bg = QColor("#31363B") # Correspond au fond du thème dark_blue.xml
        self.category_colors = [base_bg, base_bg.lighter(115)] # Une couleur de base, une légèrement plus claire

        # Filter state
        self.filter_year = None
        self.filter_company_id = None
        self.filter_pm_name = None
        self.filter_ongoing_only = True

        self.fixed_headers = ["Code", "Nom du Projet", "Chef de Projet"]
        self.material_headers = ["Prévu (€)", "Dépensé (€)", "Delta (€)"]
        self.metric_headers = ["Prévu", "Pointé", "Delta"]

        # --- Layout Principal ---
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10)
        self.layout.setSpacing(10)
        
        # --- Titre et Actions ---
        self._setup_title_bar()

        # --- Zone des Tableaux (Gauche: Figé, Droite: Scrollable) ---
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self.table_fixed = QTableWidget()
        self.table_scrollable = QTableWidget()
        
        self.splitter.addWidget(self.table_fixed)
        self.splitter.addWidget(self.table_scrollable)
        
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)

        # Positionnement initial du splitter
        self.splitter.setSizes([540, 640])

        self.layout.addWidget(self.splitter)

        self._setup_tables()
        self._connect_sync_signals()

        # --- Chargement initial ---
        self.rebuild_ui()

    def _setup_title_bar(self):
        """Crée la barre de titre avec l'icône, le titre et les boutons d'action."""
        title_bar_container = QWidget()
        title_bar_layout = QHBoxLayout(title_bar_container)
        title_bar_layout.setContentsMargins(0, 0, 0, 0)
        title_bar_layout.setSpacing(10)

        # Icône et Titre
        icon_label = QLabel()
        icon_label.setPixmap(qta.icon('fa5s.chart-pie', color='white').pixmap(32, 32))
        title = QLabel("Vue d'Ensemble Globale")
        font = title.font()
        font.setPointSize(18)
        font.setBold(True)
        title.setFont(font)
        
        title_bar_layout.addWidget(icon_label)
        title_bar_layout.addWidget(title)
        title_bar_layout.addStretch(1)

        # Filtre de recherche
        title_bar_layout.addWidget(QLabel("Rechercher:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Code, Nom, CP...")
        self.search_input.setMaximumWidth(200)
        self.search_input.textChanged.connect(self.apply_filters_and_repopulate)
        title_bar_layout.addWidget(self.search_input)

        title_bar_layout.addSpacing(10)

        # Checkbox pour les activités
        self.show_all_activities_cb = QCheckBox("Toutes les activités")
        self.show_all_activities_cb.stateChanged.connect(self.rebuild_ui)
        title_bar_layout.addWidget(self.show_all_activities_cb)

        # Bouton de filtres avancés
        self.filter_button = QPushButton(qta.icon('fa5s.filter', color='white'), " Filtres")
        self.filter_button.clicked.connect(self._open_filter_dialog)
        title_bar_layout.addWidget(self.filter_button)

        # Bouton de rafraîchissement
        self.refresh_button = QPushButton(qta.icon('fa5s.sync-alt', color='white'), " Rafraîchir")
        self.refresh_button.clicked.connect(self.rebuild_ui)
        title_bar_layout.addWidget(self.refresh_button)

        self.layout.addWidget(title_bar_container)

    def _setup_tables(self):
        """Configuration initiale des deux tableaux."""
        # Table Figée (Gauche)
        self.table_fixed.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table_fixed.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.table_fixed.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.table_fixed.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table_fixed.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_fixed.setStyleSheet("QTableWidget { border: none; border-right: 1px solid #555; }")
        self.table_fixed.setMouseTracking(True)
        self.table_fixed.setMinimumWidth(0)
        self.table_fixed.setFrameShape(QFrame.Shape.NoFrame)
        self.table_fixed.verticalHeader().setVisible(False)

        # Table Scrollable (Droite)
        self.table_scrollable.setEditTriggers(QTableWidget.EditTrigger.DoubleClicked | QTableWidget.EditTrigger.SelectedClicked | QTableWidget.EditTrigger.EditKeyPressed)
        self.table_scrollable.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.table_scrollable.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table_scrollable.setMinimumWidth(0)
        self.table_scrollable.setMouseTracking(True)
        self.table_scrollable.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_scrollable.verticalHeader().setVisible(False)
        self.table_scrollable.setFrameShape(QFrame.Shape.NoFrame)
        self.table_scrollable.setAlternatingRowColors(True)

        # Augmenter la hauteur des lignes pour une meilleure lisibilité
        self.table_fixed.verticalHeader().setDefaultSectionSize(32)
        self.table_scrollable.verticalHeader().setDefaultSectionSize(32)

    def _connect_sync_signals(self):
        """Connecte les signaux pour la synchronisation du scroll et de la sélection."""
        # Scroll Vertical
        self.table_scrollable.verticalScrollBar().valueChanged.connect(
            self.table_fixed.verticalScrollBar().setValue
        )
        self.table_fixed.verticalScrollBar().valueChanged.connect(
            self.table_scrollable.verticalScrollBar().setValue
        )

        # Sélection de ligne
        self.table_fixed.itemSelectionChanged.connect(self.sync_selection_from_fixed)
        self.table_scrollable.itemSelectionChanged.connect(self.sync_selection_from_scrollable)

        # Double Clic
        self.table_fixed.cellDoubleClicked.connect(self.on_project_double_clicked)
        self.table_scrollable.cellDoubleClicked.connect(self.on_project_double_clicked)

        # Survol (Hover)
        self.table_fixed.cellEntered.connect(self.on_cell_entered)
        self.table_scrollable.cellEntered.connect(self.on_cell_entered)

        # Édition
        self.table_scrollable.itemChanged.connect(self.on_material_budget_changed)

        # Filtre d'événements pour détecter la sortie de la souris
        self.table_fixed.viewport().installEventFilter(self)
        self.table_scrollable.viewport().installEventFilter(self)

    def _open_filter_dialog(self):
        companies = self.controller.get_all_companies()
        pms = self.controller.get_all_project_managers()

        current_filters = {
            'year': self.filter_year,
            'company_id': self.filter_company_id,
            'pm_name': self.filter_pm_name,
            'ongoing_only': self.filter_ongoing_only
        }

        dialog = DashboardFilterDialog(self, current_filters, companies, pms)
        if dialog.exec():
            new_filters = dialog.get_filters()
            self.filter_year = new_filters['year']
            self.filter_company_id = new_filters['company_id']
            self.filter_pm_name = new_filters['pm_name']
            self.filter_ongoing_only = new_filters['ongoing_only']
            
            self.apply_filters_and_repopulate()

    def sync_selection_from_fixed(self):
        if self.is_syncing_selection: return
        self.is_syncing_selection = True
        selected_ranges = self.table_fixed.selectedRanges()
        self.table_scrollable.clearSelection()
        if selected_ranges: self.table_scrollable.selectRow(selected_ranges[0].topRow())
        self.is_syncing_selection = False

    def sync_selection_from_scrollable(self):
        if self.is_syncing_selection: return
        self.is_syncing_selection = True
        selected_ranges = self.table_scrollable.selectedRanges()
        self.table_fixed.clearSelection()
        if selected_ranges: self.table_fixed.selectRow(selected_ranges[0].topRow())
        self.is_syncing_selection = False

    def _build_column_map_and_count(self):
        """Définit la structure des colonnes et prépare la table."""
        self.table_fixed.horizontalHeader().setVisible(False)
        self.table_scrollable.horizontalHeader().setVisible(False)

        self.hour_metric_categories = ["Total"] + self.MAIN_ACTIVITIES
        if self.show_all_activities_cb.isChecked():
            self.hour_metric_categories += self.SECONDARY_ACTIVITIES

        num_fixed_cols = len(self.fixed_headers)
        num_material_cols = len(self.material_headers)
        num_hour_metric_cols = len(self.hour_metric_categories) * 3
        total_scrollable_cols = num_material_cols + num_hour_metric_cols
        
        self.table_fixed.setColumnCount(num_fixed_cols)
        self.table_scrollable.setColumnCount(total_scrollable_cols)

        self.column_map = {}
        self.scrollable_column_map = {}

        for i, name in enumerate(self.fixed_headers):
            self.column_map[name] = i

        current_scrollable_col = 0
        # Material columns
        self.scrollable_column_map["MATÉRIEL"] = {
            "planned": current_scrollable_col,
            "spent": current_scrollable_col + 1,
            "delta": current_scrollable_col + 2
        }
        current_scrollable_col += 3

        # Hour metric columns
        for category in self.hour_metric_categories:
            self.column_map[category] = {
                "planned": current_scrollable_col, "logged": current_scrollable_col + 1, "delta": current_scrollable_col + 2
            }
            self.scrollable_column_map[category] = {
                "planned": current_scrollable_col,
                "logged": current_scrollable_col + 1,
                "delta": current_scrollable_col + 2
            }
            current_scrollable_col += 3

    def _create_custom_header(self):
        """Crée les deux lignes d'en-tête simulées avec fusions de cellules."""
        header_font = QFont()
        header_font.setBold(True)
        category_bg_color = QColor("#404555")
        metric_bg_color = QColor("#4a5060")

        # En-têtes fixes (fusion verticale)
        for i, header_text in enumerate(self.fixed_headers):
            self.table_fixed.setSpan(0, i, 2, 1)
            item = QTableWidgetItem(header_text)
            item.setFont(header_font)
            item.setBackground(category_bg_color)
            item.setForeground(QBrush(Qt.GlobalColor.white))
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table_fixed.setItem(0, i, item)

        # --- En-têtes scrollables ---
        # Groupe Matériel
        mat_cols = self.scrollable_column_map.get("MATÉRIEL")
        if mat_cols:
            start_col = mat_cols["planned"]
            self.table_scrollable.setSpan(0, start_col, 1, 3)
            cat_item = QTableWidgetItem("MATÉRIEL")
            cat_item.setFont(header_font)
            cat_item.setBackground(category_bg_color)
            cat_item.setForeground(QBrush(Qt.GlobalColor.white))
            cat_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table_scrollable.setItem(0, start_col, cat_item)
            for j, metric_name in enumerate(self.material_headers):
                metric_item = QTableWidgetItem(metric_name)
                metric_item.setFont(header_font)
                metric_item.setBackground(metric_bg_color)
                metric_item.setForeground(QBrush(Qt.GlobalColor.white))
                metric_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table_scrollable.setItem(1, start_col + j, metric_item)

        # En-têtes hiérarchiques pour les métriques
        for category_name in self.hour_metric_categories:
            cat_cols = self.scrollable_column_map.get(category_name)
            if not cat_cols: continue
            
            start_col = cat_cols["planned"]
            self.table_scrollable.setSpan(0, start_col, 1, 3)
            cat_item = QTableWidgetItem(category_name.replace(" ", "\n"))
            cat_item.setFont(header_font)
            cat_item.setBackground(category_bg_color)
            cat_item.setForeground(QBrush(Qt.GlobalColor.white))
            cat_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table_scrollable.setItem(0, start_col, cat_item)
            for j, metric_name in enumerate(self.metric_headers):
                metric_item = QTableWidgetItem(metric_name)
                metric_item.setFont(header_font)
                metric_item.setBackground(metric_bg_color)
                metric_item.setForeground(QBrush(Qt.GlobalColor.white))
                metric_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table_scrollable.setItem(1, start_col + j, metric_item)

    def rebuild_ui(self):
        loading_dialog = LoadingDialog("Mise à jour du tableau de bord...", self)
        loading_dialog.show()
        QApplication.processEvents()

        try:
            self._build_column_map_and_count()
            self.apply_filters_and_repopulate()
            self._adjust_column_widths()
        finally:
            loading_dialog.accept()

    def apply_filters_and_repopulate(self):
        self.table_fixed.setRowCount(0)
        self.table_scrollable.setRowCount(0)

        # Récupère les données déjà filtrées par statut depuis le contrôleur
        all_project_data = self.controller.get_matrix_dashboard_data(
            company_id=self.filter_company_id,
            year=self.filter_year,
            project_manager_name=self.filter_pm_name,
            ongoing_only=self.filter_ongoing_only
        )

        search_term = self.search_input.text().lower()

        # Applique le filtre de recherche textuel en Python sur les données déjà réduites
        if search_term:
            filtered_data = [
                p for p in all_project_data
                if search_term in p['project_code'].lower() or \
                    search_term in p['project_name'].lower() or \
                    search_term in p['project_manager'].lower()
            ]
        else:
            filtered_data = all_project_data

        num_rows = len(filtered_data) + 2
        self.table_fixed.setRowCount(num_rows)
        self.table_scrollable.setRowCount(num_rows)

        self._create_custom_header()

        for i, project_data in enumerate(filtered_data):
            self._populate_row(i + 2, project_data)

    def _populate_row(self, row, data):
        # Appliquer une couleur de fond de base pour la partie fixe pour que le survol fonctionne
        base_bg_color = self.category_colors[0]
        self._set_text_item(self.table_fixed, row, self.column_map["Code"], data['project_code'], project_id=data['project_id'], bg_color=base_bg_color)
        self._set_text_item(self.table_fixed, row, self.column_map["Nom du Projet"], data['project_name'], bg_color=base_bg_color)
        self._set_text_item(self.table_fixed, row, self.column_map["Chef de Projet"], data['project_manager'], bg_color=base_bg_color)

        project_activities = data['activities']

        # Regrouper les activités non principales dans "Autres"
        if "Autres" in self.hour_metric_categories:
            project_activities["Autres"] = {'planned': 0.0, 'logged': 0.0}
            all_defined_activities = self.MAIN_ACTIVITIES + self.SECONDARY_ACTIVITIES
            for act_name, act_data in data['activities'].items():
                if act_name not in all_defined_activities:
                    project_activities["Autres"]['planned'] += act_data['planned']
                    project_activities["Autres"]['logged'] += act_data['logged']
        
        all_scrollable_categories = ["MATÉRIEL"] + self.hour_metric_categories

        for i, category_name in enumerate(all_scrollable_categories):
            bg_color = self.category_colors[i % 2]
            col_indices = self.scrollable_column_map.get(category_name)
            if not col_indices: continue

            if category_name == "MATÉRIEL":
                planned = data.get('budget_material_planned', 0.0)
                spent = data.get('budget_material_spent', 0.0)
                self._set_editable_numeric_item(self.table_scrollable, row, col_indices["planned"], planned, project_id=data['project_id'], suffix=" €", bg_color=bg_color)
                self._set_editable_numeric_item(self.table_scrollable, row, col_indices["spent"], spent, project_id=data['project_id'], suffix=" €", bg_color=bg_color)
                self._set_delta_item(self.table_scrollable, row, col_indices["delta"], planned - spent, suffix=" €", bg_color=bg_color)
            
            elif category_name == "Total":
                planned, logged = data['total_planned'], data['total_logged']
                self._set_numeric_item(self.table_scrollable, row, col_indices["planned"], planned, bg_color=bg_color)
                self._set_numeric_item(self.table_scrollable, row, col_indices["logged"], logged, bg_color=bg_color)
                self._set_delta_item(self.table_scrollable, row, col_indices["delta"], planned - logged, bg_color=bg_color)

            else: # Other activities
                act_data = project_activities.get(category_name, {'planned': 0.0, 'logged': 0.0})
                planned, logged = act_data['planned'], act_data['logged']
                self._set_numeric_item(self.table_scrollable, row, col_indices["planned"], planned, bg_color=bg_color)
                self._set_numeric_item(self.table_scrollable, row, col_indices["logged"], logged, bg_color=bg_color)
                self._set_delta_item(self.table_scrollable, row, col_indices["delta"], planned - logged, is_zero_ok=True, bg_color=bg_color)

    def _set_text_item(self, table, row, col, text, project_id=None, bg_color=None):
        """Crée un QLabel pour une cellule de texte, en utilisant setCellWidget."""
        label = QLabel(text)
        stylesheet_parts = [f"background-color: {bg_color.name()};"] if bg_color else ["background-color: transparent;"]

        if col == self.column_map["Code"]:
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        else:
            label.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
            stylesheet_parts.append("padding-left: 5px;")

        if project_id:
            label.setProperty("project_id", project_id)
        
        stylesheet = " ".join(stylesheet_parts)
        label.setStyleSheet(stylesheet)
        label.setProperty("original_stylesheet", stylesheet)
        table.setCellWidget(row, col, label)

    def _set_numeric_item(self, table, row, col, value, suffix="", bg_color=None):
        if "€" in suffix:
            text = f"{value:.2f}{suffix}" if value != 0 else ""
        else:
            rounded_value = round(value)
            text = f"{rounded_value}{suffix}" if rounded_value != 0 else ""

        label = QLabel(text)
        label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        bg_style = f"background-color: {bg_color.name()};" if bg_color else "background-color: transparent;"
        original_stylesheet = f"{bg_style} padding-right: 5px;"
        label.setStyleSheet(original_stylesheet)
        label.setProperty("original_stylesheet", original_stylesheet)
        table.setCellWidget(row, col, label)

    def _set_editable_numeric_item(self, table, row, col, value, project_id, suffix="", bg_color=None):
        text = f"{value:.2f}{suffix}"
        item = NumericTableWidgetItem(text)
        item.setData(Qt.ItemDataRole.EditRole, value)
        item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        item.setData(Qt.ItemDataRole.UserRole, project_id)
        if bg_color:
            # Rendre la couleur de fond légèrement plus claire pour indiquer l'édition
            item.setData(Qt.ItemDataRole.BackgroundRole, QBrush(bg_color.lighter(120)))
        else:
            item.setData(Qt.ItemDataRole.BackgroundRole, QBrush(QColor("#404555"))) # Fallback
        table.setItem(row, col, item)

    def _set_delta_item(self, table, row, col, value, suffix="", is_zero_ok=False, bg_color=None):
        if "€" in suffix:
            text = f"{value:.2f}{suffix}" if abs(value) >= 0.1 else ""
        else:
            rounded_value = round(value)
            text = f"{rounded_value}{suffix}" if rounded_value != 0 else ""

        label = QLabel(text)
        label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        
        color_style = ""
        if value < 0:
            color_style = "color: #FF5555;"
        elif value > 0:
            color_style = "color: #50FA7B;"
        
        bg_style = f"background-color: {bg_color.name()};" if bg_color else "background-color: transparent;"
        original_stylesheet = f"{bg_style} padding-right: 5px; {color_style}"
        label.setStyleSheet(original_stylesheet)
        label.setProperty("original_stylesheet", original_stylesheet)
        
        table.setCellWidget(row, col, label)

    def _adjust_column_widths(self):
        # Table figée
        self.table_fixed.verticalHeader().setVisible(False)
        fixed_header = self.table_fixed.horizontalHeader()

        # Colonne 'Code' (Index 0) - Largeur fixe
        code_col = self.column_map["Code"]
        fixed_header.setSectionResizeMode(code_col, QHeaderView.ResizeMode.Fixed)
        self.table_fixed.setColumnWidth(code_col, 110)

        # Colonne 'Chef de Projet' (Index 2) - Largeur fixe
        cp_col = self.column_map["Chef de Projet"]
        fixed_header.setSectionResizeMode(cp_col, QHeaderView.ResizeMode.Fixed)
        self.table_fixed.setColumnWidth(cp_col, 150)

        # Colonne 'Nom du Projet' (Index 1) - Élastique
        nom_col = self.column_map["Nom du Projet"]
        fixed_header.setSectionResizeMode(nom_col, QHeaderView.ResizeMode.Stretch)

        # Table scrollable
        header = self.table_scrollable.horizontalHeader()
        metric_col_width = 65

        # Material columns
        mat_cols = self.scrollable_column_map.get("MATÉRIEL")
        if mat_cols:
            for i in range(3):
                header.setSectionResizeMode(mat_cols["planned"] + i, QHeaderView.ResizeMode.Fixed)
                self.table_scrollable.setColumnWidth(mat_cols["planned"] + i, 80)

        # Hour metric columns
        for category in self.hour_metric_categories:
            cat_cols = self.scrollable_column_map.get(category)
            if cat_cols:
                for i in range(3):
                    header.setSectionResizeMode(cat_cols["planned"] + i, QHeaderView.ResizeMode.Fixed)
                    self.table_scrollable.setColumnWidth(cat_cols["planned"] + i, metric_col_width)

    def refresh_data(self):
        self.rebuild_ui()

    def on_project_double_clicked(self, row, column):
        """Gère le double-clic sur une ligne pour ouvrir le détail du projet."""
        if row < 2: return # Ignorer les clics sur l'en-tête
        code_widget = self.table_fixed.cellWidget(row, self.column_map.get("Code", 0))
        if code_widget:
            project_id = code_widget.property("project_id")
            if project_id is not None:
                self.project_double_clicked.emit(project_id)

    def on_material_budget_changed(self, item):
        """Gère la mise à jour des budgets matériel (prévu et dépensé)."""
        if item.row() < 2: return # Ignorer les en-têtes

        # On bloque les signaux pour éviter que la mise à jour du delta ne redéclenche l'événement
        self.table_scrollable.blockSignals(True)
        try:
            row, col = item.row(), item.column()
            project_id = item.data(Qt.ItemDataRole.UserRole)
            if project_id is None: 
                self.table_scrollable.blockSignals(False)
                return

            mat_cols = self.scrollable_column_map.get("MATÉRIEL", {})
            planned_col, spent_col = mat_cols.get("planned"), mat_cols.get("spent")

            if col not in [planned_col, spent_col]: 
                self.table_scrollable.blockSignals(False)
                return

            new_value_str = item.text().replace("€", "").replace(",", ".").strip()
            try:
                new_value = float(new_value_str)
            except (ValueError, TypeError):
                QMessageBox.warning(self, "Valeur invalide", "Veuillez entrer un nombre valide.")
                # Revert edit by rebuilding UI
                self.rebuild_ui()
                # The finally block will unblock signals
                return

            update_field = "budget_material_planned" if col == planned_col else "budget_material_spent"
            success, message = self.controller.update_project(project_id, {update_field: new_value})

            if success:
                # Mettre à jour le modèle de données interne
                item.setData(Qt.ItemDataRole.EditRole, new_value)

                # Recalculer et mettre à jour la cellule delta
                planned_item = self.table_scrollable.item(row, planned_col)
                spent_item = self.table_scrollable.item(row, spent_col)

                # Safeguard: ensure both items exist before calculation
                if planned_item and spent_item:
                    planned_val = float(planned_item.data(Qt.ItemDataRole.EditRole))
                    spent_val = float(spent_item.data(Qt.ItemDataRole.EditRole))
                    self._set_delta_item(self.table_scrollable, row, mat_cols.get("delta"), planned_val - spent_val, suffix=" €")
                else:
                    self.rebuild_ui() # Fallback if an item is unexpectedly missing
            else:
                QMessageBox.critical(self, "Erreur", f"Impossible de mettre à jour le budget : {message}")
                self.rebuild_ui()
        finally:
            self.table_scrollable.blockSignals(False)

    def eventFilter(self, source, event):
        if (source is self.table_fixed.viewport() or source is self.table_scrollable.viewport()):
            if event.type() == event.Type.Leave:
                if self.last_hovered_row >= 2:
                    self._clear_row_highlight(self.last_hovered_row)
                self.last_hovered_row = -1
        return super().eventFilter(source, event)

    def on_cell_entered(self, row, column):
        if self.last_hovered_row != row:
            if self.last_hovered_row >= 2:
                self._clear_row_highlight(self.last_hovered_row)
            
            if row >= 2:
                self._apply_row_highlight(row)
            
            self.last_hovered_row = row

    def _apply_row_highlight(self, row):
        """Applique la couleur de survol à tous les widgets d'une ligne."""
        tables = [self.table_fixed, self.table_scrollable]
        for table in tables:
            for col in range(table.columnCount()):
                widget = table.cellWidget(row, col)
                if widget:
                    original_style = widget.property("original_stylesheet") or ""
                    widget.setStyleSheet(original_style + f" background-color: {self.hover_color.name()};")
                else:
                    item = table.item(row, col)
                    if item:
                        # Store original background if not already stored
                        if item.data(Qt.ItemDataRole.UserRole + 1) is None:
                            item.setData(Qt.ItemDataRole.UserRole + 1, item.data(Qt.ItemDataRole.BackgroundRole))
                        item.setData(Qt.ItemDataRole.BackgroundRole, QBrush(self.hover_color))

    def _clear_row_highlight(self, row):
        """Réinitialise la couleur de fond de tous les widgets d'une ligne."""
        tables = [self.table_fixed, self.table_scrollable]
        for table in tables:
            for col in range(table.columnCount()):
                widget = table.cellWidget(row, col)
                if widget:
                    widget.setStyleSheet(widget.property("original_stylesheet") or "")
                else:
                    item = table.item(row, col)
                    if item:
                        original_bg = item.data(Qt.ItemDataRole.UserRole + 1)
                        if original_bg is not None:
                            item.setData(Qt.ItemDataRole.BackgroundRole, original_bg)
                            item.setData(Qt.ItemDataRole.UserRole + 1, None)