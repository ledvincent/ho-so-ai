# AUTH-01 — reprise du portail Clerk

Statut : perimetre prepare, implementation du portail et persistance a realiser.
Le socle n'etablit ni connexion Clerk reelle, ni dossier sauvegarde, ni isolement
PostgreSQL verifie. Les cles Clerk locales restent a configurer.

## Base et branche

La branche de formulaires reste `feature/kim-form`, a la demande explicite de Kim.
La nouvelle branche du portail sera `codex/kim/auth-01-clerk-portal`, dans un
worktree propre cree depuis le commit exact du socle partage APP-01. Le responsable
du socle fournira le SHA verifie dans son compte rendu apres commit. Avant toute
modification, comparer `git rev-parse HEAD` a cette base fournie et verifier
`git status --short`. Ne pas partir du futur commit d'interface FORM-02 par hasard.

Le worktree existant `.worktrees/kim-portal`, branche `codex/kim-portal`, contient
un brouillon Auth0 non publie sous `apps/portal/` et `proposals/portal/`. Il reste
intact. Son package Next, sa proposition SQL et ses choix Auth0 ne sont pas integres
au socle Clerk. Ne pas effacer, deplacer, stasher ou recuperer ce travail automatiquement.

## Lire avant de commencer

- `AGENTS.md`, `docs/team/workflow.md`, le tableau et les decisions.
- `docs/application-contract.md` : contrat applicatif `app.v1` et etats 501 actuels.
- `docs/clerk-configuration.md` : manifeste commun sans secrets; instance et issuer encore non renseignes.
- `docs/team/identity-and-security.md` : repartition Kim / Son.
- `docs/team/contracts.md` : Vincent garde la conception du contrat des procedures.
- `web/lib/contracts.ts`, `web/lib/server/clerk.ts`, `web/app/api/profile/route.ts`,
  `api/hoso_api/{auth,profile,settings}.py` : interfaces reellement livrees.

## Perimetre d'ecriture

| Chemins | Responsabilite AUTH-01 |
| --- | --- |
| `web/app/portal/**` | Dossier connecte, navigation, etats vides/erreur et preferences du portail |
| `web/components/portal/**` | Composants du portail dans l'application Next existante |
| `api/hoso_api/portal/**` | Depot et services applicatifs avec controles proprietaire cote serveur |
| Tests limites au portail | Preuves d'authentification, de concurrence et d'isolement |

Le responsable du socle garde l'authentification partagee, `api/hoso_api/profile.py`,
les types/proxies communs, l'enregistrement des routes, les manifests, lockfiles et
la configuration racine. Signaler les adaptations necessaires et convenir d'un ordre
d'integration; ne pas creer des routes `/v1/profile` concurrentes. Le depot du portail
peut etre injecte dans les routes existantes lors de ce changement coordonne.

Reutiliser Clerk, FastAPI et le package `web` existant. Ne pas ajouter Auth0, un
second package Next, un schema de profil concurrent, un acces navigateur direct a
PostgreSQL ou un identifiant proprietaire fourni par le client. Le contrat officiel
des procedures et la collecte restent a Vincent; sessions vocales et autorisations
des outils restent a Son. Leurs composants non publies ne sont pas reputes disponibles.

## Travail concret attendu

1. Decider avec le responsable du socle le role PostgreSQL d'execution, le stockage
   et la migration applicative. Le role proprietaire de provisioning du compose
   ne constitue pas un role d'execution valide pour les donnees personnelles.
   Aucune migration ni garantie RLS n'est actuellement livree.
2. Implementer le depot de profil et les controles proprietaire, en reutilisant le
   sujet Clerk verifie et le contrat `app.v1`. Ne pas placer les champs legaux du
   profil dans les metadonnees Clerk. Conserver la distinction entre preference
   d'affichage, profil sauvegarde et copie editable d'un formulaire.
3. Coordonner le branchement des routes existantes : GET sans dossier -> 404;
   creation avec revision attendue 0; reponse avec revision positive; modification
   conditionnelle atomique; conflit -> 409. Aujourd'hui les deux routes renvoient 501.
4. Construire l'interface dans `/portal`, puis le prefill via `/api/profile`.
   Les modifications du formulaire ne sauvegardent pas automatiquement le profil.
   Un echec de sauvegarde reste visible, sans succes simule ni repli sur des donnees
   inventees.
5. Ajouter sessions et documents seulement apres accord sur leurs producteurs,
   identifiants, revisions et droits. Ne pas inventer de lien actif vers un document
   inexistant, ni de DTO officiel a la place de Vincent. Le formulaire synthetique
   est disponible a `/forms/demo`; il ne cree pas encore de document persistant.
6. Documenter les exigences de fin de session/revocation avec Son. La verification
   locale des JWT du socle ne garantit pas la revocation immediate d'un jeton.

## Preuves avant revue

- Non connecte ou jeton altere : acces personnel refuse par le serveur.
- Comptes synthetiques A/B : aucune lecture ou modification croisee, y compris
  l'appel direct au depot/API et les identifiants injectes dans un corps.
- Creation en concurrence et mauvaise revision : aucun ecrasement silencieux.
- Prefill puis correction du formulaire : le profil sauvegarde ne change pas.
- Erreurs 401/404/409/501/503 et configuration absente : interface explicite,
  aucune fausse sauvegarde; contexte de session remis a zero a la deconnexion.
- Connexion, lecture et sauvegarde locales avec un vrai tenant Clerk seulement
  apres configuration; distinguer ces resultats des tests a identites synthetiques.

Les tests restent sans appels externes. Les futurs tests PostgreSQL doivent nommer
leur base et leur role restreint et rester isoles du travail des autres. Fournir
commandes et resultats observes; ne pas transformer des criteres en preuves.

Compte rendu commun : responsable, AUTH-01, etat, branche, chemins, base exacte,
contrat `app.v1`, tests et limites, dependances avec Son/Vincent, commit et prochaine
action. Aucune fusion, publication, message a l'equipe ou approbation de formulaire
officiel n'est compris dans cette reprise.
