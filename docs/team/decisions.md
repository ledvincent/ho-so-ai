# Decisions et questions ouvertes

## Decisions confirmees — 31 octobre 2026

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
