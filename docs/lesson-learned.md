# Lessons Learned

Append-only log of approaches tried, failure causes, and validated know-how. Newest entry on top.

## Entry format

```
## [YYYY-MM-DD] One-line topic
**Tried**: which approach was taken
**Result**: success / failure + observed behavior
**Lesson**: what to do next time
```

Optional follow-up lines: `**Related files**:` and `**Related**:` (cross-link to `playbook.md` / `decisions.md` / a specific phase).

## Inclusion bar

- Real attempts only — not "I considered X". A lesson is the residue of a thing that hit the codebase or the runtime.
- Specific enough that a reader six months later can recognize the same failure mode without re-doing the diagnosis.
- If the lesson generalizes to a pattern useful outside this project, promote it to `playbook.md` and link back here.

---

_(No entries yet. The first one will land with the Phase 0 hook payload spike — see `roadmap.md`.)_
