#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sudoku with Score, Difficulty Unlocks, Coins & Skins (Tkinter, single-file)
- 9x9 board
- Score per correct guess based on speed since last correct entry
- Start with Easy unlocked; complete each difficulty once to unlock the next
- Earn coins per correct guess + completion bonus
- Shop to buy color themes (skins) using coins
- Progress and purchases are saved locally in sudoku_save.json

Run: python sudoku_shop.py
"""

import tkinter as tk
from tkinter import ttk, messagebox
import time
import random
import json
import os
from pathlib import Path

SAVE_PATH = Path("sudoku_save.json")

# ---------------------------- PUZZLES ----------------------------------
# Each item: ("puzzle_string_81_chars", "solution_string_81_chars")
# 0 denotes empty cell.
PUZZLES = {
    "Easy": [
        ("530070000600195000098000060800060003400803001700020006060000280000419005000080079",
         "534678912672195348198342567859761423426853791713924856961537284287419635345286179"),
        ("040000000060105000009030070008302900700000004006708100010080600000406090000000050",
         "541697832867145329239831476418362957753219864926758143314985672582476391697123548"),
    ],
    "Medium": [
        ("000260701680070090190004500820100040004602900050003028009300074040050036703018000",
         "435269781682571493197834562826195347374682915951743628519326874248957136763418259"),
        ("030000080006000107000009030040007500700060004003500070020100000904000600010000020",
         "137645289496832157582719436249317568751968324863524971628153794974281653315476892"),
    ],
    "Hard": [
        ("000000907000420180000705026100904000050000040000507009920108000034059000507000000",
         "812653947573492186496715326169934852258176943734527619925168734384259761567341298"),
        ("300000000005009000200504000000700000000000030040000006000000105000030000000201000",
         "397126584415389672286574319163798452872465931549812736638947125721653948954231867"),
    ]
}

# ---------------------------- SKINS / THEMES ---------------------------
SKINS = {
    "Classic": {
        "bg": "#f6f7fb",
        "grid_bg": "#ffffff",
        "given_fg": "#111827",
        "editable_fg": "#1f2937",
        "accent": "#3b82f6",
        "correct": "#10b981",
        "wrong": "#ef4444",
        "block_bg": "#f3f4f6"
    },
    "Ocean": {
        "bg": "#e6f7ff",
        "grid_bg": "#ffffff",
        "given_fg": "#0f172a",
        "editable_fg": "#0ea5e9",
        "accent": "#0284c7",
        "correct": "#14b8a6",
        "wrong": "#ef4444",
        "block_bg": "#e0f2fe"
    },
    "Sunset": {
        "bg": "#fff7ed",
        "grid_bg": "#ffffff",
        "given_fg": "#7c2d12",
        "editable_fg": "#ea580c",
        "accent": "#f97316",
        "correct": "#84cc16",
        "wrong": "#ef4444",
        "block_bg": "#ffedd5"
    },
    "Forest": {
        "bg": "#f0fdf4",
        "grid_bg": "#ffffff",
        "given_fg": "#052e16",
        "editable_fg": "#15803d",
        "accent": "#16a34a",
        "correct": "#22c55e",
        "wrong": "#ef4444",
        "block_bg": "#dcfce7"
    }
}
SKIN_PRICES = {
    "Ocean": 60,
    "Sunset": 60,
    "Forest": 60,
}

# ---------------------------- HELPERS ----------------------------------
def grid_index(r, c):
    return r * 9 + c

def parse_grid(s):
    return [int(ch) for ch in s]

def format_time(seconds):
    m = int(seconds) // 60
    s = int(seconds) % 60
    return f"{m:02d}:{s:02d}"

# ---------------------------- STATE PERSISTENCE ------------------------
DEFAULT_SAVE = {
    "coins": 0,
    "unlocked": ["Easy"],
    "owned_skins": ["Classic"],
    "active_skin": "Classic"
}

def load_state():
    if SAVE_PATH.exists():
        try:
            with open(SAVE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            # ensure keys
            for k, v in DEFAULT_SAVE.items():
                if k not in data:
                    data[k] = v
            return data
        except Exception:
            pass
    return DEFAULT_SAVE.copy()

def save_state(state):
    try:
        with open(SAVE_PATH, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        print("Failed to save state:", e)

# ---------------------------- APP --------------------------------------
class SudokuApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Sudoku — Score • Coins • Skins")
        self.resizable(False, False)

        # state
        self.state_data = load_state()
        self.skin = SKINS[self.state_data["active_skin"]]
        self.current_diff = tk.StringVar(value="Easy")
        self.score = 0
        self.coins = self.state_data["coins"]
        self.start_time = None
        self.last_correct_time = None
        self.timer_running = False
        self.selected = (0, 0)
        self.given_mask = [False]*81
        self.puzzle = [0]*81
        self.solution = [0]*81

        # UI
        self.configure(bg=self.skin["bg"])
        self.build_topbar()
        self.build_grid()
        self.build_controls()
        self.apply_skin()  # apply initial skin
        self.new_game("Easy")

    # ---------------- UI BUILDERS -----------------
    def build_topbar(self):
        top = tk.Frame(self, bg=self.skin["bg"], padx=12, pady=8)
        top.grid(row=0, column=0, sticky="ew")

        ttk.Label(top, text="Difficulty:").pack(side="left", padx=(0, 6))

        self.diff_cb = ttk.Combobox(top, textvariable=self.current_diff,
                                    values=["Easy", "Medium", "Hard"], width=8, state="readonly")
        self.diff_cb.pack(side="left")
        self.diff_cb.bind("<<ComboboxSelected>>", self.on_diff_change)

        self.new_btn = ttk.Button(top, text="New Game", command=lambda: self.new_game(self.current_diff.get()))
        self.new_btn.pack(side="left", padx=8)

        self.shop_btn = ttk.Button(top, text="Shop", command=self.open_shop)
        self.shop_btn.pack(side="left", padx=8)

        # Stats
        self.score_var = tk.StringVar(value="Score: 0")
        self.coins_var = tk.StringVar(value=f"Coins: {self.coins}")
        self.time_var = tk.StringVar(value="Time: 00:00")

        ttk.Label(top, textvariable=self.score_var).pack(side="right", padx=(8,0))
        ttk.Label(top, textvariable=self.coins_var).pack(side="right", padx=(8,0))
        ttk.Label(top, textvariable=self.time_var).pack(side="right", padx=(8,0))

    def build_grid(self):
        wrap = tk.Frame(self, bg=self.skin["bg"], padx=12, pady=8)
        wrap.grid(row=1, column=0)

        self.grid_frame = tk.Frame(wrap, bg=self.skin["grid_bg"], bd=2, relief="groove")
        self.grid_frame.pack()

        self.cells = [[None for _ in range(9)] for _ in range(9)]
        for r in range(9):
            for c in range(9):
                block_bg = self.skin["block_bg"] if ((r//3 + c//3) % 2 == 1) else self.skin["grid_bg"]
                cell_frame = tk.Frame(self.grid_frame, bg=block_bg, bd=0, relief="flat")
                cell_frame.grid(row=r, column=c, padx=(0 if c%3 else 2, 2), pady=(0 if r%3 else 2, 2))

                e = tk.Entry(
                    cell_frame,
                    width=2,
                    justify='center',
                    font=('Arial', 18),
                    relief='flat',
                    highlightthickness=0,  # removes the blue highlight border
                    highlightbackground=block_bg,  # background when unfocused
                    highlightcolor=block_bg,  # background when focused
                    bd=0,
                    insertborderwidth=0  # removes tiny inner blue border around cursor
                )
                e.grid(row=0, column=0, ipadx=4, ipady=4)
                e.bind("<FocusIn>", lambda ev, rr=r, cc=c: self.on_select(rr, cc))
                e.bind("<KeyRelease>", lambda ev, rr=r, cc=c: self.on_key(rr, cc, ev))
                self.cells[r][c] = e

        # Grid lines (bold every 3)
        for i in range(10):
            w = 3 if i % 3 == 0 else 1
            tk.Frame(self.grid_frame, bg=self.skin["accent"], height=w, width=9*38).place(x=0, y=i*38-1)
            tk.Frame(self.grid_frame, bg=self.skin["accent"], height=9*38, width=w).place(x=i*38-1, y=0)

        self.grid_frame.update_idletasks()
        # Fix size
        self.grid_frame.config(width=self.grid_frame.winfo_width(), height=self.grid_frame.winfo_height())

    def build_controls(self):
        ctrl = tk.Frame(self, bg=self.skin["bg"], padx=12, pady=8)
        ctrl.grid(row=2, column=0, sticky="ew")

        self.check_btn = ttk.Button(ctrl, text="Check Selected", command=self.check_selected)
        self.check_btn.pack(side="left")

        self.clear_btn = ttk.Button(ctrl, text="Clear Selected", command=self.clear_selected)
        self.clear_btn.pack(side="left", padx=6)

        self.hint_btn = ttk.Button(ctrl, text="Hint (−5 score)", command=self.give_hint)
        self.hint_btn.pack(side="left", padx=6)

        self.info_var = tk.StringVar(value="Tip: Select a cell, type 1-9, then click 'Check Selected'.")
        info = ttk.Label(ctrl, textvariable=self.info_var, foreground="#6b7280")
        info.pack(side="left", padx=12)

    # ---------------- EVENTS -----------------
    def on_diff_change(self, _evt=None):
        diff = self.current_diff.get()
        if diff not in self.state_data["unlocked"]:
            messagebox.showinfo("Locked", f"{diff} is locked. Finish the previous difficulty to unlock.")
            # revert to highest available
            allowed = self.state_data["unlocked"][-1]
            self.current_diff.set(allowed)
            return
        self.new_game(diff)

    def on_select(self, r, c):
        self.selected = (r, c)

    def on_key(self, r, c, ev):
        # Allow only 1..9, backspace, delete
        if ev.keysym in ("BackSpace", "Delete"):
            return
        ch = ev.char
        if not ch.isdigit() or ch == "0":
            # strip invalid
            self.cells[r][c].delete(0, tk.END)
        else:
            # Keep single digit
            val = ch[-1]
            self.cells[r][c].delete(0, tk.END)
            self.cells[r][c].insert(0, val)

    # ---------------- GAME LOGIC -----------------
    def new_game(self, diff):
        # choose random puzzle
        puzzle, solution = random.choice(PUZZLES[diff])
        self.puzzle = parse_grid(puzzle)
        self.solution = parse_grid(solution)
        self.given_mask = [v != 0 for v in self.puzzle]
        self.score = 0
        self.score_var.set(f"Score: {self.score}")
        self.info_var.set("Fill cells. Faster correct checks = more points!")
        self.populate_grid()
        self.start_timer()

    def populate_grid(self):
        for r in range(9):
            for c in range(9):
                e = self.cells[r][c]
                e.config(state="normal")
                e.delete(0, tk.END)
                idx = grid_index(r, c)
                if self.puzzle[idx] != 0:
                    e.insert(0, str(self.puzzle[idx]))
                    e.config(state="disabled", disabledforeground=self.skin["given_fg"])
                else:
                    e.config(fg=self.skin["editable_fg"])
        self.selected = (0,0)
        self.last_correct_time = time.time()

    def start_timer(self):
        self.start_time = time.time()
        self.timer_running = True
        self.update_clock()

    def stop_timer(self):
        self.timer_running = False

    def update_clock(self):
        if self.timer_running and self.start_time is not None:
            elapsed = time.time() - self.start_time
            self.time_var.set(f"Time: {format_time(elapsed)}")
            self.after(500, self.update_clock)

    def clear_selected(self):
        r, c = self.selected
        idx = grid_index(r, c)
        if self.given_mask[idx]:
            return
        self.cells[r][c].delete(0, tk.END)

    def check_selected(self):
        r, c = self.selected
        idx = grid_index(r, c)
        if self.given_mask[idx]:
            self.info_var.set("This is a given cell.")
            return
        text = self.cells[r][c].get().strip()
        if not text or not text.isdigit():
            self.info_var.set("Enter a digit (1-9).")
            return
        guess = int(text)
        if guess == self.solution[idx]:
            # correct
            now = time.time()
            delta = now - (self.last_correct_time or now)
            self.last_correct_time = now

            # points based on speed: faster -> more
            # e.g., 20 points if within 1s, then decays down to min 1
            pts = max(1, 20 - int(delta))
            self.score += pts
            # coins: small reward per correct guess
            self.coins += pts // 5

            self.state_data["coins"] = self.coins
            save_state(self.state_data)

            self.score_var.set(f"Score: {self.score}")
            self.coins_var.set(f"Coins: {self.coins}")

            self.flash_cell(r, c, good=True)
            self.cells[r][c].config(state="disabled", disabledforeground=self.skin["given_fg"])
            self.puzzle[idx] = guess
            self.given_mask[idx] = True

            if self.is_completed():
                self.on_win()
        else:
            self.flash_cell(r, c, good=False)
            # optional penalty
            self.score = max(0, self.score - 1)
            self.score_var.set(f"Score: {self.score}")
            self.info_var.set("Wrong. Try again.")

    def flash_cell(self, r, c, good=True):
        e = self.cells[r][c]
        color = self.skin["correct"] if good else self.skin["wrong"]
        old_bg = e.cget("bg")
        e.config(bg=color)
        self.after(200, lambda: e.config(bg=old_bg))

    def is_completed(self):
        return all(self.puzzle[i] == self.solution[i] for i in range(81))

    def on_win(self):
        self.stop_timer()
        diff = self.current_diff.get()
        # completion bonus coins
        bonus = {"Easy": 20, "Medium": 40, "Hard": 60}[diff]
        self.coins += bonus
        self.state_data["coins"] = self.coins
        self.coins_var.set(f"Coins: {self.coins}")

        # unlock next difficulty if applicable
        unlock_msg = ""
        order = ["Easy", "Medium", "Hard"]
        i = order.index(diff)
        if i+1 < len(order):
            next_diff = order[i+1]
            if next_diff not in self.state_data["unlocked"]:
                self.state_data["unlocked"].append(next_diff)
                unlock_msg = f"\nUnlocked: {next_diff}!"
        save_state(self.state_data)

        messagebox.showinfo("You win!", f"You completed {diff}!\nScore: {self.score}\n+{bonus} coins.{unlock_msg}")

    def give_hint(self):
        # find first empty cell and fill it with correct answer
        empties = [i for i in range(81) if not self.given_mask[i]]
        if not empties:
            return
        i = random.choice(empties)
        r, c = divmod(i, 9)
        val = self.solution[i]
        self.cells[r][c].delete(0, tk.END)
        self.cells[r][c].insert(0, str(val))
        self.cells[r][c].config(state="disabled", disabledforeground=self.skin["given_fg"])
        self.puzzle[i] = val
        self.given_mask[i] = True

        self.score = max(0, self.score - 5)
        self.score_var.set(f"Score: {self.score}")

        if self.is_completed():
            self.on_win()

    # ---------------- SHOP / SKINS -----------------
    def open_shop(self):
        win = tk.Toplevel(self)
        win.title("Shop — Skins")
        win.resizable(False, False)
        win.configure(bg=self.skin["bg"])

        ttk.Label(win, text=f"Coins: {self.coins}").grid(row=0, column=0, columnspan=3, pady=(10, 10))

        row = 1
        for name in SKINS.keys():
            if name == "Classic":
                ttk.Label(win, text=f"{name} (Owned)").grid(row=row, column=0, padx=10, pady=6, sticky="w")
                act_btn = ttk.Button(win, text="Activate", command=lambda n=name: self.set_skin(n))
                act_btn.grid(row=row, column=1, padx=6)
            else:
                owned = (name in self.state_data["owned_skins"])
                price = SKIN_PRICES.get(name, 0)
                label_text = f"{name} — {('Owned' if owned else f'{price} coins')}"
                ttk.Label(win, text=label_text).grid(row=row, column=0, padx=10, pady=6, sticky="w")

                if owned:
                    ttk.Button(win, text="Activate",
                               command=lambda n=name: self.set_skin(n)).grid(row=row, column=1, padx=6)
                else:
                    ttk.Button(win, text="Buy",
                               command=lambda n=name, p=price, w=win: self.buy_skin(n, p, w)).grid(row=row, column=1, padx=6)
            row += 1

        # Close
        ttk.Button(win, text="Close", command=win.destroy).grid(row=row, column=0, columnspan=3, pady=(12, 12))

    def buy_skin(self, name, price, win):
        if self.coins < price:
            messagebox.showwarning("Not enough coins", "You don't have enough coins.")
            return
        self.coins -= price
        self.state_data["coins"] = self.coins
        self.state_data["owned_skins"].append(name)
        save_state(self.state_data)
        self.coins_var.set(f"Coins: {self.coins}")
        messagebox.showinfo("Purchased", f"You bought '{name}'!")
        win.destroy()
        self.open_shop()

    def set_skin(self, name):
        if name not in self.state_data["owned_skins"]:
            messagebox.showerror("Locked", "You don't own this skin yet.")
            return
        self.state_data["active_skin"] = name
        save_state(self.state_data)
        self.skin = SKINS[name]
        self.apply_skin()

    def apply_skin(self):
        # Backgrounds
        self.configure(bg=self.skin["bg"])
        for child in self.winfo_children():
            if isinstance(child, tk.Frame):
                child.configure(bg=self.skin["bg"])

        # Grid cell colors
        for r in range(9):
            for c in range(9):
                e = self.cells[r][c]
                e.config(fg=self.skin["editable_fg"])
                if e.cget("state") == "disabled":
                    e.config(disabledforeground=self.skin["given_fg"])

        # Draw bold grid outlines again with accent
        for w in self.grid_frame.place_slaves():
            w.destroy()
        for i in range(10):
            w = 3 if i % 3 == 0 else 1
            tk.Frame(self.grid_frame, bg=self.skin["accent"], height=w, width=9*38).place(x=0, y=i*38-1)
            tk.Frame(self.grid_frame, bg=self.skin["accent"], height=9*38, width=w).place(x=i*38-1, y=0)

        # Update coin label color (use ttk default text color)

# ---------------------------- MAIN -------------------------------------
if __name__ == "__main__":
    # Prefer system's Tk scaling for better look on HiDPI
    try:
        tk.CallWrapper = tk.CallWrapper  # quirk to avoid linters complaining
        # try setting high DPI awareness on Windows (optional)
        if os.name == "nt":
            try:
                import ctypes
                ctypes.windll.shcore.SetProcessDpiAwareness(1)
            except Exception:
                pass
    except Exception:
        pass

    app = SudokuApp()
    app.mainloop()
