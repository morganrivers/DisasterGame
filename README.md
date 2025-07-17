# Wildfire Evacuation Game  
Natural Hazards course at Universität Potsdam  
Summer Semester 2025

**Team** · Alex · Faith · Aabid · Morgan  

---
![Disaster Game Map](https://github.com/morganrivers/DisasterGame/blob/main/assets/game_board.jpg "Disaster Game Map") 

## Table of Contents
1. [What’s This?](#whats-this)
2. [Educational Goals](#educational-goals)
3. [Quick Start](#quick-start)
4. [Game Components](#game-components)
5. [Detailed Setup](#detailed-setup)
6. [Gameplay Walk-through](#gameplay-walk-through)  
   6.1 [Preparation Phase](#1-preparation-phase)  
   6.2 [Disaster Phase](#2-disaster-phase)  
   6.3 [Trading (optional)](#3-trading-optional)  
   6.4 [Final Scoring](#4-final-scoring)
7. [Learning Outcomes & Discussion Prompts](#learning-outcomes--discussion-prompts)
8. [Real-World Wildfire References](#real-world-wildfire-references)
9. [Credits & Licensing](#credits--licensing)

---

## What’s This?

**Wildfire Evacuation Game** is a two-phase family/party game for **2–5 players**.  
You’ll first scramble for emergency supplies, then race your car along a 15-space escape route while real-life wildfire hazards (Action cards) try to slow you down.  
The code runs entirely in the terminal.

---

## Educational Goals

* Familiarise students with evacuation decision-making under time pressure.  
* Highlight the importance of Go-Kits and defensible space.   
* Teach users content from **Red Cross**, **CAL FIRE**, **NFPA Firewise**, and **Ready.gov** guidelines.  

---

## Quick Start

```bash
python3 game.py
````

1. Enter the number of players (2-5) and their names.
2. Each player privately receives a secret Character card (worth end-game bonuses).
3. Follow on-screen prompts; press **Enter** to advance.
4. First to the Safe Zone gets +5 points. Highest total score wins!

---

## Game Components

| Piece                        | Count | Purpose                                                              |
| ---------------------------- | ----- | -------------------------------------------------------------------- |
| **Location decks**           | 5     | Home, Grocery Store, Pharmacy, Gas Station, Electronics Store        |
| **Resource cards**           | \~60  | Supplies worth 1–4 points each                                       |
| **Character cards (secret)** | 5     | Elderly, Student, Parent, Pet Owner, Community Leader                |
| **Action cards (hazards)**   | 9     | Flat Tire, Heavy Smoke, Bad Directions, etc.                         |
| **Bonus Tokens**             | ∞     | Earned by “creating defensible space” or successful trades           |
| **Game board** (ASCII)       | 15+1  | Spaces 0-14 + **SZ** (Safe Zone) – shortcuts (SC) and hazard squares |

---

## Gameplay Walk-through

### 1. Preparation Phase (≤ 5 rounds)

| Choice                            | Result                                    |
| --------------------------------- | ----------------------------------------- |
| **Visit a Location**              | Draw 1 resource card from that stack.     |
| **Create Defensible Space**       | Skip the draw and gain 1 Bonus Token. |

* Rolling a 6 on the disaster die triggers the wildfire early (*suspense!*).
* After 5 normal rounds, the firefront arrives automatically.

### 2. Disaster Phase

* All players start at space 0.
* On your turn:

  1. Check skip penalties / one-space limit.
  2. Roll 1d6 for movement.
  3. Optionally spend a Bonus Token (+5 spaces).
  4. Landed on a shortcut space (SC)? Gamble (roll ≥ 5) for +3 spaces, otherwise skip next turn.
  5. Landed on a red space? Draw an Action card – decide whether to block it with the matching resource.

### 3. Trading (optional)

After each full round in the Disaster Phase, players may negotiate 1-for-1 trades.

### 4. Final Scoring

1. **Resource points** (face value).
2. **+1 pt** per card that matches your Character’s “plus” resource.
3. **×2 pts** for your Character’s “multiplier” resource (*or Bonus Tokens for the Community Leader*).
4. **Bonus Tokens** (1 pt each; 2 pts for Community Leader).
5. **Combo bonuses** (Go-Kits etc.).
6. **+5 pts** to the first player in the Safe Zone.

Highest score wins. *Tie-breaker: most Bonus Tokens, then youngest player goes for celebratory ice cream.*

---

## Learning Outcomes & Discussion Prompts

1. **Time pressure vs. thoroughness:** Is it better to rush out or secure high-value items first?
2. **Mitigation vs. adaptation:** Does creating defensible space (*a mitigation action*) pay off in points compared to stockpiling supplies?
3. **Risk communication:** How would you rewrite the Action cards to reflect European wildfire contexts?
4. **Equity issues:** The Elderly Character gains bonuses for medical supplies – what barriers exist in real life?

---

## Real-World Wildfire References

| Topic                              | Source / Link                                                                                                                                                                                                                                       |
| ---------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Evacuation Planning                | **CAL FIRE Go! Evacuation Guide** – [https://www.readyforwildfire.org/prepare-for-wildfire/go-evacuation-guide/](https://www.readyforwildfire.org/prepare-for-wildfire/go-evacuation-guide/)                                                        |
| Go-Kit Essentials                  | **American Red Cross Wildfire Safety** – [https://www.redcross.org/get-help/how-to-prepare-for-emergencies/types-of-emergencies/wildfire.html](https://www.redcross.org/get-help/how-to-prepare-for-emergencies/types-of-emergencies/wildfire.html) |
| Defensible Space & Home Hardening  | **NFPA Firewise USA®** – [https://www.nfpa.org/firewise](https://www.nfpa.org/firewise)                                                                                                                                                             |
| Air-Quality & Smoke Health Impacts | **U.S. EPA – Wildfire Smoke** – [https://www.airnow.gov/wildfire-guide-factsheets/](https://www.airnow.gov/wildfire-guide-factsheets/)                                                                                                              |
| Preparedness Checklists (PDFs)     | Red Cross downloadable guides in multiple languages – see link above (scroll to *“Wildfire Safety Checklist – English”*)                                                                                             
*All external content © their respective organisations. Links verified June 2025.*
