#!/usr/bin/env python3
"""
run_strategies.py – 25 000-game Monte-Carlo to compare opening strategies
=========================================================================
Strategies simulated
--------------------
  1. go-kit     – chase the “Portable Go-Kit” combo
  2. prepper    – chase the “Prepper Kit” combo
  3. tokens     – hoard Neighborly Tokens
  4. plus       – secure the profile’s +1-pt resource
  5. mult       – secure the profile’s ×2 resource
  6. random     – baseline (original stochastic policy)
"""
from __future__ import annotations
import random, argparse, itertools, collections, statistics
import pandas as pd
import game as wg                 # your full rules

print("""
        if self.strategy=="go-kit":
            return wg.COMBO_BONUSES[0]["required"]
        if self.strategy=="prepper":
            return wg.COMBO_BONUSES[1]["required"]
        if self.strategy=="tokens":
            return []                 # handled separately
        if self.strategy=="plus":
            return [player.character.plus_resource]
        if self.strategy=="mult":
            return [player.character.multiplier_resource]

    """)
# ----------------------------------------------------------------------#
#  Policy objects – one per player                                      #
# ----------------------------------------------------------------------#
class BasePolicy:
    """Same default behaviour you already had."""
    def choose_prep_action(self, player, game):           # mod: got `player`
        if game.rng.random() < 0.2:
            return "TakeToken"
        return f"Visit_{game.rng.choice(list(game.location_decks))}"
    # disaster-phase helpers
    def spend_token   (self, player, game): return player.tokens and game.rng.random()<0.5
    def gamble_shortcut(self, player, game): return game.rng.random()<0.5
    def use_blocker   (self, player, game): return game.rng.random()<0.8

class StrategyPolicy(BasePolicy):
    """Target-seeking variant; falls back to BasePolicy when satisfied."""
    def __init__(self, strategy:str):
        self.strategy = strategy
    # --- PREP PHASE ------------------------------------------------------
    def _wanted(self, player)->list[str]:
        if self.strategy=="go-kit":
            return wg.COMBO_BONUSES[0]["required"]
        if self.strategy=="prepper":
            return wg.COMBO_BONUSES[1]["required"]
        if self.strategy=="tokens":
            return []                 # handled separately
        if self.strategy=="plus":
            return [player.character.plus_resource]
        if self.strategy=="mult":
            return [player.character.multiplier_resource]
        return []
    def choose_prep_action(self, player, game):
        if self.strategy=="tokens":
            return "TakeToken"
        missing=[itm for itm in self._wanted(player) if not player.has_card(itm)]
        if missing:
            item=missing[0]
            # pick any location whose *remaining* deck still holds that item
            viable=[loc for loc,deck in game.location_decks.items()
                    if any(c.name==item for c in deck)]
            if viable:
                return f"Visit_{game.rng.choice(viable)}"
        return super().choose_prep_action(player, game)
# ----------------------------------------------------------------------#
#  Headless game engine that accepts *per-player* policies              #
# ----------------------------------------------------------------------#
class AutoGame:
    def __init__(self, players:list[wg.Player], policies:list[BasePolicy], rng:random.Random):
        self.players, self.policies, self.rng = players, policies, rng
        self.location_decks={loc:[wg.ResourceCard(n,pts,loc) for n,pts in cards]
                             for loc,cards in wg.LOCATIONS.items()}
        for deck in self.location_decks.values(): rng.shuffle(deck)
    # ---- Only the parts that vary by policy are shown ------------------
    def _prep_phase(self):
        for _round in range(7):
            for pl,pol in zip(self.players,self.policies):
                act=pol.choose_prep_action(pl,self)
                if act=="TakeToken":
                    pl.tokens+=1
                else:
                    loc=act.split("_",1)[1]
                    if self.location_decks[loc]:
                        pl.add_card(self.location_decks[loc].pop())
    def _disaster_phase(self):
        for p in self.players: p.position=0
        first=False
        while not all(p.reached_safe_zone for p in self.players):
            for p,pol in zip(self.players,self.policies):
                if p.reached_safe_zone or p.skipped_turns: p.skipped_turns-=p.skipped_turns>0; continue
                move=1 if p.one_space_only else self.rng.randint(1,6); p.one_space_only=False
                if pol.spend_token(p,self): p.tokens-=1; move+=5
                p.position=min(p.position+move,wg.SAFE_ZONE_INDEX)
                if p.position in wg.SHORTCUT_SPACES and pol.gamble_shortcut(p,self):
                    if self.rng.randint(1,6)>=5: p.position=min(p.position+3,wg.SAFE_ZONE_INDEX)
                    else: p.skipped_turns=1
                if p.position in wg.RED_SPACES: self._action_card(p,pol)
                if p.position>=wg.SAFE_ZONE_INDEX:
                    p.reached_safe_zone=True
                    if not first: first=True; p.bonus_points+=5
    def _action_card(self,p,pol):
        cid,title,pen,block= self.rng.choice(wg.ACTION_CARDS)
        if block and p.has_card(block) and pol.use_blocker(p,self): return
        if title=="Flat Tire":p.skipped_turns+=1
        elif title=="Road Block":p.one_space_only=True
        elif title in {"Heavy Smoke","Blackout"}:p.skipped_turns+=1
        elif title=="Bad Directions":p.position=max(0,p.position-4)
        elif title in {"Dehydration","Food Spoilage"}:p.bonus_points-=5
        elif title=="Medical Emergency":p.skipped_turns+=2
    def play(self):
        self._prep_phase(); self._disaster_phase()
# ----------------------------------------------------------------------#
#  Batch experiment                                                     #
# ----------------------------------------------------------------------#
def run(batch_games:int=1000, players_per_game:int=4, seed:int=42):
    rng=random.Random(seed)
    results=[]
    strategies=["go-kit","prepper","tokens","plus","mult","random"]
    for profile,strategy in itertools.product(wg.CHARACTER_CARDS,strategies):
        wins,scores=0,[]
        for _ in range(batch_games):
            # --- build table -------------------------------------------
            chosen=[profile]+[c for c in wg.CHARACTER_CARDS if c!=profile][:players_per_game-1]
            random.shuffle(chosen)
            players,pols=[],[]
            for idx,char_name in enumerate(chosen):
                plus,mult=wg.CHARACTER_CARDS[char_name]
                pl=wg.Player(f"P{idx}",wg.CharacterCard(char_name,plus,mult))
                players.append(pl)
                pols.append(StrategyPolicy(strategy) if idx==0 else StrategyPolicy("random"))
            g=AutoGame(players,pols,rng); g.play()
            hero=players[0]; scores.append(hero.total_points())
            if hero is max(players,key=lambda p:p.total_points()): wins+=1
        results.append({"profile":profile,"strategy":strategy,
                        "avg_score":statistics.fmean(scores),
                        "win_rate":wins/batch_games})
    df=pd.DataFrame(results)
    # add delta vs random
    base=df[df.strategy=="random"].set_index("profile")["avg_score"]
    df["delta_vs_random"]=df.apply(lambda r:r.avg_score-base[r.profile],axis=1)
    print(df.pivot(index="profile",columns="strategy",
                   values=["avg_score","win_rate","delta_vs_random"]).round(2))
# ----------------------------------------------------------------------#
if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--games",type=int,default=1000)
    args=parser.parse_args()
    run(batch_games=args.games)
