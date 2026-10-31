# Tableau de coordination

Initialise le 31 octobre 2026 (Asia/Saigon). Etat observe dans le checkout local;
branches distantes et travail non publie des membres non verifies.
Les taches proposees ne signifient pas que leur responsable les a commencees.

| ID | Priorite | Responsable | Tache / critere de fin | Etat | Dependances | Fichiers / preuve |
| --- | --- | --- | --- | --- | --- | --- |
| AUTH-01 | P0 | Kim | Connexion/deconnexion, session applicative et protection serveur du dossier par proprietaire | A faire | Choix fournisseur avec Son | `docs/team/identity-and-security.md`; implementation non verifiee |
| CONSENT-01 | P0 | Kim | Ecran accepter/refuser une demande liee a la conversation et decision authentifiee | A faire | AUTH-01 + accord d'interface avec Son | `docs/team/identity-and-security.md` |
| ACCESS-01 | P0 | Son | Sessions voix et serveur d'autorisation; blocage des outils sans accord valide | A faire | AUTH-01 + accord d'interface avec Kim | `docs/team/identity-and-security.md` |
| SECURITY-01 | P0 | Son + Kim | Demontrer acces autorise, refus, isolement entre comptes, expiration et anti-rejeu | A faire | AUTH-01 + CONSENT-01 + ACCESS-01 | Scenarios documentes, aucun test execute |
| TEAM-01 | P0 | Manager | Documenter un format commun de travail, branches, commits, PR et comptes rendus | En revue | Revue humaine puis fusion de la configuration | `docs/team/workflow.md`, `AGENTS.md`, modele de PR |
| DATA-01 | P0 | Vincent | Definir et livrer la collecte avec provenance, gestion des erreurs et tests | Laisse a Vincent; avancement a confirmer | Aucune | Ancien prototype conserve localement, retire de la branche du manager |
| CONTRACT-01 | P0 | Vincent | Definir et maintenir le format commun et un exemple synthetique; Son et Kim valident les besoins consommateurs | En attente de la proposition de Vincent | Aucune | `docs/team/contracts.md`; aucun schema impose par le manager |
| DATA-02 | P0 | Vincent | Produire un enregistrement structure, valide par un humain pour un hash precis | A faire / non observe | CONTRACT-01 | `docs/scope-and-ingestion.md`; capture brute insuffisante |
| VOICE-01 | P0 | Son | Parcours vocal vietnamien : intention, lookup, checklist sourcee; refus explicite si hors perimetre | A confirmer; code non observe ici | CONTRACT-01; DATA-02 pour donnees reelles | Aucun composant voix observe |
| REPORT-01 | P0 | Kim | Rapport mobile affichant exactement la version et la checklist du parcours vocal | A confirmer; code non observe ici | CONTRACT-01; DATA-02 pour donnees reelles | Aucun composant rapport observe |
| FORM-01 | P1 | Vincent + Kim | Resoudre l'edition CT01, verifier le fichier puis le mapping des champs | Bloque selon documentation locale | Revue humaine de la source exacte | `docs/scope-and-ingestion.md`; pas de choix automatique d'edition |
| DELIVERY-01 | P1 | Kim | Livrer un lien prive apres confirmation destination et consentement | A confirmer | REPORT-01 | Canal a choisir |
| INTEGRATION-01 | P0 | Manager + equipe | Une session voix aboutit au bon rapport; memes donnees/version; tests et demo reproductibles | En attente | VOICE-01 + REPORT-01 + DATA-02 | Test de bout en bout non disponible |

## Ordre conseille

1. CONTRACT-01 : se mettre d'accord avant de developper trois formats differents.
2. Vincent prepare les donnees; Son et Kim peuvent travailler en parallele avec
   un exemple explicitement synthetique, sans le presenter comme source validee.
3. Brancher une vraie procedure revue, puis verifier le parcours voix -> rapport.
4. Activer le formulaire rempli uniquement apres FORM-01; le rapport reste utile
   avant cette activation.

## Declaration de travail en cours

Chaque membre ajoute une ligne quand une branche commence. Aucun travail non
publie n'est presume connu. Ne pas saisir de donnees personnelles ici.

| Responsable | Tache | Branche / PR | Chemins touches | Besoin des autres | Derniere preuve |
| --- | --- | --- | --- | --- | --- |
| Manager | Installation des consignes et du suivi | Checkout local | `AGENTS.md`, `docs/team/`, `.github/`, README, repartition du perimetre | Relecture humaine avant partage | Configuration locale, 31 octobre 2026 |
