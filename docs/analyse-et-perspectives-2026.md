# Codified Context Infrastructure — analyse, croisements récents et axes d'amélioration

> Document de travail (août 2026) pour le fork de [codified-context-infrastructure](https://github.com/arisvas4/codified-context-infrastructure), compagnon du papier *« Codified Context: Infrastructure for AI Agents in a Complex Codebase »* (Vasilopoulos, [arXiv:2602.20478](https://arxiv.org/abs/2602.20478), février 2026).
>
> Objectifs : (1) expliquer le concept simplement, (2) le croiser avec les concepts et outils apparus depuis la publication, (3) proposer des axes d'amélioration et d'implémentation concrets pour ce dépôt.

---

## TL;DR

- **Le concept** : les agents de code (Claude Code, Cursor, Codex…) n'ont pas de mémoire entre les sessions. Le papier propose de traiter la **documentation comme une infrastructure** : un ensemble structuré de fichiers Markdown écrits *pour l'IA* (pas pour les humains), organisés en 3 étages selon leur fréquence de chargement — et qui simulent une mémoire persistante du projet.
- **La preuve** : l'auteur (chimiste de formation, pas développeur) a construit un jeu multijoueur C# de 108 000 lignes en 70 jours à temps partiel, avec Claude Code comme seul générateur de code, en s'appuyant sur ~26 000 lignes de « connaissance codifiée ».
- **Ce qui a changé depuis** : une grande partie de ce que le papier construit à la main existe désormais en primitives natives (Agent Skills et leur *progressive disclosure*, standard AGENTS.md, hooks, plugins, memory tools…). Le concept n'est pas périmé pour autant : c'est la **méthode** (quoi codifier, quand, comment le maintenir frais) qui reste la vraie contribution — les nouvelles primitives sont surtout de meilleurs *supports* pour l'implémenter.
- **Axes proposés** : moderniser l'implémentation (skills, AGENTS.md, plugin installable), fiabiliser (source unique de vérité pour l'index, drift sémantique, CI), automatiser la boucle d'apprentissage (distillation des leçons de session façon ACE), et évaluer (benchmark contrôlé, priorité n°1 du papier lui-même).

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

*(Section alimentée par la veille — voir sources en fin de document.)*

<!-- SECTION-VEILLE : à compléter -->

---

## 3. Axes d'amélioration et d'implémentation proposés

Classés par effort croissant. Les axes A sont réalisables en quelques sessions sur ce fork ; les axes C sont des projets.

### A. Quick wins (moderniser l'implémentation)

**A1. Source unique de vérité pour l'index des sous-systèmes.**
Aujourd'hui la même connaissance vit en *trois* endroits maintenus à la main : le dict `SUBSYSTEMS` (~500 lignes) dans `mcp-server/server.py`, la table « Subsystem Reference » de `CLAUDE.md`, et les docs `.claude/context/*.md`. Le détecteur de dérive parse même le `server.py` par AST pour retrouver le mapping — l'index peut donc lui-même dériver. Proposition : chaque doc de contexte déclare son propre front-matter YAML (`subsystem`, `keywords`, `files`), le serveur MCP construit l'index au démarrage en scannant `.claude/context/`, et la table de `CLAUDE.md` est générée par script. Un seul endroit à maintenir, et le drift detector lit le même index que le serveur.

**A2. Constitution au format standard `AGENTS.md`.**
Le papier visait la portabilité inter-outils ; le standard AGENTS.md est devenu exactement ça. Proposition : documenter (et outiller dans la constitution-factory) le pattern `AGENTS.md` comme fichier canonique + `CLAUDE.md` en lien symbolique, pour que la même constitution serve à Claude Code, Codex, Cursor, Gemini CLI, Copilot.

**A3. Hook de fin de session plutôt que (seulement) de début.**
Le drift-check tourne au `SessionStart` — c'est-à-dire *une session trop tard*. Ajouter un hook `Stop`/fin de session qui, si des fichiers code d'un sous-système ont été modifiés sans sa spec, propose immédiatement la mise à jour (le contexte de la session est encore chaud, c'est le moment le moins cher pour mettre à jour la doc).

### B. Effort moyen (fiabiliser et automatiser la boucle)

**B1. Recherche hybride plutôt que substring matching.**
Reconnu comme limite dans le papier (§5.3). Étapes graduées : BM25 (aucune dépendance lourde, gros gain de rappel) → embeddings locaux en option → fusion des scores. L'index de A1 rend ça propre.

**B2. Détection de dérive *sémantique*.**
Le détecteur actuel est purement lexical (« fichiers touchés sans docs touchées »). Proposition : quand un drift HIGH est détecté, un appel LLM peu coûteux compare le diff du code aux affirmations de la spec et produit soit « spec toujours valide », soit un patch de spec proposé. Peut tourner en hook ou en CI (GitHub Action qui ouvre une PR de mise à jour de spec).

**B3. Distillation automatique des leçons (boucle ACE).**
La règle G4 du papier (« expliqué deux fois → écris-le ») est aujourd'hui manuelle ; le hook sait déjà repérer les sessions « debugging-heavy » mais s'arrête à un avertissement. Proposition : à la fin d'une telle session, un agent « distillateur » extrait les leçons (symptôme → cause → correctif) et propose des *deltas* ciblés aux specs/agents concernés — jamais de réécriture complète, pour éviter l'effondrement du contexte (*brevity bias*/*context collapse* documentés par ACE).

**B4. CI de validation.**
`validate-architecture.sh` (références croisées) et le drift-check en GitHub Action sur chaque PR, pas seulement en hook local. Une spec cassée devient un échec de build — cohérent avec « la doc est de l'infrastructure ».

### C. Ambitieux (recherche & écosystème)

**C1. Benchmark contrôlé avec/sans étages.**
La priorité n°1 affichée par le papier. Concrètement : un jeu de tâches reproductibles sur le projet du cas d'étude (ou un projet open source instrumenté), exécutées en 4 conditions (rien / Tier 1 seul / Tiers 1+3 / complet), en mesurant taux de réussite, tours d'agent, tokens, régressions. Même à petite échelle, ce serait la première évidence causale du domaine.

**C2. Packaging en plugin installable.**
Remplacer le « copiez ces dossiers » du quickstart par un plugin Claude Code : agents + skills + hooks + serveur MCP versionnés et installables en une commande, publiables sur un marketplace. C'est aussi la réponse au problème de transférabilité multi-projets.

**C3. Passage à l'échelle équipe.**
Le papier note que l'architecture *devrait* bénéficier aux équipes (les specs remplacent une partie de la communication) mais ne l'a pas évalué. Chantiers : ownership des specs (CODEOWNERS), revue de specs dans les PR, fusion de connaissances contradictoires, et métriques d'usage (quelles specs sont retrouvées/lues, lesquelles ne servent jamais — le serveur MCP est le point de mesure naturel).

---

## 4. Sources

<!-- SECTION-SOURCES : à compléter -->
