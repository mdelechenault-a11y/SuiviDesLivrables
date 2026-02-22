import datetime
from PyQt6.QtWidgets import (
    QWidget, QMenu, QDialog, QFormLayout, QDateEdit, QDialogButtonBox, 
    QMessageBox, QRadioButton, QInputDialog, QToolTip, QTextEdit, QVBoxLayout,
    QLabel
)
from PyQt6.QtGui import QPainter, QColor, QBrush, QPen, QPolygonF, QFont, QCursor, QLinearGradient
from PyQt6.QtCore import Qt, QRectF, QPointF, pyqtSignal, QDate
import qtawesome as qta

# --- Dialogs ---

class CommentsDialog(QDialog):
    def __init__(self, comments_history, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Commentaires du Livrable")
        self.setMinimumSize(450, 350)
        layout = QVBoxLayout(self)
        self.history_display = QTextEdit()
        self.history_display.setReadOnly(True)
        layout.addWidget(self.history_display)
        if not comments_history:
            self.history_display.setPlaceholderText("Aucun commentaire pour ce livrable.")
        else:
            for comment in comments_history:
                date_str = comment['date_creation'].strftime('%Y-%m-%d %H:%M')
                html = f"<p><span style='color: #95a5a6;'>[{date_str}]</span> {comment['contenu']}</p>"
                self.history_display.append(html)
        layout.addWidget(QLabel("Nouveau commentaire :"))
        self.new_comment_input = QTextEdit()
        self.new_comment_input.setPlaceholderText("Saisir un nouveau commentaire ici...")
        self.new_comment_input.setMaximumHeight(80)
        layout.addWidget(self.new_comment_input)
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Close)
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Ajouter")
        self.buttons.button(QDialogButtonBox.StandardButton.Close).setText("Fermer")
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

    def get_new_comment(self):
        return self.new_comment_input.toPlainText().strip()

class ShiftDeliverableDialog(QDialog):
    def __init__(self, current_date, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Décaler le Livrable")
        layout = QFormLayout(self)
        
        self.date_input = QDateEdit(calendarPopup=True)
        self.date_input.setDate(QDate(current_date))
        layout.addRow("Nouvelle date prévue:", self.date_input)

        self.resp_client_radio = QRadioButton("Responsabilité Client")
        self.resp_entreprise_radio = QRadioButton("Responsabilité Entreprise")
        self.resp_entreprise_radio.setChecked(True)
        layout.addRow("Responsabilité du retard:", self.resp_client_radio)
        layout.addRow("", self.resp_entreprise_radio)

        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addRow(self.buttons)

    def get_data(self):
        responsabilite = 'Client' if self.resp_client_radio.isChecked() else 'Entreprise'
        return {
            "new_date": self.date_input.date().toPyDate(),
            "responsabilite": responsabilite
        }

# --- Main Widget ---

class FinancialTimeline(QWidget):
    data_changed = pyqtSignal()
    row_hovered = pyqtSignal(int, int)

    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.controller = controller
        
        # Data
        self.projects = []
        self.deliverables_by_project = {}
        self.monthly_totals = {}
        self.year = datetime.date.today().year
        self.time_slots = []
        self.time_slots_map = {}
        
        # Interaction
        self.milestone_rects = {}
        self.hovered_milestone_id = None
        self.hovered_row = -1
        self.setMouseTracking(True)

        # Dimensions
        self.row_height = 40
        self.header_height = 100 # hauteur de l'entête
        self.month_width = 100
        self.oval_height = 24
        self.oval_width = 0 # Sera calculé dans paintEvent
        self.y_offset = 0

        # Colors
        self.colors = {
            # Backgrounds
            "header_bg": QColor("#404555"),
            # Grids
            "month_grid": QColor("#50556b"),
            # Texts
            "total_billed_text": QColor("#2ECC71"),
            "total_planned_text": QColor("#BDC3C7"),
            # Milestones Gradients (start, end)
            "milestone_delayed": (QColor("#D35400"), QColor("#E67E22")),
            "milestone_invoiced": (QColor("#27AE60"), QColor("#2ECC71")),
            "milestone_default": (QColor("#2980B9"), QColor("#3498DB")),
            "milestone_hover_border": QColor(Qt.GlobalColor.white),
            "milestone_ghost": QColor(180, 180, 180, 150),
            # Lag Lines
            "delay_line_Entreprise": QColor("#C0392B"),
            "delay_line_Client": QColor("#FF1493"),
            "row_hover_bg": QColor(80, 85, 107, 150), # #50556b with alpha
        }

    def set_data(self, projects, deliverables_by_project, year, monthly_totals={}):
        # Reset hover state when data changes
        if self.hovered_row != -1:
            self.hovered_row = -1
        self.projects = projects
        self.deliverables_by_project = {p['project_id']: p for p in deliverables_by_project}
        self.year = year
        self.monthly_totals = monthly_totals

        # Génère une liste ordonnée de tuples représentant les 24 mois à afficher
        self.time_slots = []
        start_year = year - 1
        start_month = 7
        for i in range(24):
            current_month_abs = start_month + i
            slot_year = start_year + (current_month_abs - 1) // 12
            slot_month = (current_month_abs - 1) % 12 + 1
            self.time_slots.append((slot_year, slot_month))
        self.time_slots_map = {slot: i for i, slot in enumerate(self.time_slots)}

        self._update_dimensions()
        self.update()

    def _update_dimensions(self):
        total_width = 24 * self.month_width
        total_height = self.header_height + len(self.projects) * self.row_height + self.y_offset
        self.setMinimumSize(total_width, total_height)

    def set_hovered_row(self, row_index):
        if self.hovered_row != row_index:
            self.hovered_row = row_index
            self.update()

    # --- Interaction Methods ---

    def contextMenuEvent(self, event):
        milestone_id = self._get_milestone_at_pos(QPointF(event.pos()) - QPointF(0, self.y_offset))
        if milestone_id is None: return

        milestone = self._find_deliverable(milestone_id)
        if not milestone: return

        menu = QMenu(self)
        
        invoice_text = "Annuler la Facturation" if milestone['est_facture'] else "Facturer"
        invoice_action = menu.addAction(invoice_text)
        
        comment_action = menu.addAction("Ajouter un commentaire...")
        shift_action = menu.addAction("Décaler...")
        
        menu.addSeparator()
        delete_action = menu.addAction("Supprimer")
        delete_action.setIcon(qta.icon('fa5s.trash-alt', color='red'))
        
        action = menu.exec(event.globalPos())

        if action == invoice_action:
            self._toggle_invoice_status(milestone_id)
        elif action == comment_action:
            self._add_comment(milestone_id)
        elif action == shift_action:
            self._shift_deliverable(milestone_id)
        elif action == delete_action:
            self._delete_deliverable(milestone_id)

    def mouseMoveEvent(self, event):
        pos = event.position()
        milestone_id = self._get_milestone_at_pos(pos - QPointF(0, self.y_offset))

        if milestone_id != self.hovered_milestone_id:
            self.hovered_milestone_id = milestone_id
            self.update() # Redraw to show hover effect if any

        if self.hovered_milestone_id is not None:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
            # Clear row hover if on a milestone
            self.row_hovered.emit(-1, -1)
            milestone = self._find_deliverable(self.hovered_milestone_id)
            if milestone:
                status = "Facturé" if milestone['est_facture'] else "Non facturé"
                tooltip_text = (
                    f"<b>{milestone['nom']}</b><br>"
                    f"Montant : {milestone['montant']:.2f} €<br>"
                    f"Date Prévue : {milestone['date_prevue'].strftime('%d/%m/%Y')}<br>"
                    f"Statut : {status}"
                )
                if milestone.get('date_initiale') and milestone['date_initiale'] != milestone['date_prevue']:
                    tooltip_text += f"<br>Date Initiale : {milestone['date_initiale'].strftime('%d/%m/%Y')}"
                
                if milestone.get('last_comment'):
                    comment = milestone['last_comment']
                    truncated_comment = (comment[:47] + '...') if len(comment) > 50 else comment
                    tooltip_text += f"<br><i>Dernier com. : {truncated_comment}</i>"
                
                QToolTip.showText(QCursor.pos(), tooltip_text, self)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)
            QToolTip.hideText()

            # Emit row hover signal
            y = pos.y() - self.y_offset
            if y > self.header_height:
                row_index = int((y - self.header_height) / self.row_height)
                if 0 <= row_index < len(self.projects):
                    self.row_hovered.emit(row_index, -1)
                else:
                    self.row_hovered.emit(-1, -1) # Outside of project rows
            else:
                self.row_hovered.emit(-1, -1) # In header

    # --- Helper methods for interactions ---

    def _get_milestone_at_pos(self, pos):
        for deliverable_id, rect in self.milestone_rects.items():
            if rect.contains(QPointF(pos)):
                return deliverable_id
        return None
    
    def _find_deliverable(self, deliverable_id):
        for p_data in self.deliverables_by_project.values():
            for d in p_data['deliverables']:
                if d['id'] == deliverable_id:
                    return d
        return None

    # --- Controller Action Handlers ---

    def _toggle_invoice_status(self, deliverable_id):
        success, message = self.controller.toggle_deliverable_invoiced_status(deliverable_id)
        if success:
            self.data_changed.emit()
        else:
            QMessageBox.critical(self, "Erreur", message)

    def _add_comment(self, deliverable_id):
        comments_history = self.controller.get_deliverable_comments(deliverable_id)
        dialog = CommentsDialog(comments_history, self)
        if dialog.exec():
            new_comment = dialog.get_new_comment()
            if new_comment:
                success, message = self.controller.add_comment(deliverable_id, new_comment)
                if not success:
                    QMessageBox.critical(self, "Erreur", message)
                else:
                    self.data_changed.emit() # Refresh to update tooltips

    def _shift_deliverable(self, deliverable_id):
        deliverable = self._find_deliverable(deliverable_id)
        if not deliverable: return

        dialog = ShiftDeliverableDialog(deliverable['date_prevue'], self)
        if dialog.exec():
            data = dialog.get_data()
            success, message = self.controller.shift_deliverable(deliverable_id, data['new_date'], data['responsabilite'])
            if success:
                self.data_changed.emit()
            else:
                QMessageBox.critical(self, "Erreur", message)

    def _delete_deliverable(self, deliverable_id):
        reply = QMessageBox.question(self, "Confirmation", "Êtes-vous sûr de vouloir supprimer ce livrable ?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            success, message = self.controller.delete_deliverable(deliverable_id)
            if success:
                self.data_changed.emit()
            else:
                QMessageBox.critical(self, "Erreur", message)

    # --- Painting Methods ---

    def _date_to_x(self, date):
        """Converts a date to an X coordinate based on month and day."""
        slot_key = (date.year, date.month)
        if slot_key not in self.time_slots_map:
            return None
        
        month_index = self.time_slots_map[slot_key]
        
        if date.month == 12:
            days_in_month = 31
        else:
            days_in_month = (datetime.date(date.year, date.month + 1, 1) - datetime.date(date.year, date.month, 1)).days

        day_percentage = (date.day - 1) / days_in_month if days_in_month > 0 else 0
        
        x = (month_index * self.month_width) + (day_percentage * self.month_width)
        return x

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Mettre à jour les couleurs dépendantes de la palette à chaque peinture pour garantir la cohérence du thème
        self.colors["zebra_bg_1"] = self.palette().window().color()
        self.colors["zebra_bg_2"] = self.palette().window().color().lighter(105)
        self.colors["month_text"] = self.palette().text().color()

        # Calculer la largeur de l'ovale une seule fois
        if self.oval_width == 0 and self.projects:
            fm = painter.fontMetrics()
            # Ajouter un padding horizontal de 10px de chaque côté
            self.oval_width = fm.horizontalAdvance("999 999 €") + 20

        painter.fillRect(self.rect(), self.colors["zebra_bg_1"]) # Default background

        if not self.projects: return

        painter.save()
        painter.translate(0, self.y_offset)

        self._draw_header(painter)
        self.milestone_rects.clear()

        for i, project in enumerate(self.projects):
            y_pos = self.header_height + (i * self.row_height)
            self._draw_project_row(painter, project, y_pos, i)

        painter.restore()
    def _draw_header(self, painter):
        painter.save()
        
        # Header Background
        header_rect = QRectF(0, 0, self.width(), self.header_height)
        painter.fillRect(header_rect, self.colors["header_bg"])

        total_planned = self.monthly_totals.get("planned", {})
        total_billed = self.monthly_totals.get("billed", {})
        
        band_height = self.header_height / 3
        
        bold_font = QFont(painter.font())
        bold_font.setBold(True)
        
        large_bold_font = QFont(painter.font())
        large_bold_font.setBold(True)

        # Augmenter la taille de la police en toute sécurité, pour éviter l'erreur "Point size <= 0"
        if large_bold_font.pointSize() > 0:
            large_bold_font.setPointSize(large_bold_font.pointSize() + 1)
        elif large_bold_font.pixelSize() > 0:
            # Si la taille est en pixels, on l'augmente de 15% pour qu'elle soit visiblement plus grande
            large_bold_font.setPixelSize(int(large_bold_font.pixelSize() * 1.15))

        for i, (slot_year, slot_month) in enumerate(self.time_slots):
            x_pos = i * self.month_width
            
            # Vertical month lines
            pen = QPen(self.colors["month_grid"], 1, Qt.PenStyle.DashLine)
            # Ligne verticale épaisse pour marquer les séparations d'années
            if slot_month == 1 and i > 0:
                pen.setWidth(2)
                pen.setStyle(Qt.PenStyle.SolidLine)
            painter.setPen(pen)
            painter.drawLine(int(x_pos), 0, int(x_pos), self.height())

            month_rect = QRectF(x_pos, 0, self.month_width, self.header_height)

            # Band 3: Année et Nom du Mois
            painter.setPen(self.colors["month_text"])
            painter.setFont(painter.font())
            month_name_rect = QRectF(month_rect.left(), 2 * band_height, month_rect.width(), band_height)
            month_text = datetime.date(slot_year, slot_month, 1).strftime('%b').upper()
            if slot_month == 1 or i == 0:
                month_text = f"{slot_year}\n{month_text}"
            painter.drawText(month_name_rect, Qt.AlignmentFlag.AlignCenter, month_text)

            # Band 2: Total Planned
            painter.setPen(self.colors["total_planned_text"])
            painter.setFont(bold_font)
            planned = total_planned.get((slot_year, slot_month), 0.0)
            planned_text = f"{planned/1000:,.1f}k".replace(",", " ") if planned > 0 else ""
            planned_rect = QRectF(month_rect.left(), band_height, month_rect.width(), band_height)
            painter.drawText(planned_rect, Qt.AlignmentFlag.AlignCenter, planned_text)

            # Band 1: Total Billed
            painter.setFont(large_bold_font)
            painter.setPen(self.colors["total_billed_text"])
            billed = total_billed.get((slot_year, slot_month), 0.0)
            billed_text = f"{billed/1000:,.1f}k".replace(",", " ") if billed > 0 else ""
            billed_rect = QRectF(month_rect.left(), 0, month_rect.width(), band_height)
            painter.drawText(billed_rect, Qt.AlignmentFlag.AlignCenter, billed_text)

        # Horizontal separator
        painter.setPen(self.colors["month_grid"])
        painter.drawLine(0, int(self.header_height), self.width(), int(self.header_height))
        painter.restore()

    def _draw_project_row(self, painter, project, y_pos, row_index):
        painter.save()
        
        # Zebra Striping
        base_color = self.colors["zebra_bg_1"]
        row_color = base_color.lighter(105) if row_index % 2 == 1 else base_color
        shaded_row_color = row_color.darker(108)

        # Part 1: first 6 months (shaded)
        rect1 = QRectF(0, y_pos, 6 * self.month_width, self.row_height)
        painter.fillRect(rect1, shaded_row_color)

        # Part 2: central year (normal)
        rect2 = QRectF(6 * self.month_width, y_pos, 12 * self.month_width, self.row_height)
        painter.fillRect(rect2, row_color)

        # Part 3: last 6 months (shaded)
        rect3 = QRectF(18 * self.month_width, y_pos, 6 * self.month_width, self.row_height)
        painter.fillRect(rect3, shaded_row_color)

        # Draw hover highlight
        if row_index == self.hovered_row:
            hover_rect = QRectF(0, y_pos, self.width(), self.row_height)
            painter.fillRect(hover_rect, self.colors["row_hover_bg"])

        # Draw project lane line
        painter.setPen(self.colors["month_grid"])
        painter.drawLine(0, y_pos + self.row_height, self.width(), y_pos + self.row_height)
        
        project_deliverables = self.deliverables_by_project.get(project['id'])
        if project_deliverables:
            for d in project_deliverables['deliverables']:
                self._draw_milestone(painter, d, y_pos)
        painter.restore()

    def _draw_milestone(self, painter, deliverable, y_pos):
        center_y = y_pos + self.row_height / 2

        # --- 1. Draw Delay Line and Ghost Milestone ---
        if deliverable['date_initiale'] and deliverable['date_initiale'] != deliverable['date_prevue']:
            x_initial = self._date_to_x(deliverable['date_initiale'])
            x_prevu = self._date_to_x(deliverable['date_prevue'])

            if x_initial is not None and x_prevu is not None:
                # Ghost milestone
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(self.colors["milestone_ghost"])
                painter.drawEllipse(QPointF(x_initial, center_y), 4, 4) # Small circle

                # Delay line
                color = self.colors["delay_line_Client"] if deliverable.get('responsabilite_retard') == 'Client' else self.colors["delay_line_Entreprise"]
                pen = QPen(color, 2.5, Qt.PenStyle.SolidLine)
                pen.setCapStyle(Qt.PenCapStyle.RoundCap)
                painter.setPen(pen)
                painter.drawLine(QPointF(x_initial, center_y), QPointF(x_prevu, center_y))

        # --- 2. Draw Main Milestone (Oval/Pill) ---
        x_prevu = self._date_to_x(deliverable['date_prevue'])
        if x_prevu is None: return
        
        center_point = QPointF(x_prevu, center_y)
        
        # Calculate the oval's rectangle
        rect = QRectF(
            center_point.x() - self.oval_width / 2,
            center_point.y() - self.oval_height / 2,
            self.oval_width,
            self.oval_height
        )
        self.milestone_rects[deliverable['id']] = rect

        # Determine gradient colors
        if deliverable['est_facture']:
            gradient_colors = self.colors["milestone_invoiced"]
        elif deliverable.get('date_initiale') and deliverable['date_prevue'] > deliverable['date_initiale']:
            gradient_colors = self.colors["milestone_delayed"]
        else:
            gradient_colors = self.colors["milestone_default"]
        
        # Apply gradient
        gradient = QLinearGradient(rect.topLeft(), rect.bottomLeft())
        gradient.setColorAt(0, gradient_colors[0])
        gradient.setColorAt(1, gradient_colors[1])
        painter.setBrush(QBrush(gradient))
        painter.setPen(gradient_colors[0].darker(120)) # Border

        # Draw the oval shape
        painter.drawRoundedRect(rect, self.oval_height / 2, self.oval_height / 2)

        # Draw the amount text inside
        # Format amount with space separator for thousands
        formatted_amount = f"{deliverable['montant']:,.0f} €".replace(",", " ")
        painter.setPen(Qt.GlobalColor.white)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, formatted_amount)

        # Hover Effect
        if deliverable['id'] == self.hovered_milestone_id:
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(self.colors["milestone_hover_border"], 2))
            painter.drawRoundedRect(rect.adjusted(-1, -1, 1, 1), self.oval_height / 2, self.oval_height / 2)
