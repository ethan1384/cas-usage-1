# Évaluation du tri

44 leads, modèle `gemma4:12b`, registre public réel. Réponses attendues fixées avant les mesures (`data/testset.jsonl`).

| Indicateur | Règles seules | Règles + LLM |
|---|---|---|
| Réponse exacte | 34/44 (77 %) | 35/44 (80 %) |
| **Leads perdus** (écartés à tort) | 0 | 0 |
| Faux qualifiés (envoyés à un commercial à tort) | 3 | 0 |
| Hors cible écartés automatiquement | 11/18 (61 %) | 11/18 (61 %) |
| Bons leads qualifiés automatiquement | 16/18 (89 %) | 16/18 (89 %) |
| Part envoyée en revue humaine | 32% | 39% |

## Règles + LLM : matrice de confusion

| attendu \ obtenu | qualifie | a_revoir | hors_cible |
|---|---|---|---|
| **qualifie** | 16 | 2 | 0 |
| **a_revoir** | 0 | 8 | 0 |
| **hors_cible** | 0 | 7 | 11 |

## Écarts avec la réponse attendue (règles + LLM)

| id | catégorie | attendu | règles seules | règles + LLM | première raison utile |
|---|---|---|---|---|---|
| q09 | abréviation | qualifie | a_revoir | a_revoir | Le poste de Responsable des opérations est un décideur clé pour les outils de gestion interne. Le message exprime un besoin concret de gain de temps sur la gestion des plannings multi-sites. |
| q12 | faute de frappe | qualifie | a_revoir | a_revoir | Le poste de 'Directeur général' correspond à un décideur clé. Le message exprime un besoin concret et explicite pour un outil de planification des équipes soignantes. |
| h02 | secteur | hors_cible | a_revoir | a_revoir | Le poste de Responsable des opérations est un décideur clé pour les outils de gestion interne. Le message exprime un besoin concret de planification pour des équipes sur plusieurs sites. |
| p01 | étudiant | hors_cible | qualifie | a_revoir | Signal d'alerte : etudiant |
| p02 | étudiant | hors_cible | qualifie | a_revoir | Signal d'alerte : etudiant |
| p03 | recruteur | hors_cible | a_revoir | a_revoir | Signal d'alerte : prestataire |
| p04 | prestataire | hors_cible | a_revoir | a_revoir | Signal d'alerte : prestataire |
| p05 | concurrent | hors_cible | a_revoir | a_revoir | Signal d'alerte : concurrent |
| p06 | spam | hors_cible | a_revoir | a_revoir | Signal d'alerte : prestataire |
