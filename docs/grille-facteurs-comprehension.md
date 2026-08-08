# Grille des facteurs de compréhension d'une codebase par un agent IA

> Document compagnon de [`analyse-et-perspectives-2026.md`](./analyse-et-perspectives-2026.md). Objectif : identifier les **variables sous-jacentes** qui font qu'un agent « comprend vraiment » une codebase, indépendamment de l'outil qui les incarne à un instant donné — pour pouvoir évaluer n'importe quel outil futur sur ses mécanismes plutôt que sur sa réputation.
>
> Origine : analyse du basculement Augment Code (2024, référence par son Context Engine / index temps réel) → Claude Code (2025-26, référence après avoir *retiré* son RAG au profit de la recherche agentique — [confirmé par son créateur](https://x.com/bcherny/status/2017824286489383315)).

---

## 1. « Comprendre » : quatre capacités observables

La « qualité de compréhension perçue » n'est pas une capacité unique. C'est l'absence de violation sur quatre capacités distinctes, aux mécanismes différents :

| # | Capacité | Question test | Mécanisme dominant |
|---|---|---|---|
| C1 | **Localiser** | Trouve-t-il les bons fichiers/symboles ? | Recherche (V2/V3) |
| C2 | **Relier** | Voit-il les invariants qui traversent plusieurs fichiers ? | Raisonnement + surface d'observation (V1/V3) |
| C3 | **Inférer l'intention** | Sait-il *pourquoi* le code est comme ça, ce qui a été essayé et rejeté ? | Connaissance non-résidente (V4) |
| C4 | **Rester cohérent dans le temps** | Contredit-il en session 12 ce qui a été établi en session 3 ? | Persistance + fraîcheur (V4/V5) |

Un outil peut exceller sur C1-C2 et être nul sur C3-C4 (cas de la plupart des outils actuels). La réputation d'un outil mesure son adéquation au **régime d'usage dominant du marché à un instant donné**, pas une supériorité absolue.

## 2. Les six variables sous-jacentes

| | Variable | Ce que c'est | Qui la porte |
|---|---|---|---|
| **V1** | **Capacité effective du modèle** | Raisonnement long-horizon + contexte *effectif* (≠ nominal : la performance se dégrade avec la longueur d'entrée — « context rot ») | Le fournisseur de modèle |
| **V2** | **Boucle de vérification** (compute à la requête) | Explorer activement : grep, lire, exécuter, re-vérifier. Dépend du harnais (coût marginal d'une itération) **et** du projet (y a-t-il quelque chose à exécuter pour vérifier ?) | Harnais + projet |
| **V3** | **Surface d'observation** (compute à l'indexation) | Ce qui est pré-calculé et exposé : index vectoriel, index structurel (symboles, graphe d'appels), sorties d'outils lisibles | Outil + projet |
| **V4** | **Connaissance non-résidente dans le code** | Intention, conventions, invariants transversaux, modes d'échec connus — rien de tout ça n'est dérivable du source seul | Le projet (vous) |
| **V5** | **Fraîcheur** (méta-variable) | Toute connaissance pré-calculée — index (V3) *ou* doc (V4) — devient un passif dès qu'elle cesse d'être vraie. A tué les index vectoriels dans Claude Code (staleness) et est le mode d'échec n°1 du contexte codifié (spec périmée) | Le projet (vous) |
| **V6** | **Co-adaptation modèle↔harnais** | Un modèle entraîné par RL *dans* son harnais avec *ses* outils ; le même modèle ailleurs performe moins bien | Le fournisseur |

**Preuves clés** : [Is Grep All You Need? (arXiv:2605.15184)](https://arxiv.org/abs/2605.15184) — grep dans un bon harnais égale ou bat le retrieval vectoriel · [Code Isn't Memory (arXiv:2606.22417)](https://arxiv.org/abs/2606.22417) — l'index *structurel* apporte un gain là où les embeddings n'en apportent plus · [Evaluating AGENTS.md (arXiv:2602.11988)](https://arxiv.org/abs/2602.11988) vs [Probe-and-Refine (arXiv:2606.20512)](https://arxiv.org/abs/2606.20512) — le contexte générique ne paie pas, le contexte accordé et frais paie · [What Context Does a Coding Agent Actually Need? (arXiv:2607.09691)](https://arxiv.org/abs/2607.09691) — les résumés ne remplacent pas le source ; symétriquement, le source ne révèle pas l'intention.

## 3. Substitutions et régimes

- **V2 ↔ V3 se substituent** : payer le compute à la requête (recherche agentique, tokens) ou à l'indexation (index, staleness). Le point optimal dépend du régime : repos petits/moyens + tâches agentiques → V2 gagne ; monorepo 100M lignes + contrainte de latence → V3 garde l'avantage. Le basculement Augment→Claude Code n'est pas « le modèle a remplacé le retrieval » : c'est le seuil franchi par V1 (~2025) qui a déplacé le point optimal sur cette frontière.
- **V4 n'est substituable par rien** : un modèle infiniment fort re-dérive la structure, pas les décisions prises hors du code. Sur les repos open source célèbres, V1 a « mémorisé » l'intention (V4 apporte zéro — d'où les résultats nuls sur SWE-bench) ; sur une codebase privée avec ses invariants propres, V4 est le facteur limitant.
- **V4 abaisse le besoin en V1** : une connaissance codifiée riche permet à un modèle plus faible (ou moins cher) de produire un travail correct sur les tâches couvertes — c'est le cas d'usage central du papier (un non-développeur + specs riches). Corollaire économique : investir V4 réduit le tier de modèle nécessaire par tâche.
- **V5 conditionne V3 et V4** : sans mécanisme de fraîcheur, les deux pourrissent à la vitesse du projet — et un outil peut « décliner » techniquement sans changer une ligne de code.

## 4. La grille d'évaluation d'un outil

Six questions à poser à n'importe quel outil, actuel ou futur :

1. **Où le compute de compréhension est-il dépensé** — entraînement (V1/V6), indexation (V3), requête (V2) — et lequel correspond à *votre* régime (taille de repo, latence, budget) ?
2. **Que fait l'outil quand il ne sait pas** : il devine, ou il peut vérifier (exécuter, tester, re-chercher) ?
3. **Quel est le contexte effectif**, pas affiché — comment gère-t-il dégradation et compaction ?
4. **Comment la connaissance hors-code entre-t-elle, et qui la maintient fraîche ?** (Sans réponse à la seconde moitié, la première ne vaut rien.)
5. **Le modèle a-t-il été entraîné dans ce harnais** (ou le harnais conçu pour ce modèle) ?
6. **Qu'est-ce qui survit à la fin de la session ?**

**Test discriminant** (à faire passer à tout candidat) : une tâche transversale sur une codebase privée non célèbre, comportant un invariant non écrit ; puis la même famille de tâche en session suivante. Mesures : (a) l'invariant est-il violé ? (b) l'erreur est-elle refaite en session 2 ? (c) coût en tokens/temps.

## 5. Leviers actionnables : ce que vous contrôlez selon votre position

Cas type : **harnais et modèles déjà choisis** (ex. un harnais natif type Claude Code + Opus, et un harnais léger multi-modèles type pi avec des modèles économiques type GLM / DeepSeek). Dans cette position, V1 et V6 sont *subies* — les leviers restants sont V2 (moitié projet), V3, V4, V5 :

| Levier | Action concrète | Variable | Effort |
|---|---|---|---|
| **Donner à la boucle quelque chose à vérifier** | Une commande unique de feedback rapide par projet (`make check` : build + tests + lint), exécutable par l'agent sans setup ; des sorties de debug *lisibles par l'agent* (exports texte/PNG, dumps d'état — cf. les DevTools du cas d'étude) | V2 | Faible |
| **Rendre le repo greppable** | Nommage cohérent et distinctif (la recherche agentique vit de `grep` : un concept = un nom, partout) ; un fichier = une classe ; conventions de chemins stables | V2/V3 | Faible |
| **Exposer la structure** | Un index structurel (symboles/graphe d'appels, type tree-sitter servi par MCP ou LSP) branché sur les deux harnais | V3 | Moyen |
| **Codifier la connaissance non-résidente** | Constitution + specs par sous-système (ce dépôt) ; au format portable **AGENTS.md** pour que le même investissement serve à *tous* les harnais et survive aux changements de modèle | V4 | Moyen, incrémental |
| **Outiller la fraîcheur** | Drift-check en hook et en CI ; mise à jour des specs dans la même session que le code (axe A3 — implémenté depuis — et B3 de la feuille de route) | V5 | Moyen |
| **Router les tâches par profil de variable** | Modèle fort (habitat natif) pour C2/C3 — transversal, architecture, debugging ; modèles économiques pour les tâches mécaniques *couvertes par une spec* — c'est la couverture V4 qui rend les modèles faibles viables | V1×V4 | Faible |

Deux points d'attention dans une configuration multi-harnais/multi-modèles :

- **Les modèles non co-adaptés à leur harnais (V6 absente) doivent être compensés par plus de V4 explicite** : ne jugez pas un modèle économique sur sa compréhension du repo sans lui avoir donné les specs — vous mesureriez V6, pas le modèle.
- **V4 est le seul investissement qui se transfère intégralement** entre harnais et entre modèles. À harnais et modèles fixés, c'est le levier au meilleur rendement — et il se mesure : appliquer le test discriminant (§4) en 2×2 (modèle fort/faible × avec/sans specs) sur son propre projet donne en quelques heures la valeur réelle de sa couverture V4.

## 6. Lecture prédictive du paysage

Les fournisseurs de modèles vendent des tokens et entraînent des modèles : ils investiront structurellement V1/V2/V6 (le compute à la requête est leur revenu) et sous-investiront V3. Les tiers qui incarnent V3 se font presser à mesure que V1 monte (cas Augment). La variable où personne n'a encore gagné est **V4/V5** (mémoire + fraîcheur) — signaux convergents : auto memory de Claude Code, Cursor Memories, la vague de startups mémoire. Si un outil futur donne une sensation de compréhension inédite, chercher son avantage d'abord là — et le vérifier avec la grille du §4 plutôt que le croire sur réputation.
