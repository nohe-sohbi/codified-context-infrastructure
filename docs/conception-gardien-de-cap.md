# Gardien de cap — document de conception (v2)

> **Statut : proposition, à démonter avant toute implémentation.**
> v1 rédigée le 09/08/2026 ; **v2 le 10/08/2026, après une revue adversariale à six angles** (vérification des sources primaires, vérification de l'écosystème, cohérence interne, faisabilité contre le code réel du plugin, praticité/coût, red-team du gaming) — ~60 findings dédupliqués intégrés. L'historique de revue est en fin de document, avant les sources.

## 0. Le nom, parce qu'il dit l'idée

Le plugin possède un **gardien de dérive** (*drift guardian*) : il mesure l'écart entre le code et les **faits** documentés, et le convertit en propositions de mise à jour. Ce document conçoit son symétrique d'un étage au-dessus : le **gardien de cap** (*course guardian*) — il mesure l'écart entre l'état du produit et sa **direction** déclarée, et le convertit en propositions d'amélioration. La dérive corrige le passé qui ment ; le cap tire vers le futur qui manque.

---

## 1. Le problème

Les agents de code exécutent bien et proposent mal. Trois manifestations vécues (sessions réelles sur trois projets personnels distincts) :

1. la demande est exécutée *stricto sensu* — les exigences implicites ne sont pas inférées ;
2. les suites naturelles d'une feature ne sont jamais proposées ;
3. personne ne dit jamais « l'audio mérite un audit » — l'humain doit *pinpointer* chaque amélioration possible, ce qui fait de lui le goulot d'étranglement de son propre projet.

(Honnêteté d'abord : ces trois observations, leur confirmation et les « 12 leçons » invoquées plus bas viennent du même auteur observant ses propres projets — elles sont la **motivation** de ce document, pas sa preuve. La preuve, c'est la littérature ci-dessous, avec ses propres limites.)

### 1.1 Ce que la littérature établit (avec les réserves qui s'imposent)

- **Le gap est mesuré par trois angles indépendants.** [Implicit Intelligence](https://arxiv.org/abs/2602.20424) (fév. 2026) : le meilleur modèle testé n'atteint que **48,3 %** de scénarios passés sur les exigences implicites — *chiffre à prendre comme indicatif* : l'environnement est simulé par LLM (mondes YAML « Agent-as-a-World »), la notation passe par une rubrique d'évaluation sur cet état simulé (le partage exact entre rubrique déterministe et juge LLM n'est pas confirmé par les résumés disponibles), papier récent non consolidé. Mais [PROBE](https://arxiv.org/abs/2510.19771) (équipe et méthode différentes) localise le même goulot — identifier le problème non formulé **et le traduire en action précise et complète**, pas exécuter une action déjà spécifiée — et [SWE-EVO](https://arxiv.org/abs/2512.18470) montre que le meilleur modèle testé ne résout que **25 %** des tâches d'évolution long-horizon (consignes niveau notes de version, multi-fichiers), là où les tickets isolés de SWE-bench Verified se résolvent à ~73 % (*comparaison entre deux benchmarks et deux versions de modèle — un ordre de grandeur, pas une ablation contrôlée*). Le chiffre exact est fragile ; le phénomène est sur-déterminé.
- **La littéralité est une politique, pas une bêtise.** Les agents ne refusent jamais de contribuer, même dans des dépôts qui bannissent explicitement l'IA, et ne récupèrent presque jamais les règles d'eux-mêmes ([étude compliance, juil. 2026](https://arxiv.org/abs/2607.26819)) ; la sycophancie **se compose avec la mémoire** (échec aval de 45,0 % → 71,9 %, soit +27,0 pts, quand un accommodement est mémorisé — [arXiv:2607.10526](https://arxiv.org/abs/2607.10526)). Conséquence de conception : l'initiative doit être **contractualisée**, et la licence de désaccord **écrite**.
- **Le vocabulaire existe** : l'« *insight policy* » ([Agentic Coding Needs Proactivity, Not Just Autonomy](https://arxiv.org/abs/2605.06717), mai 2026) — la politique qui décide *ce qui compte ensuite, avec quelles preuves, s'il faut le remonter, et comment apprendre du feedback*. Ce document est la conception d'une insight policy pour un projet logiciel.

### 1.2 La loi des 12 leçons, montée d'un étage

Toute l'expérience du plugin tient en une loi : *un agent est exactement aussi bon que son contrat, jamais plus*. « Améliore mon app » n'est pas un contrat : « mieux » n'y est défini nulle part. Le diagnostic central de ce document : **le manque d'autonomie n'est pas un manque d'intelligence, c'est un artefact manquant** — nulle part dans un repo n'est écrit *vers quoi* le produit tend ni *à quoi ressemble la qualité*. codified-context capture l'**état** (comment ça marche) ; il manque la **direction** (vers quoi) et le **goût** (qu'est-ce que « bien »). Un agent ne peut pas proposer « l'audio mérite un audit » si « qualité audio » n'existe pas comme dimension notée quelque part.

La démonstration existe déjà, shippée : les agents SEO livrent **le cœur** du comportement voulu — audits récurrents auto-déclenchés, priorisation automatique par impact — *parce que* le SEO a un barème standardisé (Core Web Vitals, erreurs de crawl, positions). De façon inégale selon l'outil, et sans éliminer la revue humaine sur la priorisation business — ce qui est cohérent avec D2/D3 ci-dessous, pas une contradiction. Le mécanisme est le même ; seul le référentiel manque ailleurs.

## 2. Vocabulaire

| Terme | Définition |
|---|---|
| **Rubric** | Barème d'une dimension de qualité : échelle 1-5, critères observables par niveau, niveau **visé**, preuves à collecter, type de vérification. Le « goût » rendu vérifiable. |
| **Vision** | Document de direction : ce que le produit essaie de devenir, les non-buts, les arbitrages assumés, le budget par passage. |
| **Passage de cap** (*course-check*) | Session d'audit : noter chaque rubric avec preuves, comparer au passage précédent, choisir la dimension prioritaire, produire ≤ 3 propositions. |
| **Proposition** | Artefact structuré (écart mesuré + preuve + esquisse + critère d'acceptation + coût estimé) soumis au tri humain. Jamais un diff imposé. |
| **Archive** | Historique des scores et des propositions (acceptées / refusées avec catégorie / ajournées / faites) — la mémoire qui calibre « quoi proposer ensuite ». |
| **Insight policy** | La politique complète ci-dessus : quoi regarder, quoi remonter, quand, et comment apprendre du tri. |
| **Lignée OMNI/Voyager/DGM** | Recherche « open-ended » : un agent choisit sa prochaine tâche depuis une archive de l'acquis ([Voyager](https://arxiv.org/abs/2305.16291) : auto-curriculum ; [OMNI](https://arxiv.org/abs/2306.01711) : intérêt = faisable × intéressant, l'« intéressant » — nouveau et digne d'intérêt — étant jugé par un modèle de fondation ; [DGM](https://arxiv.org/abs/2505.22954) : auto-modifications gardées si elles compilent et restent capables de s'auto-éditer — le benchmark guide l'échantillonnage des parents dans l'archive, il ne filtre pas la rétention, et des branches moins performantes sont conservées exprès pour l'exploration). Personne n'a couplé cette machinerie à un **référentiel de qualité versionné et humain-éditable, ancré à une vision écrite, avec une archive de refus qui recalibre la sélection** — des audits périodiques dépassant le « cassé » existent déjà (l'audit quotidien de cohérence UI de Cognition/Devin, qui ouvre des tickets Linear), mais sans barème gradué ni mémoire des refus. C'est la niche, formulée étroitement. |

## 3. Périmètre

**Est** : une couche d'initiative construite *au-dessus* d'un agent littéral, pour un projet donné ; des artefacts versionnés + un protocole de session + des garde-fous ; une extension de codified-context (réutilise l'index, les hooks, la discipline de fraîcheur — avec les extensions listées en §5.5).

**N'est pas** : de l'entraînement de modèle (pas de RL ici — les mécanismes RL de la littérature informent la conception, ils ne sont pas le livrable) ; un agent qui merge tout seul ; un framework généraliste ; un scheduler dès la phase 1 (voir D8).

## 4. Les six mécanismes d'initiative observés, et la composition retenue

Le sweep écosystème (août 2026) montre que **toute** initiative shippée est fabriquée par composition de six mécanismes — jamais par « un modèle plus malin » :

| # | Mécanisme | Exemple vérifié | Limite |
|---|---|---|---|
| M1 | Scheduler + prompt permanent | Claude Code Routines ; audit quotidien Cognition/Devin (cohérence UI → tickets Linear) | L'initiative vit dans le cron, pas dans l'agent |
| M2 | Backlog à états | [snarktank/ralph](https://github.com/snarktank/ralph) (`prd.json`, drapeaux pass/fail) | Un humain écrit encore le backlog |
| M3 | Télémétrie-comme-backlog | Tembo (alertes prod → PRs) | Ne voit que le *cassé*, jamais le *médiocre* |
| M4 | Boucle rubric/juge | Agents SEO (barème gradué — l'exemple fort) ; [Spec Kit](https://github.com/github/spec-kit) `/speckit.checklist` (pass/fail — exemple faible) | Exige un référentiel — précisément ce qui manque |
| M5 | Mémoire auto-modifiable | prime-agent Continual Harness ; « Dreaming » | Méta-vue de *l'agent*, pas du *produit* |
| M6 | Évolution filtrée par benchmark | [DGM](https://github.com/jennyzzt/dgm) | Recherche ; exige une métrique vérifiable |

**Composition retenue : M4 comme cœur (le référentiel qu'on va créer), M2 comme sortie (propositions à états), M1 comme déclencheur (phase 3 seulement), M5 en emprunt ciblé (le `/refine` à preuves de prime-agent, appliqué aux rubrics — phase 4 seulement).** M3 est complémentaire (plus tard) ; M6 est hors périmètre.

## 5. Architecture

### 5.1 Les artefacts (Tier 0 — la direction et le goût)

```
VISION.md                     # direction : ambition, non-buts, arbitrages, budget par passage
.claude/rubrics/{dim}.md      # un barème par dimension de qualité
.claude/proposals/{id}.md     # les propositions, avec leur cycle de vie
.claude/cap/scores.jsonl      # l'historique des passages (append-only, écrit par script)
.claude/cap/adjacent.md       # les suites d'adjacence (entrées du prochain passage, jamais montrées hors passage)
.claude/cap/attentes/{n}.md   # note pré-enregistrée de l'humain avant le passage n (base du critère de surprise)
```

> **Confidentialité (à décider au setup, pas après)** : VISION.md expose la stratégie, `proposals/` et `scores.jsonl` exposent la liste chiffrée des faiblesses du produit. Sur un repo public ou partagé, c'est une publication. Le setup exige une décision consciente : repo privé, ou exclusion de ces artefacts du remote public.

**Format d'un rubric** (même discipline front-matter que les docs de contexte — champs `description`/`keywords` requis pour être retrouvable par l'index, cf. §5.5) :

```yaml
---
dimension: audio-quality
name: Qualité audio des vidéos produites
description: Barème du rendu audio (normalisation, bruit, mixage, mastering)
keywords: [audio, loudness, LUFS, normalisation, mixage, bruit]
weight: high                  # high=3, medium=2, low=1 dans la fonction de choix
target: 4                     # niveau visé — l'écart se mesure contre lui
verification: mesure          # mesure | oracle | verdict-humain (cf. D5)
files:
  - pipeline/audio/
last-verified: 2026-08-09
---
# Qualité audio

| Niveau | Critères observables |
|---|---|
| 1 | Volume non normalisé entre clips ; clipping audible |
| 2 | Normalisation basique ; pas de réduction de bruit ; transitions sèches |
| 3 | Loudness aux normes plateforme (-14 LUFS) ; crossfades ; bruit traité |
| 4 | + ducking musique/voix ; EQ par type de source |
| 5 | + mastering par profil de niche ; A/B testé sur rétention |

## Preuves à collecter pour noter
- lire pipeline/audio/*.py : quelles étapes existent réellement
- mesurer le LUFS des 2 dernières sorties **par mtime** (règle déterministe —
  l'échantillon n'est jamais au choix de l'agent)
## Vérification externe (anti-triche)
<!-- Cette section est RÉDIGÉE PAR L'HUMAIN (l'agent peut proposer une ébauche,
     l'humain la réécrit) : celui qui passe l'examen n'écrit pas le détecteur
     de triche. Test : un tiers peut-il rejouer cette vérification en < 5 min ? -->
- la note ne peut pas monter sans mesure LUFS jointe en preuve, sur les
  échantillons désignés par la règle ci-dessus
```

**Format d'une proposition** :

```yaml
---
id: 2026-08-12-audio-normalisation   # date + slug ; suffixe -2, -3 en cas de collision
dimension: audio-quality             # dimension principale ; secondaires dans related:
related: []
gap: "score 2/5 (cible 4), stagnant depuis 3 passages, weight high"
evidence: ["pipeline/audio/mix.py:34 — aucun appel de normalisation", "sample_0811.mp4 : -8.2 LUFS mesuré"]
effort: M            # S/M/L — l'écart estimé/réel des propositions `done` est relu au passage suivant
status: proposed     # proposed | accepted | deferred | rejected | done
until: null          # si deferred : numéro de passage à partir duquel re-proposer
reject_category: null   # hors-cap | mauvais-seuil | mauvaise-solution | pas-maintenant | deja-fait
reject_verbatim: null   # les mots exacts de l'humain — jamais reformulés
reject_reason: null     # reformulation par l'agent, RELUE par l'humain avant commit
---
## Proposition
Normaliser le loudness à -14 LUFS en sortie d'assemblage…
## Fait quand (critère d'acceptation)
La mesure LUFS des 2 dernières sorties ∈ [-14.5, -13.5] → critère du niveau 3
du rubric audio satisfait. (Le critère d'acceptation d'une proposition EST le
niveau de rubric visé et sa vérification — c'est ce qui ferme la boucle
rubric → proposition → implémentation → re-notation.)
## Ce que ça ne règle pas
…                    # licence de désaccord : dire aussi ce que la vision ignore
```

**Schéma de `scores.jsonl`** — un objet JSON par dimension et par passage :

```json
{"pass": 7, "date": "2026-08-12", "dimension": "audio-quality", "score": 2,
 "target": 4, "rubric_version": "a1b2c3d", "verification": "mesure",
 "evidence": ["sample_0811.mp4 : -8.2 LUFS"], "unchanged_since": null}
```

`rubric_version` est le hash court du fichier rubric au moment de la notation : un recalibrage du barème est détectable, et la trajectoire est re-basée (les scores d'avant ne se comparent pas à ceux d'après — jamais silencieusement). L'écriture passe par un **script du plugin** qui refuse la réécriture d'entrées passées ; le fichier est committé à chaque passage — le git log est l'audit trail. L'agent n'écrit jamais ce fichier à la main.

**Format de VISION.md** : front-matter avec `last-verified` (même discipline de fraîcheur que les rubrics — une vision morte fait proposer du hors-sujet avec une confiance parfaite) ; sections : ambition, non-buts, arbitrages assumés, licence de désaccord, et **budget par passage en unités applicables** (nombre max de fichiers lus intégralement, plafond de propositions) — pas en tokens, qu'aucun protocole ne peut compter de l'intérieur.

### 5.2 Le protocole du passage de cap

1. **Noter — incrémentalement.** `git diff` depuis le dernier passage : les dimensions dont les `files:` n'ont pas bougé **reportent** leur score précédent, marqué `unchanged_since` — jamais re-facturées. Les autres sont re-notées : collecter les preuves prescrites (lecture de code + mesures selon la règle déterministe du rubric) et poser un score argumenté. Règle de provenance héritée du plugin : chaque score cite ses preuves ou ne vaut rien. Soupape héritée de l'init : si un ensemble de `files:` est trop gros pour ce passage, le dire et réduire ou scinder — jamais compenser par de l'échantillonnage silencieux. Les scores sont écrits via le script append-only (§5.1).
2. **Diff** : comparer à `scores.jsonl` — ce qui monte, stagne, régresse. La *trajectoire* est l'information (« audio à 2/5 depuis 3 passages pendant que tout le reste monte ») — en sachant qu'elle est **vide aux passages 1-2** : ces passages valent comme premier état des lieux chiffré, pas comme boucle (assumé dans les critères §8).
3. **Choisir** : priorité = **(target − score) × poids numérique**, bonus de stagnation (≥ 2 passages sans progrès), malus si la dimension accumule des refus récents `hors-cap` ; égalité → l'humain tranche au tri. Les entrées de `adjacent.md` (§5.4) sont candidates ici. C'est l'application du modèle d'intérêt OMNI — faisable × intéressant — rendue calculable.
4. **Auditer** la dimension choisie en profondeur (contrat de profondeur du plugin : lecture intégrale des `files:` du rubric, avec la même soupape qu'à l'étape 1).
5. **Proposer** : ≤ 3 propositions, formats ci-dessus. Dédup contre l'archive — refusées ET ajournées non échues — comparée sur **dimension + files touchés + résumé structuré de l'intervention**, jamais sur le texte libre (une paraphrase n'est pas une nouveauté). Les refus *rapprochés mais écartés* de la dédup sont listés dans le rapport, pour que l'humain puisse contester.
6. **Auto-audit de complétude** (hérité de l'init) : dimensions non notées et pourquoi, couverture, question obligatoire « VISION.md contredit-il un choix produit réel des derniers passages ? ». Le rapport suit un **format standardisé et neutre** (ordre fixe : écart mesuré, preuve brute, coût — avant tout argumentaire) pour limiter le cadrage. **« Aucune proposition, cap tenu » est une sortie légitime** d'un passage — elle n'entre pas dans le calcul du taux d'acceptation. Le coût du passage est relevé **hors agent** (logs/facturation du harnais) — jamais auto-déclaré : un agent ne connaît pas sa propre consommation.

### 5.3 Le tri humain, et ce qu'il nourrit

L'humain trie chaque proposition : **oui / non + catégorie / plus tard**. La catégorie de refus est fermée — `hors-cap` (bannit : jamais re-proposé), `mauvais-seuil` (le rubric est faux, pas la proposition), `mauvaise-solution` (le gap est réel, l'esquisse non), `pas-maintenant` (→ `deferred` avec échéance de résurgence), `deja-fait` — plus un champ libre. C'est ce qui rend le tri à la fois **rapide** (une catégorie + quelques mots) et **calibrant** (un « non parce que bof » ne calibre rien ; une catégorie dit *ce qui* était faux : la dimension, le seuil, la solution ou le timing). Les mots exacts de l'humain sont stockés en `reject_verbatim`, la reformulation de l'agent en `reject_reason`, **relue avant commit** — c'est ça, la gouvernance de l'archive : verbatim conservé, reformulation contrôlée, catégories fermées. (La lignée [Proactive Agent](https://arxiv.org/abs/2410.12361) a montré qu'un modèle de « cette offre était-elle bienvenue ? » est entraînable ; ici on en fait la version artefact : l'agent relit catégories et raisons avant de proposer.)

### 5.4 Le contrat d'adjacence (capacité par-feature) — des entrées, pas des sorties

Toute fin de tâche **substantielle** — définie mécaniquement : la tâche a touché les `files:` d'au moins un rubric — ajoute jusqu'à 3 suites naturelles à `.claude/cap/adjacent.md` (une ligne datée + rubric référencé, dédupliquée à l'écriture contre le fichier ET l'archive). Ces suites ne sont **jamais montrées à l'humain hors passage** : elles sont lues comme candidates à l'étape 3 du passage suivant. La borne D4 (≤ 3 remontées par passage) reste ainsi la seule interface humaine — sans ce routage, 3 suites × 5-8 tâches/semaine = 40-90 suggestions/mois, le backlog-slop exact que D4 combat.

### 5.5 Format de livraison — où chaque brique vit

Réponse courte à « skill ? plugin ? MCP ? app externe ? modèle finetuné ? » : **tout vit dans le plugin codified-context existant** (décision D9), mais — vérifié contre le code réel — la réutilisation est faite d'**extensions ciblées**, pas de briques inchangées :

| Brique | Format concret | Statut |
|---|---|---|
| `/codified-context:course-check` (namespace du plugin) | **Skill du plugin** (même mécanique que `/init` : la commande porte tout le protocole) | nouveau |
| `VISION.md`, `.claude/rubrics/`, `.claude/proposals/`, `.claude/cap/` | **Fichiers versionnés du projet cible** — relisibles, éditables, committés | nouveau |
| Indexation des rubrics (retrouvables par `find_relevant_context`) | **Serveur MCP étendu** : scan de `.claude/rubrics/` (l'index actuel ne scanne que `.claude/context/`) + champs `description`/`keywords` dans le format rubric (sans eux, le scorer ne peut pas les retrouver) | **extension** |
| Fraîcheur des rubrics | **Gardien de dérive étendu** (≈ 5 points de code : classifier les rubrics comme docs) **+ un check de staleness temporelle à créer** — le mécanisme actuel détecte « code changé sans doc touchée », jamais l'âge de `last-verified` : un goût périmé sans changement de code est invisible pour lui | **extension + nouveau** |
| Validation des formats | `validate_architecture.py` **étendu** : checks génériques transposés (existence des `files:`, doublons, parsing) + checks de schéma **nouveaux** (enums weight/status/effort, table 1-5 complète, `reject_category` obligatoire si rejected, section « Fait quand ») | extension |
| Écriture de `scores.jsonl` | Script du plugin, append-only (§5.1) | nouveau |
| Déclenchement automatique | Routine/cron du harnais — **phase 3 uniquement** (D8) | plus tard |

Et ce qui est explicitement écarté :

- **App externe** : elle devrait redupliquer ce que le harnais fournit déjà (lecture du code, permissions, accès modèle) — coût maximal, bénéfice nul en phase 1.
- **Modèle finetuné** : rien ici n'exige des poids. Un finetune figerait le « goût » au moment de l'entraînement — l'exact opposé de rubrics versionnés que l'humain peut éditer un mardi soir. Le RL de la littérature (§1) informe la conception ; il n'est pas le livrable.
- **Nouveau serveur MCP** : rien à servir que l'index étendu ne servira pas.

### 5.6 Le workflow, concrètement (technico-fonctionnel)

**Mise en place — une fois par projet.** Lancer **`/codified-context:course-check`**. Il détecte l'absence de `VISION.md` et de rubrics → mode setup : interview (ambition, non-buts, dimensions de qualité — questions **répondues par l'humain**, règle héritée de l'init), l'agent propose VISION.md + 4-6 rubrics pré-remplis, l'humain arbitre **les critères par niveau** (pas seulement seuils et poids — le goût vit dans les critères, cf. D6), **rédige les sections de vérification externe** (cf. D5), décide la question de confidentialité (§5.1), relit, commite. **Charge honnête : comptez 2 à 4 h de travail humain réel** — 20 à 30 décisions de seuil que vous n'avez jamais formulées (c'est l'hypothèse fondatrice §1.2 : ce goût n'était écrit nulle part), plus une itération de correction attendue après les 2 premiers passages. L'heure d'écriture existe ; la pensée coûte le reste.

**Avant chaque passage — 30 secondes qui rendent le succès falsifiable.** L'humain note dans `.claude/cap/attentes/{n}.md` ce qu'il ferait ensuite s'il n'y avait pas de gardien (3 lignes max). C'est la base du critère de surprise (§8) : une proposition acceptée **absente de cette note** est une initiative prouvée — pas un souvenir reconstruit.

**À chaque passage — phase 1 : quand l'humain le décide** (fin de semaine, fin de milestone). Relancer la même commande. L'agent déroule seul le protocole §5.2. Sortie : un rapport en session (scores, trajectoire, ≤ 3 propositions) + les fichiers dans `.claude/proposals/`. **Coût machine estimé** (projet ~40k lignes, 5 rubrics) : de l'ordre de 2-8 $ en classe Sonnet, 15-40 $ en classe Opus, 45-120 min de wall-clock — surtout au premier passage ; les passages incrémentaux (étape 1) coûtent moins. À comparer aux 3-6 h humaines d'un audit équivalent.

**Le geste humain au tri : 15 à 40 minutes réelles par passage** — lire le rapport (~10 min), rendre les verdicts des rubrics en `verdict-humain` (préparés par l'agent en comparaisons A/B, 2-3 min par dimension, cf. D5), trier chaque proposition (catégorie + quelques mots — 2-5 min pour un refus qui calibre). Pas « trois mots » : trois mots ne calibrent rien, et ce design meurt si son archive est du bruit.

**Après le tri.** Une proposition acceptée devient une tâche normale : nouvelle session, « implémente la proposition `<id>` ». Le fichier contient l'écart, les preuves, l'esquisse **et le critère d'acceptation « Fait quand »** — c'est lui qui en fait un contrat au sens de la loi §1.2, pas l'esquisse seule. Au passage suivant, l'agent vérifie les propositions `done` contre leur critère et relit l'écart effort estimé/réel.

**Entre les passages : rien d'humain.** Les adjacences (§5.4) s'accumulent en silence comme candidates. Phase 3 : le scheduler lance le passage seul et ne laisse à l'humain que le tri du rapport.

En régime de croisière, la charge utilisateur est : **une commande, 30 s de pré-enregistrement, 15-40 min de jugement par passage, et l'entretien des rubrics quand le gardien de fraîcheur le demande**. C'est une conversion du pinpointing continu en jugement borné et périodique — pas son élimination, et ce document ne la promet plus.

## 6. Décisions de conception (alternatives rejetées incluses)

| # | Décision | Alternatives rejetées, et pourquoi |
|---|---|---|
| D1 | **Rubrics décomposés** comme référentiel du « mieux » | *Juge LLM à critère flou* : régresse vers le goût générique — [Rubrics as Rewards](https://arxiv.org/abs/2507.17746) mesure jusqu'à +31 % sur HealthBench (mais +7 % seulement sur GPQA-Diamond — le gain dépend du domaine) vs jugement Likert, avec moins de variance. *Métriques télémétriques seules* : aveugles au médiocre-fonctionnel. |
| D2 | **Propositions, jamais de diffs imposés** | L'alternative *forte* n'est pas l'auto-merge mais la **draft PR comme proposition** (fermable avec raison = même signal d'apprentissage). Rejetée quand même : générer ≤ 3 diffs complets par passage **avant** le tri est le chemin cher (on paie l'implémentation de ce qui sera refusé aux 2/3), et une proposition doit être triable au niveau du *gap* avant le niveau de la *solution*. Une draft PR reste possible en aval, pour une proposition déjà acceptée. |
| D3 | **Passage périodique complet** comme déclencheur principal | *Event-driven pur* : les alertes ne voient que la casse — le cas fondateur (« l'audio aurait dû être un audit ») leur est invisible. Mais l'event-driven de *complétion* (fin de feature) voit bien le médiocre adjacent : c'est exactement le contrat d'adjacence §5.4, intégré comme **entrée** du passage — D3 rejette le event-driven comme *cœur*, pas comme capteur. M3 (télémétrie) viendra en complément. |
| D4 | **≤ 3 propositions/passage, preuves obligatoires, dédup structurée contre l'archive** | *Sans borne* : le backlog-slop est le mode d'échec n°1 des outils de suggestion. La borne force la priorisation, la preuve force la lecture, la dédup (sur dimension + files + résumé structuré, §5.2.5) force la mémoire — une paraphrase n'est pas une nouveauté. |
| D5 | **Vérification typée par rubric : `mesure` \| `oracle` \| `verdict-humain` — déclarée au setup, rédigée par l'humain** | *Auto-évaluation pure* : dans [EvoTrace](https://arxiv.org/abs/2605.20086), 2 des 4 frameworks auto-améliorants étudiés surapprennent leur évaluateur sur ≥ 30 % des problèmes — le risque est réel, pas universel, et il suffit. Honnêteté sur la limite : une `mesure` exécutée et rapportée par l'agent est externe à son *jugement*, pas à sa *main* — les mitigations sont la règle d'échantillonnage déterministe (§5.1), le script append-only + git comme audit trail, et un **sondage humain périodique** (rejouer une vérification tous les N passages). Pour les dimensions sans mesure ni oracle : `verdict-humain` **préparé** (l'agent assemble des A/B en aveugle, l'humain tranche en 2-3 min) — borné et affiché, pas caché. Un projet où > 50 % des rubrics tomberaient en `verdict-humain` est un mauvais candidat (§10.1). |
| D6 | **Rubrics co-écrits — l'agent propose la structure, l'humain arbitre les critères par niveau, les seuils, les poids, ET rédige la vérification externe** | *Humain seul* : réaliste une fois (4-6 barèmes n'est pas le pinpointing continu que §1 dénonce — l'alternative n'est pas absurde), mais perd l'expertise de structuration de l'agent et rend le setup encore plus cher. *Agent seul* : le goût générique que D1 rejette rentrerait par la fenêtre — le goût vit dans les **critères par niveau**, pas dans les seuils ; les laisser à l'agent, c'est le laisser écrire son propre examen. Et les rubrics **dérivent aussi** : `last-verified` + gardien de dérive étendu + check de staleness (§5.5). |
| D7 | **Licence de désaccord écrite** + non-buts dans VISION.md | Sans elle, la déférence entraînée ([2607.26819](https://arxiv.org/abs/2607.26819)) fait ratifier le cadrage de l'humain ; les non-buts donnent à l'agent le droit de répondre « hors cap » — et la section « Ce que ça ne règle pas » institutionnalise le contre-point. Le risque résiduel — l'archive comme mémoire d'accommodements (la sycophancie mémorisée de §1.1 appliquée à nous-mêmes) — est traité par la gouvernance de §5.3 : catégories fermées, verbatim conservé, et le garde-fou Goodhart de §7. |
| D8 | **Phase 1 sans scheduler : passage manuel** | *Automatiser d'emblée (Routine nocturne)* : on automatiserait une boucle non validée — exactement le « prototyper vite » refusé. Le cron (M1) n'arrive qu'en phase 3, quand la boucle aura prouvé sa valeur en manuel. |
| D9 | **Extension de codified-context**, pas un nouveau framework | *Projet à part* : duplication de la plomberie. Chiffré honnêtement après lecture du code : le plugin fournit **~40 %** du code final (parseur front-matter générique, résolution de racine, harnais hooks/skills/MCP, squelette du validateur) ; l'index, les hooks et le validateur demandent des **extensions ciblées** (§5.5) ; le cœur — protocole, formats, archive, script scores — est à créer. `drift_stop` fournit le *pattern conversationnel* propose-puis-tri, pas le protocole à états. |
| D10 | **Rubrics dans `.claude/rubrics/` dédié, index et hooks étendus** | *Réutiliser `.claude/context/` sans toucher au code* : quatre effets de bord vérifiés contre le code — skills `ctx-*` parasites (ou warnings systématiques) dans le générateur, pollution de `list_subsystems` par des dimensions de qualité, sémantique de dérive inversée (chaque commit sous les `files:` d'un rubric déclencherait « update rubric », or un barème n'est pas invalidé par un changement de code) avec vol de suggestion par la dédup first-wins, et collisions de clés promues ERROR par le validateur. Un répertoire dédié + des extensions explicites coûtent moins cher que ces quatre poisons silencieux. |

## 7. Modes d'échec et garde-fous

| Mode d'échec | Garde-fou |
|---|---|
| Backlog-slop (noyade sous les propositions) | D4 : borne dure + preuves + dédup structurée ; les adjacences sont des entrées routées vers le passage, jamais un canal parallèle vers l'humain (§5.4) |
| L'agent s'auto-félicite (gaming du barème) | D5 : vérification typée, sections anti-triche rédigées par l'humain, échantillonnage déterministe, scores via script append-only (git = audit trail), sondage humain périodique |
| **Goodhart du consensuel** (le taux d'acceptation monte, l'audace meurt) | Suivre par passage la part de propositions de type *refonte/dérangeante* ; zéro sur 2 passages consécutifs = alerte explicite dans le rapport — indépendamment du taux d'acceptation |
| Sycophancie mémorisée (il ratifie tes biais) | D7 + gouvernance de l'archive (§5.3) : catégories fermées, `reject_verbatim` conservé, reformulation relue |
| Rubrics périmés (le goût d'il y a 6 mois) | `last-verified` + gardien de dérive étendu + **check de staleness temporelle** (§5.5 — le gardien actuel ne voit que le code) ; **recalibrage déclenché par un kill criterion : rédigé par l'humain seul** (exception à D6 — un agent menacé d'arrêt n'assouplit pas son propre barème), compteur d'acceptation gelé 1 passage après recalibrage |
| **VISION périmée** (un cap mort, suivi avec confiance) | `last-verified` sur VISION.md + question obligatoire de l'auto-audit (§5.2.6) |
| **Injection par les artefacts** (un rubric édité redirige le gardien) | Le contenu des rubrics/propositions est une **donnée, pas une instruction** : la collecte de preuves se limite à lecture de fichiers du repo + commandes de mesure sur liste blanche ; tout diff touchant « Preuves à collecter » ou « Vérification externe » est relu par l'humain avant le passage suivant |
| **Confidentialité** (stratégie et faiblesses publiées) | Décision explicite au setup (§5.1) : repo privé ou artefacts exclus du remote public |
| **Cacophonie des deux gardiens** (dérive + cap + adjacences) | Budget d'interruptions partagé par session entre les deux gardiens, file unique — avant de diagnostiquer « l'humain court-circuite le tri » comme un défaut du format, vérifier la surcharge globale |
| Coût qui dérape | Budget en **unités applicables** (fichiers lus intégralement max, dans VISION.md) + notation incrémentale (§5.2.1) + coût relevé **hors agent** — jamais auto-déclaré |
| Lassitude du tri | Automate unique de §8 : recalibrer avant de tuer, et « aucune proposition, cap tenu » est une sortie légitime — un produit au niveau visé n'est pas un gardien cassé |

## 8. Critères de succès et d'arrêt (phase 1)

Sur 4 passages de cap manuels sur un projet réel — en assumant que les passages 1-2 sont un **baseline** (trajectoire et archive quasi vides) et que la boucle ne se montre qu'aux passages 3-4 :

**Succès — critères directionnels, pas statistiques** (sur ≤ 12 propositions, un taux est du bruit : un système véritablement à 1/3 d'acceptation échouerait un seuil « ≥ 1/3 » avec ~39 % de probabilité) :

- chaque passage produit ≥ 1 proposition acceptée **ou** une sortie « cap tenu » argumentée ;
- ≥ 1 proposition acceptée dont la dimension est **absente de la note pré-enregistrée** du passage (`.claude/cap/attentes/` — la surprise falsifiable, *le* test de l'initiative) ;
- ≥ 1 refus dont la catégorie a **visiblement changé une proposition ultérieure** (la calibration observée, mesurable dès le passage 3) ;
- zéro re-proposition d'un refus `hors-cap` ;
- coût par passage sous le budget de VISION.md (relevé hors agent).

**Automate d'arrêt — un seul, unifié** : taux d'acceptation < 1/3 sur une fenêtre glissante de 3 passages → **recalibrage obligatoire des rubrics, rédigé par l'humain seul** (cf. §7), compteur gelé 1 passage ; taux < 10 % **après** recalibrage → arrêt/refonte. Si l'humain court-circuite le tri : diagnostiquer d'abord la surcharge cumulée des deux gardiens (§7) avant de conclure au défaut du format. Un passage qui coûte durablement plus que la valeur des propositions acceptées (jugement humain explicite, pas une métrique) → arrêt.

## 9. Plan par phases (chaque phase validée avant la suivante)

| Phase | Contenu | Critère d'entrée en phase suivante |
|---|---|---|
| **1 — Fondations** | Formats VISION/rubric/proposition + **`scores.jsonl` + script append-only + dédup contre archive** (le protocole §5.2 en a besoin dès le premier passage — les reléguer plus tard rendrait la phase 1 injugeable par §8) + skill `/codified-context:course-check` (manuel) + **extensions index/hooks/validateur** (§5.5) + pré-enregistrement des attentes + co-écriture des premiers rubrics sur UN projet réel | 4 passages, critères §8 atteints |
| **2 — Capteurs** | Contrat d'adjacence (`adjacent.md` comme entrée, §5.4) + exploitation pleine du diff de trajectoire + mesure du contrefactuel de choix (le choix de dimension est produit **avant** lecture du diff, puis après — on compte les divergences) | Le diff change réellement les choix, mesuré par ce contrefactuel |
| **3 — Autonomie** | Scheduler (Routine/heartbeat) + rapport de passage asynchrone + calibration par les catégories de refus | Taux d'acceptation stable ≥ 1/3 en asynchrone ; coût multi-projets soutenable (le nocturne multi-projets multiplie le coût de §5.6) |
| **4 — Exploratoire** | Co-évolution des rubrics (`/refine` à preuves façon prime-agent) — avec un **instantané « golden » gelé** de chaque rubric, non modifiable par l'agent, comparé périodiquement à la version co-évoluée pour détecter la complaisance progressive ; M3 (télémétrie) en entrée complémentaire ; multi-projets | — |

En complément du plan : **tester le gardien lui-même** avant de lui confier un cap — re-noter deux fois un état figé du projet et mesurer la variance inter-passages ; noter un commit ancien dont l'humain connaît déjà les défauts et vérifier qu'ils sortent. Un juge non reproductible n'a pas à juger une trajectoire.

## 10. Questions ouvertes (à trancher avant la phase 1)

1. Le projet-cobaye de la phase 1 — il faut un projet réel où le « médiocre-fonctionnel » se ressent, **et où les dimensions sont majoritairement mesurables** : un projet où > 50 % des rubrics tomberaient en `verdict-humain` est un mauvais premier terrain (D5). (Le choix du projet se fait en privé, pas dans ce document.)
2. La granularité des dimensions : 4-6 rubrics larges ou 10+ fins ? (Intuition : commencer large, scinder quand un rubric génère des propositions trop hétérogènes.)
3. VISION.md et rubrics : français (projets perso) — mais faut-il des exemples anglais dans le plugin pour le partage ?
4. Le nom public : *course guardian* / *cap* / autre ?
5. Le critère de surprise pré-enregistré (§5.6/§8) impose un rituel de 30 s à l'humain : le garder tel quel, ou n'exiger la note qu'aux passages d'évaluation (3 et 4) ?

---

### Historique de revue

- **v1 (09/08/2026)** : rédaction initiale.
- **v2 (10/08/2026)** : intégration d'une revue adversariale à six angles (~60 findings dédupliqués). Principaux changements : citations corrigées contre les sources primaires (SWE-EVO : comparaison inter-benchmarks, pas ablation ; DGM : rétention = compile + auto-éditable, pas filtre benchmark ; Rubrics-as-Rewards : +31 % HealthBench mais +7 % GPQA ; PROBE, OMNI, EvoTrace, compliance : portées précisées) ; claim de niche resserrée (précédent Cognition/Devin cité) ; statuts « existant, inchangé » de §5.5 corrigés contre le code réel (index et hooks = extensions ; ~70 % → ~40 % dans D9 ; D10 ajoutée) ; phase 1 réconciliée avec le protocole (`scores.jsonl` et dédup remontés en phase 1) ; D5 réécrit (vérification typée, sections anti-triche rédigées par l'humain, sondage périodique) ; gouvernance de l'archive spécifiée (catégories fermées, verbatim, relecture) ; état `deferred` ajouté ; fonction de choix rendue calculable (`target`, poids numérique) ; adjacences routées en entrées ; critères §8 rendus directionnels et falsifiables (pré-enregistrement), automate d'arrêt unifié ; charge humaine et coûts machine chiffrés honnêtement ; garde-fous ajoutés (Goodhart du consensuel, VISION périmée, injection par artefacts, confidentialité, cacophonie des deux gardiens) ; plan de test du gardien lui-même.

### Sources principales

*Littérature* : [Implicit Intelligence](https://arxiv.org/abs/2602.20424) · [PROBE](https://arxiv.org/abs/2510.19771) · [SWE-EVO](https://arxiv.org/abs/2512.18470) · [Proactivity, Not Just Autonomy](https://arxiv.org/abs/2605.06717) · [PPP/UserVille](https://arxiv.org/abs/2511.02208) · [Proactive Agent](https://arxiv.org/abs/2410.12361) · [Rubrics as Rewards](https://arxiv.org/abs/2507.17746) · [Voyager](https://arxiv.org/abs/2305.16291) · [OMNI](https://arxiv.org/abs/2306.01711) · [DGM](https://arxiv.org/abs/2505.22954) · [EvoTrace](https://arxiv.org/abs/2605.20086) · [sycophancie mémorisée](https://arxiv.org/abs/2607.10526) · [compliance des agents](https://arxiv.org/abs/2607.26819) · [survey self-evolving coding agents](https://arxiv.org/abs/2608.03392)

*Écosystème* : [prime-agent](https://github.com/PrimeIntellect-ai/prime-agent) · [snarktank/ralph](https://github.com/snarktank/ralph) · [Spec Kit](https://github.com/github/spec-kit) · [OpenSpec](https://github.com/Fission-AI/OpenSpec) · [DGM code](https://github.com/jennyzzt/dgm) · [Tembo](https://docs.tembo.io/integrations/sentry) · [OpenClaw heartbeat](https://docs.openclaw.ai/gateway/heartbeat) · [Ralph (origine)](https://ghuntley.com/ralph/) · [Cognition — Devin daily audit](https://cognition.ai/blog/how-cognition-uses-devin-to-build-devin)

*Réserves de vérification (v2)* : les 14 sources arXiv ont été vérifiées contre leurs abstracts (via extraits indexés — l'accès direct à arxiv.org était bloqué depuis l'environnement de revue) ; Tembo, OpenClaw et ghuntley.com vérifiés par corroboration secondaire (pages bloquées par le proxy de l'environnement, pas mortes) ; « Dreaming/Outcomes » (Anthropic) connu par sources secondaires uniquement ; benchmarks vendeurs non vérifiés.
