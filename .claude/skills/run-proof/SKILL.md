---
name: run-proof
description: Regenerate verification evidence (headless runs, determinism check, pytest, screenshots) for the current phase into docs/proof/<phase>/. Use after finishing a feature and before tagging a phase.
---

# run-proof

1. Add/adjust scenarios in `tests/scenarios/<name>.json` (+ optional `<name>.inputs.json`; add `"_night": 2|3` for other nights) for each new requirement. Files starting with `visual_` are for screenshots only.
2. `python tools/run_proof.py phaseN` → runs every scenario twice through the real CLI, checks identical output, saves `docs/proof/phaseN/*.jsonl`, `summary.md`, `pytest.txt`. Must print `OK`.
3. Screenshots (needs a display), then OPEN each PNG and check it shows the requirement:
   `python -m game.app --night N --seed 5 --screenshot docs/proof/phaseN/nN_play.png --frames 60 --ui play`
   `--ui menu|intro|pause|settings|result|dawn` for screens; `--scenario tests/scenarios/visual_*.json` for staged moments.
4. FPS: `python -m game.app --night N --bench 15 --bench-out docs/proof/phaseN/fps.txt` for N = 1..3 (target ≥ 30 FPS at 1280×720).
5. Phase 4+: `python -m game.bench --seed 42 --duration 30 --out docs/proof/phaseN/bench.json` and `python -m game.soak --seed 7 --nights 10 --out docs/proof/phaseN/soak.json`; report the machine honestly.
6. Update `docs/proof/phaseN/README.md` (requirement → how verified → evidence → result). Write "chưa đạt" / "kiểm bằng tay" honestly. Never hand-edit generated output.
