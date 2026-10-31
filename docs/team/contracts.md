# Contrats entre les trois composants

Statut : proposition initiale a valider par Vincent, Son et Kim.
Ce document ne decrit pas une API deja implementee.

Responsable : Vincent definit, documente et maintient le contrat des donnees et
fournit les exemples. Son et Kim precisent leurs besoins et verifient que leurs
composants peuvent le consommer. Le manager suit la compatibilite et les blocages.

## Vincent -> Son et Kim : procedure revue

Un seul contrat de lookup pour la voix et le rapport. Le transport (fonction,
fichier ou HTTP) reste a decider. Ne pas creer deux formats concurrents.

Contenu minimal propose :

| Champ | Regle proposee |
| --- | --- |
| `schema_version` | Version du contrat, distincte de la version des donnees |
| `procedure_code`, `title`, `language` | Identite de la procedure et langue du contenu |
| `record_version` | Version immuable identifiant les donnees consommees |
| `review` | Statut, identifiant du reviewer, date de revue et hashes approuves; verification humaine requise |
| `sources` | URLs, dates de collecte, SHA-256 et version du parseur; les faits pointent sur leur source |
| `requirements` | Groupes, texte officiel, quantites, conditions et references de source; aucune suppression implicite par la voix |
| `steps`, `fees`, `processing_time`, `agency` | Valeurs avec conditions et provenance; inconnu explicite si absent |
| `forms` | Edition, URL, hash, statut de revue et disponibilite; pas de formulaire rempli si non valide |

Resultats distincts : procedure disponible et revue, non revue, inconnue ou erreur
technique. Ne pas presenter une absence de donnees comme une liste vide valide.
Une nouvelle source/hash invalide l'approbation precedente pour ce nouveau contenu.

## Son -> Kim : contexte du rapport

Transmettre la reference de procedure, `schema_version`, `record_version`, langue
et les identifiants des elements affiches. Le rapport charge la meme version;
il ne relit pas silencieusement une version plus recente et ne reconstruit pas
les exigences avec un second prompt. S'il ne peut pas retrouver cette version,
afficher une erreur explicite plutot qu'un rapport different.

Destination, consentement et donnees personnelles sont traites separement des
sources et de Git. Les liens prives et jetons ne figurent pas dans les logs publics.

## Avant la premiere integration

- Les trois membres valident le format et le transport; consigner la decision.
- Vincent fournit un exemple synthetique marque comme tel, un cas non revu et un
  cas inconnu. Ne pas inventer de faits administratifs pour un exemple reel.
- Son et Kim verifient qu'ils acceptent les memes exemples et refusent les memes
  donnees non revues. Ajouter alors des tests executables sur le contrat retenu.
- Toute modification incompatible annonce les consommateurs touches et fournit
  leur adaptation avant fusion.
