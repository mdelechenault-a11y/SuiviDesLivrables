import sys
import math
from PyQt6.QtWidgets import QWidget, QApplication, QVBoxLayout, QScrollArea, QToolTip
from PyQt6.QtGui import QPainter, QColor, QBrush, QPen, QPolygonF, QCursor
from PyQt6.QtCore import Qt, QRectF, QPointF, pyqtSignal
import datetime

class GanttChart(QWidget):
    task_clicked = pyqtSignal(int)
    task_duration_changed = pyqtSignal(int, int)
    task_lag_changed = pyqtSignal(int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.tasks = []
        self.project_start_date = None
        self.zoom_factor = 1.0  # 1.0 is normal zoom
        self.base_day_width = 30 # Base width for one day
        self.task_rects = {}
        self.is_panning = False
        self.pan_start_pos = QPointF()

        self.setMouseTracking(True)
        self.resize_handle_width = 10
        self.resize_mode = None # Can be 'LAG' or 'DURATION'
        self.resizing_task_id = None
        self.initial_resize_pos = None
        self.initial_duration = 0
        self.initial_lag = 0
        self.initial_task_start_date = None
        self.show_critical_path = False
        self.initial_task_end_date = None
        self.activity_color_map = {
            "Soft": QColor("#3498db"), "Conception Mécanique": QColor("#2ecc71"),
            "Conception Électrique": QColor("#f1c40f"), "Conception Électronique": QColor("#e67e22"),
            "Montage Mécanique": QColor("#9b59b6"), "Câblage Électrique": QColor("#e74c3c"),
            "Documentation": QColor("#95a5a6"), "Gestion de Projet": QColor("#1abc9c"),
            "SAV": QColor("#d35400"), "Expertise": QColor("#34495e"),
            "Commande Matériel": QColor("#7f8c8d"), "Default": QColor("#bdc3c7")
        }
        
        self.setMinimumSize(400, 200)

    def set_data(self, tasks, project_start_date):
        self.tasks = tasks
        self.project_start_date = project_start_date
        self._update_dimensions()
        self.update()

    def set_show_critical_path(self, show):
        """Toggles the visibility of the critical path highlighting."""
        self.show_critical_path = show
        self.update() # Trigger a repaint

    def _update_dimensions(self):
        if not self.project_start_date:
            self.setMinimumSize(400, 200)
            return

        end_dates = [t['date_fin'] for t in self.tasks if t.get('date_fin')]
        project_end_date = max(end_dates) if end_dates else self.project_start_date + datetime.timedelta(days=60)
        total_days = (project_end_date - self.project_start_date).days + 30 # Add buffer
        
        total_width = total_days * self.base_day_width * self.zoom_factor
        total_height = 30 + len(self.tasks) * 25 # header + rows

        self.setMinimumSize(int(total_width), total_height)
        self.update()

    def wheelEvent(self, event):
        if event.angleDelta().y() > 0:
            self.zoom_factor *= 1.25
        else:
            self.zoom_factor *= 0.8
        
        self.zoom_factor = max(0.1, min(self.zoom_factor, 5.0)) # Clamp zoom
        self._update_dimensions()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            for task_id, rect in self.task_rects.items():
                task = next((t for t in self.tasks if t['id'] == task_id), None)
                if not task: continue

                resize_handle_left = QRectF(rect.left(), rect.top(), self.resize_handle_width, rect.height())
                resize_handle_right = QRectF(rect.right() - self.resize_handle_width, rect.top(), self.resize_handle_width, rect.height())

                # Détection du redimensionnement du décalage (Lag)
                if resize_handle_left.contains(event.position()) and task.get('parente_id') is not None:
                    self.resize_mode = 'LAG'
                    self.resizing_task_id = task_id
                    self.initial_resize_pos = event.position()
                    self.initial_lag = task.get('lag_days', 0)
                    self.initial_task_start_date = task.get('date_debut_calculee')
                    self.initial_task_end_date = task.get('date_fin')
                    self.setCursor(Qt.CursorShape.SizeHorCursor)
                    event.accept()
                    return

                # Détection du redimensionnement de la durée
                if resize_handle_right.contains(event.position()):
                    self.resize_mode = 'DURATION'
                    self.resizing_task_id = task_id
                    self.initial_resize_pos = event.position()
                    self.initial_duration = task.get('duree_jours') or 1.0
                    self.setCursor(Qt.CursorShape.SizeHorCursor)
                    event.accept()
                    return

            # Logique de panoramique avec la touche Ctrl
            if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                self.is_panning = True
                self.pan_start_pos = event.pos()
                self.setCursor(Qt.CursorShape.ClosedHandCursor)
                event.accept()
                return

            # Détection du clic sur une tâche
            for task_id, rect in self.task_rects.items():
                if rect.contains(event.position()):
                    self.task_clicked.emit(task_id)
                    event.accept()
                    return
        event.ignore()

    def mouseMoveEvent(self, event):
        if self.resize_mode:
            day_width = self.base_day_width * self.zoom_factor
            if day_width == 0: return

            delta_x = event.position().x() - self.initial_resize_pos.x()
            delta_days = round(delta_x / day_width)
            
            task = next((t for t in self.tasks if t['id'] == self.resizing_task_id), None)
            if not task: return

            if self.resize_mode == 'DURATION':
                new_duration = max(1, self.initial_duration + delta_days)
                task['duree_jours'] = new_duration
                if task.get('date_debut_calculee'):
                    task['date_fin'] = task['date_debut_calculee'] + datetime.timedelta(days=int(new_duration) - 1)
                self.update()
                event.accept()
                return
            
            if self.resize_mode == 'LAG':
                new_lag = max(0, self.initial_lag + delta_days)
                task['lag_days'] = new_lag
                if self.initial_task_start_date and self.initial_task_end_date:
                    # Pour le retour visuel, on déplace la tâche sans changer sa durée
                    duration_in_days = (self.initial_task_end_date - self.initial_task_start_date).days
                    task['date_debut_calculee'] = self.initial_task_start_date + datetime.timedelta(days=delta_days)
                    task['date_fin'] = task['date_debut_calculee'] + datetime.timedelta(days=duration_in_days)

                QToolTip.showText(event.globalPos(), f"Décalage : {new_lag} jours", self)
                self.update()
                event.accept()
                return

        if self.is_panning:
            delta = event.pos() - self.pan_start_pos
            scroll_area = self.parent().parent() # Kludgy, assumes parent is viewport, which is in QScrollArea
            if isinstance(scroll_area, QScrollArea):
                h_bar = scroll_area.horizontalScrollBar()
                v_bar = scroll_area.verticalScrollBar()
                h_bar.setValue(h_bar.value() - delta.x())
                v_bar.setValue(v_bar.value() - delta.y())
            self.pan_start_pos = event.pos()
            event.accept()
            return

        # Logique de survol pour le curseur et les infobulles
        self.setCursor(Qt.CursorShape.ArrowCursor) # Curseur par défaut
        hovered_on_task = False
        QToolTip.hideText()

        for task_id, rect in self.task_rects.items():
            task = next((t for t in self.tasks if t['id'] == task_id), None)
            if not task: continue

            resize_handle_left = QRectF(rect.left(), rect.top(), self.resize_handle_width, rect.height())
            resize_handle_right = QRectF(rect.right() - self.resize_handle_width, rect.top(), self.resize_handle_width, rect.height())
            
            if (resize_handle_right.contains(event.position())) or \
               (resize_handle_left.contains(event.position()) and task.get('parente_id') is not None):
                self.setCursor(Qt.CursorShape.SizeHorCursor)
                hovered_on_task = True
                break # Priorité au curseur de redimensionnement

            if rect.contains(event.position()):
                hovered_on_task = True
                task = next((t for t in self.tasks if t['id'] == task_id), None)
                if task:
                    start_str = task['date_debut_calculee'].strftime('%d/%m/%Y') if task.get('date_debut_calculee') else 'N/A'
                    end_str = task['date_fin'].strftime('%d/%m/%Y') if task.get('date_fin') else 'N/A'
                    duration = task.get('duree_jours', 'N/A')
                    
                    tooltip_text = (
                        f"<b>{task.get('nom', 'Tâche inconnue')}</b><br>"
                        f"Début : {start_str}<br>"
                        f"Fin : {end_str}<br>"
                        f"Durée : {duration} jours"
                    )
                    QToolTip.showText(event.globalPos(), tooltip_text, self)
                break # Tâche trouvée, pas besoin de vérifier les autres

        if not hovered_on_task:
            QToolTip.hideText()
        
        event.ignore()

    def mouseReleaseEvent(self, event):
        if self.resize_mode and event.button() == Qt.MouseButton.LeftButton:
            day_width = self.base_day_width * self.zoom_factor
            if day_width > 0:
                delta_x = event.position().x() - self.initial_resize_pos.x()
                delta_days = round(delta_x / day_width)

                if self.resize_mode == 'DURATION':
                    new_duration = max(1, self.initial_duration + delta_days)
                    self.task_duration_changed.emit(self.resizing_task_id, int(new_duration))
                elif self.resize_mode == 'LAG':
                    new_lag = max(0, self.initial_lag + delta_days)
                    self.task_lag_changed.emit(self.resizing_task_id, int(new_lag))

            self.resize_mode = None
            self.resizing_task_id = None
            self.setCursor(Qt.CursorShape.ArrowCursor)
            QToolTip.hideText()
            event.accept()
            return

        if self.is_panning and event.button() == Qt.MouseButton.LeftButton:
            self.is_panning = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
            event.accept()
            return
        
        event.ignore()

    def paintEvent(self, event):
        if not self.tasks or not self.project_start_date:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        header_height = 30
        row_height = 25
        padding = 4
        day_width = self.base_day_width * self.zoom_factor

        painter.fillRect(self.rect(), self.palette().window().color())

        total_days = int(self.width() / day_width)

        # --- Draw Timeline Header (Week and Month) ---
        for day in range(total_days):
            date = self.project_start_date + datetime.timedelta(days=day)
            x_pos = day * day_width
            
            # Use a more discreet color for the grid lines
            pen = QPen(QColor(80, 80, 80, 40)) # Dark gray with low opacity
            if date.weekday() >= 5: 
                pen = QPen(QColor(60, 60, 60, 40)) # Slightly darker for weekend
            painter.setPen(pen)
            painter.drawLine(int(x_pos), header_height, int(x_pos), self.height())
            
            painter.setPen(self.palette().windowText().color())
            if date.day == 1:
                painter.drawText(QRectF(x_pos, 0, 200, header_height/2), Qt.AlignmentFlag.AlignVCenter, date.strftime(' %B %Y'))
            if date.weekday() == 0: # Monday
                painter.drawText(QRectF(x_pos, header_height/2, 200, header_height/2), Qt.AlignmentFlag.AlignVCenter, f" W{date.isocalendar()[1]}")

        self.task_rects.clear()

        # Create a map for quick lookup of critical status
        task_critical_map = {task['id']: task.get('is_critical', False) for task in self.tasks}

        for i, task in enumerate(self.tasks):
            y_pos = header_height + i * row_height
            start_date = task.get('date_debut_calculee')
            end_date = task.get('date_fin')

            if not start_date or not end_date: continue
            
            start_day = (start_date - self.project_start_date).days
            duration_days = (end_date - start_date).days + 1
            x_pos = start_day * day_width
            bar_width = duration_days * day_width

            is_critical = task_critical_map.get(task['id'], False)

            # Determine color based on critical path status
            if self.show_critical_path and is_critical:
                color = QColor("#e74c3c") # Red for critical tasks
                painter.setBrush(color)
                painter.setPen(color.darker(150))
            else:
                color = self.activity_color_map.get(task.get('activity_type'), self.activity_color_map['Default'])
                painter.setBrush(color)
                painter.setPen(color.darker(120))

            rect = QRectF(x_pos, y_pos + padding, bar_width, row_height - 2 * padding)
            self.task_rects[task['id']] = rect
            painter.drawRoundedRect(rect, 5, 5)
            
            # --- MODIFICATION: Draw text to the right of the bar ---
            painter.setPen(self.palette().text().color())
            
            # Define the drawing area for the text
            text_rect = QRectF(
                rect.right() + 5,  # 5 pixels padding to the right of the bar
                rect.y(),
                200,  # Max width for the text before it gets truncated
                rect.height()
            )
            
            # Truncate long text with "..."
            font_metrics = painter.fontMetrics()
            elided_text = font_metrics.elidedText(task.get('nom', ''), Qt.TextElideMode.ElideRight, int(text_rect.width()))
            
            # Draw the text, vertically centered and left-aligned
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, elided_text)

        # --- Draw Dependency Arrows ---
        for task in self.tasks:
            if task.get('parente_id') in self.task_rects:
                parent_id = task['parente_id']
                child_id = task['id']

                is_parent_critical = task_critical_map.get(parent_id, False)
                is_child_critical = task_critical_map.get(child_id, False)

                # Set arrow color and thickness
                if self.show_critical_path and is_parent_critical and is_child_critical:
                    arrow_color = QColor("#e74c3c") # Red
                    arrow_pen = QPen(arrow_color, 2.0, Qt.PenStyle.SolidLine)
                else:
                    arrow_color = QColor("#f39c12") # Orange
                    arrow_pen = QPen(arrow_color, 1.5, Qt.PenStyle.SolidLine)
                
                painter.setPen(arrow_pen)
                painter.setBrush(arrow_color)

                parent_rect = self.task_rects[task['parente_id']]
                child_rect = self.task_rects[task['id']]
                
                start_point = QPointF(parent_rect.right(), parent_rect.center().y())
                end_point = QPointF(child_rect.left(), child_rect.center().y())
                painter.drawLine(start_point, end_point)
                
                angle = math.atan2(end_point.y() - start_point.y(), end_point.x() - start_point.x())
                arrow_size = 6
                arrow_p1 = end_point - QPointF(math.cos(angle - math.pi / 6) * arrow_size, math.sin(angle - math.pi / 6) * arrow_size)
                arrow_p2 = end_point - QPointF(math.cos(angle + math.pi / 6) * arrow_size, math.sin(angle + math.pi / 6) * arrow_size)
                
                painter.drawPolygon(QPolygonF([end_point, arrow_p1, arrow_p2]))

if __name__ == '__main__':
    from qt_material import apply_stylesheet
    app = QApplication(sys.argv)
    apply_stylesheet(app, theme='dark_blue.xml')
    
    scroll_area = QScrollArea()
    window = QWidget()
    layout = QVBoxLayout(window)
    gantt = GanttChart()
    layout.addWidget(scroll_area)
    scroll_area.setWidget(gantt)
    scroll_area.setWidgetResizable(True)

    start = datetime.date.today() - datetime.timedelta(days=5)
    tasks_data = [
        {'id': 1, 'nom': 'Meca Design', 'activity_type': 'Conception Mécanique', 'date_debut_calculee': start, 'date_fin': start + datetime.timedelta(days=4), 'parente_id': None},
        {'id': 2, 'nom': 'Elec Design', 'activity_type': 'Conception Électrique', 'date_debut_calculee': start, 'date_fin': start + datetime.timedelta(days=2), 'parente_id': None},
        {'id': 3, 'nom': 'Software Dev', 'activity_type': 'Soft', 'date_debut_calculee': start + datetime.timedelta(days=5), 'date_fin': start + datetime.timedelta(days=10), 'parente_id': 1},
        {'id': 4, 'nom': 'Wiring', 'activity_type': 'Câblage Électrique', 'date_debut_calculee': start + datetime.timedelta(days=3), 'date_fin': start + datetime.timedelta(days=6), 'parente_id': 2},
    ]
    gantt.set_data(tasks_data, start)
    
    window.setGeometry(100, 100, 1000, 400)
    window.show()
    sys.exit(app.exec())
