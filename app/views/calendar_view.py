from PyQt6.QtWidgets import QWidget, QHBoxLayout, QCalendarWidget, QTextBrowser, QVBoxLayout, QLabel
from PyQt6.QtGui import QPainter, QColor, QBrush
from PyQt6.QtCore import QDate

class CalendarView(QWidget):
    def __init__(self, project_controller):
        super().__init__()
        self.project_controller = project_controller
        self.events = {}  # {QDate: [event_text, ...]}

        self.init_ui()
        self.load_events()

    def init_ui(self):
        layout = QHBoxLayout(self)

        # Calendar Widget
        self.calendar = QCalendarWidget()
        self.calendar.selectionChanged.connect(self.display_events_for_selected_date)
        layout.addWidget(self.calendar, 7) # 70% of the width

        # Events Panel
        events_panel = QWidget()
        events_layout = QVBoxLayout(events_panel)
        events_panel.setStyleSheet("background-color: #2c313c;")

        title_label = QLabel("Événements du jour")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; padding: 10px;")
        
        self.events_browser = QTextBrowser()
        self.events_browser.setStyleSheet("border: none; font-size: 14px;")

        events_layout.addWidget(title_label)
        events_layout.addWidget(self.events_browser)
        
        layout.addWidget(events_panel, 3) # 30% of the width

    def load_events(self):
        """
        Charge les livrables et jalons depuis le contrôleur 
        et les stocke dans le dictionnaire self.events.
        """
        # Note: get_all_deliverables_and_milestones() needs to be implemented
        # in the ProjectController.
        events_data = self.project_controller.get_all_deliverables_and_milestones()
        
        self.events = {}
        for event in events_data:
            date = QDate.fromString(event['date'], "yyyy-MM-dd")
            if date.isValid():
                if date not in self.events:
                    self.events[date] = []
                self.events[date].append(f"<b>{event['project_name']}</b><br>"
                                       f"{event['name']}<br>"
                                       f"<small><i>Type: {event['type']}</i></small>")
        
        # Surcharge la méthode paintCell pour mettre en évidence les jours
        self.calendar.paintCell = self.paint_cell

    def paint_cell(self, painter, rect, date):
        """
        Surchargée pour dessiner une couleur de fond sur les cellules avec des événements.
        """
        # Appel de la méthode originale pour ne pas casser le dessin de base
        QCalendarWidget.paintCell(self.calendar, painter, rect, date)

        if date in self.events:
            painter.save()
            # Couleur de fond semi-transparente
            painter.setBrush(QColor(0, 150, 255, 50)) 
            painter.setPen(QColor(0,0,0,0)) # Pas de bordure
            painter.drawRect(rect)
            painter.restore()

    def display_events_for_selected_date(self):
        """
        Affiche les détails des événements pour la date sélectionnée.
        """
        selected_date = self.calendar.selectedDate()
        if selected_date in self.events:
            event_html = "<br><hr><br>".join(self.events[selected_date])
            self.events_browser.setHtml(event_html)
        else:
            self.events_browser.clear()

    def refresh_data(self):
        """
        Méthode publique pour rafraîchir les données et redessiner le calendrier.
        """
        self.load_events()
        self.calendar.updateCells() # Redessine toutes les cellules
        self.display_events_for_selected_date()
