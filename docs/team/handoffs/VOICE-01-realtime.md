# VOICE-01 — conversation en direct comme un appel

Responsable : Son

Tache : VOICE-01 — remplacer le parcours manuel record/send par une conversation
vocale interactive en continu, VI/EN. Correction explicite de Son dans le chat :
une experience de coup de fil, avec interruptions, et non une messagerie audio.

Etat : En cours pour la mission complete; mode appel local pret pour essai/revue.
Lookup de donnees revues, identite/autorisation et rapport toujours non integres.

Branche : `codex/son/voice-01-browser-conversation` (continuation de la tache).

## Livraison et chemins

- OpenAI Realtime / WebRTC, une connexion bidirectionnelle; microphone continu,
  reponses automatiques sur fin de parole, interruptions configurees via
  `semantic_vad`, `create_response=true`, `interrupt_response=true`.
- Nouveau `RealtimeVoiceClient` sans UI sous
  `son/voice/src/voice_app/static/realtime-client.js`; debut, lecture distante,
  evenements conversationnels, raccrochage, fermeture du peer et des pistes mic.
- Signalisation serveur dans `realtime.py`, `speech.py`, `app.py`, `sessions.py`.
  POST SDP au serveur local, puis requete multipart vers OpenAI. Seul le SDP est
  renvoye au navigateur; cle et ID fournisseur restent cote serveur.
- Une conversation par cookie public; quatre appels simultanes au maximum;
  bail de 180 s au plus, borne par l'expiration de session; hangup au raccrochage,
  changement de session, expiration du bail et arret serveur.
- Banc d'essai existant : `?audio=realtime&language=en` ou `vi` cache record/send
  et expose debut/fin d'appel. Adaptation fonctionnelle de diagnostic uniquement;
  Kim conserve le design et l'integration produit. CSS `[hidden]` explicite et
  CSP `media-src 'self' blob:` pour la lecture audio. Anciens modes conserves.
- Modele par defaut `gpt-realtime-2.1`, configurable par `VOICE_REALTIME_MODEL`.
  Aucun nouvel extra Python. Documentation et scripts dans `son/voice/README.md`.

## Verification reproduite

```powershell
son/voice/.venv/Scripts/python.exe -m unittest discover -s son/voice/tests -v
```

**46 tests passes**, dont 8 nouveaux sur configuration VAD, absence de tools,
session/consent/SDP, isolement entre cookies, doublons, restart/shutdown, bail,
raccrochage pendant la connexion et protocole unifie sans fuite de cle/ID.
Les appels fournisseur de cette suite sont simules. Avertissement Starlette/httpx
deja documente; pas d'echec de test.

```powershell
$env:VOICE_BROWSER_CHANNEL='msedge'
node son/voice/tests/realtime_browser_smoke.cjs
node son/voice/tests/browser_smoke.cjs
node son/voice/tests/openai_harness_smoke.cjs
```

**Trois suites navigateur passees**, Playwright 1.62.1/Edge, `NODE_PATH` du runtime
Codex selon les instructions precedentes. Nouveau scenario WebRTC simule : une
seule connexion pour plusieurs evenements de parole/reponse/interruption, aucun
MediaRecorder ni envoi de tour texte, accueil automatique, arret du mic/peer.
Anciennes interfaces testees en regression. Pas de microphone physique utilise.

### Connexion fournisseur reelle

L'utilisateur a relance le serveur prive et saisi sa cle dans son propre terminal.
`/api/voice/capabilities` sur le port 8001 confirme le nouveau backend configure.
Puis un court appel Realtime **reel** a ete lance via navigateur headless, avec
micro synthetique silencieux et sortie muette :

- signalisation serveur HTTP 200;
- etat du peer `connected`;
- evenement de debut audio et fin de reponse observes;
- 5290 octets audio entrants observes dans les stats RTP;
- fermeture du peer, pistes et demande de hangup effectuees; script sorti 0.

Un seul appel Realtime court pour cet essai, sans lecture de cle par l'agent,
sans voix personnelle, transcription dans les logs, SDP ou adresse reseau publies.
Script intermediaire local : `work/realtime_live_check.cjs` (ignore par Git).
Cette preuve valide connexion et reponse audio de l'agent, pas la qualite percue,
le micro reel, les accents VI/EN, une interruption acoustique reelle ou la latence.

## Integration et limites

Producteur Son -> consommateur Kim : nouvel adaptateur headless et routes
POST/DELETE `/api/voice/realtime`; les autres routes restent compatibles. La
capability `realtime_available` signifie configure, pas droit modele garanti.
`realtime_mode` indique audio continu et absence de verification manuelle de
transcription; le champ global de confirmation reste celui de l'ancien mode
transcription. Kim doit adopter et verifier ces comportements dans son UI.

Ce mode est **exploratoire, conversationnel uniquement**. L'agent est identifie
comme IA et recoit des instructions pour clarifier le besoin sans donner de
documents/frais/delais/eligibilite. Aucun outil de donnees officielles, dossier,
rapport, formulaire ou soumission n'existe dans sa configuration. Ces blocages
d'acces sont distincts des instructions de contenu : le modele peut ne pas suivre
parfaitement un prompt. Sa parole generee n'est pas une checklist revue et ne
doit jamais etre transmise au rapport comme fait officiel. Les tests n'etablissent
pas l'absence d'hallucination. Les futurs faits/outils exigent les gates de code
et le contrat de Vincent avant toute release de conseil administratif.

Audio et donnees de connexion transmis directement a OpenAI pendant l'appel,
avec opt-in; retention fournisseur non revue. Pas d'audio/transcription conservee
par le serveur; transcripts assistant optionnels uniquement dans la page. Cookie
public != identite applicative; aucun acces personnel autorise par la parole.
Les limites locales ne constituent pas une protection d'abus/facturation pour un
service heberge; hangup en echec reseau ne garantit pas l'arret immediat des frais.

Aucun fichier du collecteur ou de Kim modifie, aucun schema de Vincent modifie,
aucun choix automatique CT01. Aucun message d'equipe ou approbation de source.

Git : code `551246bea059daf27ead568c4a87e62b0a11bd94`; pousse non; PR aucune.
`git diff --cached --check` passe avant commit; chemins explicites, prototypes
locaux hors tache preserves. Publication/fusion et integration complete non faites.

Prochaine action : Son essaie son micro sur le lien d'appel; Kim valide l'adaptateur
produit. L'equipe choisit les controles de grounding avant de brancher un vrai
record/version/checklist de Vincent et le rapport de Kim.
