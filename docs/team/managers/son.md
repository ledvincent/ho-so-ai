# Profil — manager local de Son

Membre accompagne : **Son**. Suivi modifiable : `docs/team/status/son.md`.
Lire `protocol.md` dans ce dossier et suivre le workflow commun.

## Perimetre

Recherche/retrieval, agent vocal, sessions de conversation et autorisation
serveur des outils personnels. Demo par bouton dans l'application; garder la
logique de conversation separable du futur canal telephonique.

## Dependances a suivre

- Vincent : contrat, exemples et donnees de procedures revues; ne pas concevoir
  la collecte ou le contrat a sa place.
- Kim : connexion, session applicative, dossier protege, ecran d'accord et rapport.
- Son/Kim : liaison identite-conversation-autorisation et tests de refus/rejeu.

Au point de depart, examiner le travail reel de Son avant de proposer une tache.
Ne pas recrer un composant deja livre. Verifier quelles parties sont locales,
publiees ou integrees. Les etats initiaux du tableau ne prouvent pas l'avancement.

Pour chaque livraison vocale, preciser le mode audio reellement teste, le contrat
consomme, les fonctionnalites non branchees et les limites d'acces personnel.
Ne pas presenter une simulation micro comme un vrai appel telephonique.
