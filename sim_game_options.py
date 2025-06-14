"""
Wildfire Evacuation – Monte‑Carlo Balance Simulator
===================================================
Run thousands of automated plays of *wildfire_game.py* and measure how
valuable each possible action is for every secret character profile.

Requirements
------------
* Python ³·9+
* pandas (for tabular aggregation / pretty printing)

Place **wildfire_sim.py** in the *same directory* as your original
`wildfire_game.py`.  The simulator imports classes and constants from it
so it stays in sync even as your rules evolve.

Quick start::

    # 10 000 games, 4 players, identical default policy for everyone
    python wildfire_sim.py --games 10000 --players 4

The script prints a pivot table (profile × action) with three metrics:
  * **use_rate** – how often that action was chosen (per game)
  * **avg_points_if_used** – mean final score of players *who used* the action
  * **marginal_delta** – average score difference versus players of the
    same profile *in the same simulation* who **did not** use the action.

Interpret the *marginal* number as the expected value added (or lost) by
that decision under the current point schedule and strategy mix.
Adjust card or combo values, rerun, and watch the deltas converge toward
zero for a well‑balanced design.
"""
from __future__ import annotations

import argparse
import random
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional
import matplotlib.pyplot as plt

import pandas as pd

# -----------------------------------------------------------------------------
#  Load your original game implementation -------------------------------------
# -----------------------------------------------------------------------------

import game as wg  # noqa: E402 – must live in same folder

# --- Type helpers ------------------------------------------------------------
Action = str  # simple alias; every distinct player decision has a short id


@dataclass
class PlayerStats:
    """Holds per‑simulation counts for one player."""

    profile: str
    actions: Counter = field(default_factory=Counter)
    points: int = 0


@dataclass
class Policy:
    """Probabilities that drive automated choices.

    You can tweak these or subclass Policy for sophisticated bots.
    """

    token_prob: float = 0.25           # prep‑phase – clear yard for a token
    spend_token_prob: float = 0.5      # disaster – burn a token for +5 move
    shortcut_prob: float = 0.5         # disaster – gamble on shortcut square
    use_blocker_prob: float = 0.8      # disaster – play matching blocker card

    def choose_prep_action(self, locations: List[str], rng: random.Random) -> Action:
        if rng.random() < self.token_prob:
            return "TakeToken"
        return f"Visit_{rng.choice(locations)}"

    def spend_token(self, tokens: int, rng: random.Random) -> bool:
        return tokens > 0 and rng.random() < self.spend_token_prob

    def gamble_shortcut(self, rng: random.Random) -> bool:
        return rng.random() < self.shortcut_prob

    def use_blocker(self, rng: random.Random) -> bool:
        return rng.random() < self.use_blocker_prob


# -----------------------------------------------------------------------------
#  Core simulator -------------------------------------------------------------
# -----------------------------------------------------------------------------

class SimulationRunner:
    def __init__(self, games: int, players_per_game: int, seed: int, policy: Policy):
        self.games = games
        self.players_per_game = players_per_game
        self.rng = random.Random(seed)
        self.policy = policy
        # store raw records – list[dict]
        self.records: List[Dict[str, object]] = []

    # ---------------------------------------------------------------------
    #  Single game ---------------------------------------------------------
    # ---------------------------------------------------------------------

    def _setup_players(self) -> List[wg.Player]:
        char_pool = list(wg.CHARACTER_CARDS.items())
        self.rng.shuffle(char_pool)
        chosen = char_pool[: self.players_per_game]
        players: List[wg.Player] = []
        for idx in range(self.players_per_game):
            name = f"P{idx + 1}"
            char_name, (plus, mult) = chosen[idx]
            players.append(
                wg.Player(name=name, character=wg.CharacterCard(char_name, plus, mult))
            )
        return players

    def _deal_starting_resources(self, game: "AutoGame") -> None:
        for p in game.players:
            for _ in range(2):
                loc = self.rng.choice(list(game.location_decks))
                if game.location_decks[loc]:
                    p.add_card(game.location_decks[loc].pop())

    def run_one_game(self) -> None:
        players = self._setup_players()
        game = AutoGame(players, self.rng, self.policy)
        self._deal_starting_resources(game)
        game.play_full_game()
        # record stats ----------------------------------------------------
        for ps in game.player_stats.values():
            for action, cnt in ps.actions.items():
                self.records.append(
                    {
                        "profile": ps.profile,
                        "action": action,
                        "performed": True,
                        "count": cnt,
                        "points": ps.points,
                    }
                )
            # also note *not* performed, so we can compute delta properly
            for action in game.all_actions:
                if action not in ps.actions:
                    self.records.append(
                        {
                            "profile": ps.profile,
                            "action": action,
                            "performed": False,
                            "count": 0,
                            "points": ps.points,
                        }
                    )

    # ---------------------------------------------------------------------
    #  Main loop -----------------------------------------------------------
    # ---------------------------------------------------------------------

    def run(self) -> pd.DataFrame:
        for _ in range(self.games):
            self.run_one_game()
        df = pd.DataFrame(self.records)
        # aggregate – compute use rate and marginal delta -----------------
        summary = (
            df.groupby(["profile", "action"]).agg(
                use_rate=("performed", "mean"),
                avg_points_if_used=("points", lambda s: s[df.loc[s.index, "performed"]].mean()),
                avg_points_if_not=("points", lambda s: s[~df.loc[s.index, "performed"]].mean()),
            )
        )
        summary["marginal_delta"] = (
            summary["avg_points_if_used"] - summary["avg_points_if_not"]
        )
        return summary.reset_index()


# -----------------------------------------------------------------------------
#  Non‑interactive auto‑play of one game --------------------------------------
# -----------------------------------------------------------------------------

class AutoGame:
    """Stripped‑down, headless re‑implementation of the essential rules.

    It operates only on the data – no `input()` or `print()` – so it runs
    millions of iterations quickly.  Whenever a player *could* make a
    decision, we consult the shared `Policy` instance.
    """

    def __init__(self, players: List[wg.Player], rng: random.Random, policy: Policy):
        self.players = players
        self.rng = rng
        self.policy = policy
        self.player_stats: Dict[str, PlayerStats] = {
            p.name: PlayerStats(profile=p.character.name) for p in players
        }
        self.all_actions: set[str] = set()  # filled as game proceeds
        # build shuffled location decks (copy structure from original file)
        self.location_decks: Dict[str, List[wg.ResourceCard]] = {
            loc: [wg.ResourceCard(n, pts, loc) for n, pts in cards]
            for loc, cards in wg.LOCATIONS.items()
        }
        for deck in self.location_decks.values():
            self.rng.shuffle(deck)

    # -------------- Preparation phase -----------------------------------

    def _prep_phase(self):
        locations = list(self.location_decks)
        for _round in range(7):
            for p in self.players:
                action = self.policy.choose_prep_action(locations, self.rng)
                self.all_actions.add(action)
                self.player_stats[p.name].actions[action] += 1
                if action == "TakeToken":
                    p.tokens += 1
                else:  # Visit_<loc>
                    loc = action.split("_", 1)[1]
                    deck = self.location_decks[loc]
                    if deck:
                        p.add_card(deck.pop())

    # -------------- Disaster phase --------------------------------------

    def _disaster_phase(self):
        first_to_safe = False
        for p in self.players:
            p.position = 0
            p.skipped_turns = 0
            p.one_space_only = False
            p.reached_safe_zone = False
            p.bonus_points = 0
        turns = 0
        while not all(pl.reached_safe_zone for pl in self.players) and turns < 200:
            turns += 1
            for p in self.players:
                if p.reached_safe_zone:
                    continue
                if p.skipped_turns > 0:
                    p.skipped_turns -= 1
                    continue
                # movement ------------------------------------------------
                move = 1 if p.one_space_only else self.rng.randint(1, 6)
                p.one_space_only = False
                # spend token?
                if self.policy.spend_token(p.tokens, self.rng):
                    p.tokens -= 1
                    move += 5
                    action = "SpendToken"
                    self.all_actions.add(action)
                    self.player_stats[p.name].actions[action] += 1
                # advance
                p.position = min(p.position + move, wg.SAFE_ZONE_INDEX)
                # shortcut gamble -------------------------------------
                if (
                    p.position in wg.SHORTCUT_SPACES
                    and self.policy.gamble_shortcut(self.rng)
                ):
                    action = "ShortcutGamble"
                    self.all_actions.add(action)
                    self.player_stats[p.name].actions[action] += 1
                    roll = self.rng.randint(1, 6)
                    if roll >= 5:
                        p.position = min(p.position + 3, wg.SAFE_ZONE_INDEX)
                    else:
                        p.skipped_turns = 1
                # red space – action card ------------------------------
                if p.position in wg.RED_SPACES:
                    self._resolve_action_card(p)
                # reached safe zone -----------------------------------
                if p.position >= wg.SAFE_ZONE_INDEX:
                    p.reached_safe_zone = True
                    if not first_to_safe:
                        first_to_safe = True
                        p.bonus_points += 5
        # end while

    # ---- action card resolution ----------------------------------------

    def _draw_action_card(self):
        # simple infinite deck – uniform sample
        return self.rng.choice(wg.ACTION_CARDS)

    def _resolve_action_card(self, p: wg.Player):
        card_id, title, penalty, blocker = self._draw_action_card()
        # optionally prevent --------------------------------------------------
        if blocker and p.has_card(blocker) and self.policy.use_blocker(self.rng):
            action = "UseBlocker"
            self.all_actions.add(action)
            self.player_stats[p.name].actions[action] += 1
            return  # penalty avoided
        # apply penalty -------------------------------------------------------
        if title == "Flat Tire":
            p.skipped_turns += 1
        elif title == "Road Block":
            p.one_space_only = True
        elif title in {"Heavy Smoke", "Blackout"}:
            p.skipped_turns += 1
        elif title == "Bad Directions":
            p.position = max(0, p.position - 4)
        elif title in {"Dehydration", "Food Spoilage"}:
            p.bonus_points -= 5
        elif title == "Medical Emergency":
            p.skipped_turns += 2
        # other penalties (Panic, Car Trouble) are ignored for simplicity

    # ---------------------------------------------------------------------
    #  Run full game -------------------------------------------------------
    # ---------------------------------------------------------------------

    def play_full_game(self):
        self._prep_phase()
        self._disaster_phase()
        # final scoring ---------------------------------------------------
        for p in self.players:
            self.player_stats[p.name].points = p.total_points()


# -----------------------------------------------------------------------------
#  CLI Entrypoint -------------------------------------------------------------
# -----------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Wildfire – Monte‑Carlo balance simulator")
    parser.add_argument("--games", type=int, default=5000, help="number of simulated games")
    parser.add_argument("--players", type=int, default=4, help="players per game (2‑5)")
    parser.add_argument("--seed", type=int, default=12345, help="RNG seed for reproducibility")
    args = parser.parse_args()

    if not 2 <= args.players <= 5:
        parser.error("--players must be between 2 and 5.")

    sim = SimulationRunner(
        games=args.games,
        players_per_game=args.players,
        seed=args.seed,
        policy=Policy(),  # tweak or subclass for smarter bots
    )
    summary_df = sim.run()

    # pretty print ---------------------------------------------------------
    pd.set_option("display.max_rows", None)
    pd.set_option("display.precision", 2)
    print("\n==== Monte‑Carlo Balance Summary ====")
    print(summary_df.to_string(index=False))

    raw_df = pd.DataFrame(sim.records)

    # For now, let's get the mean for each profile across all the points recorded:
    profile_avg = raw_df.groupby("profile")["points"].mean()

    profile_avg.plot(kind="bar")
    plt.title("Average Final Score by Profile")
    plt.ylabel("Average Score")
    plt.xlabel("Profile")
    plt.tight_layout()
    plt.show()



if __name__ == "__main__":
    main()
