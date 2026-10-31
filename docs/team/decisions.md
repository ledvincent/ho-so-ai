# Decisions et questions ouvertes

## Decisions confirmees — 31 octobre 2026

- Un manager local par membre, avec consignes communes et profil explicite.
  Les suivis individuels et les preuves Git/PR servent de memoire partagee,
  sans synchronisation automatique des chats. Le manager commun consolide le
  tableau; chacun publie son suivi sur sa branche. Preuve : demande de Son
  d'implementer les managers personnels dans le chat de configuration.

- Demo voix par bouton dans l'application sur telephone; entree telephonique
  reelle gardee comme extension, avec la meme logique de conversation.
  Preuve : choix explicite de Son dans le chat du manager.
- A la demande de Son, repartition de la connexion et de l'autorisation entre
  Son et Kim : Kim prend connexion/session applicative, dossier et ecran d'accord;
  Son prend sessions de conversation et serveur d'autorisation des outils.
  Ils testent ensemble les controles de securite decrits dans
  `docs/team/identity-and-security.md`. Il s'agit d'une attribution, pas d'une
  implementation ou d'un resultat de test.

- Les agents utilisent une convention commune de travail et de livraison :
  `docs/team/workflow.md`. Elle couvre branches, commits, PR et comptes rendus;
  aucun hook de blocage automatique n'est installe. Preuve : demande de Son
  d'homogeneiser le travail et les commits de chaque agent.

- A la demande de Son, laisser la collecte, ses tests et le contrat de donnees
  a Vincent. Retirer le prototype de collecte et sa CI de la branche du manager,
  en conservant les fichiers sur l'ordinateur. Le manager coordonne les besoins
  et verifie la compatibilite des livraisons de Vincent.

- Vincent est responsable du contrat de donnees commun : definition, documentation,
  exemples et maintenance. Son et Kim valident les besoins de leurs composants.
  Preuve : attribution confirmee par Son dans le chat du manager.

- Son : recherche et agent vocal. Vincent : sources, collecte, donnees structurees
  et validation. Kim : formulaires, rapport mobile et envoi.
  Preuve : repartition confirmee par Son dans le chat de configuration.
- Le manager conseille, prepare les corrections et verifie l'integration;
  validation humaine des fusions. Preuve : accord de Son dans ce meme chat.
- Premiere cible documentee : inscription de residence temporaire `1.004194`,
  puis renouvellement `1.002755`. Preuve : `docs/scope-and-ingestion.md`.

## Questions ouvertes

| Question | Participants | Impact |
| --- | --- | --- |
| Format et transport du lookup commun | Vincent, Son, Kim | Premiere integration |
| Edition CT01 et fichier officiel exact | Vincent, Kim, reviewer humain | Formulaire rempli |
| Technologie voix et canal de livraison | Son, Kim | Scenario de demo |
| Branches/PR et avancement reels de chacun | Tous | Detection des chevauchements |
| Publication du checkout, CI et protection de main | Mainteneur du depot | Controles partages avant fusion |

Pour chaque nouvelle decision, ajouter date, decision, justification, preuve et
composants touches. Ne pas transformer une proposition du manager en accord equipe.

## Kim's manager adoption and shared workflow proposal — 31 October 2026

- Confirmed by Kim: this manager acts as Kim's local coordinator and applies the
  common English workflow. Kim explicitly requested updating the shared manager
  documents so Son and Vincent can use the same approach. This is the scope of
  TEAM-03 on `codex/kim/team-03-manager-protocol`.
- The proposed shared workflow uses each member's published status file, exact
  delivery commits and explicit consumer acknowledgements. Local managers retain
  their respective implementation ownership and preserve active worktrees.
- Proposed integration coordinator: Kim's manager. Son and Vincent's agreement
  has not been recorded here. Check for an existing designation and record each
  member's response before presenting this as a collective decision. Independent
  work and Kim's already authorized local coordination can continue meanwhile.
- Kim's local monitoring was explicitly requested and configured in her own chat.
  The repository instructions do not activate schedules or grant access on Son's
  or Vincent's machines. Private chat routing and automation state remain local.
- This entry does not approve new procedure facts, legal forms, authentication
  compatibility or a successful combined demo. Existing technical boundaries remain.
