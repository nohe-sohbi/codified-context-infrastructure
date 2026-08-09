# Gardien de cap — document de conception

> **Statut : proposition, à démonter avant toute implémentation.**
> Rédigé le 09/08/2026, à partir de deux revues (littérature nov. 2025 → août 2026, écosystème outillage) et des 12 leçons de terrain du plugin codified-context. Sources en fin de document.

## 0. Le nom, parce qu'il dit l'idée

Le plugin possède un **gardien de dérive** (*drift guardian*) : il mesure l'écart entre le code et les **faits** documentés, et le convertit en propositions de mise à jour. Ce document conçoit son symétrique d'un étage au-dessus : le **gardien de cap** (*course guardian*) — il mesure l'écart entre l'état du produit et sa **direction** déclarée, et le convertit en propositions d'amélioration. La dérive corrige le passé qui ment ; le cap tire vers le futur qui manque.

---

## 1. Le problème

Les agents de code exécutent bien et proposent mal. Trois manifestations vécues (sessions réelles sur trois projets personnels distincts) :

1. la demande est exécutée *stricto sensu* — les exigences implicites ne sont pas inférées ;
2. les suites naturelles d'une feature ne sont jamais proposées ;
3. personne ne dit jamais « l'audio mérite un audit » — l'humain doit *pinpointer* chaque amélioration possible, ce qui fait de lui le goulot d'étranglement de son propre projet.

### 1.1 Ce que la littérature établit (avec les réserves qui s'imposent)

- **Le gap est mesuré par trois angles indépendants.** [Implicit Intelligence](https://arxiv.org/abs/2602.20424) (fév. 2026) : ~48 % des exigences implicites satisfaites au mieux — *chiffre à prendre comme indicatif* : environnement et juge simulés par LLM (circularité possible), choix des « exigences implicites » discutable, papier récent non consolidé. Mais [PROBE](https://arxiv.org/abs/2510.19771) (équipe et méthode différentes) localise le même goulot — *trouver le problème non formulé*, pas l'exécuter — et [SWE-EVO](https://arxiv.org/abs/2512.18470) mesure l'effondrement 73 % → 25 % quand la consigne passe du ticket au niveau roadmap. Le chiffre exact est fragile ; le phénomène est sur-déterminé (et confirmé par nos propres transcripts).
- **La littéralité est une politique, pas une bêtise.** Les agents ne refusent jamais un travail et ne récupèrent presque jamais les règles d'eux-mêmes ([étude compliance, juil. 2026](https://arxiv.org/abs/2607.26819)) ; la sycophancie **se compose avec la mémoire** (+27 pts d'échec quand un accommodement est mémorisé — [arXiv:2607.10526](https://arxiv.org/abs/2607.10526)). Conséquence de conception : l'initiative doit être **contractualisée**, et la licence de désaccord **écrite**.
- **Le vocabulaire existe** : l'« *insight policy* » ([Agentic Coding Needs Proactivity, Not Just Autonomy](https://arxiv.org/abs/2605.06717), mai 2026) — la politique qui décide *ce qui compte ensuite, avec quelles preuves, s'il faut le remonter, et comment apprendre du feedback*. Ce document est la conception d'une insight policy pour un projet logiciel.

### 1.2 La loi des 12 leçons, montée d'un étage

Toute l'expérience du plugin tient en une loi : *un agent est exactement aussi bon que son contrat, jamais plus*. « Améliore mon app » n'est pas un contrat : « mieux » n'y est défini nulle part. Le diagnostic central de ce document : **le manque d'autonomie n'est pas un manque d'intelligence, c'est un artefact manquant** — nulle part dans un repo n'est écrit *vers quoi* le produit tend ni *à quoi ressemble la qualité*. codified-context capture l'**état** (comment ça marche) ; il manque la **direction** (vers quoi) et le **goût** (qu'est-ce que « bien »). Un agent ne peut pas proposer « l'audio mérite un audit » si « qualité audio » n'existe pas comme dimension notée quelque part.

La démonstration par l'absurde existe déjà, shippée : les agents SEO 2026 livrent exactement le comportement voulu (audits auto-déclenchés, plan d'action hebdo priorisé) **parce que le SEO a un barème standardisé** (Core Web Vitals, erreurs de crawl, positions). Le mécanisme est le même ; seul le référentiel manque ailleurs.

## 2. Vocabulaire

| Terme | Définition |
|---|---|
| **Rubric** | Barème d'une dimension de qualité : échelle 1-5, critères observables par niveau, indices de preuve. Le « goût » rendu vérifiable. |
| **Vision** | Document de direction : ce que le produit essaie de devenir, les non-buts, les arbitrages assumés. |
| **Passage de cap** (*course-check*) | Session d'audit : noter chaque rubric avec preuves, comparer au passage précédent, choisir la dimension prioritaire, produire ≤ N propositions. |
| **Proposition** | Artefact structuré (écart mesuré + preuve + esquisse + coût estimé) soumis au tri humain. Jamais un diff imposé. |
| **Archive** | Historique des scores et des propositions (acceptées/refusées/faites) — la mémoire qui calibre « quoi proposer ensuite ». |
| **Insight policy** | La politique complète ci-dessus : quoi regarder, quoi remonter, quand, et comment apprendre du tri. |
| **Lignée OMNI/Voyager/DGM** | Recherche « open-ended » : un agent choisit sa prochaine tâche depuis une archive de l'acquis ([Voyager](https://arxiv.org/abs/2305.16291) : auto-curriculum ; [OMNI](https://arxiv.org/abs/2306.01711) : modèle d'intérêt = nouveau × faisable × utile ; [DGM](https://arxiv.org/abs/2505.22954) : auto-modifications gardées si elles améliorent un benchmark). Personne n'a pointé cette machinerie vers une roadmap produit — c'est la niche. |

## 3. Périmètre

**Est** : une couche d'initiative construite *au-dessus* d'un agent littéral, pour un projet donné ; des artefacts versionnés + un protocole de session + des garde-fous ; une extension de codified-context (réutilise l'index, les hooks, la discipline de fraîcheur).

**N'est pas** : de l'entraînement de modèle (pas de RL ici — les mécanismes RL de la littérature informent la conception, ils ne sont pas le livrable) ; un agent qui merge tout seul ; un framework généraliste ; un scheduler dès la phase 1 (voir D8).

## 4. Les six mécanismes d'initiative observés, et la composition retenue

Le sweep écosystème (août 2026) montre que **toute** initiative shippée est fabriquée par composition de six mécanismes — jamais par « un modèle plus malin » :

| # | Mécanisme | Exemple vérifié | Limite |
|---|---|---|---|
| M1 | Scheduler + prompt permanent | Claude Code Routines ; rapports CodeRabbit | L'initiative vit dans le cron, pas dans l'agent |
| M2 | Backlog à états | [snarktank/ralph](https://github.com/snarktank/ralph) (`prd.json`, drapeaux pass/fail) | Un humain écrit encore le backlog |
| M3 | Télémétrie-comme-backlog | Tembo (alertes prod → PRs) | Ne voit que le *cassé*, jamais le *médiocre* |
| M4 | Boucle rubric/juge | [Spec Kit](https://github.com/github/spec-kit) `/analyze` ; agents SEO ; « Outcomes » | Exige un référentiel — précisément ce qui manque |
| M5 | Mémoire auto-modifiable | prime-agent Continual Harness ; « Dreaming » | Méta-vue de *l'agent*, pas du *produit* |
| M6 | Évolution filtrée par benchmark | [DGM](https://github.com/jennyzzt/dgm) | Recherche ; exige une métrique vérifiable |

**Composition retenue : M4 comme cœur (le référentiel qu'on va créer), M2 comme sortie (propositions à états), M1 comme déclencheur (en phase 3 seulement), M5 en emprunt ciblé (le `/refine` à preuves de prime-agent, appliqué aux rubrics).** M3 est complémentaire (plus tard) ; M6 est hors périmètre.

## 5. Architecture

### 5.1 Les artefacts (Tier 0 — la direction et le goût)

```
VISION.md                     # direction : ambition, non-buts, arbitrages assumés
.claude/rubrics/{dim}.md      # un barème par dimension de qualité
.claude/proposals/{id}.md     # les propositions, avec leur cycle de vie
.claude/cap/scores.jsonl      # l'historique des passages (append-only)
```

**Format d'un rubric** (même discipline front-matter que les docs de contexte — indexé, validé, surveillé pareil) :

```yaml
---
dimension: audio-quality
name: Qualité audio des vidéos produites
weight: high                  # poids dans la priorisation
files:                        # où cette dimension vit dans le code
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
- sortir 2 échantillons récents et mesurer LUFS réel
## Vérification externe (anti-triche)
- la note ne peut pas monter sans mesure LUFS ou test d'écoute
```

**Format d'une proposition** :

```yaml
---
id: 2026-08-12-audio-normalisation
dimension: audio-quality
gap: "score 2/5, stagnant depuis 3 passages, weight high"
evidence: ["pipeline/audio/mix.py:34 — aucun appel de normalisation", "sample_0811.mp4 : -8.2 LUFS mesuré"]
effort: M            # S/M/L — estimation honnête
status: proposed     # proposed | accepted | rejected | done
reject_reason: null  # OBLIGATOIRE si rejected — c'est le signal d'apprentissage
---
## Proposition
Normaliser le loudness à -14 LUFS en sortie d'assemblage…
## Ce que ça ne règle pas
…                    # licence de désaccord : dire aussi ce que la vision ignore
```

### 5.2 Le protocole du passage de cap

1. **Noter** : pour chaque rubric, collecter les preuves prescrites (lecture de code + mesures externes) et poser un score argumenté. Règle de provenance héritée du plugin : chaque score cite ses preuves ou ne vaut rien.
2. **Diff** : comparer à `scores.jsonl` — ce qui monte, stagne, régresse. La *trajectoire* est l'information (« audio à 2/5 depuis 3 passages pendant que tout le reste monte »).
3. **Choisir** : dimension prioritaire = f(écart au niveau visé, poids, stagnation, archive des refus). C'est l'application directe du modèle d'intérêt OMNI : nouveau (pas déjà refusé) × faisable (effort estimable) × utile (poids × écart).
4. **Auditer** la dimension choisie en profondeur (contrat de profondeur du plugin : lecture intégrale des `files:` du rubric).
5. **Proposer** : ≤ 3 propositions, formats ci-dessus, dédupliquées contre l'archive (y compris les refusées — leçon « dedup vs seen » du premier jour du projet).
6. **Auto-audit de complétude** (hérité de l'init) : dimensions non notées et pourquoi, couverture, coût du passage.

### 5.3 Le tri humain, et ce qu'il nourrit

L'humain trie : oui / non (+ raison) / plus tard. Ce tri est **le signal d'apprentissage** : l'archive des accepte/refuse-avec-raison calibre les passages suivants (la lignée [Proactive Agent](https://arxiv.org/abs/2410.12361) a montré qu'un modèle de « cette offre était-elle bienvenue ? » est entraînable ; ici on en fait la version artefact : l'agent relit les raisons de refus avant de proposer).

### 5.4 Le contrat d'adjacence (capacité par-feature)

Indépendamment des passages de cap : toute fin de tâche substantielle inclut une étape obligatoire « 3 suites naturelles de cette feature, une ligne chacune, référencées aux rubrics concernés ». Même mécanique que l'auto-audit de complétude — une exigence de contrat, pas une capacité de modèle.

### 5.5 Format de livraison — où chaque brique vit

Réponse courte à « skill ? plugin ? MCP ? app externe ? modèle finetuné ? » : **tout vit dans le plugin codified-context existant** (c'est la décision D9, déclinée brique par brique) :

| Brique | Format concret | Statut |
|---|---|---|
| `/course-check` | **Skill du plugin** (même mécanique que `/init` : la commande porte tout le protocole, aucun prompt à rédiger) | nouveau |
| `VISION.md`, `.claude/rubrics/`, `.claude/proposals/`, `.claude/cap/` | **Fichiers versionnés du projet cible** — relisibles, éditables, committés comme le reste | nouveau |
| Indexation des rubrics (retrouvables par `find_relevant_context`) | **Serveur MCP existant**, inchangé — le front-matter des rubrics suit la même discipline que les docs de contexte, l'index les avale tel quel | existant |
| Fraîcheur des rubrics (`last-verified`) | **Gardien de dérive existant**, inchangé | existant |
| Validation des formats | `validate_architecture.py` **étendu** (rubrics et propositions = mêmes checks que les docs) | extension |
| Déclenchement automatique | Routine/cron du harnais — **phase 3 uniquement** (D8) | plus tard |

Et ce qui est explicitement écarté :

- **App externe** : elle devrait redupliquer ce que le harnais fournit déjà (lecture du code, permissions, accès modèle) — coût maximal, bénéfice nul en phase 1.
- **Modèle finetuné** : rien ici n'exige des poids. Un finetune figerait le « goût » au moment de l'entraînement — l'exact opposé de rubrics versionnés que l'humain peut éditer un mardi soir. Le RL de la littérature (§1) informe la conception ; il n'est pas le livrable.
- **Nouveau serveur MCP** : rien à servir que l'index existant ne sert pas déjà.

### 5.6 Le workflow, concrètement (technico-fonctionnel)

**Mise en place — une fois par projet, une session (~1 h la première fois) :**

1. Le plugin est déjà installé — rien de plus à installer.
2. Lancer **`/course-check`**. Il détecte l'absence de `VISION.md` et de rubrics → bascule en mode setup : interview courte (ambition du produit, non-buts, dimensions de qualité qui comptent — questions **répondues par l'humain**, jamais auto-répondues, règle héritée de l'init), puis il propose `VISION.md` + 4-6 rubrics pré-remplis, l'humain arbitre seuils et poids (D6), relit, commite.

**À chaque passage — phase 1 : quand l'humain le décide (fin de semaine, fin de milestone…) :**

3. Lancer **`/course-check`** (la même commande — elle détecte que le setup existe). L'agent déroule seul le protocole §5.2 : noter avec preuves, diff de trajectoire, choisir la dimension, auditer en profondeur, produire ≤ 3 propositions.
4. Sortie : un **rapport en session** (scores, trajectoire, propositions) + les fichiers dans `.claude/proposals/`.
5. Le geste humain : **trois mots par proposition** — « 1 oui, 2 non parce que X, 3 plus tard ». L'agent met à jour `status`/`reject_reason` dans les fichiers. C'est tout le tri.

**Après le tri :**

6. Une proposition acceptée devient une tâche normale : nouvelle session, « implémente la proposition `<id>` » — le fichier contient déjà l'écart, les preuves et l'esquisse, donc le contrat est déjà écrit.

**Entre les passages : rien.** Phase 2 ajoute le contrat d'adjacence (3 suites proposées automatiquement en fin de tâche substantielle) ; phase 3 fait tourner le passage tout seul (Routine) et ne laisse à l'humain que le tri du rapport.

En régime de croisière, la charge utilisateur totale est : **lancer une commande, répondre oui/non/raison**. Zéro prompt à rédiger, zéro fichier à écrire à la main.

## 6. Décisions de conception (alternatives rejetées incluses)

| # | Décision | Alternatives rejetées, et pourquoi |
|---|---|---|
| D1 | **Rubrics décomposés** comme référentiel du « mieux » | *Juge LLM à critère flou* : régresse vers le goût générique — la lignée [Rubrics-as-Rewards](https://arxiv.org/abs/2507.17746) montre ~+30 % vs jugement Likert et moins de variance. *Métriques télémétriques seules* : aveugles au médiocre-fonctionnel. |
| D2 | **Propositions, jamais de diffs imposés** | *Auto-PR façon Tembo* : coût d'erreur asymétrique (une proposition ratée = 10 s de tri ; un diff raté = revert + confiance brûlée) et surtout **perte du signal d'apprentissage** — sans tri explicite, pas d'archive accepte/refuse, donc pas de calibration. |
| D3 | **Passage périodique complet** comme déclencheur principal | *Event-driven pur* : ne voit que ce qui casse. Le cas d'usage fondateur (« l'audio aurait dû être un audit ») est invisible à toute alerte. L'event-driven (M3) viendra en complément, pas en cœur. |
| D4 | **≤ 3 propositions/passage, preuves obligatoires, dédup contre l'archive** | *Sans borne* : le backlog-slop est le mode d'échec n°1 (50 suggestions/nuit → désinstallation). La borne force la priorisation, la preuve force la lecture, la dédup force la mémoire. |
| D5 | **Vérification externe des scores** (mesures, tests, verdict humain) | *Auto-évaluation pure* : les boucles auto-améliorantes surapprennent leur propre évaluateur ([EvoTrace](https://arxiv.org/abs/2605.20086)). Chaque rubric déclare sa vérification non-contrôlée-par-l'agent. |
| D6 | **Rubrics co-écrits** : l'agent les propose (il sait ce qu'est un barème audio), l'humain arbitre seuils et poids | *Humain seul* : on retombe dans le pinpointing qu'on veut éliminer. *Agent seul* : goût générique + sycophancie. Et les rubrics **dérivent aussi** : `last-verified`, surveillés par le gardien de dérive existant — même discipline de fraîcheur que les faits. |
| D7 | **Licence de désaccord écrite** + non-buts dans VISION.md | Sans elle, la déférence entraînée ([2607.26819](https://arxiv.org/abs/2607.26819)) fait ratifier le cadrage de l'humain ; les non-buts donnent à l'agent le droit de répondre « hors cap » — et la section « Ce que ça ne règle pas » institutionnalise le contre-point. |
| D8 | **Phase 1 sans scheduler : `/course-check` manuel** | *Automatiser d'emblée (Routine nocturne)* : on automatiserait une boucle non validée — exactement le « prototyper vite » refusé. Le cron (M1) n'arrive qu'en phase 3, quand la boucle aura prouvé sa valeur en manuel. |
| D9 | **Extension de codified-context**, pas un nouveau framework | *Projet à part* : duplication de l'index, des validateurs, des hooks, de la discipline front-matter — le plugin est déjà ~70 % de l'infrastructure (l'index indexe les rubrics tel quel ; le gardien de dérive les surveille tel quel ; le protocole proposition/tri existe dans drift_stop). |

## 7. Modes d'échec et garde-fous

| Mode d'échec | Garde-fou |
|---|---|
| Backlog-slop (noyade sous les propositions) | D4 : borne dure + preuves + dédup contre les refusées |
| L'agent s'auto-félicite (gaming du barème) | D5 : vérification externe déclarée par rubric ; la note ne monte pas sans elle |
| Sycophancie mémorisée (il ratifie tes biais) | D7 : licence de désaccord + section contre-point obligatoire + gouvernance de ce qui entre dans l'archive |
| Rubrics périmés (le goût d'il y a 6 mois) | D6 : `last-verified` + gardien de dérive existant appliqué aux rubrics |
| Coût qui dérape (passages trop chers) | Budget par passage déclaré dans VISION.md ; le rapport de passage affiche son coût |
| Lassitude du tri (l'humain ne trie plus) | Taux d'acceptation suivi dans l'archive : < 1/3 sur 3 passages = signal que les rubrics ou la borne sont mal calibrés — c'est un **kill criterion**, pas un détail |

## 8. Critères de succès et d'arrêt (phase 1)

Sur 4 passages de cap manuels sur un projet réel :

- **Succès** : ≥ 1/3 des propositions acceptées ; ≥ 1 proposition acceptée que l'humain reconnaît ne pas avoir eue en tête (*le* test de l'initiative) ; coût par passage sous le budget déclaré ; zéro proposition dupliquée d'un refus antérieur.
- **Arrêt/refonte** : < 10 % d'acceptation après recalibrage des rubrics ; ou l'humain court-circuite le tri (signal que le format ne sert pas) ; ou le passage coûte plus cher que la valeur des propositions acceptées.

## 9. Plan par phases (chaque phase validée avant la suivante)

| Phase | Contenu | Critère d'entrée en phase suivante |
|---|---|---|
| **1 — Fondations** | Formats VISION/rubric/proposition + skill `/course-check` (manuel) + extension du validateur (rubrics = mêmes checks que les docs) + co-écriture des premiers rubrics sur UN projet réel | 4 passages, critères §8 atteints |
| **2 — Mémoire** | `scores.jsonl` + diff de trajectoire + dédup contre archive + contrat d'adjacence en fin de tâche | Le diff change réellement les choix de dimension |
| **3 — Autonomie** | Scheduler (Routine/heartbeat) + rapport de passage asynchrone + calibration par les raisons de refus | Taux d'acceptation stable ≥ 1/3 en asynchrone |
| **4 — Exploratoire** | Co-évolution des rubrics (`/refine` à preuves façon prime-agent) ; M3 (télémétrie) en entrée complémentaire ; multi-projets | — |

## 10. Questions ouvertes (à trancher avant la phase 1)

1. Le projet-cobaye de la phase 1 — il faut un projet réel où le « médiocre-fonctionnel » se ressent. (Le choix du projet se fait en privé, pas dans ce document.)
2. La granularité des dimensions : 4-6 rubrics larges ou 10+ fins ? (Intuition : commencer large, scinder quand un rubric génère des propositions trop hétérogènes.)
3. VISION.md et rubrics : français (projets perso) — mais faut-il des exemples anglais dans le plugin pour le partage ?
4. Le nom public : *course guardian* / *cap* / autre ?

---

### Sources principales

*Littérature* : [Implicit Intelligence](https://arxiv.org/abs/2602.20424) · [PROBE](https://arxiv.org/abs/2510.19771) · [SWE-EVO](https://arxiv.org/abs/2512.18470) · [Proactivity, Not Just Autonomy](https://arxiv.org/abs/2605.06717) · [PPP/UserVille](https://arxiv.org/abs/2511.02208) · [Proactive Agent](https://arxiv.org/abs/2410.12361) · [Rubrics as Rewards](https://arxiv.org/abs/2507.17746) · [Voyager](https://arxiv.org/abs/2305.16291) · [OMNI](https://arxiv.org/abs/2306.01711) · [DGM](https://arxiv.org/abs/2505.22954) · [EvoTrace](https://arxiv.org/abs/2605.20086) · [sycophancie mémorisée](https://arxiv.org/abs/2607.10526) · [compliance des agents](https://arxiv.org/abs/2607.26819) · [survey self-evolving](https://arxiv.org/abs/2608.03392)

*Écosystème* : [prime-agent](https://github.com/PrimeIntellect-ai/prime-agent) · [snarktank/ralph](https://github.com/snarktank/ralph) · [Spec Kit](https://github.com/github/spec-kit) · [OpenSpec](https://github.com/Fission-AI/OpenSpec) · [DGM code](https://github.com/jennyzzt/dgm) · [Tembo](https://docs.tembo.io/integrations/sentry) · [OpenClaw heartbeat](https://docs.openclaw.ai/gateway/heartbeat) · [Ralph (origine)](https://ghuntley.com/ralph/)

*Réserves de vérification* : « Dreaming/Outcomes » (Anthropic) connu par sources secondaires uniquement ; benchmarks vendeurs (Greptile 82 %, Harvey 6x) non vérifiés ; Implicit Intelligence : voir §1.1.
