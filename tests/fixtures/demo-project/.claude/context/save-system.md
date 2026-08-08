---
subsystem: save-system
name: Save System
description: Two-tier save architecture (disk JSON + in-memory run state)
keywords: [save, persistence, autosave, herosave]
files:
  - src/services/save_service.py
  - src/services/
priority: high
related: [networking]
version: 2
last-verified: 2026-08-08
---
# Save System

The save system uses a two-tier architecture: a disk tier for permanent
player data and a memory tier for temporary state.

## Key Files

| File | Purpose |
|------|---------|
| `src/services/save_service.py` | Disk tier |

## References

- `.claude/context/networking.md`
