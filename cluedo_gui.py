#!/usr/bin/env python3
"""
cluedo_gui.py – Card‑grid Cluedo helper  (v1.9‑en)

Features
--------
• ✅ / ❌ / ? marks in a single grid  
• spare‑card distribution + live (known / total) counters in the column headers  
• click a row to append its enum token to the command‑entry box  
• commands:
    own <card>                     – you own CARD (✅ for you, ❌ for others)
    not <player> <card>            – that player lacks CARD (❌)
    has <player> <card>            – that player has CARD (✅, ❌ for others)
    ask <asker> c1 c2 c3 <showers …|none>
         * marks ? for each shower
         * if YOU already own 2/3 cards → the shower must hold the 3rd,
           so it’s marked ✅ for the shower and ❌ for every other player
    reset                           – clear the grid
    help                            – popup cheat‑sheet
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from enum import Enum
from typing import Dict, List, Tuple

# --------------------------------------------------------------------------- #
# Card definitions
# --------------------------------------------------------------------------- #
class Suspect(Enum):
    SCARLET = "Miss Scarlet"
    MUSTARD = "Colonel Mustard"
    WHITE   = "Mrs. White"
    GREEN   = "Reverend Green"
    PEACOCK = "Mrs. Peacock"
    PLUM    = "Professor Plum"

class Weapon(Enum):
    CANDLESTICK = "Candlestick"
    DAGGER      = "Dagger"
    LEAD_PIPE   = "Lead Pipe"
    REVOLVER    = "Revolver"
    ROPE        = "Rope"
    WRENCH      = "Wrench"

class Room(Enum):
    KITCHEN        = "Kitchen"
    BALLROOM       = "Ballroom"
    CONSERVATORY   = "Conservatory"
    DINING_ROOM    = "Dining Room"
    BILLIARD_ROOM  = "Billiard Room"
    LIBRARY        = "Library"
    LOUNGE         = "Lounge"
    HALL           = "Hall"
    STUDY          = "Study"

Card = Suspect | Weapon | Room
CARDS: List[Card] = [*Suspect, *Weapon, *Room]
TOTAL_IN_PLAY = len(CARDS) - 3          # 3 cards in the case‑file

CARD_LOOKUP: Dict[str, Card] = (
    {c.name.lower(): c for c in CARDS} |
    {c.value.lower(): c for c in CARDS}
)

NO_SYMBOL, YES_SYMBOL, MAYBE_SYMBOL = "❌", "✅", "?"

# --------------------------------------------------------------------------- #
class CluedoGUI(tk.Tk):
    PAD = {"padx": 6, "pady": 6}
    MIN_P, MAX_P = 3, 6

    # ..................................................................... #
    def __init__(self) -> None:
        super().__init__()
        self.title("Cluedo Solver v1.9‑en")
        self.resizable(True, True)

        self.card_images: Dict[str, tk.PhotoImage] = {}

        self.num_players = 4
        self.players: List[str] = []
        self.expected: Dict[str, int] = {}
        self.known: Dict[str, int]   = {}

        self.grid_state: Dict[Tuple[Card, str], str] = {}
        self.case: Dict[str, Card] = {}          # NEW – found solution pieces

        self._build_menu()
        self._build_ui()

    # ------------------------------------------------------------------ #
    # Menu
    # ------------------------------------------------------------------ #
    def _build_menu(self) -> None:
        bar = tk.Menu(self)

        game = tk.Menu(bar, tearoff=0)
        game.add_command(label="Reset", command=self._reset)
        game.add_separator()
        game.add_command(label="Quit", command=self.destroy)
        bar.add_cascade(label="Game", menu=game)

        settings = tk.Menu(bar, tearoff=0)
        settings.add_command(label="Player Count…",
                             command=self._player_count_dialog)
        bar.add_cascade(label="Settings", menu=settings)

        self.config(menu=bar)

      # ------------------------------------------------------------------ #
    # UI
    # ------------------------------------------------------------------ #
    def _get_card_image(self, name: str) -> tk.PhotoImage:
        """Load and cache the image for a card (e.g., 'scarlet.png'). Fallback to 'card.png'."""
        name = name.lower()
        if name in self.card_images:
            return self.card_images[name]
        try:
            img = tk.PhotoImage(file=f"cards/{name}.png")
        except Exception:
            img = self.card_image  # fallback to default
        self.card_images[name] = img
        return img



    def _build_ui(self) -> None:
        for w in self.winfo_children():
            w.destroy()

        self.grid_state.clear()

            # Load card image
        try:
            self.card_image = tk.PhotoImage(file="cards/card.png")

        except Exception as e:
            messagebox.showwarning("Image Load Error", f"Could not load card.png\n{e}")
            self.card_image = None


        self.known.clear()
        self._compute_totals()

        # Layout container
        main = ttk.Frame(self)
        main.grid(row=0, column=0, sticky="nsew")
        main.columnconfigure(0, weight=3)
        main.columnconfigure(1, weight=1)
        main.rowconfigure(0, weight=1)

        left_panel = ttk.Frame(main)
        left_panel.grid(row=0, column=0, sticky="nsew", **self.PAD)

        right_panel = ttk.Frame(main)
        right_panel.grid(row=0, column=1, sticky="nsew", **self.PAD)


        # ▶ toolbar
        top = ttk.Frame(left_panel)
        top.pack(fill="x")
        ttk.Button(top, text="Players…", command=self._player_count_dialog).pack(side="left")

        # ▶ Treeview grid
        self.tree = ttk.Treeview(
            left_panel, columns=["card", *self.players],
            show="headings", height=len(CARDS)
        )
        self.tree.heading("card", text="Card")
        self.tree.column("card", width=180, anchor="w")
        for p in self.players:
            self.tree.heading(p, text=self._hdr(p))
            self.tree.column(p, width=70, anchor="center")
        for card in CARDS:
            short_name = card.name.capitalize()
            self.tree.insert("", "end", iid=card.name, values=[short_name] + ["" for _ in self.players])

        self.tree.bind("<<TreeviewSelect>>", self._on_row_click)
        self.tree.pack(fill="both", expand=True, **self.PAD)

        # ▶ live suggestion label
        self.suggest_var = tk.StringVar(value="Next suggestion → …")
        ttk.Label(left_panel, textvariable=self.suggest_var, font=("TkDefaultFont", 10, "italic"))\
            .pack(anchor="w", **self.PAD)

        # ▶ action bar
        action_bar = ttk.Frame(left_panel)
        action_bar.pack(anchor="w", **self.PAD)
        for act in ("own", "not", "has", "ask", "play", "is", "reset"):
            ttk.Button(action_bar, text=act, command=lambda a=act: self._append_entry(a)).pack(side="left", padx=2)

        # ▶ help + command
        ttk.Label(left_panel, text="own / not / has / ask • click a row to paste its token\n(type 'help' for details)", justify="left").pack(anchor="w", **self.PAD)

        bar = ttk.Frame(left_panel)
        bar.pack(fill="x", **self.PAD)
        self.cmd = tk.StringVar()
        self.entry = ttk.Entry(bar, textvariable=self.cmd)
        self.entry.pack(side="left", fill="x", expand=True)
        self.entry.bind("<Return>", self._on_cmd)
        ttk.Button(bar, text="Execute", command=self._on_cmd).pack(side="left", padx=4)

        # ▶ right panel – clickable cards
        for label, group in (("Suspects", Suspect), ("Weapons", Weapon)):
            section = ttk.LabelFrame(right_panel, text=label)
            section.pack(fill="x", pady=4)
            for card in group:
                btn = ttk.Button(
                    section,
                    text=card.name.capitalize(),
                    image=self._get_card_image(card.name),
                    compound="top",  # image left of text
                    width=1,
                    command=lambda c=card.name: self._append_entry(c)
                )
                btn.pack(side="left", padx=2, pady=2)

        # Room cards → split into two rows
        room_section = ttk.LabelFrame(right_panel, text="Rooms")
        room_section.pack(fill="x", pady=4)

        rooms = list(Room)
        half = len(rooms) // 2

        upper_row = ttk.Frame(room_section)
        upper_row.pack(fill="x")
        for card in rooms[:half]:
            btn = ttk.Button(
                upper_row,
                text=card.name.capitalize(),
                image=self._get_card_image(card.name),

                compound="top",  # image left of text
                width=1,
                command=lambda c=card.name: self._append_entry(c)
            )
            btn.pack(side="left", padx=2, pady=2)

        lower_row = ttk.Frame(room_section)
        lower_row.pack(fill="x")
        for card in rooms[half:]:
            btn = ttk.Button(
                lower_row,
                text=card.value,
                image=self._get_card_image(card.name),

                compound="top",  # image left of text
                width=1,
                command=lambda c=card.name: self._append_entry(c)
            )
            btn.pack(side="left", padx=2, pady=2)




        # ▶ initial suggestion
        self._update_suggestion()

    # ------------------------------------------------------------------ #
    # Totals / headers
    # ------------------------------------------------------------------ #
    def _compute_totals(self) -> None:
        self.players = ["You"] + [f"Player {i}"
                                  for i in range(2, self.num_players + 1)]
        base, extras = divmod(TOTAL_IN_PLAY, self.num_players)
        self.expected = {p: base for p in self.players}
        for i in range(1, extras + 1):
            if i < len(self.players):
                self.expected[self.players[i]] += 1
        self.known = {p: 0 for p in self.players}

    def _hdr(self, p: str) -> str:
        return f"{p} ({self.known[p]}/{self.expected[p]})"

    def _refresh_hdrs(self) -> None:
        for p in self.players:
            self.tree.heading(p, text=self._hdr(p))

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _normalize_player(self, tok: str) -> str:
        t = tok.lower()
        if t in {"you", "me"}:
            return "You"
        if t.isdigit() and 2 <= int(t) <= self.num_players:
            return f"Player {int(t)}"
        if t.startswith("player") and t[6:].isdigit():
            n = int(t[6:])
            if 2 <= n <= self.num_players:
                return f"Player {n}"
        raise ValueError(f"Unknown player: {tok}")

    def _parse_card(self, parts) -> Card:
        key = " ".join(parts).lower()
        card = CARD_LOOKUP.get(key)
        if card is None:
            raise ValueError(f"Unknown card: {' '.join(parts)}")
        return card
    
    # ------------------------------------------------------------------ #
    # Entry helper (used by card clicks *and* action‑bar buttons)
    # ------------------------------------------------------------------ #
    def _append_entry(self, token: str):
        cur = self.cmd.get()
        space = " " if cur and not cur.endswith(" ") else ""
        self.cmd.set(f"{cur}{space}{token} ")
        self.entry.icursor("end")
        self.entry.focus_set()


    # ------------------------------------------------------------------ #
    # Suggestion helper
    # ------------------------------------------------------------------ #
    def _update_suggestion(self):
        """Propose a trio — prefer cards that are not solved yet."""

        def pick(group):
            for card in group:
                # Skip if it's in the case file
                if card in self.case.values():
                    continue

                # Skip if anyone has it (✅)
                if any(self.grid_state.get((card, p)) == YES_SYMBOL for p in self.players):
                    continue

                # Prefer cards with at least one '?' (uncertainty)
                col_vals = [self.grid_state.get((card, p), "") for p in self.players]
                if "?" in col_vals:
                    return card.name

            # Otherwise, pick any unsolved card (even if all ❌ — might be case file!)
            for card in group:
                if card not in self.case.values() and not any(
                    self.grid_state.get((card, p)) == YES_SYMBOL for p in self.players
                ):
                    return card.name

            return "(done)"

        sus  = pick(Suspect)
        wep  = pick(Weapon)
        room = pick(Room)
        self.suggest_var.set(f"Next suggestion →  {sus} • {wep} • {room}")


    def _mark(self, player: str, card: Card, sym: str) -> None:
        col = self.players.index(player) + 1
        vals = list(self.tree.item(card.name, "values"))
        prev = self.grid_state.get((card, player))
        if prev == YES_SYMBOL and sym != YES_SYMBOL:
            self.known[player] -= 1
        if prev in {YES_SYMBOL, NO_SYMBOL} and sym == MAYBE_SYMBOL:
            return  # keep definitive info
        vals[col] = sym
        self.tree.item(card.name, values=vals)
        self.grid_state[(card, player)] = sym

    def _set_yes(self, player: str, card: Card) -> None:
        if self.grid_state.get((card, player)) != YES_SYMBOL:
            self.known[player] += 1
        self._mark(player, card, YES_SYMBOL)
    


    # ------------------------------------------------------------------
    # Case‑file helpers
    # ------------------------------------------------------------------
    def _auto_deduce_case(self):
        """If a card is ❌ for all players → mark as case file.  
        If only one unknown card remains in a group → mark that too.
        """
        for group, label in ((Suspect, "suspect"), (Weapon, "weapon"), (Room, "room")):
            if label in self.case:
                continue

            unsolved = []
            for card in group:
                if card in self.case.values():
                    continue

                all_no = all(
                    self.grid_state.get((card, p)) == NO_SYMBOL
                    for p in self.players
                )
                if all_no:
                    self._set_case(card)
                    continue

                # track card for fallback logic
                any_yes = any(self.grid_state.get((card, p)) == YES_SYMBOL for p in self.players)
                if not any_yes:
                    unsolved.append(card)

            # fallback logic: only one unknown → must be the case file
            if label not in self.case and len(unsolved) == 1:
                self._set_case(unsolved[0])


    
    def _set_case(self, card: Card):
        """Visually mark a card as the case‑file solution."""
        cat = (
            "suspect" if isinstance(card, Suspect)
            else "weapon" if isinstance(card, Weapon)
            else "room"
        )
        if self.case.get(cat) == card:
            return                              # already done
        self.case[cat] = card

        # add a ★ prefix to the leftmost cell
        vals = list(self.tree.item(card.name, "values"))
        if not vals[0].startswith("★ "):
            vals[0] = f"★ {vals[0]}"
            self.tree.item(card.name, values=vals)

        # everyone else cannot own it
        for p in self.players:
            self._mark(p, card, NO_SYMBOL)


    # ------------------------------------------------------------------ #
    # UI events
    # ------------------------------------------------------------------ #
    def _on_row_click(self, _event) -> None:
        sel = self.tree.selection()
        if sel:
            token = sel[0]
            cur = self.cmd.get()
            self._append_entry(token)
            self.entry.icursor("end")

    # ------------------------------------------------------------------ #
    # Command router
    # ------------------------------------------------------------------ #
    def _on_cmd(self, *_event) -> None:
        text = self.cmd.get().strip()
        self.cmd.set("")
        if not text:
            return
        cmd, *args = text.split()
        try:
            {
                "own":  self._c_own,
                "not":  self._c_not,
                "has":  self._c_has,
                "ask":  self._c_ask,
                "play": self._c_play,      # ⇒ play = ask with bypass logic
                "is":   self._c_is,
                "reset": lambda *_: self._reset(),
                "help":  lambda *_: self._help()
            }[cmd.lower()](args)
        except KeyError:
            messagebox.showerror("Error", "Unknown command")
        except (IndexError, ValueError) as exc:
            messagebox.showerror("Error", str(exc))

    # ------------------------------------------------------------------ #
    # Command implementations
    # ------------------------------------------------------------------ #
    def _c_own(self, args):
        if not args:
            raise IndexError("own syntax: own <card1> <card2> …")

        cards = [self._parse_card([arg]) for arg in args]
        expected = self.expected["You"]

        if len(cards) != expected:
            raise ValueError(f"You are expected to have {expected} cards, not {len(cards)}.")

        owned = set(cards)

        for card in CARDS:
            if card in owned:
                self._set_yes("You", card)
                for p in self.players[1:]:
                    self._mark(p, card, NO_SYMBOL)
            else:
                self._mark("You", card, NO_SYMBOL)

        self._refresh_hdrs()
        self._auto_deduce_case()
        self._update_suggestion()


    def _c_not(self, args):
        if len(args) < 2:
            raise IndexError
        player = self._normalize_player(args[0])
        card   = self._parse_card(args[1:])
        self._mark(player, card, NO_SYMBOL)
        self._refresh_hdrs()
        self._auto_deduce_case()          # NEW
        self._update_suggestion()         # (if you added the suggestion line)



    def _c_has(self, args):
        if len(args) < 2:
            raise IndexError
        player = self._normalize_player(args[0])
        card   = self._parse_card(args[1:])
        self._set_yes(player, card)
        for p in self.players:
            if p != player:
                self._mark(p, card, NO_SYMBOL)
        self._refresh_hdrs()
        self._auto_deduce_case()          # NEW
        self._update_suggestion()         # (if you added the suggestion line)


    def _c_is(self, args):
        """is <card> – manually state that CARD is in the case file."""
        if not args:
            raise IndexError
        card = self._parse_card(args)
        self._set_case(card)
        self._refresh_hdrs()
        self._auto_deduce_case()          # NEW
        self._update_suggestion()         # (if you added the suggestion line)




    # ------------------------------------------------------------------ #
    # ask / play    (same implementation; 'play' maps here too)
    # ------------------------------------------------------------------ #
    def _c_ask(self, args):
        """
        ask|play <asker> c1 c2 c3 <shower|none>

        • '?' for every listed shower
        • If YOU or the asker already owns two of the three cards,
          the shower must have the third  → ✅ + global ❌.
        • NEW: every opponent *between* asker and shower (exclusive,
          clockwise) is marked ❌ on all three cards.  If nobody shows,
          every opponent is ❌ on all three cards.
        """
        if len(args) < 5:
            raise IndexError("ask syntax: asker c1 c2 c3 <shower …|none>")

        asker_tok, c1, c2, c3, *tail = args
        cards = [self._parse_card([tok]) for tok in (c1, c2, c3)]

        shower_given = (len(tail) > 0 and tail[0].lower() != "none")
        showers = [self._normalize_player(t) for t in tail] if shower_given else []
        asker  = self._normalize_player(asker_tok)
        showers = [] if (len(tail)==1 and tail[0].lower()=="none") \
                  else [self._normalize_player(t) for t in tail]

        # every other opponent is known NOT to have any of the three cards
        bypasses = [p for p in self.players
                    if p not in {asker, "You", *showers}]
        for p in bypasses:
            for c in cards:
                self._mark(p, c, NO_SYMBOL)

        # --- 2. core shower logic (old behaviour) ----------------------
        owned_two_holder = None
        for player in {"You", asker}:
            yes_count = sum(
                self.grid_state.get((c, player)) == YES_SYMBOL
                for c in cards
            )
            if yes_count >= 2:
                owned_two_holder = player
                break

        deduced = None
        if owned_two_holder:
            deduced = next(
                c for c in cards
                if self.grid_state.get((c, owned_two_holder)) != YES_SYMBOL
            )

        for shower in showers:
            if deduced:
                self._set_yes(shower, deduced)
                for p in self.players:
                    if p != shower:
                        self._mark(p, deduced, NO_SYMBOL)
                for c in cards:
                    if c != deduced:
                        self._mark(shower, c, NO_SYMBOL)
            else:
                for c in cards:
                    self._mark(shower, c, MAYBE_SYMBOL)

        # --- 3. finish up ---------------------------------------------
        self._refresh_hdrs()
        self._auto_deduce_case()
        self._update_suggestion()

        # ------------------------------------------------------------------ #
    # play  – one command for every real‑life outcome
    # ------------------------------------------------------------------ #
    def _c_play(self, args):
        """
        play <asker> c1 c2 c3  p1 [shown1]  p2 [shown2] ... | none

        • explicit “shownX” card → ✅ for shower on that card, ❌ otherwise
        • player without card → ❌ for all three
        • 'none' → nobody answered → ❌ for all opponents on cards you don’t have
        """
        if len(args) < 4:
            raise IndexError("play syntax: c1 c2 c3 <pairs…|none>")

        c1, c2, c3, *tail = args
        asker = "You"
        trio = [self._parse_card([c]) for c in (c1, c2, c3)]

        pairs: list[tuple[str, Card | None]] = []
        if len(tail) == 1 and tail[0].lower() == "none":
            # Nobody answered → deduce for each card
            for c in trio:
                if self.grid_state.get((c, "You")) != YES_SYMBOL:
                    for p in self.players:
                        if p != "You":
                            self._mark(p, c, NO_SYMBOL)
            self._refresh_hdrs()
            self._auto_deduce_case()
            self._update_suggestion()
            return

        # ---- parse player/shown pairs
        i = 0
        while i < len(tail):
            player = self._normalize_player(tail[i])
            i += 1
            shown: Card | None = None
            if i < len(tail):
                try:
                    shown_candidate = self._parse_card([tail[i]])
                    if shown_candidate in trio:
                        shown = shown_candidate
                        i += 1
                except ValueError:
                    pass
            pairs.append((player, shown))

        showers = {p for p, _ in pairs}
        bypasses = [p for p in self.players if p not in {asker, "You"} | showers]

        # ---- mark based on what each player showed or didn’t
        for shower, shown in pairs:
            if shown:
                self._set_yes(shower, shown)
                for c in trio:
                    if c != shown and self.grid_state.get((c, shower)) not in {YES_SYMBOL, NO_SYMBOL}:
                        self._mark(shower, c, M)
                for p in self.players:
                    if p != shower:
                        self._mark(p, shown, NO_SYMBOL)
            else:
                # no card shown → mark ❌ for all three
                for c in trio:
                    self._mark(shower, c, NO_SYMBOL)

        # ---- bypass players can't have any of the cards
        for p in bypasses:
            for c in trio:
                self._mark(p, c, NO_SYMBOL)

        self._refresh_hdrs()
        self._auto_deduce_case()
        self._update_suggestion()




    # ------------------------------------------------------------------ #
    # Misc UI helpers
    # ------------------------------------------------------------------ #
    def _reset(self):
        if messagebox.askyesno("Reset", "Clear the grid?"):
            self._build_ui()

    def _help(self):
        messagebox.showinfo("Commands", HELP_TEXT)

    def _player_count_dialog(self):
        n = simpledialog.askinteger(
            "Players", "Number of players (3–6):",
            parent=self,
            minvalue=self.MIN_P, maxvalue=self.MAX_P,
            initialvalue=self.num_players
        )
        if n and n != self.num_players:
            self.num_players = n
            self._build_ui()
    

# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    CluedoGUI().mainloop()
