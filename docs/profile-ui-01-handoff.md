# PROFILE-UI-01 — point de revue

Responsable UI : Kim. **En revue, implementation en pause** le 31 octobre 2026.
Pas de push, de deploiement ni de fusion. Le manager garde la publication du suivi.
Les livrables de logo et les apercus UI-02/UI-03 restent preserves.

## Commits exacts

- Branche : `codex/kim/profile-ui-01-consented-prefill`.
- Checkout : `C:/Users/Kim/Documents/ChatGPT/Hackathon/work/kim-profile-ui`.
- Base UI-03 : `1825f5e15cf84fc6259004c56cec7185799ae12c`.
- Premier checkpoint UI : `8eefcde`.
- Backend producteur : `33d1d3d03d98a6542ba80b16a8add8ad9eece10d`, consomme une
  fois comme `b4b178f`; preuves producteur `e3cad28dc251dac181a13f682182da5607346d05`
  consommees comme `646b53d`.
- Code consommateur final : **`9afe5d75bfc5ed9d7ed91040180a0e4b02d0a8c1`**.
- Contrat : [profile-01-contract.md](profile-01-contract.md), SHA-256
  `3821c90d1eb21e95c31affd442667340b499b321791d041ce4e8fc8e0fe33df1`.

Les types generes, handlers, stockage et proxy v2 proviennent du commit backend.
Aucun schema, hash, original de formulaire, dependance ou manifeste n'a ete redessine.
Les deux pages serveur LOCAL ne changent que leur affichage d'erreur; leurs gardes
et redirections d'authentification sont conserves.

## Comportement livre

- Profil facultatif : bases, contact, passeport et residence. Sauvegarde explicite,
  annulation locale et confirmation avant rechargement destructif des edits non sauves.
  Snapshot complet sur PUT; anciens nationalite/adresse visibles en lecture seule.
- Apres confirmation de l'exact tuple procedure/formulaire/schema : choix d'utiliser
  le profil ou de continuer manuellement. Pas de chargement de profil a l'ouverture
  du workspace. Confirmation du demandeur avant lecture; confirmation distincte du
  passeport utilise avant selection de ses propositions.
- Source et valeur affichees pour chaque proposition; correction et deselection.
  Telephone, email et combinaison sont des alternatives exclusives pour un seul champ.
  Toutes les reponses deja remplies restent verrouillees. Aucun remplacement implicite.
- Avant Apply : relecture de la session et du profil; liaison compte/session,
  ID/revision du profil, procedure/hash/schema/epoch et revision du brouillon.
  Une sauvegarde dans un autre onglet invalide aussi le plan. Une application constitue
  une seule modification annulable; les questions locales visent les champs manquants.
  Edits/undo du document ne sauvegardent jamais le profil.
- VI/EN pour le parcours LOCAL actuel : login, workspace, profil, consentement,
  propositions, guidage local, Q&A, suivi de preparation, revue, erreurs et confidentialite.
  Seule la preference non sensible `hoso-ui-locale` est stockee sur l'appareil.
  Changer de langue conserve brouillon, edits non sauves, consentement et selections,
  sans reinitialiser leurs composants ni ajouter de champ locale aux requetes.
  Valeurs saisies, sources/citations et reponses du service restent dans leur langue
  d'origine. Les labels locaux des champs ne modifient pas le schema ni les images.
- Q&A explicite sur la procedure selectionnee, historique distinct des reponses
  personnelles. Un envoi sans choix demande son intention. Q&A ne modifie aucun champ;
  son contrat ne garantit pas une reponse liee a l'edition exacte du formulaire.
- Suivi compact des lignes `requirements`, avec texte exact, quantites et associations
  `form_ids` resolues dans la meme reponse. Ce ne sont pas automatiquement des documents
  obligatoires : instructions, alternatives et applicabilite inconnue restent indiquees.
  Le suivi manuel n'etablit jamais la completude du dossier ou une approbation officielle.
  Versions/hashes complets sont dans les details de source; autres documents en lecture
  seule/preparation manuelle. Changer de procedure confirme l'effacement du brouillon.
- Pas de catalogue producteur disponible : etat honnete « catalogue non connecte »,
  distinct de « aucun resultat ». Catalogue de scenarios seulement sur la route marquee.

## Verification observee

- **150 tests frontend hors ligne reussis**; trace
  `output/profile-ui-01/frontend-tests.txt`.
- Apres les derniers ajustements limites de libelles : **10 checks cibles reussis**
  (locale, metadonnees d'historique et exigences); **build final Next/TypeScript reussi**,
  trace `output/profile-ui-01/final-build.txt`.
- **428 tests API reussis**, une alerte de deprecation Starlette/httpx existante.
  Le premier lancement avait un parent de repertoire temporaire absent : 109 erreurs
  de setup, puis creation du parent et relance complete reussie. Pas de correctif API.
- Revue en lecture seule : preservation de la nouvelle saisie apres echec asynchrone,
  email historique en texte compatible v1, consentement, revisions et application atomique.
- Navigateur : sauvegarde/relecture de trois dates ISO (naissance, emission, expiration),
  annulation sans sauvegarde, conflit conservant les edits, optionalite du profil.
  CUA `fill` seul sur date ne declenchait pas toujours l'etat React; les touches natives
  haut/bas ont declenche l'edit et la relecture a confirme les trois valeurs sauvegardees.
- Navigateur : nom deja saisi preserve, passeport initialement non selectionnable,
  choix contact exclusif, correction d'une proposition et deselection de nationalite.
  Sauvegarde explicite du profil dans un second onglet -> ancien plan efface; nouvelle
  lecture -> Apply de huit champs. Le nom tape reste intact et le champ sex non resolu
  est demande ensuite. Undo unique restaure le brouillon avec seulement ce nom.
- Q&A via fixture explicite : revue du brouillon exactement identique avant/apres;
  envoi ambigu bloque en attendant le choix de mode. Apres reponse de champ, les
  messages UI precedents gardent leur traduction et leurs metadonnees de changements.
- Locale : edit de profil non sauve conserve VI -> EN; EN conserve au rechargement et
  a la deconnexion. Consentement passeport, contact choisi et valeur corrigee conserves
  VI -> EN -> VI. Texte source/alternatives inchanges et suivi manuel conserve.
- Isolation navigateur **sequentielle**, apres fin de la revue manager : admin logout,
  reviewer login -> profil vide sans donnees admin; logout puis rechargement de l'ancien
  onglet -> login sans brouillon. La premiere revue concurrente partageait le cookie IAB;
  elle ne constitue pas une preuve d'isolation de deux sessions simultanees.
- Composer : bas du champ a **675.83/720 px** sur desktop; **807.33/844 px** en
  390x844; **431.33/450 px** en 390x450, VI et EN. Pas de debordement horizontal observe
  a 390 px. Simulation de viewport court, pas un test de clavier physique de telephone.

Les garanties zero lecture avant opt-in / recheck de revision sont couvertes par
tests du client et inspection des appels; aucun traceur reseau navigateur exhaustif
n'a ete ajoute. Les scenarios de selection/Q&A sont synthetiques; la sauvegarde et
le prefill utilisent bien l'API authentifiee et SQLite de cet apercu.

Captures ignorees dans `output/profile-ui-01/` : `profile-en.jpg`,
`consent-en-desktop.jpg`, `consent-en-mobile.jpg`, `stale-proposals.jpg`,
`applied-review-en.jpg`, `dossier-en.jpg`, `short-mobile-en.jpg`, `short-mobile-vi.jpg`.

## Apercu laisse actif

- UI : `http://127.0.0.1:3022/login`; API : `http://127.0.0.1:8022`.
- Scenarios hors ligne : `http://127.0.0.1:3022/workspace/scenarios`.
- Comptes de demonstration locaux : `admin / admin`, `reviewer / reviewer-demo`.
- Base isolee, nouvelle a ce checkpoint : `api/tmp/profile-ui-preview.sqlite`, ignoree.
  Donnees fictives uniquement; aucun fichier de session/secret/base n'est commite.
- UI-02 `3018/8018` et UI-03 `3020/8020` n'ont pas ete arretes ni modifies.
- Lancement API : Python deja installe dans le venv du checkpoint AUTH; script
  `api/scripts/run_local_checkpoint.py --database <chemin-absolu-isole> --origin
  http://127.0.0.1:3022 --port 8022 --demo-seed`, `OPENAI_API_KEY` vide, sans key-file.
- Next : variables `HOSO_AUTH_PROVIDER=local`, `HOSO_PUBLIC_ORIGIN=http://127.0.0.1:3022`,
  `HOSO_API_URL=http://127.0.0.1:8022`, `HOSO_VINCENT_API_URL` vide;
  `node node_modules/next/dist/bin/next start --hostname 127.0.0.1 --port 3022` depuis web.

## Limites et prochain relais

Aucun appel modele/provider/Vincent vivant, migration PostgreSQL, deploiement public,
integration vocale ACCESS-01, approbation juridique ou PDF officiel rempli n'est prouve.
Les originaux et le verrou de telechargement sont preserves. La copie du profil est
deterministe, mais les messages tapes peuvent aller a l'IA/au retrieval une fois les
services connectes; l'information de confidentialite le dit explicitement.

Pas de promesse de chiffrement au repos, certification, suppression ou protection
universelle. Les ecrans Clerk historiques et leurs anciens demos hors parcours LOCAL
ne sont pas convertis par ce checkpoint. Pas de traduction automatique des reponses
du backend, donc aucune preuve d'un modele bilingue vivant.

Catalogue absent; pas de classification fiable des lignes en types de pieces ou
groupes d'alternatives stables. L'affichage des exigences ne calcule pas une decision
juridique d'applicabilite ou de completude. Le suivi de preparation et les brouillons
restent en memoire de page, distincts du profil sauvegarde.

Prochain relais : revue humaine de ce point exact par Kim/manager; aucune nouvelle
implementation ni publication automatique lancee apres ce compte rendu.
