# Todo List - Améliorations Suivi des Livrables

## Barre de Navigation Latérale (Sidebar)
- **Proposition :** Remplacer la barre de menu par une barre de navigation latérale (sidebar) rétractable avec des icônes pour chaque section.
- **Bénéfice :** Navigation plus intuitive, rapide et conforme aux standards actuels.
- **Prompt pour l'IA :** "Modifie la structure de la `MainWindow` dans `main.py` pour remplacer la `QMenuBar` actuelle par une barre de navigation latérale personnalisée. Cette barre devra être un widget custom (par exemple, `SidebarWidget`) qui contiendra des `QToolButton` avec icônes et texte pour chaque section (Pilotage, Projets, Paramètres, etc.). Implémente une fonctionnalité pour la rétracter et n'afficher que les icônes. Assure-toi que chaque bouton de la sidebar change la vue affichée dans le `QStackedWidget` central."

## Vue Calendrier
- **Proposition :** Ajouter une vue calendrier affichant les échéances des livrables et les jalons des projets, synchronisée avec le Gantt.
- **Bénéfice :** Vision temporelle complémentaire, idéale pour la planification.
- **Prompt pour l'IA :** "Crée une nouvelle vue `calendar_view.py` contenant un widget `QCalendarWidget`. Ajoute une méthode dans `ProjectController` pour récupérer tous les livrables et les tâches importantes (jalons) avec leurs dates. Dans `CalendarView`, surcharge la méthode `paintCell` du calendrier pour mettre en évidence les jours contenant des échéances. Ajoute un panneau à côté du calendrier pour afficher la liste des événements du jour sélectionné."

## Gestion Documentaire
- **Proposition :** Permettre d'attacher des fichiers (devis, etc.) aux projets, tâches ou clients.
- **Bénéfice :** Centralise toutes les informations d'un projet.
- **Prompt pour l'IA :** "Modifie le schéma de la base de données (`app/models/schema.py`) pour ajouter une table `documents` avec des liens polymorphiques vers les projets, tâches et clients. Implémente un `DocumentController` pour gérer l'ajout (copie du fichier dans un dossier `data/documents`) et la suppression de documents. Modifie les vues `ProjectManagementWidget` et `ClientManagementView` pour y ajouter un onglet ou une section "Documents" avec un tableau listant les fichiers attachés, un bouton pour en ajouter et un autre pour les ouvrir."

## Optimisation et Caching
- **Proposition :** Analyser et optimiser les requêtes SQL, et mettre en place un cache pour les données peu volatiles.
- **Bénéfice :** Améliore la réactivité et la fluidité de l'application.
- **Prompt pour l'IA :** "Analyse les méthodes des contrôleurs, en particulier `get_matrix_dashboard_data` et `get_global_project_summary`. Optimise les requêtes SQLAlchemy en utilisant des `joinedload` plus ciblés et en réduisant le nombre de requêtes dans les boucles. Implémente un cache simple basé sur un dictionnaire en mémoire dans les contrôleurs pour les données qui changent rarement, comme la liste des utilisateurs (`get_all_users`) et des profils (`get_all_profils`), avec une méthode pour invalider le cache manuellement."

## Rapports Personnalisés
- **Proposition :** Développer un module de reporting flexible (PDF/Excel) où les utilisateurs construisent leurs propres rapports (temps, budget, etc.) avec des filtres et des modèles.
- **Bénéfice :** Outil puissant pour l'analyse et la communication.
- **Prompt pour l'IA :** "Crée une nouvelle vue `report_builder_view.py`. Cette vue permettra à l'utilisateur de choisir un type de rapport (ex: 'Rapport de temps', 'Rapport financier de projet'). En fonction du choix, affiche des options de filtrage (période, projet, utilisateur). Ajoute une méthode dans `ReportGenerator` qui prend ces options, construit une requête SQLAlchemy dynamique pour agréger les données, et génère un fichier PDF en utilisant la bibliothèque `reportlab`."

## Module Financier Avancé
- **Proposition :** Étendre la fonctionnalité `est_facture` pour y associer des factures, suivre les statuts de paiement et générer des récapitulatifs financiers.
- **Bénéfice :** Centralise la gestion financière et offre une vision claire de la rentabilité.
- **Prompt pour l'IA :** "Crée une nouvelle table `invoices` dans `app/models/schema.py` liée à la table `livrables`. Ajoute des colonnes pour le numéro de facture, la date, le statut du paiement (enum: 'En attente', 'Payé', 'En retard'). Crée une vue `financial_view.py` qui affiche un tableau de tous les livrables facturables, permet de générer une facture (créer une entrée dans la table `invoices`) et de changer le statut de paiement."

## Notifications Interactives
- **Proposition :** Un clic sur une notification de mention ouvrirait directement le projet et le livrable concernés, avec le commentaire en surbrillance.
- **Bénéfice :** Fluidifie le flux de travail et réduit le temps d'accès au contexte.
- **Prompt pour l'IA :** "Modifie la méthode `refresh_notifications` dans `main.py`. Pour chaque action de notification, stocke l'ID du projet et l'ID du livrable. Crée une nouvelle méthode `navigate_to_mention(self, project_id, deliverable_id)`. Cette méthode activera la vue `DeliverablesTrackingView`, la filtrera pour le projet spécifié, et émettra un signal pour que la vue sélectionne et mette en surbrillance le livrable concerné."

## Packaging et Déploiement
- **Proposition :** Utiliser `PyInstaller` ou `cx_Freeze` pour créer un exécutable unique, voire un installeur complet.
- **Bénéfice :** Simplifie grandement l'installation pour les utilisateurs finaux.
- **Prompt pour l'IA :** "Crée un script `build.py` à la racine du projet. Ce script utilisera le module `PyInstaller` pour analyser l'application à partir de `main.py`. Configure le script pour inclure les assets nécessaires (fichiers `.xml` de `qt_material`, icônes, etc.) dans le bundle final via l'option `add-data`. Le script doit produire un exécutable unique dans un dossier `dist`."
