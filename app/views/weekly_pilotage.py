import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView,
    QLabel, QHBoxLayout, QComboBox, QGroupBox, QDateEdit, QSplitter
)
from PyQt6.QtGui import QFont, QColor, QBrush
from PyQt6.QtCore import Qt, QDate

from app.controllers.project_controller import ProjectController
from app.controllers.user_controller import UserController

class WeeklyPilotageView(QWidget):
    def __init__(self, current_user):
        super().__init__()
        self.current_user = current_user
        self.project_controller = ProjectController()
        self.user_controller = UserController()
        self.summary_data = []

        # --- Main Layout ---
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)

        # --- Main Horizontal Splitter ---
        h_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(h_splitter)

        # --- Panels ---
        left_panel = self._create_left_panel()
        right_panel = self._create_right_panel()
        left_panel.setMinimumWidth(0)
        right_panel.setMinimumWidth(0)

        h_splitter.addWidget(left_panel)
        h_splitter.addWidget(right_panel)
        h_splitter.setStretchFactor(0, 0) # Left panel has fixed size policy
        h_splitter.setStretchFactor(1, 1) # Right panel expands
        h_splitter.setSizes([250, 750])   # Initial size ratio

        self._connect_signals()
        self._on_year_changed(self.year_selector.currentText()) # Initial data load

    def _create_left_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)

        # --- Vertical Splitter for Filters and Weeks Table ---
        v_splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Filters Widget
        self.filter_group = self._create_filter_group()
        
        # Weeks Table
        self.table_weeks_list = QTableWidget()
        self.table_weeks_list.setColumnCount(2)
        self.table_weeks_list.setHorizontalHeaderLabels(["Année", "N° Semaine"])
        self.table_weeks_list.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_weeks_list.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table_weeks_list.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table_weeks_list.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table_weeks_list.verticalHeader().setVisible(False)

        v_splitter.addWidget(self.filter_group)
        v_splitter.addWidget(self.table_weeks_list)
        v_splitter.setStretchFactor(0, 0) # Filters have fixed size
        v_splitter.setStretchFactor(1, 1) # Table expands

        layout.addWidget(v_splitter)
        return panel

    def _create_right_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)

        # Detail Table
        self.table_daily_detail = QTableWidget()
        self.table_daily_detail.setColumnCount(9)
        self.table_daily_detail.setHorizontalHeaderLabels(["Projet & Tâche", "Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim", "Total Semaine"])
        self.table_daily_detail.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table_daily_detail.verticalHeader().setVisible(False)
        self.table_daily_detail.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        layout.addWidget(self.table_daily_detail)
        return panel

    def _create_filter_group(self):
        filter_group = QGroupBox("Filtres")
        filter_layout = QHBoxLayout(filter_group)

        filter_layout.addWidget(QLabel("Année:"))
        self.year_selector = QComboBox()
        current_year = QDate.currentDate().year()
        for year in range(current_year - 5, current_year + 2):
            self.year_selector.addItem(str(year))
        self.year_selector.setCurrentText(str(current_year))
        self.year_selector.setMinimumWidth(100)
        self.year_selector.setMinimumHeight(30)
        self.year_selector.setStyleSheet("QComboBox { padding: 5px; }")
        filter_layout.addWidget(self.year_selector)

        filter_layout.addWidget(QLabel("Utilisateur:"))
        self.user_selector = QComboBox()
        self.populate_user_filter()
        filter_layout.addWidget(self.user_selector)

        filter_layout.addStretch()
        return filter_group

    def _connect_signals(self):
        self.year_selector.currentTextChanged.connect(self._on_year_changed)
        self.user_selector.currentIndexChanged.connect(self.refresh_data)
        self.table_weeks_list.itemSelectionChanged.connect(self._on_week_selected)

    def _on_year_changed(self, year_str):
        self.refresh_data()

    def populate_user_filter(self):
        self.user_selector.blockSignals(True)
        self.user_selector.clear()
        users = self.user_controller.get_all_users()
        current_user_index = -1
        for i, user in enumerate(users):
            self.user_selector.addItem(user['name'], userData=user['id'])
            if user['id'] == self.current_user.id:
                current_user_index = i
        if current_user_index != -1:
            self.user_selector.setCurrentIndex(current_user_index)
        if self.current_user.profil.nom != "Admin":
            self.user_selector.setEnabled(False)
        self.user_selector.blockSignals(False)

    def refresh_data(self):
        user_id = self.user_selector.currentData()
        year = int(self.year_selector.currentText())
        start_date = datetime.date(year, 1, 1)
        end_date = datetime.date(year, 12, 31)

        if not user_id:
            self.table_weeks_list.setRowCount(0)
            self.summary_data = []
            return

        self.summary_data = self.project_controller.get_weekly_time_summary(start_date, end_date, user_id)
        self._populate_weeks_table()
        self._clear_detail_view()

    def _populate_weeks_table(self):
        self.table_weeks_list.setRowCount(len(self.summary_data))
        for row, week_data in enumerate(self.summary_data):
            year = week_data['year']
            week_num = week_data['week_num']

            year_item = QTableWidgetItem(str(year))
            year_item.setData(Qt.ItemDataRole.UserRole, (year, week_num)) # Store key
            week_num_item = QTableWidgetItem(f"{week_num:02d}")

            year_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            week_num_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            self.table_weeks_list.setItem(row, 0, year_item)
            self.table_weeks_list.setItem(row, 1, week_num_item)

    def _on_week_selected(self):
        selected_items = self.table_weeks_list.selectedItems()
        if not selected_items:
            self._clear_detail_view()
            return

        key_item = self.table_weeks_list.item(selected_items[0].row(), 0)
        if not key_item: return

        year, week_num = key_item.data(Qt.ItemDataRole.UserRole)
        selected_week_data = next((w for w in self.summary_data if w['year'] == year and w['week_num'] == week_num), None)

        if selected_week_data:
            self._populate_detail_table(selected_week_data)

    def _populate_detail_table(self, week_data):
        self.table_daily_detail.setRowCount(0)
        # Add 1 for the total row
        task_row_count = sum(len(p['tasks']) for p in week_data['projects'])
        self.table_daily_detail.setRowCount(task_row_count + 1)

        daily_totals = [0.0] * 7
        current_row = 0
        bold_font = QFont()
        bold_font.setBold(True)

        for project_data in week_data['projects']:
            for task_data in project_data['tasks']:
                # Col 0: Name
                name_item = QTableWidgetItem(f"[{project_data['code']}] {project_data['name']} - {task_data['name']}")
                self.table_daily_detail.setItem(current_row, 0, name_item)

                # Cols 1-7: Daily hours
                for day_index, hours in enumerate(task_data['hours']):
                    cell_item = QTableWidgetItem(f"{hours:.2f}" if hours > 0 else "0.00")
                    cell_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                    self.table_daily_detail.setItem(current_row, day_index + 1, cell_item)
                    daily_totals[day_index] += hours

                # Col 8: Total Semaine
                total_item = QTableWidgetItem(f"{task_data['total']:.2f}")
                total_item.setFont(bold_font)
                total_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.table_daily_detail.setItem(current_row, 8, total_item)

                current_row += 1
        
        # --- Populate Totals Row ---
        total_row_index = current_row
        total_bg_color = QColor("#404555") # A slightly lighter color for dark themes

        bold_font = QFont()
        bold_font.setBold(True)

        total_label_item = QTableWidgetItem("TOTAL GÉNÉRAL")
        total_label_item.setFont(bold_font)
        total_label_item.setBackground(QBrush(total_bg_color))
        self.table_daily_detail.setItem(total_row_index, 0, total_label_item)

        grand_total = 0.0
        for i, total in enumerate(daily_totals):
            cell_item = QTableWidgetItem(f"{total:.2f}" if total > 0 else "0.00")
            cell_item.setFont(bold_font)
            cell_item.setBackground(QBrush(total_bg_color))
            cell_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table_daily_detail.setItem(total_row_index, i + 1, cell_item)
            grand_total += total

        grand_total_item = QTableWidgetItem(f"{grand_total:.2f}")
        grand_total_item.setFont(bold_font)
        grand_total_item.setBackground(QBrush(total_bg_color))
        grand_total_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.table_daily_detail.setItem(total_row_index, 8, grand_total_item)

    def _clear_detail_view(self):
        self.table_daily_detail.setRowCount(0)