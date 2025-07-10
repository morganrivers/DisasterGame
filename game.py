#!/usr/bin/env python3
"""Wildfire Evacuation Game (CLI)

Two-phase family game for 2-5 players:
  • Preparation phase – visit locations for resource cards (or speed through forNeighborly Token).
  • Disaster phase – race along a 25-space path to the Safe Zone while avoiding Action card hazards.

Characters are secret and award end-game bonuses (+1 pt per specific resource and ×2 for another).
The first player to arrive receives +5 pts. Highest score wins.

Run directly:  python wildfire_game.py
"""
from __future__ import annotations

import os
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional

# ────────────────────────────── CARD DATA ──────────────────────────────

LOCATIONS: Dict[str, List[tuple[str, int]]] = {
    "Home": \
          [("Emergency Blanket", 1)] * 3\
        + [("Important Documents", 2)] * 3\
        + [("Extra Clothes", 1)] * 3,\
    "Grocery Store":\
          [("Water Bottle", 1)] * 3 \
        + [("Extra Cash", 2)] * 2 \
        + [("Canned Food", 3)] * 3,\
    "Pharmacy":\
          [("N95 Respirator", 2)] * 2 \
        + [("First Aid Kit", 1)] * 3 \
        + [("1 Month of Medication", 3)] * 3,\
    "Gas Station": \
          [("Gas Canister", 1)] * 3 \
        + [("Flashlight", 2)] * 2 \
        + [("Spare Tire", 3)] * 1,\
    "Electronics Store":\
          [("Batteries", 2)] * 3  \
        + [("Hand Crank Radio", 3)] * 1 \
        + [("Power Bank", 1)] * 2  
}

def print_prep_map(
    p1, p2, p3, p4, p5,
    g1, g2, g3, g4, g5,
    a1, a2, a3, a4, a5,
    h1, h2, h3, h4, h5,
    e1, e2, e3, e4, e5,
    y1, y2, y3, y4, y5
):
    print(f"""
                            _______________
                           /{g4} {g2} {g1} {g3} {g5} \\
             +-------------| Grocery Store |-------------+
             |             *---------------*             | 
             |                     |                     |
      ___ ___|______         ______|______         ______|______ 
     /{p4} {p2} {p1} {p3} {p5}\\   {y3} /{h4} {h2} {h1} {h3} {h5}\\ {y1}   /{a4} {a2} {a1} {a3} {a5}\\
     |   Pharmacy   |------|     HOME     |------|  Gas Station |
     *--------------*   {y4} *--------------* {y2}   *--------------*
             |                  {y5} |                     |            
             |            _________|__________           |            
             |           /   {e4} {e2} {e1} {e3} {e5}   \\          |            
             +-----------|  Electronics Store | ---------+
                         *--------------------*
    """)


CHARACTER_CARDS = {
    "Elderly": (\
        "N95 Respirator",\
        "First Aid Kit"),  # x2 points for each of these
    "Student": ("Water Bottle",\
                "Batteries"),    # x2 points for each of these
    "Parent": ("Extra Clothes",\
               "Extra Cash"),    # x2 points for these
    "Pet Owner": ("Emergency Blanket",\
                  "Canned Food"),       # x2 points for these
    "Community Leader": ("Hand Crank Radio",\
                         "Neighborly Token"),  # x2 points for these
}

ACTION_CARDS = [
    (1, "Flat Tire", "Skip next turn", "Spare Tire"),
    (2, "Road Block", "Move only 1 space next turn", "Important Documents"),
    (3, "Heavy Smoke", "Skip next turn", "N95 Respirator"),
    (4, "Blackout", "Lose next turn’s die roll", "Flashlight"),
    # (5, "Car Trouble", "Discard 1 resource card", "Power Bank"),
    # (6, "Panic", "Trade 1 card if possible", "Blanket"),
    (5, "Bad Directions", "Backtrack 4 spaces", "Hand Crank Radio"),
    (6, "Dehydration", "Lose 5 points", "Water Bottle"),
    (7, "Medical Emergency", "Skip 2 turns", "First Aid Kit"),
    (8, "Food Spoilage", "Lose 5 points", "Canned Food"),
]

# ────────────── COMBO BONUSES ──────────────

COMBO_BONUSES = [
    {
        "name": "Portable Go-Kit Bonus",
        "required": [
            "Water Bottle",
            "First Aid Kit",
            "Canned Food",
        ],
        "points": 3,
        "description": (
            "    [A portable Go-Kit]\n"
            "    You should have this portable kit prepared plus a few more items to carry you through 3 days away from home.\n"
            "    Source: Red Cross"
        ),
    },
    {
        "name": "Prepper Kit Bonus",
        "required": [
            "Water Bottle",
            "First Aid Kit",
            "Canned Food",
            "Important Documents",
            "1 Month of Medication",
        ],
        "points": 6,
        "description": (
            "    [A portable Go-Kit + More!]\n"
            "    Preparing a portable 3-day Go-Kit, plus 1 month of medication in a child-proof container and have important documents ready to go in an emergency.\n"
            "    Source: Red Cross "
        ),
    },
    # Add more combos here later!
]

# --- new board size ---
PATH_LENGTH     = 15          # squares 0-14; Safe Zone is index 15
SAFE_ZONE_INDEX = PATH_LENGTH  # unchanged code that uses this still works

# Action (“red”) squares – cluster near the end
RED_SPACES = {4, 8, 10, 12, 13}

# Shortcuts (optional) – adjust to fit the shorter path
SHORTCUT_SPACES = {5, 9}

NT_BONUS = 3
COMMUNITY_LEADER_NT_BONUS = 4
RESOURCE_POINTS = 2
SAFE_ZONE_POINTS = 5


# ─────────────────────────────── DATA CLASSES ───────────────────────────────

@dataclass
class ResourceCard:
    name: str
    points: int
    origin: str


@dataclass
class CharacterCard:
    name: str
    plus_resource: str
    multiplier_resource: str  # or "Neighborly Token" for Community Leader


@dataclass
class Player:
    name: str
    character: CharacterCard
    inventory: List[ResourceCard] = field(default_factory=list)
    tokens: int = 0
    position: int = 0  # path index during disaster phase
    skipped_turns: int = 0
    one_space_only: bool = False
    reached_safe_zone: bool = False
    bonus_points: int = 0
    last_location: str = "(none)"   # add this field

    # ── inventory helpers ──
    def add_card(self, card: ResourceCard):
        self.inventory.append(card)

    def has_card(self, name: str) -> bool:
        return any(c.name == name for c in self.inventory)

    def remove_any(self, name: Optional[str] = None, value: Optional[int] = None) -> bool:
        """Try to pop a card matching criteria; return True if removed."""
        for idx, c in enumerate(self.inventory):
            if (name is None or c.name == name) and (value is None or c.points == value):
                self.inventory.pop(idx)
                return True
        return False

    # ── scoring ──
    def total_points(self) -> int:
        pts = sum(c.points for c in self.inventory)
        # +1 per matching resource
        pts += sum(RESOURCE_POINTS for c in self.inventory if c.name == self.character.plus_resource)
        # ×2 multiplier for matching resource (add its points again)
        if self.character.multiplier_resource != "Neighborly Token":
            pts += sum(c.points for c in self.inventory if c.name == self.character.multiplier_resource)
        # Neighborly Tokens
        token_value = COMMUNITY_LEADER_NT_BONUS if self.character.name == "Community Leader" else NT_BONUS
        pts += self.tokens * token_value
        # arrival bonus
        pts += self.bonus_points
        # combo bonuses!
        pts += self.combo_bonus_points()
        return pts

    def get_combo_bonuses(self) -> List[str]:
        """Returns the single highest-value combo bonus achieved by this player."""
        inventory_names = [card.name for card in self.inventory]
        # Sort combos by points descending
        for combo in sorted(COMBO_BONUSES, key=lambda c: c["points"], reverse=True):
            if all(req in inventory_names for req in combo["required"]):
                return [combo["name"]]
        return []
    def combo_bonus_points(self) -> int:
        inventory_names = [card.name for card in self.inventory]
        for combo in sorted(COMBO_BONUSES, key=lambda c: c["points"], reverse=True):
            if all(req in inventory_names for req in combo["required"]):
                return combo["points"]
        return 0

    # ── display helpers ──
    def secret_label(self) -> str:
        return f"{self.name} (Character card is secret)"

    def reveal(self) -> str:
        return (
            f"{self.name} – {self.character.name} | Tokens:{self.tokens} | Score: {self.total_points()}"
        )

# ──────────────────────────────── GAME CLASS ────────────────────────────────

class WildfireGame:
    """Top-level game controller."""

    def __init__(self, players: List[Player]):
        self.players = players
        self.phase = "prep"
        self.prep_round = 1
        self.rng = random.Random()
        # build location decks
        self.location_decks: Dict[str, List[ResourceCard]] = {
            loc: [ResourceCard(n, pts, loc) for n, pts in cards] for loc, cards in LOCATIONS.items()
        }
        for deck in self.location_decks.values():
            self.rng.shuffle(deck)

        # --- Give everyone 2 random starting resources ---
        for pl in self.players:
            for _ in range(2):
                loc = self.rng.choice(list(self.location_decks))
                if self.location_decks[loc]:
                    pl.add_card(self.location_decks[loc].pop())

        # action card deck
        self.action_deck = ACTION_CARDS.copy()
        self.rng.shuffle(self.action_deck)
        self.first_to_safe_zone: Optional[Player] = None
    # ───────────────────── TRADING PHASE ─────────────────────
    def trading_phase(self) -> None:
        print("\n=== Optional Trading Phase ===")
        active = [p for p in self.players if not p.reached_safe_zone and p.inventory]
        for p in active:
            if input(f"{p.name}, start a trade? (y/N): ").strip().lower() != "y":
                continue

            partners = [pl for pl in active if pl is not p]
            if not partners:
                print("No partners available.")
                continue

            partner_name = input(f"Pick partner {', '.join(pl.name for pl in partners)}: ").strip()
            partner = next((pl for pl in partners if pl.name == partner_name), None)
            if not partner:
                print("Bad choice – aborted.")
                continue

            print(f"{p.name}'s cards: {[c.name for c in p.inventory]}")
            give = input("Card to give: ").strip()
            print(f"{partner.name}'s cards: {[c.name for c in partner.inventory]}")
            take = input("Card to receive: ").strip()

            if not p.has_card(give) or not partner.has_card(take):
                print("Trade failed – card not owned.")
                continue

            # execute swap
            card_give   = next(c for c in p.inventory      if c.name == give)
            card_take   = next(c for c in partner.inventory if c.name == take)
            p.inventory.remove(card_give)
            partner.inventory.remove(card_take)
            p.inventory.append(card_take)
            partner.inventory.append(card_give)

            # # reward tokens
            # p.tokens += 1
            # partner.tokens += 1
            print("Trade successful – Always check with neighbors to ensure they’re also prepared! [Source: CAL FIRE]")


    # # ── simple ASCII map of a 15-square serpentine path ──
    # def draw_path(self) -> None:
    #     cells = [f"{i:02}" for i in range(PATH_LENGTH)]  # 00–14
    #     for p in self.players:
    #         if p.reached_safe_zone:
    #             continue
    #         mark = p.name[0].upper()
    #         cells[p.position] = mark * 2                  # overwrite number

    #     # 3 rows × 5 columns, serpentine
    #     rows = []
    #     for r in range(2, -1, -1):                       # bottom row is index 0
    #         row = cells[r * 5:(r + 1) * 5]
    #         if (2 - r) % 2:                              # reverse every other row
    #             row.reverse()
    #         rows.append(" ".join(row))

    #     print("\nBelow: letter pairs are players first initials repeated twice, to show their position.")
    #     print("\nSZ == Safe Zone.")
    #     print("\nEvacuation Route (0-14 → SZ):")
    #     for line in rows:
    #         print(line)
    #     print("SZ = Safe Zone (index 15)\n")
    def draw_path(self) -> None:
        # Board positions
        board = [f"{i:02}" for i in range(PATH_LENGTH)] + ["SZ"]

        # Shortcut markers (above)
        shortcut_row = []
        for i in range(PATH_LENGTH):
            if i in SHORTCUT_SPACES:
                shortcut_row.append("SC")
            else:
                shortcut_row.append("  ")
        shortcut_row.append("  ")  # No shortcut in SZ
        print("\nShortcuts: SC means you can gamble for a jump ahead.\n" +
              " ".join(shortcut_row))

        # Number row
        print("Spaces:        " + " ".join(board))

        # Action squares row
        action_row = ["XX" if i in RED_SPACES else "  " for i in range(PATH_LENGTH)] + ["  "]
        print("Action Squares:" + " ".join(action_row))

        # Player rows
        for p in self.players:
            if p.reached_safe_zone:
                pos = PATH_LENGTH  # SZ
            else:
                pos = p.position
            row = ["  " for _ in board]
            initials = (p.name[0] * 2).upper()
            row[pos] = initials
            print(f"{p.name[:10]:10}    :" + " ".join(row))

        print(f"\nSZ = Safe Zone (index 15). +{SAFE_ZONE_POINTS} to reach the safe zone first!")


    # ────────────────────────── TERMINAL HELPERS ──────────────────────────
    @staticmethod
    def clear():
        os.system("cls" if os.name == "nt" else "clear")

    # ────────────────────────────── PHASES ──────────────────────────────

    def run(self):
        self.clear()
        print("=== Wildfire Ready-Set-Go ===\n")
        print("BONUS COMBOS available this game:")
        for combo in COMBO_BONUSES:
            print(f" - {combo['name']} (+{combo['points']} pts):")
            print(f"    Needs: {', '.join(combo['required'])}")
            print(f"{combo['description']}\n")
        print()

        self.preparation_phase()
        self.disaster_phase()
        self.final_scoring()

    # ─────────────────── PREPARATION PHASE ───────────────────

    def preparation_phase(self):
        while self.phase == "prep":
            for p in self.players:
                self.take_prep_turn(p)
                if self.prep_round > 3:
                    if self.roll_disaster_die():
                        print("The wildfire sparks early! Everyone evacuate!\n")
                        self.phase = "disaster"
                        break
            if self.phase == "disaster":
                break
            if self.prep_round >= 7:
                print("Seven rounds complete – the fire front arrives. Evacuate!\n")
                self.phase = "disaster"
                break
            self.prep_round += 1

    def take_prep_turn(self, player: Player):

        # self.clear()
        # print("Players' Inventories and Tokens:")
        # for pl in self.players:
        #     cards = ", ".join(c.name for c in pl.inventory) or "(none)"
        #     print(f"  {pl.name}: {cards} | Tokens: {pl.tokens}")
        # print("-" * 40)
        self.clear()
        # ── compact prep-phase player map ──
        initials = [(pl.name[0] * 2).upper() for pl in self.players]
        initials += ["  "] * (5 - len(initials))   # pad out to 5 slots
        # --- Build minimap arguments by location for up to 5 players ---
        def initials(player):
            return (player.name[0]*2).upper()

        def by_location(locname):
            # Get up to 5 initials of players at this loc
            lst = [initials(pl) if getattr(pl, "last_location", None) == locname else None for pl in self.players]
            # filter to those at loc, keep order, pad with '  '
            result = [i for i in lst if i]
            result += ["  "] * (5 - len(result))
            return result[:5]

        pharmacy   = by_location("Pharmacy")
        grocery    = by_location("Grocery Store")
        gas        = by_location("Gas Station")
        home       = by_location("Home")
        elec       = by_location("Electronics Store")
        yard       = by_location("Yard")

        # Unpack as 25 arguments (order: p1..p5,g1..g5,a1..a5,h1..h5,e1..e5)
        print_prep_map(
            *pharmacy,
            *grocery,
            *gas,
            *home,
            *elec,
            *yard,
        )

        print(f"Preparation Round {self.prep_round}/7 – {player.secret_label()}")
        print()
        print("Players' Inventories, Tokens, Locations, and Profiles:")
        for pl in self.players:
            cards = ", ".join(c.name for c in pl.inventory) or "(none)"
            location = getattr(pl, "last_location", "(none)")
            char = pl.character
            profile = (
                f"{char.name}: +1/{char.plus_resource}, "
                f"x2/{char.multiplier_resource}"
            )
            print(f"  {pl.name}: {cards} | Tokens: {pl.tokens} | Location: {location} | Profile: {profile}")
        print()

        print("\n--- Combo Bonuses Available This Game ---")
        for combo in COMBO_BONUSES:
            print(f" - {combo['name']}: {combo['points']} pts")
            print(f"    Needs: {', '.join(combo['required'])}")
            print(f"{combo['description']}\n")
        print("--- Neighborly Token ---")
        print(f"   The Neighborly Token lets you leave sooner (+5 spaces ahead in disaster). It's also worth {NT_BONUS} points at the end of the game.")
        print()
        print("--- Items Typically Available at Each Location (if not sold out)---")
        for loc, items in LOCATIONS.items():
            items_list = [name for name, _ in items]
            unique_items = sorted(set(items_list), key=items_list.index)  # preserve order, unique
            loc_pad = 25
            print(f"{loc+':': <{loc_pad}} {', '.join(unique_items)}\n", end="")
            # print(f"{loc})
        # print("-" * 40)
        print()
        print("Tokens:", player.tokens)
        print("Inventory:", ", ".join(c.name for c in player.inventory) or "(none)")
        # choice: fast path (token) or visit location
        print(f"\nChoose an action (each resource will be worth {RESOURCE_POINTS} points at end of game):")
        print("  0 – Create a defensible space by clearing flammable vegetation near your home (earn 1 Neighborly Token)")
        for idx, loc in enumerate(LOCATIONS.keys(), 1):
            print(f"  {idx} – Go to {loc} ({len(self.location_decks[loc])} cards left)")
        choice = input("Your selection: ").strip()
        if choice == "0":
            player.tokens += 1
            print("You reduced your fire hazard, earn a Neighborly Token.")
            player.last_location = "Yard"

        elif choice.isdigit() and 1 <= int(choice) <= len(LOCATIONS):
            loc = list(LOCATIONS.keys())[int(choice) - 1]
            deck = self.location_decks[loc]
            player.last_location = loc
            if deck:
                card = deck.pop()
                player.add_card(card)
                print(f"You drew: {card.name} (worth {card.points} pts)")
            else:
                print("No cards left at this location – you lose the turn.")
        else:
            print("Invalid choice – you lose the turn.")
        input("Press Enter to end your turn…")

    def roll_disaster_die(self) -> bool:
        """Return True if a 6 is rolled (disaster triggers)."""
        result = self.rng.randint(1, 6)
        print(f"Disaster die rolled a {result}.")
        return result == 6

    # ───────────────────── DISASTER PHASE ─────────────────────

    def disaster_phase(self):
        self.clear()
        print("=== Disaster Phase – Evacuate! ===")
        # everyone starts at path index 0
        for p in self.players:
            p.position = 0
        turn_counter = 1
        while not self.first_to_safe_zone:
            for p in self.players:
                self.take_disaster_turn(p, turn_counter)
                if self.first_to_safe_zone:
                    break
            # Only allow trading if game is still in progress
            if not self.first_to_safe_zone:
                self.trading_phase()
            turn_counter += 1

        while not self.first_to_safe_zone:
            for p in self.players:
                self.take_disaster_turn(p, turn_counter)
                if self.first_to_safe_zone:
                    break
            self.trading_phase()              # ← add this line
            turn_counter += 1

    def take_disaster_turn(self, player: Player, turn_no: int):
        self.clear()
        self.draw_path()          # ← add this line
        print("Players' Inventories and Tokens:")
        for pl in self.players:
            cards = ", ".join(c.name for c in pl.inventory) or "(none)"
            pos   = f" | Pos: {pl.position}" if self.phase == "disaster" else ""
            print(f"  {pl.name}: {cards} | Tokens: {pl.tokens}{pos}")
        print("-" * 40)
        print()

        print(f"Disaster Turn {turn_no} – {player.name}")
        print(f"Position: {player.position}/24 | Tokens:{player.tokens} | Skips:{player.skipped_turns}")
        print("\n--- Action Cards Reference ---")
        for (num, title, effect, blocker) in ACTION_CARDS:
            if blocker:
                print(f"{title}: {effect} (Prevent with {blocker})")
            else:
                print(f"{title}: {effect}")
        print("-" * 40)

        if player.reached_safe_zone:
            input("Already safe – press Enter…")
            return
        if player.skipped_turns > 0:
            player.skipped_turns -= 1
            print("You are delayed and lose this turn.")
            input("Press Enter…")
            return
        # roll movement die
        if player.one_space_only:
            move = 1
            player.one_space_only = False
            print("Road Block – you may move only 1 space this turn.")
        else:
            move = 2*self.rng.randint(1, 3)
            print(f"You rolled a {move}.")
        # optional token spend
        if player.tokens and not player.reached_safe_zone:
            spend = input("Spend a token to move +5 spaces (y/N)? ").strip().lower()
            if spend == "y":
                player.tokens -= 1
                move += 5
                print("Token spent! +5 movement.")
        # move along path
        new_pos = min(player.position + move, SAFE_ZONE_INDEX)
        print(f"You advance to space {new_pos}.")
        player.position = new_pos
        # check shortcut gamble
        if player.position in SHORTCUT_SPACES and not player.reached_safe_zone:
            gamble = input("You found a shortcut! Gamble? 1-4=fail(+skip), 5-6=skip ahead 3 (y/N): ").strip().lower()
            if gamble == "y":
                roll = self.rng.randint(1, 6)
                print("Roll:", roll)
                if roll >= 5:
                    player.position = min(player.position + 3, SAFE_ZONE_INDEX)
                    print("Success! You jump ahead.")
                else:
                    player.skipped_turns = 1
                    print("Failed – you lose next turn.")
        # check red space
        if player.position in RED_SPACES and not player.reached_safe_zone:
            self.resolve_action_card(player)
        # check safe zone
        if player.position >= SAFE_ZONE_INDEX:
            player.reached_safe_zone = True
            if not self.first_to_safe_zone:
                self.first_to_safe_zone = player
                player.bonus_points += 5
                print(f"Congratulations – you reached the Safe Zone first (+{SAFE_ZONE_POINTS} pts)!")
            else:
                print("You made it to the Safe Zone – well done.")

        # # --- show what each square represents ---
        # print("\nBoard Squares Legend:")
        # for idx in range(PATH_LENGTH):
        #     label = "ACTION" if idx in RED_SPACES else "empty"
        #     print(f"{idx:02}: {label}")
        # print("-" * 40)


        input("Press Enter to pass play…")

    # ───────────────────── ACTION CARDS ─────────────────────

    def draw_action_card(self):
        if not self.action_deck:
            self.action_deck.extend(ACTION_CARDS)
            self.rng.shuffle(self.action_deck)
        return self.action_deck.pop()

    def resolve_action_card(self, player: Player):
        card_id, title, penalty, blocker = self.draw_action_card()
        print(f"‼️  ACTION CARD – {title}: {penalty}")
        # prevention?
        if blocker and player.has_card(blocker):
            use = input(f"Use {blocker} to avoid the penalty (y/N)? ").strip().lower()
            if use == "y":
                print("Penalty avoided.")
                return
        # apply penalty
        if title == "Flat Tire":
            player.skipped_turns += 1
            print("You will skip your next turn.")
        elif title == "Road Block":
            player.one_space_only = True
            print("Next turn you may move only 1 space.")
        elif title == "Heavy Smoke":
            player.skipped_turns += 1
        elif title == "Blackout":
            player.skipped_turns += 1
        elif title == "Car Trouble":
            if player.inventory:
                player.inventory.pop()
                print("You discarded a random resource.")
            else:
                print("No resources to discard.")
        # elif title == "Panic":
        #     others = [pl for pl in self.players if pl is not player and pl.inventory]
        #     if others and player.inventory:
        #         target = self.rng.choice(others)
        #         card_give = player.inventory.pop()
        #         card_take = target.inventory.pop()
        #         player.inventory.append(card_take)
        #         target.inventory.append(card_give)
        #         player.tokens += 1
        #         target.tokens += 1
        #         print(f"You traded with {target.name} and both earned a token.")
        #     else:
        #         print("Trade impossible – no effect.")
        elif title == "Bad Directions":
            player.position = max(0, player.position - 4)
            print("You move back 4 spaces.")
        elif title == "Dehydration":
            player.bonus_points -= 5
            print("You lose 5 points.")
        elif title == "Medical Emergency":
            player.skipped_turns += 2
        elif title == "Food Spoilage":
            # removed = player.remove_any(value=2)
            # print("Food item discarded." if removed else "No 2-pt food to spoil.")
            player.bonus_points -= 5
            print("You lose 5 points.")
        else:
            print("Unknown penalty – none applied.")

    # ───────────────────── FINAL SCORING ─────────────────────

    def final_scoring(self):
        self.clear()
        print("=== Final Scores ===\n")
        ranked = sorted(self.players, key=lambda p: p.total_points(), reverse=True)
        for p in ranked:
            print(p.reveal())
            combos = p.get_combo_bonuses()
            if combos:
                print(f"    Combo Bonuses: {', '.join(combos)} (+{p.combo_bonus_points()} pts)")
        winner = ranked[0]
        print(f"\nWinner: {winner.name} with {winner.total_points()} pts!")


# ────────────────────────────── UTILITIES ──────────────────────────────

def choose_players() -> List[Player]:
    num = 0
    while num not in range(2, 6):
        try:
            num = int(input("How many players (2-5)? "))
        except ValueError:
            pass
    names = []
    for i in range(1, num + 1):
        name = input(f"Name for player {i}: ").strip() or f"Player{i}"
        names.append(name)
    rng = random.Random()
    character_pool = list(CHARACTER_CARDS.items())
    rng.shuffle(character_pool)
    players: List[Player] = []
    for name in names:
        char_name, (plus, mult) = character_pool.pop()
        character = CharacterCard(char_name, plus, mult)
        players.append(Player(name=name, character=character))
        # secretly tell the player their character card
        os.system("cls" if os.name == "nt" else "clear")
        print(f"{name}, your secret character is: {char_name}\n")
        print(f"  +1 pt for each {plus}")
        if mult == "Neighborly Token":
            print(f"  Neighborly Tokens are worth {COMMUNITY_LEADER_NT_BONUS} pts each instead of {NT_BONUS}.")
        else:
            print(f"  ×2 points for each {mult}")
        input("Memorise this and press Enter (others look away)…")
    os.system("cls" if os.name == "nt" else "clear")
    return players

# ──────────────────────────────── MAIN ────────────────────────────────

if __name__ == "__main__":
    players = choose_players()
    game = WildfireGame(players)
    game.run()
