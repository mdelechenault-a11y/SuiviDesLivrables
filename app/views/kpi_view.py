from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QComboBox, QHBoxLayout, QLabel, 
                             QSizePolicy, QPushButton, QFrame, QGridLayout, QTableWidget, 
                             QTableWidgetItem, QHeaderView, QProgressBar,
                             QSplitter)
from PyQt6.QtCore import QDate, Qt
import numpy as np
import qtawesome as qta
from PyQt6.QtGui import QFont
# Matplotlib imports
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.style as mplstyle

from app.controllers.deliverable_controller import DeliverableController
from app.controllers.company_controller import CompanyController

class KPIView(QWidget):
    def __init__(self, current_user):
        super().__init__()
        self.controller = DeliverableController()
        self.current_user = current_user
        self.company_controller = CompanyController()

        mplstyle.use('dark_background')

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.layout.setSpacing(15)

        self._setup_title_bar()

        # --- Main Splitter ---
        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setStyleSheet("""
            QSplitter::handle:vertical {
                height: 2px;
                background-color: #4a5060;
            }
            QSplitter::handle:hover {
                background-color: #3498db;
            }
        """)

        # Top container for KPIs
        top_container = QWidget()
        kpi_layout = self._setup_kpi_cards()
        top_container.setLayout(kpi_layout)

        # Bottom container for charts
        bottom_container = QWidget()
        chart_layout = self._setup_charts()
        bottom_container.setLayout(chart_layout)

        splitter.addWidget(top_container)
        splitter.addWidget(bottom_container)
        splitter.setSizes([250, 750]) # Give more space to charts initially

        self.layout.addWidget(splitter)

        self.year_selector.currentTextChanged.connect(self.refresh_data)
        self.company_selector.currentIndexChanged.connect(self._on_company_filter_changed)
        self.refresh_button.clicked.connect(self.refresh_data)

        self._populate_year_filter()
        self.refresh_data()

    def _setup_title_bar(self):
        title_bar = QHBoxLayout()
        
        icon_label = QLabel()
        icon_label.setPixmap(qta.icon('fa5s.tachometer-alt', color='white').pixmap(32, 32))
        title = QLabel("KPI - Indicateurs Clés de Performance")
        font = title.font()
        font.setPointSize(18)
        font.setBold(True)
        title.setFont(font)

        title_bar.addWidget(icon_label)
        title_bar.addSpacing(10)
        title_bar.addWidget(title)
        title_bar.addStretch()

        title_bar.addWidget(QLabel("Année:"))
        self.year_selector = QComboBox()
        self.year_selector.setMinimumWidth(100)
        title_bar.addWidget(self.year_selector)
        
        title_bar.addSpacing(15)
        title_bar.addWidget(QLabel("Société:"))
        self.company_selector = QComboBox()
        self._populate_company_filter()
        title_bar.addWidget(self.company_selector)

        self.refresh_button = QPushButton(qta.icon('fa5s.sync-alt', color='white'), " Rafraîchir")
        title_bar.addWidget(self.refresh_button)

        self.layout.addLayout(title_bar)

    def _populate_company_filter(self):
        self.company_selector.blockSignals(True)
        self.company_selector.clear()
        self.company_selector.addItem("Toutes les sociétés", userData=None)
        companies = self.company_controller.get_all_companies_for_filter()
        for company in companies:
            self.company_selector.addItem(company['name'], userData=company['id'])
        self.company_selector.blockSignals(False)

    def _populate_year_filter(self):
        """Dynamically populates the year selector based on available data."""
        current_selection = self.year_selector.currentText()
        company_id = self.company_selector.currentData()

        self.year_selector.blockSignals(True)
        self.year_selector.clear()

        available_years = self.controller.get_available_years(company_id=company_id)
        
        if not available_years:
            available_years = [QDate.currentDate().year()]

        for year in available_years:
            self.year_selector.addItem(str(int(year)))

        if current_selection in [str(int(y)) for y in available_years]:
            self.year_selector.setCurrentText(current_selection)
        elif available_years:
            self.year_selector.setCurrentText(str(int(available_years[0])))

        self.year_selector.blockSignals(False)

    def _on_company_filter_changed(self):
        self._populate_year_filter()
        self.refresh_data()

    def _create_delay_table(self):
        """Creates the left-side frame with the delay tracking table."""
        frame = QFrame()
        frame.setObjectName("kpiCard")
        frame.setStyleSheet("""
            #kpiCard {{
                background-color: #2c3e50;
                border-radius: 10px;
            }}
        """)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(15, 10, 15, 10)

        title = QLabel("Fiabilité du Planning (Année en cours)")
        title.setStyleSheet("color: #bdc3c7; font-size: 14px; font-weight: bold; margin-bottom: 5px;")
        layout.addWidget(title)

        table = QTableWidget()
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels(["Mois", "OK", "NOK", "Décalé", "Décalé Client"])
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setAlternatingRowColors(True)
        
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        
        header.setStyleSheet("QHeaderView::section { background-color: #34495e; padding: 4px; }")

        # Initialiser le tableau avec 13 lignes (1 ligne de Total + 12 mois).
        table.setRowCount(13)
        months = ["Jan", "Fév", "Mar", "Avr", "Mai", "Juin", "Juil", "Aoû", "Sep", "Oct", "Nov", "Déc"]
        for i, month in enumerate(months):
            item = QTableWidgetItem(month)
            table.setItem(i + 1, 0, item)

        layout.addWidget(table)
        return frame, table

    def _create_grouped_objectives_card(self):
        """Creates the right-side frame with grouped objectives and progress bars."""
        frame = QFrame()
        frame.setObjectName("kpiCard")
        frame.setStyleSheet("""
            #kpiCard {{
                background-color: #2c3e50;
                border-radius: 10px;
            }}
        """)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(15, 10, 15, 10)
        layout.setSpacing(10)

        title = QLabel("Atteinte des Objectifs Financiers")
        title.setStyleSheet("color: #bdc3c7; font-size: 14px; font-weight: bold;")
        layout.addWidget(title)

        objectives_widgets = {}

        colors = {
            "pm": "#e74c3c",
            "obj1": "#f39c12",
            "obj2": "#2ecc71"
        }
        names = {
            "pm": "POINT MORT",
            "obj1": "OBJECTIF 1",
            "obj2": "OBJECTIF 2"
        }

        for key in ["pm", "obj1", "obj2"]:
            # Label row
            label_layout = QHBoxLayout()
            name_label = QLabel(names[key])
            name_label.setStyleSheet(f"color: {colors[key]}; font-weight: bold;")
            
            target_label = QLabel("Cible: N/A")
            target_label.setStyleSheet("color: #95a5a6;")
            
            actual_label = QLabel("Actuel: N/A")
            actual_label.setStyleSheet("color: white;")
            
            percent_label = QLabel("0%")
            percent_label.setStyleSheet(f"color: {colors[key]}; font-weight: bold; font-size: 16px;")
            
            label_layout.addWidget(name_label)
            label_layout.addStretch()
            label_layout.addWidget(target_label)
            label_layout.addSpacing(15)
            label_layout.addWidget(actual_label)
            label_layout.addSpacing(15)
            label_layout.addWidget(percent_label)
            
            # Progress bar
            progress_bar = QProgressBar()
            progress_bar.setTextVisible(False)
            progress_bar.setFixedHeight(8)
            progress_bar.setStyleSheet(f"""
                QProgressBar {{
                    border: 1px solid #4a5060;
                    border-radius: 4px;
                    background-color: #34495e;
                }}
                QProgressBar::chunk {{
                    background-color: {colors[key]};
                    border-radius: 3px;
                }}
            """)
            
            layout.addLayout(label_layout)
            layout.addWidget(progress_bar)
            
            objectives_widgets[key] = {
                'target': target_label,
                'actual': actual_label,
                'percent': percent_label,
                'progress': progress_bar
            }

        layout.addStretch()
        return frame, objectives_widgets

    def _setup_activity_bar_card(self):
        """Creates the central card for the activity distribution bar chart."""
        frame = QFrame()
        frame.setObjectName("kpiCard")
        frame.setStyleSheet("""
            #kpiCard {
                background-color: #2c3e50;
                border-radius: 10px;
            }
        """)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(5, 10, 5, 10)

        title = QLabel("Répartition Activités (h)")
        title.setStyleSheet("color: #bdc3c7; font-size: 14px; font-weight: bold; margin-bottom: 5px; padding-left: 10px;")
        layout.addWidget(title)

        self.activity_bar_figure = Figure()
        self.activity_bar_canvas = FigureCanvas(self.activity_bar_figure)
        self.activity_bar_ax = self.activity_bar_figure.subplots()
        # Adjust margins to make space for Y-axis labels
        self.activity_bar_figure.subplots_adjust(left=0.4, right=0.95, top=0.95, bottom=0.1)
        
        self.activity_bar_figure.patch.set_alpha(0)
        self.activity_bar_ax.set_facecolor('#2c3e50')

        layout.addWidget(self.activity_bar_canvas)
        return frame

    def _setup_top_clients_card(self):
        """Creates the central card for the top 10 clients list."""
        frame = QFrame()
        frame.setObjectName("kpiCard")
        frame.setStyleSheet("""
            #kpiCard {
                background-color: #2c3e50;
                border-radius: 10px;
            }
        """)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(10, 10, 10, 10)

        title = QLabel("Top 10 Clients (Prévu Annuel)")
        title.setStyleSheet("color: #bdc3c7; font-size: 14px; font-weight: bold; margin-bottom: 5px;")
        layout.addWidget(title)

        table = QTableWidget()
        table.setColumnCount(3)
        table.setHorizontalHeaderLabels(["#", "Client", "Montant"])
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setShowGrid(False)
        table.setStyleSheet("QTableWidget { border: none; } QHeaderView::section { background-color: #34495e; }")
        
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        table.setColumnWidth(0, 30)
        table.setColumnWidth(2, 90)

        layout.addWidget(table)
        return frame, table

    def _setup_kpi_cards(self):
        kpi_layout = QHBoxLayout()
        kpi_layout.setSpacing(15)

        self.delay_table_frame, self.delay_table = self._create_delay_table()
        self.activity_bar_card = self._setup_activity_bar_card()
        self.top_clients_card, self.top_clients_table = self._setup_top_clients_card()
        self.objectives_frame, self.objectives_widgets = self._create_grouped_objectives_card()

        kpi_layout.addWidget(self.delay_table_frame, 10)
        kpi_layout.addWidget(self.activity_bar_card, 9)
        kpi_layout.addWidget(self.top_clients_card, 7)
        kpi_layout.addWidget(self.objectives_frame, 6)

        return kpi_layout

    def _setup_charts(self):
        self.figure = Figure(tight_layout=True)
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.canvas.setMinimumSize(0, 0)
        
        chart_layout = QGridLayout()
        chart_layout.addWidget(self.canvas, 0, 0, 1, 2)

        self.ax1, self.ax2 = self.figure.subplots(1, 2)
        return chart_layout

    def refresh_data(self):
        year_str = self.year_selector.currentText()
        if not year_str:
            return
        year = int(year_str)

        company_id = self.company_selector.currentData()
        stats = self.controller.get_financial_stats(year, user_id=self.current_user.id, company_id=company_id)
        
        self._update_kpis(stats)
        self._update_plots(stats, year)

    def _update_kpis(self, stats):
        self._update_activity_bar(stats.get('activity_distribution', {}))
        self._update_top_clients_table(stats.get('top_clients', []))

        # --- Mise à jour du tableau des décalages ---
        if 'delay_stats' in stats:
            delay_stats = stats['delay_stats']
            bold_font = QFont()
            bold_font.setBold(True)

            # 1. Calculer et afficher les totaux annuels sur la première ligne
            total_ok = sum(m.get('invoiced', 0) for m in delay_stats)
            total_nok = sum(m.get('delayed_count', 0) for m in delay_stats)
            total_delayed_non_client = sum(m.get('delayed_amount_non_client', 0.0) for m in delay_stats)
            total_delayed_client = sum(m.get('delayed_amount_client', 0.0) for m in delay_stats)

            # Ligne de total
            total_label_item = QTableWidgetItem("TOTAL ANNÉE")
            total_label_item.setFont(bold_font)
            
            total_ok_item = QTableWidgetItem(str(total_ok))
            total_ok_item.setFont(bold_font)
            total_ok_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            total_nok_item = QTableWidgetItem(str(total_nok))
            total_nok_item.setFont(bold_font)
            total_nok_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            total_delayed_item = QTableWidgetItem(self.format_currency(total_delayed_non_client))
            total_delayed_item.setFont(bold_font)
            total_delayed_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

            total_delayed_client_item = QTableWidgetItem(self.format_currency(total_delayed_client))
            total_delayed_client_item.setFont(bold_font)
            total_delayed_client_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

            self.delay_table.setItem(0, 0, total_label_item)
            self.delay_table.setItem(0, 1, total_ok_item)
            self.delay_table.setItem(0, 2, total_nok_item)
            self.delay_table.setItem(0, 3, total_delayed_item)
            self.delay_table.setItem(0, 4, total_delayed_client_item)

            # 2. Remplir les données mensuelles
            for i, month_stat in enumerate(delay_stats):
                table_row = i + 1  # Décalage pour la ligne de total

                # Col 'OK' (count)
                ok_count = month_stat.get('invoiced', 0)
                ok_item = QTableWidgetItem(str(ok_count))
                ok_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if ok_count > 0:
                    ok_item.setIcon(qta.icon('fa5s.check-circle', color='#2ecc71'))
                self.delay_table.setItem(table_row, 1, ok_item)

                # Col 'NOK' (count)
                nok_count = month_stat.get('delayed_count', 0)
                nok_item = QTableWidgetItem(str(nok_count))
                nok_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if nok_count > 0:
                    nok_item.setIcon(qta.icon('fa5s.exclamation-triangle', color='#f39c12'))
                self.delay_table.setItem(table_row, 2, nok_item)

                # Col 'Décalé' (montant non-client)
                delayed_item = QTableWidgetItem(self.format_currency(month_stat.get('delayed_amount_non_client', 0.0)))
                delayed_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.delay_table.setItem(table_row, 3, delayed_item)

                # Col 'Décalé Client' (montant client)
                delayed_client_item = QTableWidgetItem(self.format_currency(month_stat.get('delayed_amount_client', 0.0)))
                delayed_client_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.delay_table.setItem(table_row, 4, delayed_client_item)

        # --- Update Objectives Card ---
        current_cumul_to_display = sum(stats.get('monthly_planned', []))
        objectives = stats.get('objectives', {})

        def format_currency(value):
            return f"{value:,.0f} €".replace(",", " ")

        # Point Mort
        target_pm = objectives.get('objective_point_mort', 0.0)
        self.objectives_widgets['pm']['target'].setText(f"Cible: {format_currency(target_pm)}")
        self.objectives_widgets['pm']['actual'].setText(f"Actuel: {format_currency(current_cumul_to_display)}")
        if target_pm > 0:
            percent_pm = (current_cumul_to_display / target_pm) * 100
            self.objectives_widgets['pm']['percent'].setText(f"{percent_pm:.0f}%")
            self.objectives_widgets['pm']['progress'].setValue(int(min(percent_pm, 100)))
        else:
            self.objectives_widgets['pm']['percent'].setText("N/A")
            self.objectives_widgets['pm']['progress'].setValue(0)

        # Objectif 1
        target_obj1 = objectives.get('objective_1', 0.0)
        self.objectives_widgets['obj1']['target'].setText(f"Cible: {format_currency(target_obj1)}")
        self.objectives_widgets['obj1']['actual'].setText(f"Actuel: {format_currency(current_cumul_to_display)}")
        if target_obj1 > 0:
            percent_obj1 = (current_cumul_to_display / target_obj1) * 100
            self.objectives_widgets['obj1']['percent'].setText(f"{percent_obj1:.0f}%")
            self.objectives_widgets['obj1']['progress'].setValue(int(min(percent_obj1, 100)))
        else:
            self.objectives_widgets['obj1']['percent'].setText("N/A")
            self.objectives_widgets['obj1']['progress'].setValue(0)

        # Objectif 2
        target_obj2 = objectives.get('objective_2', 0.0)
        self.objectives_widgets['obj2']['target'].setText(f"Cible: {format_currency(target_obj2)}")
        self.objectives_widgets['obj2']['actual'].setText(f"Actuel: {format_currency(current_cumul_to_display)}")
        if target_obj2 > 0:
            percent_obj2 = (current_cumul_to_display / target_obj2) * 100
            self.objectives_widgets['obj2']['percent'].setText(f"{percent_obj2:.0f}%")
            self.objectives_widgets['obj2']['progress'].setValue(int(min(percent_obj2, 100)))
        else:
            self.objectives_widgets['obj2']['percent'].setText("N/A")
            self.objectives_widgets['obj2']['progress'].setValue(0)
    
    def format_currency(self, value):
        """Formate un nombre en chaîne de caractères monétaire."""
        return f"{value:,.2f} €".replace(",", " ")
    
    def _update_activity_bar(self, activity_data):
        """Updates the horizontal bar chart with new activity data."""
        self.activity_bar_ax.clear()
        
        if not activity_data:
            self.activity_bar_ax.text(0.5, 0.5, 'Aucune donnée', horizontalalignment='center', verticalalignment='center', color='grey', transform=self.activity_bar_ax.transAxes)
            self.activity_bar_canvas.draw()
            return

        # Sort data ascending by value to have the largest bar at the top with barh
        sorted_data = sorted(activity_data.items(), key=lambda item: item[1])
        labels = [item[0] for item in sorted_data]
        sizes = [item[1] for item in sorted_data]
        
        y_pos = np.arange(len(labels))
        
        bars = self.activity_bar_ax.barh(y_pos, sizes, color='#3498db', align='center', height=0.6)
        
        self.activity_bar_ax.set_yticks(y_pos)
        self.activity_bar_ax.set_yticklabels(labels, color='white', fontsize=9)

        # Remove spines and ticks for a cleaner look
        self.activity_bar_ax.spines['top'].set_visible(False)
        self.activity_bar_ax.spines['right'].set_visible(False)
        self.activity_bar_ax.spines['bottom'].set_visible(False)
        self.activity_bar_ax.spines['left'].set_color('#2c3e50') # Make it invisible against background
        self.activity_bar_ax.tick_params(axis='x', which='both', bottom=False, top=False, labelbottom=False)
        self.activity_bar_ax.tick_params(axis='y', length=0)

        # Add value labels at the end of each bar
        for bar in bars:
            width = bar.get_width()
            self.activity_bar_ax.text(width + (max(sizes) * 0.02 if sizes else 0),
                                    bar.get_y() + bar.get_height()/2,
                                    f'{int(width)} h',
                                    va='center', color='white', fontsize=9)

        self.activity_bar_canvas.draw()

    def _update_top_clients_table(self, top_clients_data):
        """Updates the top clients table with new data."""
        self.top_clients_table.setRowCount(0)
        if not top_clients_data:
            return
        
        self.top_clients_table.setRowCount(len(top_clients_data))
        for i, client_data in enumerate(top_clients_data):
            rank = i + 1
            
            rank_item = QTableWidgetItem(str(rank))
            rank_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            
            name_item = QTableWidgetItem(client_data['name'])
            
            amount_str = f"{client_data['amount']:,.0f} €".replace(",", " ")
            amount_item = QTableWidgetItem(amount_str)
            amount_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            
            self.top_clients_table.setItem(i, 0, rank_item)
            self.top_clients_table.setItem(i, 1, name_item)
            self.top_clients_table.setItem(i, 2, amount_item)

    def _update_plots(self, stats, year):
        objectives = stats.get('objectives', {})
        target_point_mort = objectives.get('objective_point_mort', 0.0)
        target_obj_1 = objectives.get('objective_1', 0.0)
        target_obj_2 = objectives.get('objective_2', 0.0)

        monthly_planned = stats['monthly_planned']
        monthly_billed = stats['monthly_billed']
        cumulative_planned = stats['cumulative_planned']
        
        months = ['Jan', 'Fév', 'Mar', 'Avr', 'Mai', 'Juin', 'Juil', 'Août', 'Sep', 'Oct', 'Nov', 'Déc']
        x = np.arange(len(months))
        width = 0.35

        self.ax1.clear()
        self.ax2.clear()

        bg_color = self.palette().window().color().name()
        self.figure.patch.set_facecolor(bg_color)
        self.ax1.set_facecolor(bg_color)
        self.ax2.set_facecolor(bg_color)

        # Plot 1: Monthly Revenue
        self.ax1.bar(x - width/2, monthly_planned, width, label='Prévu', color='#3498db')
        self.ax1.bar(x + width/2, monthly_billed, width, label='Facturé', color='#2ecc71')
        
        if target_point_mort > 0:
            self.ax1.axhline(y=target_point_mort / 12, color='#e74c3c', linestyle='--', label='Point Mort', alpha=0.5)
        if target_obj_1 > 0:
            self.ax1.axhline(y=target_obj_1 / 12, color='#f39c12', linestyle='--', label='Objectif 1', alpha=0.5)
        if target_obj_2 > 0:
            self.ax1.axhline(y=target_obj_2 / 12, color='#2ecc71', linestyle='--', label='Objectif 2', alpha=0.5)

        self.ax1.set_ylabel('Montant (€)')
        self.ax1.set_title(f"Chiffre d'Affaires Mensuel ({year})")
        self.ax1.set_xticks(x, months, rotation=45)
        self.ax1.legend()
        self.ax1.yaxis.set_major_formatter(lambda val, pos: f'{val/1000:.0f}k')
        self.ax1.grid(axis='y', linestyle='--', alpha=0.3)

        # Plot 2: Cumulative Trajectory
        if target_point_mort > 0:
            target_pm_cum = np.linspace(target_point_mort / 12, target_point_mort, 12)
            self.ax2.plot(months, target_pm_cum, color='#e74c3c', linestyle='--', label='Traj. Point Mort', zorder=1, alpha=0.5)
        if target_obj_1 > 0:
            target_o1_cum = np.linspace(target_obj_1 / 12, target_obj_1, 12)
            self.ax2.plot(months, target_o1_cum, color='#f39c12', linestyle='--', label='Traj. Obj 1', zorder=1, alpha=0.5)
        if target_obj_2 > 0:
            target_o2_cum = np.linspace(target_obj_2 / 12, target_obj_2, 12)
            self.ax2.plot(months, target_o2_cum, color='#2ecc71', linestyle='--', label='Traj. Obj 2', zorder=1, alpha=0.5)

        line_color = "#3498db"
        self.ax2.plot(months, cumulative_planned, marker='o', linestyle='-', label='Cumul Prévu', color=line_color, zorder=2)
        self.ax2.fill_between(months, cumulative_planned, alpha=0.2, color=line_color, zorder=2)
        
        self.ax2.set_ylabel('Montant Cumulé (€)')
        self.ax2.set_title("Trajectoire du Chiffre d'Affaires Cumulé")
        self.ax2.set_xticks(x, months, rotation=45)
        self.ax2.legend()
        self.ax2.grid(True, which='both', linestyle='--', alpha=0.3)
        self.ax2.yaxis.set_major_formatter(lambda val, pos: f'{val/1000:.0f}k')

        self.canvas.draw()