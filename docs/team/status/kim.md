# Suivi — Kim

Responsable : Kim
Derniere mise a jour : 31 octobre 2026 (Asia/Saigon), avant le commit du socle APP-01
Tache : APP-01 — socle et contrat applicatif; FORM-02 — formulaire et PDF synthetique; preparation AUTH-01
Etat : APP-01 et FORM-02 en cours; AUTH-01 reste a implementer pour le dossier persistant
Branche / PR : `feature/kim-form`, conservee a la demande explicite de Kim; aucune PR applicative declaree dans ce point
Livraison : socle Next.js/TypeScript/Tailwind, FastAPI/Pydantic, configuration PostgreSQL et raccord Clerk prepares localement; contrat applicatif `app.v1`; interface manuelle ou copie du profil et rendu synthetique separes du futur portail
Verification : resultats et limites detailles ci-dessous; verification frontend finale en cours
Preuves : `513d01b`, `60cb3be`, `docs/application-contract.md`, `docs/shared-scaffold.md`, `docs/team/portal-handoff.md`, `web/`, `api/hoso_api/`; le commit applicatif n'existe pas encore dans ce point
Publication / integration : consignes de `main` integrees localement; socle APP-01 et changement FORM-02 non encore committes/publies dans ce point; aucune connexion Clerk reelle ou integration voix declaree
Dependances avec Son : convenir du transport de session, des decisions d'accord et de la revocation; interoperabilite Clerk non encore verifiee
Dependances avec Vincent : consommer son futur contrat de procedures et ses sources/formulaires revus; aucun schema concurrent ni choix automatique d'edition CT01
Blocages : cles/instance Clerk non configurees ici; Docker indisponible; role PostgreSQL d'execution et migration du profil a decider; build frontend final en cours
Prochaine action : terminer les controles combines, committer APP-01 sur la branche existante, fournir son SHA exact et creer le worktree Clerk propre avant le commit d'interface FORM-02

## Faits observes localement

- Le checkout reste sur `feature/kim-form`. `513d01b` est le commit local
  `chore(team): integrate local manager profiles`. L'ascendance de `60cb3be`
  vers HEAD a ete verifiee avec `git merge-base --is-ancestor 60cb3be HEAD`
  (code 0). Ces commits portent les consignes communes, pas le socle applicatif.
- Les consignes actuelles demandent aux managers locaux d'ecrire leur seul suivi
  personnel. Le tableau global et les decisions communes restent au manager commun;
  les choix applicatifs ci-dessous sont donc rapportes ici, sans les imposer a l'equipe.
- Les sources du socle definissent `app.v1` pour identite, profil et requetes de
  formulaire. Les champs et limites du profil TypeScript sont generes depuis le
  modele Python dans `web/lib/profile.generated.ts`; le controle de derive est
  documente dans `docs/application-contract.md`.
- GET/PUT `/v1/profile` authentifient puis renvoient 501. Aucun profil n'est
  sauvegarde par ce socle. Les identifiants proprietaire ne proviennent pas du
  navigateur. Stockage, controles proprietaire et preuves entre comptes A/B sont
  du travail AUTH-01, pas un resultat acquis.
- Le rendu disponible est un modele synthetique, active explicitement par
  configuration. Apercu PNG et PDF utilisent le meme moteur; la version de modele,
  le refus de debordement et l'accord avant telechargement sont controles. Aucun
  modele officiel CT01/NA5 n'est approuve ou livre par ce seam.

## Choix de Kim et limites d'integration

- Kim confirme dans ce chat Next.js/TypeScript/Tailwind, FastAPI/Pydantic,
  PostgreSQL et Clerk. Ce choix concerne son application; l'accord technique et
  l'interoperabilite avec Son ne sont pas encore verifies.
- La saisie manuelle et la copie du profil restent distinctes. Les corrections
  locales d'un formulaire ne modifient pas automatiquement le profil sauvegarde.
  Une route 501 ou une erreur ne doit jamais produire un message de sauvegarde reussie.
- Vincent garde le contrat de donnees officielles, la collecte et la revue des
  sources. `app.v1` ne remplace pas ce contrat et ne definit pas les sessions
  vocales ou le serveur d'autorisation de Son.
- Le portail Clerk est prevu sur `codex/kim/auth-01-clerk-portal`, dans un nouveau
  worktree propre cree depuis le commit exact APP-01 une fois celui-ci disponible.
  Le SHA reel sera fourni dans le compte rendu et compare a HEAD avant demarrage;
  aucun hash futur n'est invente dans ce suivi.
- Le brouillon Auth0 non publie de `.worktrees/kim-portal` reste intact et n'est
  pas adopte. Le nouveau portail etend le package `web` et les interfaces FastAPI
  communes; il ne cree ni seconde application Next ni schema de profil concurrent.
  Le handoff precise les chemins autorises et les adaptations a coordonner avec
  le responsable du socle.

## Verification : reproduite et declaree

| Verification | Observation / limite |
| --- | --- |
| Ascendance Git et branche | Reproduit dans ce point : `feature/kim-form`, HEAD `513d01b`, ascendance `60cb3be` confirmee |
| Lecteur de corps borne des proxies | 6 tests reproduits avec Node 24 et son chargeur TypeScript : corps sans Content-Length, longueur fausse, limite 8192 octets, Unicode coupe entre chunks, annulation et erreurs sans donnees; la commande normale `pnpm test` reste a confirmer apres installation |
| API et PDF | Resultat declare par les agents d'implementation : 62 tests API reussis et revue visuelle du PDF synthetique; non reproduits dans ce point de suivi et sans valeur d'approbation officielle |
| Frontend | Dependances installees selon le responsable du socle; correction d'une incompatibilite Clerk en cours de validation; resultats finaux `pnpm typecheck`, `pnpm test` et `pnpm build` a consigner apres execution |
| Contrat de profil genere | Sources Python/TypeScript presentes; commande de controle `python scripts/export_profile_contract.py --check` a executer depuis l'environnement API selon le contrat applicatif |
| Clerk, PostgreSQL, voix -> rapport | Non verifies : pas de resultat de connexion reelle, de migration/base demarree, de controle SQL/RLS ou de parcours commun de bout en bout |

Une verification locale de JWT ne garantit pas la revocation immediate a la
deconnexion. La future implementation doit resoudre ce point avec Son avant toute
affirmation contraire. Les donnees des tests et de la demonstration restent synthetiques.

## Historique utile

- Le suivi initialise dans `main` etait non renseigne; cela ne signifiait pas
  absence de travail de Kim.
- `60cb3be` apporte les profils et suivis des managers dans `main`;
  `513d01b` les integre au checkout local de Kim en conservant sa branche.
- Ce point prepare APP-01, FORM-02 et la reprise AUTH-01. Un suivi documentaire
  ulterieur pourra citer les hashes applicatifs effectivement crees, puis distinguer
  commit local, publication sur branche et fusion dans `main`.
