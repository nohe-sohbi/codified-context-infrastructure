# Codified Context Infrastructure — analyse, croisements récents et axes d'amélioration

> Document de travail (août 2026) pour le fork de [codified-context-infrastructure](https://github.com/arisvas4/codified-context-infrastructure), compagnon du papier *« Codified Context: Infrastructure for AI Agents in a Complex Codebase »* (Vasilopoulos, [arXiv:2602.20478](https://arxiv.org/abs/2602.20478), février 2026).
>
> Objectifs : (1) expliquer le concept simplement, (2) le croiser avec les concepts et outils apparus depuis la publication, (3) proposer des axes d'amélioration et d'implémentation concrets pour ce dépôt.

---

## TL;DR

- **Le concept** : les agents de code (Claude Code, Cursor, Codex…) n'ont pas de mémoire entre les sessions. Le papier propose de traiter la **documentation comme une infrastructure** : un ensemble structuré de fichiers Markdown écrits *pour l'IA* (pas pour les humains), organisés en 3 étages selon leur fréquence de chargement — et qui simulent une mémoire persistante du projet.
- **La preuve** : l'auteur (chimiste de formation, pas développeur) a construit un jeu multijoueur C# de 108 000 lignes en 70 jours à temps partiel, avec Claude Code comme seul générateur de code, en s'appuyant sur ~26 000 lignes de « connaissance codifiée ».
- **Ce qui a changé depuis** : une grande partie de ce que le papier construit à la main existe désormais en primitives natives (Agent Skills et leur *progressive disclosure*, auto memory de Claude Code, standard AGENTS.md sous Linux Foundation, hooks, plugins…). Le concept n'est pas périmé pour autant : c'est la **méthode** (quoi codifier, quand, comment le maintenir frais) qui reste la vraie contribution — et son composant le plus original, le **détecteur de dérive doc↔code, n'a toujours pas d'équivalent dominant** en 2026.
- **Le débat à connaître** : deux études contrôlées de 2026 trouvent que les fichiers de contexte *génériques* n'améliorent pas le taux de réussite (et coûtent +20 % de tokens), tandis qu'un contexte *accordé itérativement* fait gagner +7,5 points sur SWE-bench. La variable discriminante — curation + fraîcheur — est exactement ce que ce dépôt outille.
- **Axes proposés** : moderniser l'implémentation (skills, AGENTS.md + règles conditionnelles, plugin installable), fiabiliser (source unique de vérité pour l'index, dérive sémantique, CI), automatiser la boucle d'apprentissage (distillation des leçons de session façon ACE), et évaluer (benchmark contrôlé — qui répondrait au débat ci-dessus).

---

## 1. Le concept, expliqué simplement

### 1.1 Le problème : des agents amnésiques

Un agent de code démarre chaque session **sans aucun souvenir** des sessions précédentes : conventions établies, erreurs déjà commises, architecture décidée la semaine dernière — tout est oublié. Sur un petit projet, un fichier unique (`CLAUDE.md`, `.cursorrules`, `AGENTS.md`) suffit à tout ré-expliquer. Mais un fichier unique ne tient pas à l'échelle : on ne décrit pas un système de 100 000 lignes dans un prompt.

Résultat sans infrastructure : l'agent ré-explore le code à chaque fois, dérive des conventions, et **répète les mêmes bugs** (le papier documente par exemple des bugs de désynchronisation réseau récurrents, jusqu'à ce que la « théorie du déterminisme » du projet soit codifiée).

### 1.2 L'idée clé : la documentation comme infrastructure

Le renversement de perspective du papier : la doc n'est pas un *artefact* qu'on écrit après coup pour les humains, c'est une **infrastructure porteuse** dont l'agent dépend pour produire du code correct — au même titre que le build system ou les tests. Deux conséquences pratiques :

- Elle est écrite **pour une IA** : tableaux, chemins de fichiers exacts, formules, patterns « fais ceci / pas cela », tables symptôme→cause→correctif. Pas de prose.
- Elle est **vivante** : générée et mise à jour par l'IA elle-même sous direction humaine, dans la même session que le changement de code. Une spec périmée est pire que pas de spec (l'agent lui fait confiance aveuglément).

### 1.3 Les trois étages

L'architecture sépare la connaissance selon sa **fréquence de chargement** — exactement comme une hiérarchie mémoire en informatique (cache / RAM / disque) :

| Étage | Contenu | Chargement | Analogie |
|---|---|---|---|
| **Tier 1 — Constitution** (`CLAUDE.md`, ~660 lignes) | Conventions, commandes de build, checklists, **tables de routage** vers les agents | Toujours (chaque session) | Le règlement intérieur affiché au mur |
| **Tier 2 — Agents spécialisés** (19 fichiers, ~9 300 lignes) | Personas experts d'un domaine, avec >50 % de connaissance projet embarquée (formules, pièges connus) | À l'invocation, routés automatiquement | Les experts métier qu'on consulte |
| **Tier 3 — Base de connaissance** (34 specs, ~16 250 lignes) | Une spec détaillée par sous-système, servie à la demande par un serveur MCP de recherche | À la demande | La bibliothèque technique |

Le point subtil : les étages **se recouvrent volontairement**. Les agents du Tier 2 embarquent en dur la connaissance de leur domaine au lieu de tout aller chercher dans le Tier 3 — parce que l'expérience a montré qu'un agent « maigre » qui doit récupérer son contexte fait plus d'erreurs (le papier relie ça au *brevity bias* identifié par ACE).

### 1.4 Comment on s'en sert, concrètement

Au quotidien, le développeur **ne manipule presque jamais l'infrastructure directement**. Le flux type :

1. Vous tapez un prompt court (« ajoute une capacité de gel de zone ») — 80 % des prompts du papier font moins de 100 mots, justement parce que le contexte est déjà chargé.
2. La constitution (toujours chargée) contient une table de déclenchement : « si la tâche touche les abilities → invoquer `ability-designer` ; après toute modif de `Network/` → invoquer `code-reviewer-game-dev` ».
3. L'agent spécialisé interroge le serveur MCP (`find_relevant_context("ability gel de zone")`) qui lui renvoie les 2-3 specs pertinentes du Tier 3 — au lieu de charger les 34.
4. En fin de tâche, si l'architecture a changé, la checklist de la constitution demande de mettre à jour la spec concernée (~5 min).
5. Au démarrage de session suivant, un hook (`context-drift-check.py`) compare les commits récents aux specs : si du code réseau a changé sans que `network-*.md` bouge, un avertissement est injecté dans le contexte.

Pour **démarrer sur votre propre projet**, le dépôt fournit des « factory agents » (`quickstart/`) : on les copie dans `.claude/agents/`, on demande à l'assistant de lire le README, et chaque factory pose 3 questions avant de générer respectivement la constitution, les agents, et les docs de contexte. La règle d'or du papier : **ne rien concevoir à l'avance** — on crée un agent ou une spec quand un pattern d'échec se répète (« si tu l'as expliqué deux fois, écris-le »).

### 1.5 Est-ce pertinent, et pour qui ?

Ce que les données du papier suggèrent (283 sessions, 2 801 prompts, 4 études de cas) :

- **Ça paie sur la durée** : la spec du système de sauvegarde a été référencée dans 74 sessions sur 4 semaines, sans un seul bug de persistance ; la spec `ui-sync-patterns.md` (126 lignes, écrite après une séance de debugging pénible) a permis d'implémenter la fonctionnalité réseau suivante correctement **du premier coup**.
- **Le coût est réel mais borné** : ~4,3 % des prompts consacrés à l'infrastructure, 1-2 h de maintenance par semaine, ratio connaissance/code ~24 % en fin de projet.
- **Le profil qui en bénéficie le plus** : les experts d'un domaine qui construisent du logiciel *hors* de leur expertise première (l'auteur est chimiste) — la connaissance codifiée compense l'expérience d'ingénierie. Pour un développeur expérimenté, la valeur est ailleurs : tenir la cohérence d'une base trop grosse pour une seule tête.
- **Quand ça ne vaut pas le coup** : petit projet (< ~10-20 k lignes) où un simple `CLAUDE.md` suffit ; prototype jetable ; domaine simple sans conventions fortes. L'infrastructure a émergé *parce que* le domaine (simulation distribuée temps réel, déterminisme réseau) est impitoyable avec les incohérences.

Limites honnêtement posées par le papier : un seul développeur, un seul projet, aucune expérience contrôlée — les chiffres sont observationnels, pas causaux.

---

## 2. Ce qui a changé depuis février 2026 — croisements

*(Veille arrêtée en août 2026. Chaque sous-section se termine par « → croisement » : ce que ça change pour l'architecture du papier.)*

### 2.1 Le débat 2026 : les fichiers de contexte servent-ils vraiment ?

C'est l'évolution la plus importante depuis la publication — et elle est inconfortable. Deux études contrôlées ont trouvé un résultat nul :

- **Evaluating AGENTS.md** (ETH Zurich, [arXiv:2602.11988](https://arxiv.org/abs/2602.11988), fév. 2026, révisé juin 2026) : sur des tâches SWE-bench et des issues réelles de dépôts ayant des fichiers de contexte committés par leurs développeurs, fournir ces fichiers **n'améliore pas le taux de réussite** et augmente le coût d'inférence de plus de 20 % en moyenne — résultat robuste à travers modèles, agents, et fichiers écrits par humains comme par LLM.
- **Two-Agent Ablation Study** ([arXiv:2607.27250](https://arxiv.org/abs/2607.27250), juil. 2026) : 288 runs contrôlés sur Claude Code et Codex, aucun effet mesurable de la stratégie d'injection de contexte sur la correction ; l'analyse des échecs les attribue au *skill* d'implémentation, pas à un manque de connaissance du dépôt.

Mais en face :

- **Probe-and-Refine** (Williams College, [arXiv:2606.20512](https://arxiv.org/abs/2606.20512), juin 2026) : en *accordant* itérativement l'AGENTS.md d'un dépôt contre des sondes synthétiques de bug-fix, le taux de résolution sur SWE-bench Verified passe de 25,5 % à 33,0 % (p < 0,001). Le plus fort résultat positif du domaine.
- **Impact of AGENTS.md on Efficiency** ([arXiv:2601.20404](https://arxiv.org/abs/2601.20404), janv. 2026) : mesure l'effet sur l'efficacité opérationnelle (étapes, tokens, temps) plutôt que la seule réussite.
- **Agent READMEs** ([arXiv:2511.12884](https://arxiv.org/abs/2511.12884), nov. 2025) : 2 303 fichiers de contexte minés sur 1 925 dépôts — la population réelle privilégie commandes de build (62 %), détails d'implémentation (70 %) et architecture (68 %) ; ils évoluent par petits ajouts fréquents, comme de la configuration.

**→ Croisement.** La lecture qui réconcilie tout : un fichier de contexte *générique et statique* ne paie pas ; un contexte *curé, accordé et maintenu frais* paie. Or curation disciplinée + détection de dérive + étagement sont précisément les variables que les études nulles ne contrôlaient pas — et précisément ce que le papier apporte. Deux implications : (1) le bénéfice à défendre n'est pas d'abord le taux de réussite brut sur tâche isolée, mais la **cohérence inter-sessions, l'efficacité en tokens et la prévention des régressions** (ce que les cas d'étude du papier montrent, et que SWE-bench ne mesure pas) ; (2) un benchmark contrôlé de *cette* architecture (axe C1) aurait une vraie valeur scientifique, car il testerait exactement la variable manquante du débat.

### 2.2 Outillage : ce que les primitives natives couvrent désormais

Le papier a construit à la main, en janvier-février 2026, des mécanismes que les éditeurs ont depuis livrés en natif. État des lieux (août 2026) :

**Chez Anthropic / Claude Code :**

- **Auto memory** : Claude Code écrit désormais lui-même ses notes de projet dans `~/.claude/projects/<projet>/memory/` — un index `MEMORY.md` chargé à chaque session + des fichiers thématiques lus à la demande. C'est très exactement le design « index chaud + specs froides » du Tier 3, en natif et auto-entretenu. Le `/doctor` propose même des coupes dans un CLAUDE.md trop gros (cousin productisé du drift detector).
- **Règles à portée de chemin** (`.claude/rules/` avec front-matter `paths:`) : la constitution monolithique peut être décomposée en fragments chargés *seulement* quand l'agent touche les fichiers concernés. Cursor (`.cursor/rules/*.mdc`) et Copilot (`.github/instructions/*.instructions.md`) ont convergé vers le même mécanisme — le standard de fait 2026 est la **constitution décomposée à chargement conditionnel**, pas le fichier unique toujours chargé.
- **Agent Skills** (SKILL.md, lancés oct. 2025) : chargement en trois niveaux — nom+description toujours en contexte (~dizaines de tokens), corps du SKILL.md au déclenchement, fichiers annexes au besoin. La *progressive disclosure* fait nativement, et sans serveur, ce que le serveur MCP du papier fait avec du keyword matching. La doctrine officielle est explicite : « toujours-actif → CLAUDE.md court ; connaissance contextuelle/procédurale → skills ».
- **Subagents avec mémoire persistante** : les agents du Tier 2 peuvent maintenant avoir chacun leur répertoire de mémoire auto-entretenu — la connaissance embarquée devient auto-actualisable entre sessions.
- **Plugins + marketplaces** (oct. 2025) : un plugin empaquette skills, subagents, hooks, serveurs MCP en une unité installable et versionnée — le canal de distribution qui manquait au papier (dont le quickstart reste « copiez ces dossiers »).
- **Côté API** : memory tool, context editing, compaction serveur, tool search avec `defer_loading` — l'équivalent premier-parti des trois étages existe aussi au niveau API.

**Standardisation :**

- **AGENTS.md** a été donné par OpenAI à la **Agentic AI Foundation** (Linux Foundation, déc. 2025 — avec MCP), est lu nativement par ~30 agents (Codex, Cursor, Copilot, Gemini CLI, Zed, Aider…) et adopté par 60 000+ dépôts. Claude Code lit toujours CLAUDE.md mais recommande officiellement l'import `@AGENTS.md` ou un lien symbolique, et fournit `/import` pour migrer. La constitution du papier peut donc être **portable et sous gouvernance neutre** — ce qui n'était pas vrai en février.
- **MCP, spec 2026-07-28** : la plus grosse révision depuis le lancement (cœur stateless, dépréciation de Roots/Sampling/Logging avec 12 mois de préavis). Le serveur du dépôt continue de fonctionner, mais une réécriture 2026 serait stateless. Surtout, la doctrine a changé : pour récupérer les specs de *son propre dépôt*, skills + recherche agentique battent un serveur MCP custom (les définitions d'outils MCP coûtent cher en contexte) ; le serveur MCP reste le bon pattern **quand la base doit être partagée entre outils hétérogènes** (Codex, Cursor, Copilot) ou vit hors du dépôt.

**La concurrence a convergé vers la même architecture :**

- **Google Conductor** (déjà cité par le papier) a ajouté en février 2026 des revues automatisées, et se positionne mi-2026 comme plugin de spec-driven development supportant… Claude Code aussi. Son modèle — contexte versionné en Markdown dans le dépôt (`product.md`, `tech-stack.md`, `workflow.md`, specs par feature) — est la plus forte confirmation indépendante de la thèse du papier.
- **GitHub Spec Kit** (125 000+ étoiles) a même un artefact nommé… `constitution` (`/speckit.constitution`), organisé par feature (spec/plan/tâches) — complémentaire d'une base de connaissance *persistante* par sous-système comme celle du papier.
- **Copilot** réplique désormais les trois étages : instructions (constitution), custom agents (Tier 2), skills (Tier 3).
- Tout un écosystème commercial et open source réinvente le couple « constitution statique + base vivante interrogeable » : Basic Memory, Hindsight, ByteRover (arbres de contexte à sémantique git), Context Portal/ConPort (le plus proche équivalent OSS du Tier 3), claude-mem (populaire mais épinglé par un audit de sécurité en fév. 2026 — l'empoisonnement de mémoire est un risque réel), Mem0/OpenMemory, Letta (le même étagement hot/cold généralisé au-delà du code), Zep/Graphiti (graphes de connaissance *temporels* avec fenêtres de validité des faits — de la détection de dérive au niveau du fait, pas du fichier). Repomix génère désormais des skills à partir d'un dépôt packé.

**→ Croisement — verdict par étage :**

| Composant du papier | Verdict août 2026 |
|---|---|
| Tier 1 (constitution) | **Confirmé partout, mais a évolué** : portable (AGENTS.md) et décomposée (règles à portée de chemin), plus monolithique |
| Tier 2 (agents spécialisés) | **Confirmé et étendu** : formats standardisés (markdown + front-matter) et mémoire persistante par agent |
| Tier 3 (base + MCP keyword) | **Le plus supplanté** : skills/auto-memory en natif pour le mono-outil ; le serveur MCP devient le *fallback* multi-outils |
| Détecteur de dérive | **Toujours sans équivalent dominant** — la contribution la plus durable du papier (les analogues — `/doctor`, revues Conductor, fenêtres de validité Graphiti — ne couvrent chacun qu'une partie) |

### 2.3 La dérive documentaire est devenue un champ de recherche

Le papier identifiait la spec périmée comme *le* mode d'échec principal, avec un détecteur heuristique (« du code a changé sans sa doc »). En 2026, trois lignes de travaux attaquent le même problème avec des outils plus puissants :

- **DocPrism** ([arXiv:2511.00215](https://arxiv.org/abs/2511.00215), nov. 2025) : détection d'incohérences code↔documentation par LLM sans fine-tuning, qui surligne les fragments incohérents et explique pourquoi, en filtrant les faux positifs non actionnables. Fonctionne a posteriori, sans diff.
- **SkillGuard** ([arXiv:2605.10990](https://arxiv.org/abs/2605.10990), mai 2026) : extrait des documents de connaissance des « contrats d'environnement » *exécutables* (versions épinglées, hypothèses d'API) et ne valide que les hypothèses porteuses — 0 fausse alerte sur 599 cas sans dérive, 76 % de rappel sur les dérives réelles.
- **Library Drift** (Amazon Science, [arXiv:2605.19576](https://arxiv.org/abs/2605.19576), mai 2026) : nomme et répare le mode d'échec silencieux des bibliothèques de connaissances auto-mises-à-jour qui se dégradent par accumulation d'entrées périmées ou contradictoires — la santé au niveau *bibliothèque*, pas seulement document par document.

**→ Croisement.** Le `context-drift-check.py` du dépôt peut évoluer de « coïncidence de changements » vers de la vraie vérification de contenu : DocPrism comme moteur de comparaison sémantique (axe B3), l'approche contrat de SkillGuard pour les hypothèses vérifiables mécaniquement (versions, chemins de fichiers, signatures — un `validate-architecture.sh` généralisé), et un bilan de santé périodique de toute la base façon Library Drift (spécs jamais retrouvées, contradictions entre docs).

### 2.4 Du contexte écrit à la main au contexte auto-évolutif

Le papier cite déjà ACE ([arXiv:2510.04618](https://arxiv.org/abs/2510.04618), ICLR 2026) et ses « playbooks évolutifs » (boucle générer-réfléchir-curer, mises à jour incrémentales qui évitent l'effondrement du contexte). La suite 2026 va plus loin :

- **CODESKILL** ([arXiv:2605.25430](https://arxiv.org/abs/2605.25430), mai 2026) : extraction automatique de *skills* procéduraux depuis les trajectoires d'agents, avec politique de gestion apprise par RL et banque bornée — +9,7 points de réussite moyens sur EnvBench/SWE-bench Verified/Terminal-Bench 2.
- **Auto-Dreamer** ([arXiv:2605.20616](https://arxiv.org/abs/2605.20616), mai 2026) : consolidation *hors-ligne* de la mémoire (inspirée du sommeil / du « sleep-time compute » de Letta) — un consolidateur lent inspecte la banque mémoire, remonte la provenance vers les trajectoires sources, et synthétise des entrées compactes qui généralisent à travers les sessions.
- **Self-Evolving Coding Agents** (survey, [arXiv:2608.03392](https://arxiv.org/abs/2608.03392), août 2026) : cartographie tout ce champ — les agents qui améliorent leur comportement futur en mettant à jour framework, mémoire, skills, outils ou structures de collaboration.
- **Probe-and-Refine** (§2.1) : même logique appliquée au Tier 1 — la constitution accordée automatiquement contre des sondes.

**→ Croisement.** La règle G4 du papier (« expliqué deux fois → écris-le ») décrit une distillation *manuelle* de trajectoires en connaissance. Toute cette littérature montre comment l'automatiser, avec les garde-fous que le papier avait pressentis (le *brevity bias* d'ACE justifiait déjà ses agents « riches »). L'hybride le plus prometteur : des étages curés par l'humain, *entretenus* par des boucles de consolidation automatiques, sous surveillance des détecteurs de dérive de §2.3. C'est l'axe B4.

### 2.5 Mémoire persistante et retrieval : les briques à greffer

**Mémoire.** Le plus proche parent architectural du papier est **PROJECTMEM** ([arXiv:2606.12329](https://arxiv.org/abs/2606.12329), juin 2026) : un journal *event-sourced* local (issues, tentatives, correctifs, décisions typés) projeté en résumés compacts servis par MCP, plus une **barrière pré-action** qui avertit l'agent avant qu'il ne répète un correctif déjà échoué ou touche un fichier connu comme fragile (« Memory-as-Governance »). Là où le papier codifie l'état *final* de la connaissance (des specs), PROJECTMEM capture la *trajectoire* (mémoire épisodique) — les deux sont complémentaires. À noter aussi : **Multi-Agent Transactive Memory** ([arXiv:2606.19911](https://arxiv.org/abs/2606.19911)) pour le partage de connaissances entre agents (les 19 experts du Tier 2 dérivent aujourd'hui indépendamment), et le survey **Always-On Agents** ([arXiv:2606.30306](https://arxiv.org/abs/2606.30306)) qui cartographie Mem0, la lignée MemGPT/Letta et les graphes de connaissance temporels Zep/Graphiti, avec leurs risques (empoisonnement de mémoire, staleness).

**Retrieval.** Trois résultats utiles, dont un contre-intuitif :

- **Is Grep All You Need?** ([arXiv:2605.15184](https://arxiv.org/abs/2605.15184), mai 2026) : dans un bon harnais, la recherche type grep **égale ou bat** le retrieval par embeddings — une validation empirique a posteriori du choix « keyword matching » du papier, que son auteur présentait comme une limite.
- **Code Isn't Memory** ([arXiv:2606.22417](https://arxiv.org/abs/2606.22417), juin 2026) : un index *structurel* (symboles, graphe d'appels) apporte en revanche un vrai gain de localisation et de résolution, à coût par solve inférieur.
- **Codebase-Memory** ([arXiv:2603.27277](https://arxiv.org/abs/2603.27277), mars 2026) : graphe de connaissance tree-sitter (66 langages, un fichier SQLite) exposé par MCP — 14 requêtes structurelles typées (chemins d'appel, analyse d'impact) en latence sub-milliseconde.

Et une mise en garde : **What Context Does a Coding Agent Actually Need?** ([arXiv:2607.09691](https://arxiv.org/abs/2607.09691), juil. 2026) montre que les résumés en langage naturel du code répondent à très peu des questions comportementales que le source lui-même permet de trancher (4/45 contre 27/45) — les specs *complètent* le code au moment d'éditer, elles ne le remplacent pas.

**→ Croisement.** Pour le serveur MCP du dépôt : inutile de se précipiter sur les embeddings (grep suffit souvent) ; le gain est plutôt dans un **index structurel du code** adossé aux specs — et l'analyse d'impact d'un graphe type Codebase-Memory donnerait un détecteur de dérive bien plus précis (« ce commit touche des fonctions citées par ces 2 specs »). Côté mémoire, une couche épisodique event-sourced façon PROJECTMEM comblerait le vrai manque : le papier note que les leçons de debugging se perdent si personne ne pense à les codifier.

### 2.6 Le cadre conceptuel s'est structuré

- **Spec-Driven Development** ([arXiv:2602.00180](https://arxiv.org/abs/2602.00180), janv.-fév. 2026) formalise le mouvement (GitHub Spec Kit, AWS Kiro, OpenSpec…) en trois niveaux de rigueur : *spec-first*, *spec-anchored*, *spec-as-source*. Le papier implémente de facto du **spec-anchored** (les specs vivent à côté du code et le contraignent, avec détection de dérive) — le vocabulaire permet de le positionner et trace une évolution possible.
- **Harness Engineering** ([arXiv:2602.14690](https://arxiv.org/abs/2602.14690), fév. 2026, AIware) : taxonomie de huit mécanismes de configuration des agents (fichiers statiques → hooks exécutables → intégrations externes) avec données d'adoption sur 2 853 dépôts GitHub — situe les trois étages du papier dans un espace de conception plus large et pointe les mécanismes qu'il n'exploite pas encore.
- **Mise en Place for Agentic Coding** ([arXiv:2605.05400](https://arxiv.org/abs/2605.05400), mai 2026) : la méthodologie *processus* complémentaire de l'infrastructure *artefact* du papier — comment la connaissance tacite devient specs structurées (« context fluency » comme compétence du développeur).

**→ Croisement.** Le papier n'est plus un objet isolé : il a désormais un nom de famille (spec-anchored development), des cousins (harness engineering) et un manuel de rédaction (Mise en Place). C'est un argument de plus pour la pertinence du concept — la communauté a convergé vers les mêmes questions par plusieurs chemins indépendants.

---

## 3. Axes d'amélioration et d'implémentation proposés

Classés par effort croissant : les axes A sont réalisables en quelques sessions sur ce fork, les axes B demandent un vrai chantier, les axes C sont des projets. Fil conducteur issu de la veille : **moderniser les supports (les étages) avec les primitives natives, et concentrer l'effort original là où le papier reste sans équivalent — la fraîcheur de la connaissance (dérive + distillation).**

### A. Quick wins (moderniser l'implémentation)

**A1. Source unique de vérité pour l'index des sous-systèmes.**
Aujourd'hui la même connaissance vit en *trois* endroits maintenus à la main : le dict `SUBSYSTEMS` (~500 lignes) dans `mcp-server/server.py`, la table « Subsystem Reference » de `CLAUDE.md`, et les docs `.claude/context/*.md`. Le détecteur de dérive parse même le `server.py` par AST pour retrouver le mapping — l'index peut donc lui-même dériver. Proposition : chaque doc de contexte déclare son propre front-matter YAML (`subsystem`, `keywords`, `files`), le serveur MCP construit l'index au démarrage en scannant `.claude/context/`, et la table de `CLAUDE.md` est générée par script. Un seul endroit à maintenir, le drift detector lit le même index que le serveur — et ce front-matter est précisément le format qui prépare la conversion en skills (B1).

**A2. Constitution portable (AGENTS.md) et décomposée (règles à portée de chemin).**
Deux mises à niveau du Tier 1 devenues standard : (a) `AGENTS.md` comme fichier canonique (désormais sous gouvernance Linux Foundation, lu par ~30 agents) avec `CLAUDE.md` en lien symbolique ou import `@AGENTS.md` ; (b) décomposer les sections spécifiques à un domaine en règles conditionnelles (`.claude/rules/*.md` avec `paths:`) pour réduire la taxe de contexte permanente — le pattern qu'ont adopté Claude Code, Cursor et Copilot. À intégrer dans la constitution-factory du quickstart.

**A3. Déplacer la détection de dérive en fin de session.**
Le drift-check tourne au `SessionStart` — c'est-à-dire *une session trop tard*. Ajouter un hook de fin de session (`Stop`) qui, si du code d'un sous-système a été modifié sans sa spec, propose immédiatement la mise à jour, pendant que le contexte de la session est encore chaud. Le hook `InstructionsLoaded` (qui trace quels fichiers d'instructions ont été chargés, quand et pourquoi) donne au passage l'observabilité qui manquait : on peut enfin mesurer quelles specs servent réellement.

### B. Effort moyen (fiabiliser et automatiser la boucle)

**B1. Exposer le Tier 3 en Agent Skills, garder le serveur MCP comme pont multi-outils.**
La *progressive disclosure* des skills (métadonnées toujours en contexte → corps au déclenchement → annexes au besoin) fait nativement, sans serveur et sans coût de définitions d'outils, ce que le serveur MCP fait aujourd'hui au keyword matching. Proposition : un script de conversion `context-docs → .claude/skills/` (le front-matter de A1 fournit nom/description), et le serveur MCP conservé pour le cas multi-outils (Codex, Cursor, Copilot) — c'est désormais son vrai rôle selon la doctrine 2026.

**B2. Retrieval : BM25 et index *structurel*, pas de course aux embeddings.**
Surprise de la veille : le choix « keyword matching » du papier, présenté comme une limite, a été validé empiriquement (« Is Grep All You Need? » — dans un bon harnais, grep égale ou bat les embeddings). Le vrai gain identifié est ailleurs : un **index structurel du code** (symboles, graphe d'appels, façon Codebase-Memory : tree-sitter + SQLite exposé par MCP) qui complète les specs — et dont les requêtes d'analyse d'impact bénéficient directement au drift detector (« ce commit touche des fonctions citées par ces 2 specs »). BM25 en remplacement du substring matching reste un petit pas utile et sans dépendance lourde.

**B3. Détection de dérive *sémantique* — doubler la mise sur la contribution la plus durable.**
Le détecteur actuel est lexical (« fichiers touchés sans docs touchées ») ; c'est pourtant le composant du papier qui reste sans équivalent dominant en 2026 — le bon endroit où investir. Trois upgrades documentés par la recherche : (a) comparaison de contenu par LLM façon **DocPrism** — quand un drift HIGH est détecté, comparer le diff aux affirmations de la spec et produire « spec valide » ou un patch proposé ; (b) **contrats exécutables** façon SkillGuard — extraire des specs les hypothèses vérifiables mécaniquement (chemins de fichiers, signatures, versions) et les valider en continu, généralisation de l'actuel `validate-architecture.sh` ; (c) **bilan de santé de la base** façon Library Drift — détecter périodiquement les specs jamais retrouvées, contradictoires entre elles, ou orphelines. En hook et en CI (GitHub Action qui ouvre une PR de mise à jour de spec).

**B4. Distillation automatique des leçons (boucle ACE).**
La règle G4 du papier (« expliqué deux fois → écris-le ») est aujourd'hui manuelle ; le hook sait repérer les sessions « debugging-heavy » mais s'arrête à un avertissement. Proposition : en fin de session, un agent distillateur extrait les leçons (symptôme → cause → correctif) et propose des *deltas* ciblés aux specs/agents concernés — jamais de réécriture complète (le *brevity bias* et l'effondrement de contexte documentés par ACE), avec validation humaine façon Cursor Memories. Les primitives natives portent déjà la moitié du chemin : auto memory et mémoire par subagent fournissent la capture ; la valeur ajoutée du dépôt est la *consolidation* vers les specs curées (façon Auto-Dreamer), sous surveillance des détecteurs de B3. Une couche épisodique event-sourced façon PROJECTMEM (journal typé des tentatives/échecs + barrière pré-action « ce correctif a déjà échoué ») comblerait le manque restant : la mémoire de *trajectoire*, complémentaire des specs d'*état*.

**B5. CI de validation.**
`validate-architecture.sh`, le drift-check et les contrats de B3 en GitHub Action sur chaque PR, pas seulement en hook local. Une spec cassée devient un échec de build — cohérent avec « la doc est de l'infrastructure ».

### C. Ambitieux (recherche & écosystème)

**C1. Benchmark contrôlé avec/sans étages — répondre au débat 2026.**
La priorité n°1 affichée par le papier, devenue urgente : les études nulles (ETH, Khatri) et le résultat positif de Probe-and-Refine (§2.1) laissent ouverte exactement la question que ce dépôt peut trancher — *un contexte curé, étagé et maintenu frais* fait-il mieux qu'un fichier générique ? Protocole : tâches reproductibles sur un projet instrumenté, 4 conditions (rien / Tier 1 seul / Tiers 1+3 / complet), mesures de réussite **et** d'efficacité (tokens, tours) **et** de cohérence inter-sessions (les métriques que SWE-bench ne voit pas). S'inspirer de Probe-and-Refine pour générer les sondes.

**C2. Packaging en plugin installable.**
Remplacer le « copiez ces dossiers » du quickstart par un plugin Claude Code : factories, skills, hooks et serveur MCP versionnés, installables en une commande (`/plugin install`), publiables sur un marketplace. C'est le canal de distribution standard depuis oct. 2025, et la réponse à la transférabilité multi-projets. Leçon de sécurité au passage (audit claude-mem, threat model « memory poisoning » du survey Always-On Agents) : signer/auditer ce que le plugin injecte en contexte.

**C3. Passage à l'échelle équipe.**
Le papier note que l'architecture *devrait* bénéficier aux équipes (les specs remplacent une partie de la communication) mais ne l'a pas évalué. Chantiers : ownership des specs (CODEOWNERS), revue de specs dans les PR, fusion de connaissances contradictoires (le problème « transactive memory » de §2.5), et métriques d'usage — quelles specs sont retrouvées/lues, lesquelles ne servent jamais ; le serveur MCP et le hook `InstructionsLoaded` sont les points de mesure naturels.

---

## 4. Sources

### Papier et dépôt

- Vasilopoulos, *Codified Context: Infrastructure for AI Agents in a Complex Codebase*, [arXiv:2602.20478](https://arxiv.org/abs/2602.20478) (fév. 2026) ; [dépôt compagnon](https://github.com/arisvas4/codified-context-infrastructure).

### Recherche (nov. 2025 – août 2026)

*Efficacité des fichiers de contexte* : [Agent READMEs, arXiv:2511.12884](https://arxiv.org/abs/2511.12884) · [Impact of AGENTS.md on Efficiency, arXiv:2601.20404](https://arxiv.org/abs/2601.20404) · [Evaluating AGENTS.md (ETH), arXiv:2602.11988](https://arxiv.org/abs/2602.11988) · [Two-Agent Ablation, arXiv:2607.27250](https://arxiv.org/abs/2607.27250) · [Probe-and-Refine, arXiv:2606.20512](https://arxiv.org/abs/2606.20512) · [Harness Engineering, arXiv:2602.14690](https://arxiv.org/abs/2602.14690) · [Mise en Place, arXiv:2605.05400](https://arxiv.org/abs/2605.05400)

*Dérive documentaire* : [DocPrism, arXiv:2511.00215](https://arxiv.org/abs/2511.00215) · [SkillGuard, arXiv:2605.10990](https://arxiv.org/abs/2605.10990) · [Library Drift (Amazon), arXiv:2605.19576](https://arxiv.org/abs/2605.19576) · [RIVA, arXiv:2603.02345](https://arxiv.org/abs/2603.02345)

*Contexte auto-évolutif* : [ACE, arXiv:2510.04618](https://arxiv.org/abs/2510.04618) (ICLR 2026) · [CODESKILL, arXiv:2605.25430](https://arxiv.org/abs/2605.25430) · [Auto-Dreamer, arXiv:2605.20616](https://arxiv.org/abs/2605.20616) · [Self-Evolving Coding Agents (survey), arXiv:2608.03392](https://arxiv.org/abs/2608.03392) · [SkillOps, arXiv:2605.13716](https://arxiv.org/abs/2605.13716) · [SWE-MeM, arXiv:2606.28434](https://arxiv.org/abs/2606.28434)

*Mémoire et retrieval* : [PROJECTMEM, arXiv:2606.12329](https://arxiv.org/abs/2606.12329) · [Multi-Agent Transactive Memory, arXiv:2606.19911](https://arxiv.org/abs/2606.19911) · [Always-On Agents (survey), arXiv:2606.30306](https://arxiv.org/abs/2606.30306) · [Is Grep All You Need?, arXiv:2605.15184](https://arxiv.org/abs/2605.15184) · [Code Isn't Memory, arXiv:2606.22417](https://arxiv.org/abs/2606.22417) · [Codebase-Memory (tree-sitter KG), arXiv:2603.27277](https://arxiv.org/abs/2603.27277) · [What Context Does a Coding Agent Actually Need?, arXiv:2607.09691](https://arxiv.org/abs/2607.09691)

*Cadre conceptuel* : [Spec-Driven Development, arXiv:2602.00180](https://arxiv.org/abs/2602.00180) · [Agent Skills survey, arXiv:2602.12430](https://arxiv.org/abs/2602.12430)

### Écosystème / outillage (état août 2026)

[Mémoire de Claude Code (CLAUDE.md, auto memory, règles)](https://code.claude.com/docs/en/memory) · [Agent Skills](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview) · [Subagents](https://code.claude.com/docs/en/sub-agents) · [Hooks](https://code.claude.com/docs/en/hooks) · [Plugins](https://code.claude.com/docs/en/plugins) · [Memory tool (API)](https://platform.claude.com/docs/en/agents-and-tools/tool-use/memory-tool) · [AGENTS.md](https://github.com/openai/agents.md) · [Agentic AI Foundation](https://www.linuxfoundation.org/press/linux-foundation-announces-the-formation-of-the-agentic-ai-foundation) · [Spec MCP 2026-07-28](https://blog.modelcontextprotocol.io/posts/2026-07-28/) · [Roadmap MCP 2026](https://blog.modelcontextprotocol.io/posts/2026-mcp-roadmap/) · [Code execution with MCP (Anthropic)](https://www.anthropic.com/engineering/code-execution-with-mcp) · [Google Conductor](https://github.com/gemini-cli-extensions/conductor) · [GitHub Spec Kit](https://github.com/github/spec-kit) · [Copilot & AGENTS.md](https://github.blog/changelog/2025-08-28-copilot-coding-agent-now-supports-agents-md-custom-instructions/) · [Cursor rules](https://cursor.com/docs/context/rules) & [memories](https://cursor.com/docs/context/memories) · [Mem0](https://github.com/mem0ai/mem0) · [Letta](https://github.com/letta-ai/letta) · [Graphiti](https://github.com/getzep/graphiti) · [ByteRover CLI](https://github.com/campfirein/byterover-cli) · [claude-mem](https://github.com/thedotmack/claude-mem) · [Basic Memory](https://basicmemory.com) · [Hindsight](https://hindsight.vectorize.io) · [Context Portal](https://github.com/GreatScottyMac/context-portal) · [Repomix](https://github.com/yamadashy/repomix) · [llms.txt](https://llmstxt.org)

> *Note de méthode : veille réalisée le 8 août 2026 par recherche web assistée. Les dates arXiv ont été vérifiées via les pages d'abstract ; certains domaines officiels (anthropic.com, cursor.com) étaient inaccessibles directement depuis l'environnement de travail — les éléments concernés reposent sur des recoupements de sources secondaires concordantes.*
