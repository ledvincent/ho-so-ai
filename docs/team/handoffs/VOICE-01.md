# VOICE-01 — livraison du socle public de conversation

Responsable : Son

Tache : VOICE-01 — parcours vocal vietnamien dans l'application navigateur.

Etat : En cours. Le socle public est pret pour revue locale. Le lookup de donnees
revues et la checklist ne sont pas connectes; les criteres complets de VOICE-01 ne
sont donc pas remplis. Aucune fusion ni integration voix-vers-rapport verifiee.

Branche : `codex/son/voice-01-browser-conversation`, partie de `origin/main`
actualise au commit `97e8461`. La configuration du manager est deja fusionnee
dans cette base, observe apres `git fetch origin` le 31 octobre 2026.

## Livraison

- Composant autonome sous `son/voice/`, sans modifier les prototypes locaux de
  collecte ni la configuration Python racine : FastAPI et page responsive.
- Saisie vietnamienne, reconnaissance vocale navigateur avec verification du
  texte avant envoi, lecture des reponses optionnelle, repli vers le texte.
- Routage deterministe inscription/renouvellement, clarification des ambiguites,
  refus hors perimetre. Aucun LLM ou fournisseur Realtime branche a ce stade.
- Sessions publiques anonymes en memoire, cookie HttpOnly/SameSite strict,
  expiration absolue de 10 minutes, fin/reinitialisation et limites de capacite.
  Aucune conservation des transcriptions dans le stockage de session.
- Aucun outil personnel. Une phrase d'accord n'autorise pas l'acces au dossier.
  Ce socle ne livre pas AUTH-01, CONSENT-01, ACCESS-01 ou SECURITY-01.
- Arret explicite sur `lookup_pending`, sans checklist, frais, formulaire,
  donnees synthetiques presentees comme vraies, ni choix automatique de CT01.

## Verification observee

Environnement : Windows, Python 3.13.15, dependances Python epinglees dans
`son/voice/requirements.lock.txt`, Playwright 1.62.1 avec Edge headless installe.
Python 3.12 est declare compatible mais n'a pas ete teste dans cette livraison.

```powershell
son/voice/.venv/Scripts/python.exe -m unittest discover -s son/voice/tests -v
```

Resultat : 20 tests passes. Intention, ambiguite, absence/hors perimetre,
absence de lookup revu, refus des demandes personnelles, sessions independantes,
expiration, fin/reinitialisation, validation sans echo du contenu, taille du
corps, origine des mutations, bornes et transition concurrente testees.
Un avertissement de deprecation Starlette concernant son adaptateur httpx de test
est present; il n'a pas fait echouer les tests.

Serveur local demarre avec :

```powershell
son/voice/.venv/Scripts/python.exe -m uvicorn voice_app.app:app --host 127.0.0.1 --port 8000 --no-access-log
```

```powershell
$env:VOICE_BROWSER_CHANNEL='msedge'
node son/voice/tests/browser_smoke.cjs
```

Resultat navigateur : passe. Clarification, selection inscription/renouvellement,
refus personnel, reinitialisation, texte HTML echappe, repli sans reconnaissance,
format 390 px sans debordement horizontal et absence de localStorage. Adaptateur
micro teste avec reconnaissance **simulee**, controle du texte avant envoi et
refus micro simule. Aucun resultat de reconnaissance acoustique reelle revendique.
Pour cette execution, `NODE_PATH` pointait vers Playwright fourni par le runtime
Codex; installation autonome documentee dans `son/voice/README.md`.

Captures locales inspectees visuellement : `work/voice-qa/desktop.png` et
`work/voice-qa/mobile.png`, non committes. Aucun chevauchement observe. Leur
format mobile n'etablit pas un test sur telephone physique.

`git diff --cached --check` : passe pour le code avant son commit. Fichiers
selectionnes explicitement; aucun fichier du prototype de Vincent ajoute.

## Integration et demandes aux responsables

**Vincent — CONTRACT-01 / DATA-02** : besoin du moyen de lookup, d'une version de
record exacte, d'un statut de revue lie aux hashes, de la checklist avec conditions
et provenance, et des comportements no-result/unreviewed/error. Son adaptera le
consommateur a la proposition de Vincent; aucun schema producteur impose ici.
Le champ `candidate_code` du dialogue est seulement une intention, pas la preuve
d'un resultat officiel revu.

**Kim — integration UI et identite** : page autonome a integrer/remplacer dans
l'application. Convenir du fournisseur et du transport d'identite avec Son avant
la liaison ACCESS-01. Ce cookie public ne vaut ni connexion ni autorisation.
Le rapport reste a produire par Kim depuis exactement le record/version/checklist
que consommera la voix; le socle actuel ne produit aucun objet de rapport.

Ordre propose : revoir ce socle -> adapter le lookup au contrat de Vincent ->
brancher un record humainement revu -> integrer l'application de Kim et verifier
les identites/autorisations -> tester voix et rapport sur le meme record/version.
Les consommateurs existants restent inchanges; aucune migration de contrat
producteur dans cette livraison. Une fusion ne suffit pas a lever ces dependances.

## Limites et prochaine action

Reconnaissance/restitution sonore reelles, navigateur sur telephone physique,
HTTPS heberge, IAM/CSRF de l'application, autorisation des outils personnels,
revocation, rapport/livraison, recuperation semantique sur les donnees de Vincent
et integration complete non testes/non implementes ici. La reconnaissance du
navigateur peut utiliser son service distant : opt-in micro explicite et donnees
de demo uniquement; retention fournisseur non verifiee.

Prochaine action : Vincent fournit CONTRACT-01; Kim et Son conviennent de la
liaison d'identite. Son connecte ensuite les adaptateurs de recherche et d'acces.
En attendant, l'essai local permet de valider l'ergonomie et les phrases vietnamiennes.

Git : code `a28d937ccbba48424a793d3555a5d13bd71326fb`; pousse non; PR aucune.
Compte rendu et tableau ajoutes dans un commit documentaire de la meme tache.
Aucun message envoye aux membres ou au manager; aucun choix de fusion effectue.
