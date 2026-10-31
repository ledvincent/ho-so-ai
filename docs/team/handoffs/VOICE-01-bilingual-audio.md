# VOICE-01 — suite bilingue et audio controle

Responsable : Son

Tache : VOICE-01 — dialogue et agent vocal vietnamien/anglais, dans le perimetre
confirme par Son le 31 octobre 2026.

Etat : En cours. Extension locale prete pour revue; essai fournisseur reel,
lookup de donnees revues, identite et integration voix-vers-rapport non verifies.

Branche : `codex/son/voice-01-browser-conversation`, continuation de la tache.
`git fetch origin` execute avant cette extension; pas de nouvelle fusion.

## Livraison

- Dialogue et choix VI/EN; langue par session, changement par tour sans perte
  d'intention. Distinction inscription/renouvellement, ambiguite, refus personnel,
  hors perimetre et absence de resultat dans les deux langues.
- API audio OpenAI optionnelle, desactivee par defaut : transcription -> texte a
  confirmer par l'utilisateur -> dialogue deterministe -> lecture de la reponse
  serveur. Pas de parole libre issue d'un LLM et pas de faits officiels traduits.
- Adaptateur navigateur sans UI, `VoiceAudioClient`, pour Kim : enregistrement,
  arret/interruption de lecture, nettoyage des pistes micro et URLs audio,
  confirmation de transcription, fin de session. Aucun HTML/CSS produit modifie.
- Limites locales : enregistrement client 20 s; requete audio 2 MiB; sortie 4 MiB;
  timeout amont 20 s; 20 tentatives audio/session et une operation en vol.
- Le serveur refuse un texte de synthese fourni par le client; seul son dernier
  message predefini peut etre lu. Expiration/fin de session pendant une requete
  audio invalide la reponse. Les erreurs ne renvoient pas les details fournisseur.
- Ni audio ni transcription persistes par ce composant. Cle serveur uniquement;
  pas de jeton ou cle transmis au navigateur. Opt-in audio technique distinct de
  l'autorisation d'acces au dossier. Pas de nouveaux droits personnels.

Fichiers principaux : `son/voice/src/voice_app/languages.py`, `dialogue.py`,
`sessions.py`, `speech.py`, `app.py`, `static/audio-client.js`; tests et README du
composant. Extra Python `audio` ajoute, dependance httpx deja epinglee dans le lock
de tests existant; aucune dependance/configuration racine de collecte modifiee.

## Verification

Windows / Python 3.13.15; Python 3.12 non execute ici. Documentation OpenAI lue :
[pipelines voix](https://developers.openai.com/api/docs/guides/voice-agents),
[transcription](https://developers.openai.com/api/docs/guides/speech-to-text),
[synthese](https://developers.openai.com/api/docs/guides/text-to-speech).

```powershell
son/voice/.venv/Scripts/python.exe -m unittest discover -s son/voice/tests -v
```

Resultat : **34 tests passes**. Inclus : regressions VI, intentions EN, negation,
cas hors perimetre, langues invalides, changement VI/EN conservant l'intention,
opt-in/session avant appel audio, signature/taille, budget/concurrence audio,
transcription sans execution automatique, lecture du seul message serveur,
erreurs fournisseur filtrees, rejet des sorties non audio/trop grandes, fin de
session en vol. Requetes HTTP fournisseur simulees via `httpx.MockTransport`.
L'avertissement de deprecation Starlette/httpx reste non bloquant.

Serveur de test lance selon le README; avec Playwright 1.62.1 fourni par le runtime,
`NODE_PATH` configure vers ses modules et Edge installe :

```powershell
$env:VOICE_BROWSER_CHANNEL='msedge'
node son/voice/tests/browser_smoke.cjs
node son/voice/tests/audio_client_smoke.cjs
```

Resultat : **deux suites passees**. La premiere couvre la regression du banc
d'essai VI et le format mobile. La seconde utilise un faux micro/MediaRecorder,
un faux lecteur et des routes HTTP simulees : session EN, opt-in requis,
transcription recue sans tour automatique, tour confirme vers `1.002755`,
interruption de lecture, fermeture des pistes et refus de recording apres fin.
Aucun test acoustique, appel OpenAI live, frais ou validation de latence reclame.

`git diff --cached --check` passe avant commit; selection explicite des chemins.

## Integration / migration

**Producteur Son -> consommateur Kim :** les routes existantes restent valides.
Ajout de `?language=en|vi` a la creation (defaut `vi`), de `language` optionnel
dans les tours et des champs de reponse `language` / `speech_language`. Les etats
et `candidate_code` restent compatibles. Nouvelles routes de capacites,
transcription, synthese et module `/audio-client.js`; formats et exemples dans
`son/voice/README.md`. Ces changements sont additifs. Kim doit valider le transport
et les adopter dans son UI; son code non publie n'a pas ete inspecte ou modifie.

L'UI existante du banc d'essai reste VI et gelee; elle ne montre pas les nouveaux
controles audio du SDK. Le test du SDK se fait sans nouvelle interface produit.
Kim gere selecteur de langue, erreurs/promesses, verification du texte reconnu,
information sur l'envoi d'audio et mention d'une voix generee par IA.

**Vincent -> Son/Kim :** aucun changement au contrat procedure/rapport et aucun
schema concurrent cree. Le lookup reste indisponible. Les messages bilingues
concernent le dialogue uniquement; pas de traduction ou inference de faits legaux.

**Identite / autorisation :** l'adaptateur est une demo publique locale, pas une
session applicative authentifiee. AUTH-01/CONSENT-01/ACCESS-01 et tests communs
SECURITY-01 restent a integrer selon les accords Son/Kim. Les limitations locales
ne sont pas une protection de facturation pour un service expose publiquement.

## Configuration et limites

Aucune cle OpenAI/Gemini presente dans l'environnement observe. L'adaptateur exige
`OPENAI_API_KEY` serveur **et** `VOICE_ENABLE_AUDIO_API=1`; sans cela il renvoie 503
et le dialogue texte fonctionne. Modele de transcription/synthese configurable,
valeurs par defaut `gpt-4o-mini-transcribe` / `gpt-4o-mini-tts`. Choix de fournisseur
provisoire, acces et qualite acoustique VI/EN non valides. Details d'activation
privee et extras Python dans le README; pas de cle a copier dans le chat ou Git.

Audio potentiellement transmis a OpenAI une fois active; retention du fournisseur
non verifiee. Donnees de demo synthetiques seulement a ce stade. Une interruption
locale ne retire pas l'audio deja envoye ni ne garantit l'annulation de facturation.
Pas de full-duplex Realtime/VAD, pas de benchmark de latence, pas d'autorisation
personnelle, pas de checklist ni rapport reels, pas de test sur telephone physique.

Git : code `d847dbd424740c0c468c4a1fe665a74c52a90388`; pousse non; PR aucune.

Prochaine action : configurer une cle dans le processus serveur si le fournisseur
est retenu, puis Son teste sur audio synthetique reel VI/EN; Kim valide et branche
l'adaptateur dans son UI. Vincent fournit le lookup/version revus avant tout
contenu officiel. Aucun message d'equipe envoye, aucune fusion proposee comme
integree ou effectuee.

## Suivi — activation privee de la cle

Son confirme disposer d'une cle API OpenAI dans le chat; aucune valeur n'est
recue ou verifiee. Lanceur ajoute : `python -m voice_app.launch` dans l'environnement
du composant. Saisie masquee interactive, refus de repli avec echo, cle en memoire
uniquement et serveur lie a `127.0.0.1:8001`. Pas d'appel payant au demarrage.
Le README contient la commande complete. L'activation attend la saisie privee par
l'utilisateur; aucun test fournisseur reel n'est revendique. La page de test
reste gelee et son micro utilise encore le navigateur.

Verification : `son/voice/.venv/Scripts/python.exe -m unittest discover -s son/voice/tests -p test_launch.py -v`
-> 4 tests passes, avec cle synthetique et serveur simule : saisie non interactive
refusee, repli non masque refuse, aucun secret imprime/persiste, annulation sans
demarrage. Documentation et code selectionnes explicitement avant commit.

Ce suivi complete le compte rendu existant; code dans
`son/voice/src/voice_app/launch.py` et tests de saisie/activation. Main distant observe au
commit `60cb3be` apres fetch, ajouts de profils managers consultes sans les
fusionner; aucun changement du tableau commun dans cette suite.
