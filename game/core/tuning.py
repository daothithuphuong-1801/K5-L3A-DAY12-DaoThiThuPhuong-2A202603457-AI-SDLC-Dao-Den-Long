"""Tuning is read from game.contract.json so the declared numbers can never drift from the game.
Constants below are the Ticket-02 standard values that the contract has no key for."""
import json
from pathlib import Path

CONTRACT_PATH = Path(__file__).resolve().parents[2] / "game.contract.json"

TICK_RATE = 60
DT = 1.0 / TICK_RATE

# movement
JUMP_SPEED = 7.0
GRAVITY = 20.0
STEP_HEIGHT = 0.35          # max ground rise walked over in one tick (ramps); cliffs are walls
CHARM_SPEED = 7.2
FALL_Y = -10.0
RESPAWN_WAIT = 60
# motes
MOTE_START = 20
MOTE_CAP = 30
MOTE_SPAWN_EVERY = 240
PICKUP_DY = 1.5
DROP_TTL = 480
DROP_R = (1.5, 2.5)
# pulse
PULSE_CENTER_DY = 0.8
PUSH_TICKS = 15
# shades
SHADE_FIRST = 300
SHADE_DETECT = 12.0
SHADE_LOSE = 18.0
SHADE_HIT_DY = 1.5
SHADE_SPAWN_MIN_DIST = 15.0
SHADE_SPAWNING_TICKS = 30     # assumption: rise-from-fog time before acting
SHADE_WANDER_SPEED = 1.5      # assumption
RECOIL_TICKS = 60
RECOIL_DIST = 2.0
EVICT_MAX_TICKS = 30
# drifters (Gió Lạc)
DRIFTER_SPEED = 7.0
DRIFTER_IDLE_SPEED = 2.0
DRIFTER_MAX = 2
DRIFTER_EVERY = 1200
DRIFTER_CHASE_CARRY = 5
DRIFTER_CHASE_DIST = 15.0
DRIFTER_TOUCH = 1.2
DRIFTER_STEAL = 3
DRIFTER_FLEE_TICKS = 240
DRIFTER_DROP_TICKS = 120
# charms (Bùa Gió)
CHARM_TICKS = 600
CHARM_RESPAWN = 2700
# wind (night 3)
WIND_EVERY = 1800
WIND_TICKS = 300
WIND_WARN = 120
WIND_SPEED = 2.0
INTERACT_DY = 1.5            # assumption: lantern must be on the same level


def load_tuning(path: Path = CONTRACT_PATH) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)["tuning"]
# Ticket-03 (contract v1.2): lantern fuel, integer units of 1/60 to avoid float drift
FUEL_UNIT = 60                 # 1 fuel = 60 units; decay 1/s = 1 unit per tick
LOW_FUEL_DIST = 2.0            # shade starts draining within 2 m (XZ)
DRAIN_BREAK_DIST = 6.0         # draining shade turns to chase if Mây within 6 m
DRAIN_EVENT_EVERY = 60
SCORE_RELIGHT = 40
SCORE_DRAIN_STUN = 15          # total for a shade that was draining (instead of 5)
SCORE_DAWN_LANTERN = 50        # + floor(fuel) per lit lantern at dawn
CAPACITY_PER_LIGHT = 2
