# Journal de bord

Matière pour la partie « ce qui n'a pas marché » de l'explication.

## 2026-11-02 : première chaîne de bout en bout

- **Une note de confiance chiffrée ne veut rien dire.** Sur la même demande, trois modèles ont renvoyé
  70, 0.2 et 3, et `gemma4:12b` l'a comprise comme une probabilité d'achat. Remplacée par trois niveaux
  (`elevee`, `moyenne`, `faible`) avec une consigne explicite.
- **Le registre public est imparfait.** Sur 25 résultats pour « centre de santé », 6 n'ont pas
  d'effectif (`NN`) et plusieurs sont classés hors des codes attendus (86.90D, 94.99Z, 65.12Z). Une
  règle stricte aurait écarté de bons leads : ces cas partent donc en revue.
- **Le LLM est prudent sur l'étudiant.** Il le détecte, mais sans certitude élevée : le lead part en
  revue au lieu d'être écarté. C'est acceptable, mais à mesurer sur le jeu de test.
- **Un formulaire public est une surface d'attaque.** Un message de test demandant au modèle
  d'ignorer ses instructions a bien été signalé comme spam. Il contenait aussi un `<!channel>`, échappé
  avant l'envoi à Slack.

## 2026-11-03 : jeu de test et mesure

- **Un registre qui répond n'est pas un registre fiable.** Une des mesures a placé un lead en revue parce
  que l'API avait échoué ponctuellement. Le filet de sécurité a bien fonctionné (revue, pas poubelle), mais
  le résultat changeait d'une exécution à l'autre. Ajout de 3 tentatives sur les erreurs 429 et 5xx, et de
  la raison de l'échec dans `data/eval_details.jsonl`.
- **Deux défauts de règles trouvés par les données, pas par la réflexion.** Les cliniques vétérinaires
  partaient en revue à cause du mot « clinique » dans leur nom, et un EHPAD était écarté sans preuve alors
  qu'un humain doit trancher. Corrigés après la première mesure : le score final n'est donc plus
  indépendant du jeu de test. La première mesure (32/44, 1 lead perdu) est gardée dans
  `data/eval_report_v1.md`.
- **Le LLM détecte tout, mais n'ose rien trancher.** Sur étudiants, concurrent, prestataire et spam, il
  trouve le bon signal d'alerte mais répond « certitude moyenne » même quand c'est évident. Avec ma règle
  (écarter seulement si certitude élevée), aucun n'est écarté : ils arrivent en revue avec la raison.
  Baisser le seuil aurait fait passer mon propre test, sans preuve que ça tienne sur de vrais leads, donc je
  ne l'ai pas fait. À reprendre avec plus de données ou un autre modèle.
- **Le LLM apporte de la sécurité, pas de l'automatisation.** Même nombre de leads écartés qu'avec les
  règles seules, mais 3 faux qualifiés évités (deux étudiants et le message qui donne des ordres), au prix
  de 7 points de revue humaine en plus.
- **Les noms de grands groupes ne se résolvent pas.** « Michelin » renvoie quatre sociétés homonymes, donc
  revue. Même chose pour Elsan. Un groupe multi-sites reste un cas pour un humain.
- **Limites du rapprochement de noms** : « Clinque de l'Alma » (faute de frappe) et « LBM Bruny »
  (abréviation) partent en revue. C'est sûr, mais coûteux en temps humain.
