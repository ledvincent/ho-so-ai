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

### Perimetre UI et raccordement pour Kim

Clarification de Son le 31 octobre 2026 : **Kim realise toute l'interface produit**,
y compris l'ecran voix et les controles micro. Son garde backend, dialogue,
recherche, sessions et autorisation des outils. La page statique locale est un
banc d'essai technique; aucun nouveau design produit n'y sera developpe. Kim
n'a pas a la reproduire ou l'integrer telle quelle.

Comportement actuel du backend (description de l'existant, pas un accord deja
valide avec Kim, ni le contrat de procedures de Vincent) :

| Appel | Entree / resultat actuel | Point d'attention UI |
| --- | --- | --- |
| `POST /api/voice/session` | Sans corps; reponse `reply`, `state`, `choices`, `expires_in`; cookie HttpOnly | Demarrer le dialogue public, ne pas assimiler le cookie a une connexion applicative |
| `POST /api/voice/turn` | JSON `{ "text": "besoin synthetique" }`, maximum 600 caracteres | Envoyer le texte apres reconnaissance; afficher `reply`, `choices`, `state` |
| Reponse de tour | `candidate_code`, `reviewed_lookup_available` en plus des champs de dialogue | Le code est une intention; aucune checklist disponible, `reviewed_lookup_available` reste faux |
| `DELETE /api/voice/session` | Fin et invalidation de la session publique | Arreter micro et lecture cote navigateur, effacer l'affichage local |

Etats existants : `welcome`, `clarify`, `lookup_pending`, `not_found`,
`not_covered`, `personal_access_unavailable`, `ended`. Erreurs : 401 session
publique absente/expiree (pas un diagnostic de connexion utilisateur), 403 origine
refusee, 413 contenu trop volumineux, 415 JSON requis, 422 entree invalide,
429 limite de tours, 503 capacite atteinte. Les corps d'erreur ne renvoient pas
la transcription. Un exemple de `choices` comporte `label` et `text`.

Points a convenir avant raccordement avec Kim :

- Montage sous la meme origine via le serveur/proxy de l'application, ou transport
  interservices explicite. L'API locale ne fournit pas de CORS entre deux serveurs
  frontend/backend : ne pas resoudre cela par une origine universelle.
- Choix et disponibilite du fournisseur de reconnaissance/restitution audio. Le
  Web Speech du banc d'essai est un adaptateur provisoire, pas un choix impose.
- Mapping de la session applicative authentifiee vers la conversation cote serveur
  et decisions d'accord pour ACCESS-01; jamais un `user_id` libre dicte au modele.
- Branchement du meme record/version/checklist revu vers voix et rapport apres
  livraison de Vincent. Ne pas convertir `candidate_code` en validation de source.

Ordre de raccordement propose : Kim realise ses composants UI -> Son et Kim
valident le transport et les etats -> connexion au backend -> essais communs
micro/expiration/erreurs -> lookup revu et rapport. Aucun changement de fichiers
appartenant a Kim effectue; accord et integration non verifies.

**Vincent — CONTRACT-01 / DATA-02** : besoin du moyen de lookup, d'une version de
record exacte, d'un statut de revue lie aux hashes, de la checklist avec conditions
et provenance, et des comportements no-result/unreviewed/error. Son adaptera le
consommateur a la proposition de Vincent; aucun schema producteur impose ici.
Le champ `candidate_code` du dialogue est seulement une intention, pas la preuve
d'un resultat officiel revu.

**Kim — integration UI et identite** : interface produit a realiser par Kim en
consommant le backend de Son; page locale uniquement pour les tests. Convenir du
fournisseur et du transport d'identite avec Son avant
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

Suivi de la clarification UI : documentation seule, `git diff --cached --check`
verifie avant commit; pas de nouveau test applicatif necessaire. Les 20 tests et
le scenario navigateur ci-dessus restent la derniere preuve de comportement,
sans nouvelle revendication d'integration. Prochaine action de coordination :
faire valider les points de raccordement par Kim, puis Son adaptera le backend
au transport retenu. Publication toujours non effectuee.
