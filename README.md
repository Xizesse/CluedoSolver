# Cluedo GUI Solver

An interactive grid-based assistant to help you solve the game of Cluedo (Clue) with logic and speed. Track cards, ask questions, and let the app deduce the hidden case file with minimal effort.

---

## Features

- ✅ / ❌ / ? status tracking in a shared grid
- Card ownership command system
- Automatic deduction of case-file cards (solution)
- Live player card counters (known / total)
- Click-to-insert card tokens
- Smart suggestions for next guesses

---

## GUI

![image](https://github.com/user-attachments/assets/796fb156-25f1-4d43-b617-6308fef5514c)

---

## How to Run

### Requirements
- Python 3.7+
- Tkinter

### Launch

```bash
python cluedo_gui.py
```

---

## Commands and How to Use Them

You can interact with the logic assistant using natural, simple commands typed into the input box at the bottom of the app. Press **Enter** or click **Execute** to run a command.

---

### 🎮 Command List

| Command                      | What It Does                                                                 |
|-----------------------------|------------------------------------------------------------------------------|
| `own <card1> <card2> …`     | Declare that you own the listed cards. ✅ for you, ❌ for others.             |
| `not <player> <card>`       | Mark that a player **does not** have a certain card.                        |
| `has <player> <card>`       | Mark that a player **has** a card. Others will be marked ❌ for that card.   |
| `ask <asker> c1 c2 c3 <shower1> <shower2> … \| none` | Used when a player asked about 3 cards. Marks `?` for any player who **might** have shown a card. If 2/3 are known to be owned by the asker or you, the third is deduced. |
| `play <c1> <c2> <c3> <p1> [shown1] <p2> [shown2] … \| none` | Used to record a real play. You can specify who showed and what. Handles automatic ❌s and ✅s. |
| `is <card>`                 | Manually declare that a card is part of the case file (solution).           |
| `reset`                     | Clears the entire grid and restarts.                                        |
| `help`                      | Shows a popup with a cheat-sheet of commands.                               |

---

### 💡 Examples

```text
own dagger lounge plum
```
→ You own those 3 cards. They are ❌ for all other players.

```text
not player2 kitchen
```
→ Player 2 does **not** have the Kitchen card.

```text
has player3 wrench
```
→ Player 3 has the Wrench card. Everyone else is ❌ for it.

```text
ask player2 revolver ballroom scarlet player3
```
→ Player 2 asked about these 3 cards. Player 3 responded, but we don’t know what they showed.

```text
play revolver ballroom scarlet player3 ballroom
```
→ You asked and player 3 showed **Ballroom**.

```text
play revolver ballroom scarlet none
```
→ You asked and **nobody** showed any card. If you don’t own a card, everyone else is ❌ for it — possibly case file!

```text
is rope
```
→ You manually mark Rope as one of the solution cards.
