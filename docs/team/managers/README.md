# Un manager local par membre

Chacun ouvre son propre chat Codex attache a sa copie du depot et lui donne
l'instruction correspondante. Les profils et les fichiers de suivi sont livres
par le depot; aucun chat n'est cree ou active sur l'ordinateur des autres membres.

| Membre | Instruction a copier dans son chat |
| --- | --- |
| Son | Agis comme mon manager local. Lis AGENTS.md, docs/team/manager.md, docs/team/managers/protocol.md et docs/team/managers/son.md, puis fais mon point de depart. |
| Vincent | Agis comme mon manager local. Lis AGENTS.md, docs/team/manager.md, docs/team/managers/protocol.md et docs/team/managers/vincent.md, puis fais mon point de depart. |
| Kim | Agis comme mon manager local. Lis AGENTS.md, docs/team/manager.md, docs/team/managers/protocol.md et docs/team/managers/kim.md, puis fais mon point de depart. |

## Installation

1. Recuperer la configuration une fois fusionnee dans main, sans ecraser le
   travail en cours. Un nouveau clone peut partir directement de main.
2. Ouvrir un chat dans ce depot et copier l'instruction de son profil.
3. Le manager lit les regles, actualise les references Git et presente ce qui est
   observe, inconnu et necessaire pour avancer. Il ne choisit pas son membre a
   partir du nom du PC, de l'auteur d'un commit ou du proprietaire d'un dossier.

Avant fusion, configuration disponible sur
`codex/manager/team-02-local-managers`. Le manager peut lire les fichiers de
cette reference avec `git show origin/codex/manager/team-02-local-managers:<chemin>`
apres fetch; il ne doit pas changer la branche applicative pour charger un profil.

## Utilisation

- « Qu'est-ce que Son a publie et qu'est-ce que ca change pour moi ? »
- « De quoi Kim a besoin de ma part ? »
- « Compare ma branche avec celle de Vincent; y a-t-il une incompatibilite ? »
- « Mets a jour mon suivi avec le commit et les tests que je viens de faire. »
- « Prepare ma prochaine tache sans toucher au perimetre des autres. »

Les chats ne partagent pas leur historique automatiquement. Le suivi partage,
les commits et les PR sont leur memoire commune. Sans push, les autres managers
ne voient pas les changements locaux. Aucun suivi periodique n'est active.

Les managers lisent tous les fichiers de [suivi](../status/README.md), mais
chacun met a jour uniquement celui de son membre. Le [protocole](protocol.md)
precise comment lire les suivis publies sur les branches avant leur fusion.
