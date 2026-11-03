# Évaluation du tri

44 leads, modèle `gemma4:12b`, registre public réel. Réponses attendues fixées avant les mesures (`data/testset.jsonl`).

| Indicateur | Règles seules | Règles + LLM |
|---|---|---|
| Réponse exacte | 31/44 (70 %) | 32/44 (73 %) |
| **Leads perdus** (écartés à tort) | 1 | 1 |
| Faux qualifiés (envoyés à un commercial à tort) | 3 | 0 |
| Hors cible écartés automatiquement | 9/18 (50 %) | 9/18 (50 %) |
| Bons leads qualifiés automatiquement | 16/18 (89 %) | 16/18 (89 %) |
| Part envoyée en revue humaine | 34% | 41% |

## Règles + LLM : matrice de confusion

| attendu \ obtenu | qualifie | a_revoir | hors_cible |
|---|---|---|---|
| **qualifie** | 16 | 2 | 0 |
| **a_revoir** | 0 | 7 | 1 |
| **hors_cible** | 0 | 9 | 9 |

## Écarts avec la réponse attendue (règles + LLM)

| id | catégorie | attendu | règles seules | règles + LLM | première raison utile |
|---|---|---|---|---|---|
| q09 | abréviation | qualifie | a_revoir | a_revoir | Le poste de Responsable des opérations est un décideur clé pour les outils de gestion interne. Le message exprime un besoin concret de gain de temps sur la gestion des plannings multi-sites. |
| q12 | faute de frappe | qualifie | a_revoir | a_revoir | Le poste de 'Directeur général' correspond à un décideur clé. Le message exprime un besoin concret et explicite pour un outil de planification des équipes soignantes. |
| h02 | secteur | hors_cible | a_revoir | a_revoir | Le poste de Responsable des opérations est un décideur clé pour les outils de gestion interne. Le message exprime un besoin concret de planification pour des équipes sur plusieurs sites. |
| h04 | secteur proche | hors_cible | a_revoir | a_revoir | La demande mentionne explicitement un besoin concret de planification des gardes pour les vétérinaires et auxiliaires. Le poste de 'Directrice' indique une prise de décision possible, bien que le secteur vétérinaire ne soit pas le cœur de cible principal. |
| h12 | secteur proche | hors_cible | a_revoir | a_revoir | Le poste de 'Gérant' correspond à un décideur et le message exprime un besoin concret de gérer les plannings pour une équipe de 25 personnes. La demande est directe et centrée sur la fonctionnalité principale de Lumio. |
| p01 | étudiant | hors_cible | qualifie | a_revoir | Signal d'alerte : etudiant |
| p02 | étudiant | hors_cible | qualifie | a_revoir | Signal d'alerte : etudiant |
| p03 | recruteur | hors_cible | a_revoir | a_revoir | Signal d'alerte : prestataire |
| p04 | prestataire | hors_cible | a_revoir | a_revoir | Signal d'alerte : prestataire |
| p05 | concurrent | hors_cible | a_revoir | a_revoir | Signal d'alerte : concurrent |
| p06 | spam | hors_cible | a_revoir | a_revoir | Signal d'alerte : prestataire |
| r07 | secteur voisin | a_revoir | hors_cible | hors_cible | Effectif dans la cible (tranche INSEE 21) |
