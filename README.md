# IBVAP — Intelligent Border Video Analytics Platform

> SIH 2026 | SSB (Sashastra Seema Bal) | Blockchain & Cybersecurity theme

AI analytics on existing CCTV hardware — no proprietary boxes.

---

## Team

| Member | Module(s) |
|--------|-----------|
| **Prince** | Human Detection, Human Tracking, Architecture |
| Abhilasha | Virtual Fence Intrusion Detection |
| Omkar | Suspicious Activity Detection |
| Prachi | Vehicle Detection + Classification, ANPR |
| New #5 | Alarm Manager |
| New #6 | Website / Dashboard |

---

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the contract tests (must pass before any PR merges)
pytest tests/contract/ -v

# 3. Read the build brief before coding your module
cat docs/AI_BUILD_BRIEF.md
```

---

## Repo Structure

```
ibvap/
├── contracts/              ← FROZEN shared schema — read-only after Phase 0
│   ├── schema.py           ← DetectionResult + DetectedObject (Pydantic)
│   └── fake_detector.py    ← FakeDetector for parallel dev without real models
├── configs/
│   ├── system.yaml         ← Camera defs, model states, timing knobs
│   └── rules.yaml          ← Alarm rules (severity, evidence) — not code
├── docs/
│   ├── ARCHITECTURE.md     ← Full architecture & decisions
│   └── AI_BUILD_BRIEF.md   ← Paste this into your AI tool before coding
├── human_detection/        ← Prince
├── human_tracking/         ← Prince
├── vehicle_detection/      ← Prachi
├── anpr/                   ← Prachi
├── virtual_fence/          ← Abhilasha
├── suspicious_activity/    ← Omkar
├── face_analysis/          ← Optional, Phase 2
├── alarm_manager/          ← New member #5
├── website/                ← New member #6
├── integration/            ← Pairwise + full-system integration tests
├── tests/
│   ├── contract/           ← CI gate — runs on every PR
│   └── fixtures/scenarios/ ← Shared test data used by all modules
└── storage/                ← Local DB, media, sync queue (edge runtime)
```

---

## The One Rule That Matters

Every module does exactly **one thing**: produce a `DetectionResult` and call:

```python
alarm_manager.submit(result)
```

Nothing else. No alerts, no file saves, no DB writes, no UI calls.

---

## Development Phases

| Phase | When | What |
|-------|------|------|
| 0 — Foundations | Week 1 | Freeze schema, repo skeleton, CI |
| 1 — Parallel dev | Weeks 2–4 | All modules built independently |
| 2 — Pairwise integration | Week 5 | Contract tests between pairs |
| 3 — System integration | Week 6 | Full pipeline on real camera |
| 4 — Demo hardening | Remaining | Polish, stretch goals |
