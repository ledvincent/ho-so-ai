# Identite, autorisation et demonstration de securite

Statut : cadrage et criteres a implementer et tester, pas une attestation de
securite. Aucun service d'identite ou d'autorisation n'est livre par ce document.

## Repartition

| Responsable | Livraison |
| --- | --- |
| Kim — AUTH-01 | Connexion/deconnexion, integration d'un fournisseur d'identite etabli, session applicative et acces au dossier personnel cote serveur avec verification de son proprietaire |
| Kim — CONSENT-01 | Ecran de confirmation : demarche, donnees demandees, conversation concernee, expiration, accepter/refuser; envoi d'une decision authentifiee au serveur de Son |
| Son — ACCESS-01 | Sessions de conversation et serveur d'autorisation : verifier l'identite authentifiee, lier compte/conversation/demarche, gerer la decision et bloquer tout outil d'acces personnel sans droit valide |
| Son + Kim — SECURITY-01 | Tests d'isolement entre comptes et de refus/expiration/rejeu; preuves pour la demo |
| Vincent | Official documents/data, document retrieval, search through RAG and the procedure contract; no added ownership of user accounts |

Kim protege le stockage et les routes du dossier. Son protege les outils de
l'agent et la validite de l'autorisation : les deux controles sont necessaires.
Son et Kim conviennent du fournisseur d'identite et du format de verification de
session avant de coder leur liaison. Ne pas construire une gestion maison des
mots de passe. Le contrat des procedures de Vincent reste distinct de cet accord.

## Parcours et extension telephone

Pour la demo : application connectee -> bouton Parler -> session de conversation
creee par le serveur -> demande d'acces au dossier -> confirmation dans
l'application -> verification serveur -> acces limite -> rapport personnel.
Le compte vient de la session authentifiee, pas d'un identifiant dicte ou d'un
champ utilisateur libre. Le simple bouton d'accord n'est pas un second facteur.

Plus tard : ajouter une entree telephonique vers la meme logique de conversation.
Un identifiant ou numero d'appel sert uniquement au rapprochement; il ne prouve
pas l'identite. L'approbation reste dans l'application authentifiee et liee a
l'appel exact. Ce futur canal n'est pas inclus dans la demo.

## Regles de securite a implementer

1. Refus par defaut. Avant autorisation, seuls les renseignements generaux publics
   sont accessibles. Verifier les droits cote serveur a chaque lecture/ecriture,
   y compris les routes de rapport, pas seulement dans l'interface ou le prompt.
2. Les requetes d'approbation sont creees par le serveur, non predictibles et
   liees au compte, a la conversation, a la demarche et aux actions/champs permis.
   Cible demo : demande valable 2 minutes; accord actif au maximum 10 minutes et
   jamais au-dela de la fin de conversation. Valeurs configurables a confirmer.
3. Une demande passe de pending a approved, denied ou expired. Une decision deja
   consommee ne cree pas un autre accord; aucun transfert vers une autre session.
   Refus, expiration, revocation et deconnexion interdisent les nouveaux acces.
   La transition doit etre atomique face aux requetes concurrentes.
4. Verifier signature, expiration et destinataire des jetons selon le fournisseur.
   Protections de session et CSRF adaptees au transport retenu. Authentifier aussi
   les appels entre services; ne pas exposer une route interne sans controle.
5. Chaque route du dossier et du rapport verifie le proprietaire. Modifier un ID
   dans une URL ou une requete ne doit jamais donner acces au dossier d'autrui.
6. HTTPS pour la demo hebergee; secrets et cles longues uniquement cote serveur.
   Pour le navigateur, jeton audio temporaire et limite si le fournisseur le
   permet. Limiter les tentatives de connexion, d'approbation et de creation de
   sessions; ne pas divulguer si un compte arbitraire existe.
7. L'agent recoit uniquement les donnees necessaires a l'etape autorisee. Ni une
   phrase de l'utilisateur ni un document consulte ne peut donner de droits.
   Ne pas donner au modele un acces direct sans filtre a toute la base.
8. Demo avec comptes et dossiers synthetiques. Ne pas journaliser mots de passe,
   jetons, documents personnels, audio ou transcriptions complets. Conserver
   uniquement une trace minimale des decisions et acces, avec acces restreint;
   Son et Kim documentent duree de conservation et suppression avant usage reel.
   Inventorier les fournisseurs recevant audio ou texte et leurs reglages de
   conservation. Une revocation ne supprime pas retroactivement des donnees deja
   transmises : eviter de les envoyer inutilement.

## Preuves a montrer au jury

Tous les scenarios ci-dessous sont **non executes** a ce stade. Les responsables
ajoutent la commande ou le scenario manuel reproductible, le resultat observe
et la reference du commit une fois l'implementation disponible.

| Scenario | Resultat attendu | Responsables |
| --- | --- | --- |
| Demande personnelle avant approbation, y compris appel direct a l'API | Acces refuse par le serveur | Son + Kim |
| Connexion puis accord pour la bonne conversation | Acces aux seuls champs/actions autorises | Son + Kim |
| Compte B demande le dossier ou le rapport du compte A | Acces refuse, aucune donnee de A retournee | Kim |
| B tente d'approuver la demande de A | Refus cote serveur | Son |
| Refus, demande expiree, fin de session ou deconnexion | Aucun nouvel acces personnel | Son + Kim |
| Rejouer une approbation ou la reutiliser pour une autre conversation | Aucun nouvel accord, acces autre session refuse | Son |
| Dire a l'agent de contourner la verification | Outil bloque par le serveur, aucune fuite personnelle | Son |
| Inspection des requetes navigateur, du depot et des logs | Aucune cle serveur ni donnee personnelle de test divulguee | Son + Kim |

Presentation : montrer un parcours accepte ET les acces refuses avec comptes A/B.
Dire « voici les controles testes et leurs resultats », sans annoncer « 100 %
securise », une certification, une conformite legale ou une verification officielle
d'identite. Connexion au compte et consentement ne prouvent pas une identite civile.

References de conception :
- [OWASP — Authorization](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html)
- [OWASP — Transaction Authorization](https://cheatsheetseries.owasp.org/cheatsheets/Transaction_Authorization_Cheat_Sheet.html)
