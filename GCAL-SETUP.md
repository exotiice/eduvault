# Google Agenda : synchronisation automatique (v20)

EduVault crée un agenda dédié **« EduVault »** dans ton compte Google et le garde à jour
(création, modification, suppression). Tes autres agendas ne sont jamais touchés.

## Mise en place (une seule fois, ~5 min)

Utilise le **même projet Google Cloud** que celui du Client ID déjà utilisé pour Drive.

1. Google Cloud Console > **APIs et services > Bibliothèque** > « Google Calendar API » > **Activer**.
2. **Écran de consentement OAuth** (ou « Accès aux données ») > **Ajouter des niveaux d'accès** :
   `https://www.googleapis.com/auth/calendar.app.created`
   (le plus restreint possible : créer SON agenda et gérer SEULEMENT les événements de cet agenda).
3. Si l'appli est en mode **Test** : ajoute ton adresse Gmail dans **Utilisateurs test**.
   Ce niveau d'accès est classé « sensible » : un message « appli non vérifiée » s'affiche, clique
   *Paramètres avancés > Continuer*. Pour plus de 100 utilisateurs, il faut la validation Google.
4. **Identifiants > ID client OAuth** : vérifie que l'adresse de ton site figure dans
   « Origines JavaScript autorisées » (déjà fait pour Drive).
5. Dans EduVault : **Agenda > 🗓 > Connecter Google Agenda**.

## Ce qui est synchronisé

| EduVault | Google Agenda |
|---|---|
| Cours (emploi du temps du semestre actif) | événement hebdomadaire récurrent ; semaines A/B = toutes les 2 semaines ; jours de vacances exclus (EXDATE) ; rappel 30 min |
| Examens | événement 2 h, rappels 1 jour / 3 h / 30 min |
| Devoirs et révisions | événement 30 min, rappels 1 jour / 1 h |
| Couleur du module | couleur d'événement Google la plus proche |

Les tâches terminées sont retirées de l'agenda. Les cours se répètent jusqu'à la date choisie dans la fenêtre 🗓 (par défaut ~16 semaines).

## Sens Google > EduVault

Quand tu modifies un événement dans Google : titre et date d'un examen/devoir, heure et salle d'un cours.
Si tu **supprimes** un événement dans Google, l'élément n'est plus synchronisé (bouton « Les resynchroniser » pour annuler).
En cas de conflit (modifié des deux côtés avant la synchro), la version EduVault l'emporte.

## Limites à connaître

- La connexion Google dure 1 h (limite d'une appli sans serveur) : la synchro tourne tant que l'appli est ouverte ; après 1 h elle se reconnecte au prochain toucher. Une synchro appli fermée demanderait un petit serveur (par exemple en étendant `admin/send-push.js`).
- Changer de semestre actif retire de l'agenda les cours de l'autre semestre.
- Les règles `firestore.rules` n'ont pas besoin de changer : l'état de synchro est stocké dans tes données EduVault déjà chiffrées/synchronisées.
