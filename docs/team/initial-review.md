# Premier point du manager

Date : 31 octobre 2026, Asia/Saigon. Observation du checkout local uniquement.

Note ulterieure : ce point est historique. Le prototype de collecte, ses tests
et sa CI ont ensuite ete retires de la branche du manager a la demande de Son.
Ces fichiers sont conserves localement; Vincent gere leur implementation et le
contrat de donnees. Les propositions techniques ci-dessous ne lui sont pas imposees.

## Resultats verifies

- Remote configure : `https://github.com/ledvincent/ho-so-ai.git`.
- Branche locale : `main`. Refs connues : `origin/main`, non actualisees pendant
  cette installation. Etat reel des PR et branches distantes non verifie.
- Collecteur Python et fixtures presents. Commande executee avec succes :
  `.\.venv\Scripts\python.exe -m unittest discover -s tests -v` : 5 tests passes.
- `git diff --check` sans erreur de whitespace sur le diff suivi.
- Aucun composant voix, recherche applicative ou rapport observe dans les fichiers
  du checkout. Cela ne prouve pas leur absence sur les machines des membres.
- README deja modifie et plusieurs fichiers applicatifs non suivis avant
  installation du manager. Aucune fusion, aucun commit ni push effectue.

## Prochaines actions conseillees

- Vincent : proposer un premier enregistrement structure et sa provenance,
  puis faire valider la source exacte avant toute consommation reelle.
- Son : choisir le point d'entree voix et definir avec Vincent le lookup;
  commencer avec une fixture synthetique clairement identifiee.
- Kim : convenir avec Son des references de version du rapport et construire
  l'affichage sur la meme fixture; garder CT01 desactive tant que non valide.
- Tous : valider `contracts.md`, declarer leurs branches et chemins touches
  dans `board.md`, puis choisir l'ordre d'integration.

## Limites de l'installation

Le workflow de tests et le modele de PR sont prepares localement. La CI n'a pas
ete executee sur GitHub; aucune protection de branche ni integration de revue
automatique Codex n'a ete configuree. Les tests actuels couvrent la collecte,
pas un parcours voix -> rapport. Le manager fonctionne a la demande dans ce chat.

References de configuration consultees :
- [Revue Codex sur GitHub](https://learn.chatgpt.com/docs/third-party/github)
- [Action checkout](https://github.com/actions/checkout)
- [Action setup-python](https://github.com/actions/setup-python)
