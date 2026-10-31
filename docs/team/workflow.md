# Convention commune pour les agents

Cette convention s'applique aux agents de Son, Vincent, Kim et au manager.
Elle definit la facon de travailler et de livrer; le schema des donnees reste
sous la responsabilite de Vincent.

## 1. Un responsable par perimetre

| Agent | Travail principal | Coordination necessaire |
| --- | --- | --- |
| Son | Recherche, voix, sessions de conversation et serveur d'autorisation de l'agent | Consommer le contrat de Vincent; verifier avec Kim identite, accord et acces au dossier |
| Vincent | Collecte, donnees, validation, contrat commun et tests associes | Documenter le format et fournir des exemples a Son et Kim |
| Kim | Connexion, dossier et controles proprietaire, ecran d'accord, formulaires, rapport et envoi | Transmettre a Son une decision authentifiee; consommer les memes donnees/version que la voix |
| Manager | Suivi, revue, compatibilite et corrections demandees | Ne pas implementer la partie donnees a la place de Vincent |

L'agent modifie les fichiers necessaires a sa tache. S'il faut intervenir dans
le perimetre d'un autre membre, il decrit le besoin et coordonne le changement
avec le responsable avant de l'implementer. Il ne reformate pas tout le depot.
Les changements de dependances et de configuration communes sont annonces dans
la PR. Un nom de dossier ne constitue pas une preuve de responsabilite.

## 2. Demarrer une tache

1. Lire `AGENTS.md`, ce document, le tableau, les decisions et le contrat disponible.
2. Examiner `git status --short`. Ne pas committer les fichiers locaux d'un autre
   travail. Ne pas effacer, stasher ou deplacer ce travail automatiquement.
3. Faire `git fetch origin` si l'acces le permet. Indiquer toute impossibilite.
4. Pour une nouvelle tache, partir de `origin/main` actualise et utiliser une
   branche distincte. Ne pas changer de branche avec un travail local incompatible.
   Pour une tache existante, reprendre sa branche au lieu d'en recreer une.
5. Declarer ID, responsable, branche, chemins touches et dependances dans le tableau.
   Pour un nouvel ID, suivre le prefixe du composant et verifier qu'il est libre.

Format des branches : `codex/<responsable>/<id-en-minuscules>-<sujet>`.
Responsables : `son`, `vincent`, `kim`, `manager`.

Exemples :

```text
codex/son/voice-01-conversation
codex/vincent/contract-01-procedure-format
codex/kim/report-01-mobile-report
codex/manager/team-01-agent-workflow
```

Une tache, une branche, une PR. La branche historique `codex/hackathon-manager`
est conservee pour la configuration initiale; appliquer ce format aux nouvelles.
Tant que cette configuration n'est pas fusionnee dans main, chaque membre doit
la consulter sur cette branche. Ne pas demarrer une tache applicative sur la
branche du manager pour recuperer les consignes.

## 3. Developper et verifier

- Faire de petits changements coherents avec la tache, sans melanger du nettoyage
  independant ou les travaux d'un autre membre.
- Suivre le style existant : identifiants et messages de commit en anglais,
  points de suivi en francais. Ne pas convertir le style de tout le projet.
- Avant un changement de contrat, Vincent documente les consommateurs touches et
  l'adaptation necessaire. Son et Kim ne creent pas un format concurrent.
- Si le contrat manque, signaler la dependance. Une fixture provisoire doit etre
  marquee synthetique et ne devient pas le contrat par defaut.
- Executer les controles adaptes au changement et noter commande et resultat.
  Si un test ne peut pas tourner, donner la raison; ne pas le declarer reussi.
  Une modification documentaire n'exige pas de nouveau test applicatif.
- Pour une integration, verifier aussi que voix et rapport utilisent les memes
  donnees/version. Les tests du collecteur seuls ne suffisent pas.

## 4. Faire les commits

Format obligatoire du titre : `<type>(<scope>): <action courte en anglais>`.

| Type | Utilisation |
| --- | --- |
| `feat` | Nouvelle fonctionnalite |
| `fix` | Correction d'un probleme |
| `docs` | Documentation uniquement |
| `test` | Ajout ou adaptation de tests uniquement |
| `refactor` | Restructuration sans changement de comportement attendu |
| `chore` | Configuration et maintenance |

Scopes communs : `data`, `contract`, `search`, `voice`, `forms`, `report`,
`delivery`, `auth`, `access`, `security`, `team`, `ci`. Choisir le scope principal; separer les travaux sans lien.
Pour un changement incompatible, ajouter `!` avant `:` et expliquer la migration
dans le corps du commit et la PR.

```text
feat(voice): add procedure intent detection
feat(contract): define reviewed procedure format
fix(report): preserve procedure record version
docs(team): clarify agent workflow
```

Un commit represente un changement explicable seul et inclut ses tests pertinents.
Avant chaque commit :

1. Selectionner explicitement les fichiers de la tache avec `git add -- <chemins>`.
   Ne pas utiliser `git add .` ou `git add -A`.
2. Examiner `git diff --cached` et `git diff --cached --check` : verifier contenu,
   chemins, secrets, fichiers generes et travail des autres avant de committer.
3. Utiliser l'identite Git du membre concerne. Chaque membre configure son propre
   nom et e-mail; ne pas copier ceux de Son sur les autres ordinateurs.
4. Inclure l'ID dans le corps du commit, par exemple `Task: VOICE-01`.

Ne pas ajouter `.env`, identifiants, donnees personnelles, captures locales,
environnements virtuels ou fichiers de travail. Ne pas publier un prototype
appartenant a un autre membre sans sa demande.

## 5. Publier et proposer une fusion

- Pousser la branche de la tache quand la publication est autorisee par le membre.
- Utiliser le meme titre que le format des commits pour la PR et remplir
  `.github/pull_request_template.md`.
- Indiquer responsable, ID, resultat, consommateurs touches, contrat/version,
  dependances, controles et limites. Lier les PR dont celle-ci depend.
- Si l'acces main a evolue, comparer a `origin/main` actualise. Traiter les conflits
  sur la branche de travail; ne pas choisir aveuglement une version de fichier.
  Refaire les controles concernes apres resolution ou adaptation.
- Ne pas pousser directement sur main, fusionner, forcer un push ou reecrire
  l'historique partage de sa propre initiative. Un humain valide la fusion.

## 6. Compte rendu commun apres chaque livraison

```text
Responsable : Son | Vincent | Kim | Manager
Tache : ID — objectif
Etat : A faire | En cours | Bloque | En revue | Termine
Branche : nom
Livraison : comportement obtenu et fichiers principaux
Verification : commandes, resultats et limites
Integration : contrat/version, membres concernes, dependances ou aucune
Git : hash du commit; pousse oui/non; lien PR si creee
Prochaine action : action concrete et responsable
```

Reporter les faits utiles dans le tableau. `En revue` signifie pret pour une
revue; `Termine` signifie criteres verifies et fusion confirmee. Un commit ou un
push seul ne signifie pas que la tache est terminee. Le manager verifie ces
conventions lors des revues; aucun hook de blocage automatique n'est installe.

## Instruction a donner a chaque agent

> Tu es l'agent de [Son/Vincent/Kim]. Lis AGENTS.md et docs/team/workflow.md.
> Travaille sur [ID et objectif] dans mon perimetre. Respecte le format commun
> des branches, commits, PR et comptes rendus. Preserve les changements locaux
> hors tache. Signale les dependances avec les autres membres et laisse les
> fusions a validation humaine.
