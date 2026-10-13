# EduVault avec comptes (Firebase)

## 1. Règles Firestore (OBLIGATOIRE, sinon "Accès refusé")
Firebase console > Firestore Database > onglet **Règles** > remplacer tout par le contenu de `firestore.rules` > **Publier**.
(Les anciennes règles ne couvraient pas les sous-documents `c/` utilisés pour la sauvegarde.)

## 2. Authentication
Build > Authentication > Sign-in method > **Email/Password** activé.
Settings > **Authorized domains** : ajouter `exotiice.github.io`.
Settings > **Password policy** (optionnel) : minimum 8 caractères.

## 3. App Check (reCAPTCHA v3) : empêche d'utiliser ta clé Firebase depuis un autre site/script
1. https://www.google.com/recaptcha/admin > créer un site **reCAPTCHA v3**, domaines : `exotiice.github.io` (+ `localhost` pour tester). Copie la **clé de site**.
2. Firebase console > Build > **App Check** > ton app web > **reCAPTCHA** > colle la **clé secrète** > Enregistrer.
3. Dans `index.html`, colle la clé de site dans `const APPCHECK_KEY='...'` (tout en haut du bloc Firebase). Vide = App Check désactivé.
4. Teste d'abord : App Check > APIs > Cloud Firestore / Authentication : regarde les « requêtes vérifiées ». **Quand ~100 % sont vérifiées, clique « Appliquer » (Enforce).**
   Tant que tu n'as pas cliqué sur Appliquer, App Check ne bloque rien.
- En local (`localhost`) l'appli active le mode debug : un jeton s'affiche dans la console du navigateur, ajoute-le dans App Check > Gérer les jetons de débogage.
- App Check protège TES services Firebase. Il ne protège pas les clés IA (Gemini/Groq) que chaque étudiant saisit : elles restent chez lui.

## 3 bis. Protéger la clé API (recommandé)
Google Cloud Console > APIs & Services > Credentials > "Browser key" > Application restrictions : **Websites** >
ajouter `https://exotiice.github.io/*` (et `http://localhost:*` pour tester).

## 4. Surveiller les quotas
Firebase console > Usage and billing > **Details & settings** : mettre une alerte budget.
Plan gratuit (Spark) : 50 000 lectures et 20 000 écritures par jour. L'application limite les écritures :
une sauvegarde toutes les 15 s au maximum, seulement si les données ont changé, et seuls les blocs modifiés sont réécrits.

## 4 bis. Partage par code de classe, fiches/quiz par lien, chiffrement
- **Nouvelles règles `shares/`** (dans `firestore.rules`) : à republier (§1), sinon « Accès refusé » au partage.
- Un étudiant de la filière importe le PDF avec l'IA, puis **Réglages > Partage & code de classe > Partager mon emploi du temps** : un code à 8 caractères (ex. `7F5F-DUQA`) et un lien `…#j=7F5FDUQA`.
  Les autres entrent le code (ou ouvrent le lien) : ils importent les séances sans clé IA. « Mettre à jour » côté auteur ; « Mettre à jour » côté membre re-synchronise.
  Le partage ne contient ni notes, ni photos, ni fichiers. Il faut un compte (gratuit) pour publier OU rejoindre ; pour autoriser la lecture sans compte, remplace `allow get: if request.auth != null && …` par `allow get: if …` (déconseillé).
- **Chiffrement côté client** : Compte > Chiffrement > Activer. AES-256-GCM, clé dérivée du mot de passe de chiffrement (PBKDF2-SHA256, 600 000 itérations) ; le mot de passe n'est jamais envoyé. Mot de passe oublié = données CLOUD perdues
  (« Mot de passe oublié » efface le cloud et renvoie ce qui reste sur l'appareil en clair). Ne couvre pas : copie locale de l'appareil, fichiers/Drive, partages par code.
- **Statistiques** : Accueil > Statistiques. Les heures viennent des minuteurs Focus terminés ; fiches/quiz sont estimés à 30 s l'unité. L'historique commence à la mise à jour.

## 5. Déployer
Remplacer `index.html`, `sw.js` et `firestore.rules` dans le dépôt GitHub (le reste ne change pas), puis Ctrl+Shift+R.

## 6. Google Drive (optionnel, par utilisateur)
- Avec un compte EduVault, les données (cours, horaires, notes, quiz...) sont sauvegardées par Firebase.
- Google Drive sert uniquement aux FICHIERS (PDF...) et seulement si l'utilisateur le choisit :
  Réglages > Google Drive (optionnel) > "Connecter mon Drive" puis "Copier mes fichiers dans mon Google Drive".
- Choix fichier par fichier (Modules > trombone) : "Sur cet appareil", "Sur cet appareil seulement (jamais envoyé)", "Dans mon Google Drive", "Lien web".
- Le fichier est créé dans le Drive de l'utilisateur lui-même (portée drive.file : l'app ne voit que les fichiers qu'elle a créés).
- Pour que plusieurs utilisateurs puissent connecter leur Drive, le Client ID Google doit être celui de TON projet :
  Google Cloud > APIs & Services > Credentials > OAuth client "Web" > Authorized JavaScript origins : https://exotiice.github.io
  puis dans l'app : Réglages > bouton 🔑. Écran de consentement OAuth : mode "Production" (ou ajoute les testeurs en mode "Test").

## 6. Nouveautés v10 (à lire une fois)
**Fichiers à remplacer sur GitHub :** `index.html`, `sw.js` (+ `firestore.rules` à PUBLIER dans la console, §1). Le dossier `admin/` reste sur ton ordinateur (ne le mets pas dans GitHub).

- **Annuler (5 s)** après suppression d'un module, d'une échéance, d'une fiche ou d'une séance. Les fichiers locaux d'un module ne sont effacés qu'après le délai.
- **Simulateur de notes** (Modules > 🎯) : « si j'ai 12 à l'examen… » et « combien me faut-il pour valider ? » par module et pour le semestre.
- **PDF → fiches/quiz** (Fiches ou Quiz > 📄) : l'IA (clé de l'étudiant) lit le PDF (texte ; si scanné, les 3 premières pages en image).
- **Export emploi du temps** (Horaires > 🖨) : image (partage WhatsApp) ou PDF via l'impression.
- **Plan de révision** (Agenda > 📅 Plan) : choisis un examen ; l'appli place des blocs dans tes créneaux libres (hors cours A/B et autres échéances) et les ajoute à l'agenda (type « Révision »).
- **Historique** (Réglages > 🕘) : une copie du cloud par jour de modification, 5 gardées. Restaurer est annulable 5 s. Marche aussi avec le chiffrement (copies chiffrées ; mot de passe de chiffrement redemandé si la clé a changé). Coût : ~1 lecture + 1 écriture par bloc, une fois par jour.
- **Signaler / Idée** : écrit dans Firestore (`feedback`). Les erreurs techniques anonymes (message + 4 lignes de pile, version, navigateur) vont dans `errors` ; l'utilisateur peut les désactiver dans la fenêtre « Signaler ».
- **Niveaux, badges, série** (Statistiques) ; **classement de classe** facultatif (pseudo + XP, par code de classe). Les scores sont déclaratifs (un utilisateur motivé peut tricher) : à présenter comme un jeu.
- **Ressources de classe** : uniquement des **liens https** (Drive, etc.), invisibles tant que tu ne les as pas validés dans la page admin. Pas de stockage de fichiers (donc pas de plan Blaze). Droit d'auteur : un avertissement est affiché et tu peux supprimer n'importe quel lien.

### Devenir admin
Firebase console > Firestore > crée la collection **`admins`** > document dont l'ID est **ton UID** (Authentication > Utilisateurs > colonne « UID ») > un champ quelconque (ex. `ok: true`). Ensuite : Réglages > **🛠 Admin** (comptes, feedback, erreurs, liens à valider, annonce dans l'appli). Impossible à créer depuis l'appli. Le nombre de comptes vient d'un `count()` sur `users` (1 lecture facturée par ~1000 docs).

### Notifications push (annonces, appli fermée)
1. Firebase console > Paramètres du projet > **Cloud Messaging** > « Web Push certificates » > Générer une paire de clés > copie la **clé publique** dans `const FCM_VAPID_KEY=''` (dans `index.html`).
2. Les utilisateurs activent : Réglages > 🔔 Annonces (compte requis ; sur iPhone l'appli doit être ajoutée à l'écran d'accueil).
3. Pour envoyer : `cd admin && npm install firebase-admin`, mets ta clé de compte de service dans `admin/service-account.json` (Paramètres du projet > Comptes de service), puis `node send-push.js "Examen reporté" "Le 20 octobre"`. Gratuit (Spark). Ça publie aussi l'annonce dans l'appli pour ceux qui n'ont pas les notifications.
- La console « Notifications composer » ne sait pas cibler tous les navigateurs web sans serveur : d'où ce petit script local.
- **Non testé de bout en bout** (pas d'accès à FCM dans mon environnement) : teste avec ton téléphone avant d'annoncer.

### Ce qui n'est PAS fait
- **Upload de fichiers par les étudiants** (épreuves/TD en PDF) : nécessite Firebase Storage (plan Blaze) + modération des fichiers. Les liens couvrent le besoin sans ça.
- **Graphique d'erreurs / alertes automatiques** dans l'admin : la page liste les 30 dernières ; pour mieux, Firebase Crashlytics/Analytics (autre SDK).

## 7. Nouveautés v13 (accueil intelligent, IA, travail de groupe)
**À remplacer sur GitHub :** `index.html` (+ **republier `firestore.rules`** : nouvelles collections `cls/` et `prj/`). `sw.js` ne change pas.

**Accueil intelligent** (cartes triées par gravité, 4 maximum, jamais de popup) :
- 🎯 *Compte à rebours d'examen* : « DS Java · dans 3 jours — 6 fiches pas encore révisées » + boutons ⚡ Réviser (mini-quiz de 8 questions) et 📅 Plan. Rouge ≤ 2 j, orange ≤ 7 j.
- 🧠 *Détecteur d'oubli* : module avec fiches/quiz non travaillé depuis ≥ 7 jours (mesuré depuis la date de dernière révision d'une fiche ou une session). Bouton ⚡ 15 min. L'historique commence à partir de cette mise à jour.
- 🚫 *Alerte absences* : Réglages > Études > « Limite d'absences par module » (0 = désactivé). Orange à limite − 1, rouge à la limite, + alerte au moment où tu ajoutes une absence.
- 📊 *Bilan de la semaine* (dimanche et lundi) : heures de révision, jours actifs, modules non touchés, variation de moyenne (comparée à l'instantané enregistré chaque jour, 70 jours gardés). Se ferme avec ✕.

**Agenda — priorité intelligente** : tri par `coefficient × difficulté (moyenne basse + fiches en retard) × type / (jours restants + 1)`. Bouton 🎯/📅 pour revenir au tri par date ; puces « Priorité haute / moyenne ».

**Mode concentration** (onglet Focus) : masque la navigation, coupe les toasts et rappels de l'appli (sauf erreurs), garde l'écran allumé (Wake Lock si le navigateur le permet).

**IA et révision**
- 📸 *Photo → notes + fiches* (Fiches/Quiz) : jusqu'à 3 photos de tableau/cahier ; l'IA (clé de l'étudiant) transcrit en notes (rangées dans l'aide-mémoire) et crée des fiches.
- 📌 *Aide-mémoire* (Modules ou Réglages > Classe & partage) : formules, définitions, notes par module ; impression A4 en 2 colonnes.
- 📝 *Examen blanc* (Quiz, bas de page) : module + nombre de questions + durée ; chrono global, pas de correction avant la fin, navigation/marquage « à revoir », note /20 et correction des erreurs. Compte dans l'historique et les XP.

**Travail de groupe (Réglages > Classe & partage)**
- 💬 *Espace de classe* : discussion en temps réel + « Demandes » (ex. « notes du cours de réseaux du 5 oct. ») avec réponses et lien https ; l'auteur marque « Résolu ». Une classe = un code de partage (rejoindre d'abord via « Rejoindre avec un code »).
- 🤝 *Projets de groupe* : crée un projet (code à 8 caractères), partage-le ; chacun ajoute des tâches (responsable + échéance) et coche les siennes en direct ; barre d'avancement ; filtre « Mes tâches ».
- Sécurité : le **code joue le rôle de clé** (comme les partages) : quiconque le connaît et a un compte peut lire/écrire dans l'espace. Pas de vérification de « membre » possible côté règles Firestore sans serveur. L'admin (🛠) peut supprimer n'importe quel message (✕) ; l'auteur supprime les siens.
- Coût : lecture temps réel ≈ 60 messages à l'ouverture puis seulement les nouveaux ; les abonnements sont fermés à la fermeture de la fenêtre.
- Pas de modération automatique : si le chat grossit, envisage App Check (§3) + règles de taux (nécessite Cloud Functions).

**Ce qui n'est pas fait** : « espace de chat » = discussion de classe (pas de messages privés / pièces jointes) ; l'aide-mémoire n'a pas de rendu mathématique (texte brut) ; la priorité intelligente n'envoie pas de notification.

## 8. Nouveautés v14 (chat public + Réglages en pages)

**À faire : republier `firestore.rules`** (Firestore > Règles > Publier). Sans ça le chat affiche « Chat indisponible ».

### Chat public (bouton 💬 en haut, ou Plus > Chat public)
- **Tout le monde peut lire**, même sans compte (visiteurs). Pour **écrire**, il faut un compte.
- Collection `chat`. Règles : 500 caractères max, 1 message toutes les 2 s (appliqué côté serveur via `chatMeta/{uid}`), pas d'usurpation du pseudo/uid.
- **Modération** : chacun supprime ses messages ; l'admin supprime n'importe lequel et peut **bloquer** un compte (bouton 🚫) → crée `banned/{uid}`. Pour débloquer : supprime ce document dans la console Firebase.
- **Quota (plan Spark = 50 000 lectures/jour)** : l'appli ne charge que les **40 derniers messages**, ne s'abonne que quand la page Chat est ouverte, et coupe l'abonnement en quittant la page (ou 60 s en arrière-plan). Compte environ 40 lectures par ouverture + 1 par nouveau message et par personne présente. Surveille Usage dans la console ; si tu approches de la limite, baisse `CH_LIMIT` dans `index.html`.
- Les messages sont **publics** : ils sont visibles de toute personne qui connaît l'adresse du site (et la clé API publique). Rappelle-le aux étudiants (un avertissement est affiché dans la page). Active **App Check** (§3) pour limiter les abus par script.

### Réglages en pages
Plus (en bas à droite) ouvre maintenant une **page** (plus une fenêtre) : Apparence, Études, Données, Classe & partage, **Outils & progression** (stats, classement, aide-mémoire, annonces), Compte, Aide. Le bouton ‹ du téléphone / du navigateur revient à la liste.


## v16 : nouveautés
- **Notes** : blocs de code colorés (```cpp, ```python…) et formules LaTeX ($V=RI$ ou $$\frac{a}{b}$$), bouton Aperçu dans la fenêtre de notes. Bibliothèques : highlight.js 11.9.0 et KaTeX 0.16.9 (cdnjs), chargées à la demande puis gardées en cache.
- **Projets** (onglet Kanban) : colonnes À faire / En cours / Terminé, glisser-déposer (souris + tactile) ou boutons ‹ ›. Les projets sont sauvegardés et synchronisés avec le reste des données.
- **Assistant** : bouton 🤖 (panneau latéral) et bouton dans les notes. Utilise la clé Gemini/Groq déjà saisie dans ✨ IA ; aucune donnée ne passe par ton serveur.
- **Statistiques** : focus par matière, progression des quiz par matière (alerte « À réviser » sous 60 %).
- **Google Agenda** : bouton 🗓 dans Agenda (lien d'ajout par échéance + export .ics des échéances).

## v17 : animations
- Transition en cascade à chaque onglet, ombres chaudes douces, effets au survol (cartes, boutons, navigation), ondulation sur les boutons, confettis quand une échéance ou une carte Kanban passe à « Terminé ».
- Tout est désactivé automatiquement si le système demande « réduire les animations ».

## v18 : couleurs des modules
- Nouvelle palette de 12 teintes bien distinctes (terracotta, bleu, vert, magenta, moutarde, cyan, rouge, violet, olive, ardoise, rose, anthracite). Les 6 premières sont les plus éloignées les unes des autres.
- Carte plus lisible : fond très léger, bande de couleur de 6 px, monogramme coloré (initiale du module), titre assombri pour le contraste.
- Sélecteur de couleurs dans le formulaire du module : pastille « déjà utilisée » et avertissement si la couleur est trop proche d une autre du même semestre.
- Migration unique : les anciennes couleurs par défaut sont remplacées, semestre par semestre ; les couleurs personnalisées sont conservées. Réglages > 🎨 permet de tout recolorer.

## v19 : icônes par format de fichier
- Chaque document d un module affiche une tuile selon son format : 🖼️ image (avec miniature), 📕 PDF, 📘 Word, 📗 Excel/CSV, 📙 Slides, 🗒️ texte, 💻 code (.ino, .py, .cpp…), 🗜️ archive, 🎬 vidéo, 🎵 audio, 🧊 3D/CAD, 🔌 circuit, ▶️ YouTube, 🗂️ Drive, 🔗 lien.
- Nom du format et taille du fichier affichés ; à l ajout, aperçu du fichier choisi et titre rempli automatiquement.
- Les anciens fichiers sont reconnus automatiquement (type relu une seule fois depuis le stockage de l appareil).

## v20 : Google Agenda automatique
- Synchro bidirectionnelle (création, modification, suppression) vers un agenda dédié « EduVault ». Mise en place : voir GCAL-SETUP.md.

## v21 / v22 : nouveautés
- **Accueil** : après le niveau, l'appli demande l'école et l'âge (facultatif). Réglages > École et âge pour modifier.
- **Règles de moyenne** (Bilan annuel ou Réglages > Règles) : modules validés, note éliminatoire, compensation semestre/année, rattrapage (meilleure note / remplace / plafonnée), ECTS. Les 3 préréglages sont des exemples à adapter à ton règlement. **Simulateur** : change des notes sans rien enregistrer.
- **Visionneuse** : PDF continu avec zoom (boutons, pincement, Ctrl+molette), Word (.docx), CSV, Markdown, texte/code, audio, vidéo, images ; balayage ou flèches entre les fichiers du module. PDF et Word utilisent pdf.js / mammoth (CDN, mis en cache).
- **Installation** : manifest avec raccourcis (Quiz, Focus, Fiches, Agenda) et « Partager vers EduVault » (Android/Chrome, appli installée). iOS ne propose pas le partage vers une PWA.
- **Voix** : 🎤 dictée dans les notes (Chrome/Edge, arabe Maroc/arabe/français/anglais, nécessite Internet) ; 🔊 lecture d'une note ; 🎧 lecture des fiches (question, pause, réponse). Il faut une voix arabe installée sur le téléphone.
- **Import .ics** : Réglages > Importer un calendrier : examens, vacances, devoirs.
- **Fiches** : cartes à trous `{{c1::mot}}` et images avec zones masquées.
- **ENIAD** : lecture de `data/timetables.json` et `data/events.json` (robot GitHub). Voir ENIAD-LISEZ-MOI.txt.

## v23 : visite guidée
- La visite guidée présente toutes les nouveautés (fichiers, notes et voix, fiches, règles de moyenne, ENIAD/agenda, projets/installation). Les anciens utilisateurs la voient une seule fois (6 étapes) ; Réglages > Revoir la visite affiche la version complète.
- La carte ENIAD de l accueil n apparait que si l école est ENIAD ou si une classe est choisie.

## v24 : confirmation ENIAD + séances supplémentaires
- Les changements de l emploi du temps ENIAD ne sont JAMAIS appliqués tout seuls : la carte « Emploi du temps modifié » ouvre la liste des différences (ajoutées / supprimées / modifiées) ; tu choisis Confirmer, Plus tard ou Ignorer cette version.
- Séances supplémentaires (bouton ➕ Supp. dans Horaires) : date précise, heure, salle, type (supplémentaire / rattrapage / remplacement), prof et note. Elles apparaissent dans Aujourd hui et la semaine, ont un rappel, sont exportées en .ics et en Google Agenda, et ne sont jamais écrasées par une mise à jour ENIAD.
