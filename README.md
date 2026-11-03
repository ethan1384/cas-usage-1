# Lumio : qualification et routage des demandes de démo

Cas pratique du stage Automation & IA d'Audit Revenue. L'explication destinée aux recruteurs est dans
[EXPLICATION.md](EXPLICATION.md).

Lumio reçoit environ 150 demandes de démo par mois, dont près de la moitié sont hors cible, et le tri
se fait à la main. Ce service vérifie chaque demande et l'envoie au bon endroit, avec ses raisons.

## Le flux

```
Formulaire → webhook → registre public → règles → LLM → décision → HubSpot + Slack + journal
```

1. **Enrichissement** : l'API Recherche d'entreprises donne le code NAF et la tranche d'effectif.
2. **Règles sans IA** : secteur et taille (20 à 500 salariés). Écarter exige une preuve.
3. **LLM** : uniquement pour ce que les règles ne savent pas lire, c'est-à-dire le poste et le message
   libre. Il n'est pas appelé quand les règles ont déjà écarté le lead.
4. **Décision** :

| Verdict | HubSpot | Slack |
|---|---|---|
| `qualifie` | contact créé, statut `NEW` | notification avec le commercial attribué |
| `a_revoir` | contact créé, statut `OPEN` | demande de revue humaine |
| `hors_cible` | contact créé, statut `UNQUALIFIED` | rien |

Écarter un bon lead coûte plus cher que de faire regarder un mauvais lead. Donc tout ce qui est
incertain (registre muet, homonymes, effectif absent, panne du LLM) part en revue humaine, et le LLM ne
peut jamais repêcher un lead écarté par les règles. Un contact déjà présent dans HubSpot n'est jamais
modifié : la création seule est utilisée, jamais l'upsert.

## Lancer le projet

Prérequis : [uv](https://docs.astral.sh/uv/) et [Ollama](https://ollama.com) avec le modèle `gemma4:12b`
(ou un autre via `OLLAMA_MODEL`). Sans Ollama, le service fonctionne mais tous les leads non écartés
par les règles partent en revue.

```bash
uv sync
uv run pytest

# Un lead, sans rien envoyer à HubSpot ni à Slack
uv run python -m lumio data/exemples/qualifie.json --dry-run

# Le webhook
uv run uvicorn lumio.main:app --port 8765
curl -X POST http://127.0.0.1:8765/webhook/demo-request \
  -H 'Content-Type: application/json' -d @data/exemples/qualifie.json
```

Sans uv, avec Python 3.12 ou plus :

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m pytest
python -m lumio data/exemples/qualifie.json --dry-run
```

Pour de vrais envois, copier `.env.example` vers `.env`, le remplir, puis lancer le serveur avec
`uv run --env-file .env uvicorn lumio.main:app --port 8765`. Sans identifiants, chaque envoi est simulé
et écrit dans `data/outbox.jsonl`. Toutes les décisions sont journalisées dans `data/decisions.csv`.

## Lancer la démo

```bash
./demo.sh
```

Le script efface les données de démonstration précédentes, active Slack s'il est configuré dans `.env`,
et remplace HubSpot par un **simulateur local** : une page qui affiche chaque contact reçu, avec son
statut, et qui se met à jour toute seule. Ouvrir http://127.0.0.1:8765/mock/hubspot à côté du terminal,
puis envoyer les leads de `data/exemples/`. Envoyer deux fois le même lead montre qu'un contact existant
n'est pas modifié.

Le simulateur ([lumio/mock_hubspot.py](lumio/mock_hubspot.py)) n'est pas HubSpot : il reçoit la même
requête de création de contact que l'API HubSpot, et c'est le vrai code d'envoi de Lumio qui tourne contre
lui. Il n'est actif qu'avec `MOCK_HUBSPOT=1`.

## Mesurer la qualité du tri

```bash
uv run python -m lumio.evaluate     # 44 leads, quelques minutes (registre et LLM réels)
```

`data/testset.jsonl` contient 44 leads : de vraies structures du registre, des personnes fictives, et la
réponse attendue fixée avant la mesure (18 à qualifier, 18 hors cible, 8 à revoir). Le rapport est écrit
dans `data/eval_report.md`.

| | Règles seules | Règles + LLM |
|---|---|---|
| Réponse exacte | 34/44 | 35/44 |
| Leads perdus (écartés à tort) | 0 | 0 |
| Faux qualifiés | 3 | 0 |
| Part envoyée en revue | 32 % | 39 % |

Les 27 décisions automatiques de la dernière mesure sont toutes correctes. Le LLM n'écarte aucun lead de
plus que les règles : il empêche surtout les faux qualifiés (étudiants, injection de consignes) en les
renvoyant en revue. La première mesure, avant deux corrections de règles, est conservée dans
`data/eval_report_v1.md`. Le jeu de test est petit et écrit par le même auteur que le code : ces chiffres
sont des indications, pas une garantie.

## Le code

| Fichier | Rôle | Équivalent n8n |
|---|---|---|
| `lumio/main.py` | Réception du formulaire | Webhook |
| `lumio/enrichment.py` | Appel au registre public | HTTP Request |
| `lumio/rules.py` | Critères secteur et taille | IF / Code |
| `lumio/llm.py` | Prompt et sortie JSON validée | Basic LLM Chain + Output Parser |
| `lumio/routing.py` | Décision et attribution | Switch |
| `lumio/connectors.py` | HubSpot et Slack | HubSpot, Slack |
| `lumio/mock_hubspot.py` | Simulateur HubSpot de démonstration | (pas d'équivalent) |
| `lumio/pipeline.py` | Enchaînement et journal | Le workflow, Google Sheets |
| `lumio/evaluate.py` | Mesure sur le jeu de test | (pas d'équivalent) |

## État d'avancement

**Fonctionne, vérifié de bout en bout** : webhook, registre réel, LLM réel, décision, Slack réel,
journal, mesure.

**Simulé** : HubSpot, faute de compte. Le vrai code d'envoi tourne contre un simulateur local visible
(voir « Lancer la démo »), mais il n'a jamais parlé au vrai service. Le simulateur applique deux
hypothèses à confirmer sur un vrai compte : que la création d'un e-mail déjà existant renvoie bien une
erreur 409, et que le jeton d'application privée suffit avec le droit d'écriture sur les contacts.

**Pas fait** :

- réponse automatique aux leads hors cible (à rédiger puis à faire valider par l'équipe commerciale) ;
- attribution dans HubSpot : le commercial n'apparaît que dans le message Slack, et ses noms sont fictifs ;
- tolérance aux fautes de frappe et aux abréviations dans le nom de la structure (renvoyés en revue) ;
- traitement asynchrone : le webhook attend le LLM (4 à 9 s), un vrai formulaire devrait recevoir une
  réponse immédiate ;
- protection contre les doublons : un formulaire envoyé deux fois produit deux notifications.
