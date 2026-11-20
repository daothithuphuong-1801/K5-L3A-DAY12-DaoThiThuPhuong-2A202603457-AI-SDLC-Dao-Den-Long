# Đảo Đèn Lồng — agent guide

Python 3.11. Rules in `game/core/` (pure Python: `sim.py`, `maps.py`, `tuning.py`), 3D view in `game/app.py` + `game/view/` (Ursina), CLI `game/headless.py`. Contract **v1.2** (Ticket-03 on top of Ticket-02). Design decisions in `docs/adr/`, breaking changes in `CHANGELOG.md`.

## Commands
- Test: `python -m pytest -q` (Stop hook blocks finishing while red)
- Headless: `python -m game.headless --seed 1 --night 1|2|3 --ticks 600 --out out.jsonl [--scenario f.json] [--inputs f.json]`
- Play: `python -m game.app [--night N]` · Screenshot: `--screenshot f.png --frames 60 --ui play|menu|intro|pause|settings|result|dawn`
- FPS: `python -m game.app --night N --bench 15 --bench-out docs/proof/phaseN/fps.txt`
- Proof: `python tools/run_proof.py phaseN` (skill `run-proof`) · Sounds: `python tools/gen_sounds.py`

## Rules
- `game/core/` MUST NOT import ursina/panda3d. All game rules live in `core/`; `app.py` only renders + maps keys to `InputState`.
- Tuning numbers come ONLY from `game.contract.json`; Ticket-02 constants without a contract key live in `core/tuning.py`. Map geometry ONLY in `core/maps.py` (`ground(x,z)` -> height or None).
- Tick order is mandatory (see `Sim.step` docstring). Events use tick = k+1; spawned things act from the next tick.
- Lantern fuel is integer 1/60 units (`fuel_u`, 100 = 6000); safe zone = `Sim._safe(l)` (lit and fuel >= 30), never `l.lit` alone.
- Test Contract is exact: event names/fields, shade states `spawning|wander|chase|recoil|stunned|drain`, 3-decimal rounding, exit 2 for bad scenario/inputs.
- Determinism: only `self.rng` (seeded); no time, no `hash()`, no set iteration in sim.
- Visual design must be original; listed components use the Ticket-02 palette hex (`world.py`, `ui.py`).
- Creative extras must be view-only; headless output must not change.
- Every new feature: a scenario in `tests/scenarios/` (`"_night": N` for nights 2/3) + a test. Never weaken a test; when a ticket replaces a rule, change the test, tag it `[TNN]` with the reason, add an ADR + CHANGELOG entry.
- Assumptions go in `docs/notes/phaseN-spec.md`. Do not git commit/tag (the user commits manually).
