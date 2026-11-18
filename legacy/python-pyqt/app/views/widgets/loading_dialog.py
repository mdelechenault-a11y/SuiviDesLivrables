from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QProgressBar, QApplication, QGraphicsDropShadowEffect, QWidget
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

class LoadingDialog(QDialog):
    """
    Une boîte de dialogue modale, sans cadre, professionnelle et stylisée pour afficher
    une animation de chargement pendant les opérations longues.
    """
    def __init__(self, message="Chargement des données en cours...", parent=None):
        super().__init__(parent)
        self.setModal(True)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Widget conteneur principal pour le style et l'ombre
        self.container = QWidget(self)
        self.container.setObjectName("container")
        self.container.setStyleSheet("""
            #container {
                background-color: rgba(35, 40, 55, 0.95); /* Fond plus sombre pour le contraste */
                border: 2px solid #3498db; /* Bordure d'accentuation */
                border-radius: 10px; /* Coins arrondis */
            }
            QLabel {
                color: #E0E0E0;
                font-size: 14px;
                font-weight: bold; /* Texte en gras */
            }
            QProgressBar {
                border: 1px solid #555;
                border-radius: 5px;
                text-align: center;
                background-color: #3a3f50;
                color: transparent; /* Cache le texte de pourcentage */
            }
            QProgressBar::chunk {
                background-color: #3498db; /* Couleur de la barre animée */
                width: 20px;
            }
        """)

        # Effet d'ombre portée pour un effet de profondeur
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, int(255 * 0.5))) # Noir avec 50% d'opacité
        shadow.setOffset(0, 0)
        self.container.setGraphicsEffect(shadow)

        # Layout pour le contenu à l'intérieur du conteneur
        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(20, 20, 20, 20) # Padding interne
        
        self.message_label = QLabel(message)
        self.message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0) # Mode indéterminé pour l'animation

        container_layout.addWidget(self.message_label)
        container_layout.addWidget(self.progress_bar)

        # Layout principal du dialogue pour centrer le conteneur
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(self.container)
        main_layout.setContentsMargins(15, 15, 15, 15) # Marge pour que l'ombre soit visible