from PyQt6.QtWidgets import QWidget, QVBoxLayout, QComboBox, QHBoxLayout, QLabel, QSizePolicy
from PyQt6.QtCore import QDate
import numpy as np

# Matplotlib imports
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.style as mplstyle

from app.controllers.deliverable_controller import DeliverableController

class StatisticsView(QWidget):
    def __init__(self, current_user):
        super().__init__()
        self.controller = DeliverableController()
        self.current_user = current_user

        # Use a style that works well with dark themes
        mplstyle.use('dark_background')

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(40, 10, 40, 10)

        # --- Top Bar for Filters ---
        top_bar = QHBoxLayout()
        top_bar.addWidget(QLabel("Année:"))
        self.year_selector = QComboBox()
        current_year = QDate.currentDate().year()
        for year in range(current_year - 5, current_year + 2):
            self.year_selector.addItem(str(year))
        self.year_selector.setCurrentText(str(current_year))
        top_bar.addWidget(self.year_selector)
        top_bar.addStretch()
        self.layout.addLayout(top_bar)

        # --- Matplotlib Canvas ---
        self.figure = Figure(tight_layout=True)
        self.canvas = FigureCanvas(self.figure)
        # Permettre au graphique de rétrécir en dessous de sa taille préférée
        self.canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.canvas.updateGeometry()
        self.canvas.setMinimumSize(0, 0)
        self.layout.addWidget(self.canvas)
        self.layout.addStretch()

        # Create subplots
        self.ax1, self.ax2 = self.figure.subplots(1, 2, sharex=False)

        # --- Connections ---
        self.year_selector.currentTextChanged.connect(self.refresh_data)

        # Initial data load
        self.refresh_data()

    def refresh_data(self):
        year_str = self.year_selector.currentText()
        if not year_str:
            return
        year = int(year_str)

        stats = self.controller.get_financial_stats(year, user_id=self.current_user.id)
        self._update_plots(stats, year)

    def _update_plots(self, stats, year):
        # --- Récupérer les objectifs dynamiques ---
        objectives = stats.get('objectives', {})
        target_point_mort = objectives.get('objective_point_mort', 0.0)
        target_obj_1 = objectives.get('objective_1', 0.0)
        target_obj_2 = objectives.get('objective_2', 0.0)

        monthly_planned = stats['monthly_planned']
        monthly_billed = stats['monthly_billed']
        cumulative_planned = stats['cumulative_planned']
        
        months = ['Jan', 'Fév', 'Mar', 'Avr', 'Mai', 'Juin', 'Juil', 'Août', 'Sep', 'Oct', 'Nov', 'Déc']
        x = np.arange(len(months))  # the label locations
        width = 0.35  # the width of the bars

        # --- Clear previous plots ---
        self.ax1.clear()
        self.ax2.clear()

        # --- Set background colors to match theme ---
        bg_color = self.palette().window().color().name()
        self.figure.patch.set_facecolor(bg_color)
        self.ax1.set_facecolor(bg_color)
        self.ax2.set_facecolor(bg_color)

        # --- Plot 1 (Left): Monthly Revenue ---
        self.ax1.bar(x - width/2, monthly_planned, width, label='Prévu', color='#3498db')
        self.ax1.bar(x + width/2, monthly_billed, width, label='Facturé', color='#2ecc71')
        
        # Ajouter les lignes d'objectifs si elles sont définies
        if target_point_mort > 0:
            self.ax1.axhline(y=target_point_mort / 12, color='#e74c3c', linestyle='--', label='Point Mort')
            self.ax1.axhline(y=target_obj_1 / 12, color='#f39c12', linestyle='--', label='Objectif 1')
            self.ax1.axhline(y=target_obj_2 / 12, color='#2ecc71', linestyle='--', label='Objectif 2')

        self.ax1.set_ylabel('Montant (€)')
        self.ax1.set_title(f"Chiffre d'Affaires Mensuel ({year})")
        self.ax1.set_xticks(x, months, rotation=45)
        self.ax1.legend()
        self.ax1.yaxis.set_major_formatter(lambda val, pos: f'{val/1000:.0f}k')
        self.ax1.grid(axis='y', linestyle='--', alpha=0.3)

        # --- Plot 2 (Right): Cumulative Revenue ---
        # Plot target trajectories first (low zorder)
        if target_point_mort > 0:
            target_pm_cum = np.linspace(target_point_mort / 12, target_point_mort, 12)
            target_o1_cum = np.linspace(target_obj_1 / 12, target_obj_1, 12)
            target_o2_cum = np.linspace(target_obj_2 / 12, target_obj_2, 12)
            self.ax2.plot(months, target_pm_cum, color='#e74c3c', linestyle='--', label='Traj. Point Mort', zorder=1)
            self.ax2.plot(months, target_o1_cum, color='#f39c12', linestyle='--', label='Traj. Obj 1', zorder=1)
            self.ax2.plot(months, target_o2_cum, color='#2ecc71', linestyle='--', label='Traj. Obj 2', zorder=1)

        # Plot actual data on top (high zorder)
        line_color = "#3498db"
        self.ax2.plot(months, cumulative_planned, marker='o', linestyle='-', label='Cumul Prévu', color=line_color, zorder=2)
        self.ax2.fill_between(months, cumulative_planned, alpha=0.2, color=line_color, zorder=2)
        
        self.ax2.set_ylabel('Montant Cumulé (€)')
        self.ax2.set_title("Trajectoire du Chiffre d'Affaires Cumulé (YTD)")
        self.ax2.set_xticks(x, months, rotation=45)
        self.ax2.legend()
        self.ax2.grid(True, which='both', linestyle='--', alpha=0.3)
        self.ax2.yaxis.set_major_formatter(lambda val, pos: f'{val/1000:.0f}k')

        # Redraw the canvas
        self.canvas.draw()