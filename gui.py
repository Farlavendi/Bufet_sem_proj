import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from db.connection import Database
from models.tovar import Tovar
from models.zakaznik import Zakaznik
from models.objednavka import Objednavka
from models.pouzivatel import Pouzivatel
from repositories.tovar_repo import TovarRepo
from repositories.zakaznik_repo import ZakaznikRepo
from repositories.objednavka_repo import ObjednavkaRepo
from repositories.pouzivatel_repo import PouzivatelRepo

# ── Farby a fonty ─────────────────────────────────────
BG         = "#1e1e2e"   # tmavé pozadie
SURFACE    = "#2a2a3d"   # karty / panely
ACCENT     = "#f5a623"   # oranžová — bufet, jedlo
ACCENT2    = "#7c6af7"   # fialová — sekundárna
TEXT       = "#e8e8f0"
TEXT_DIM   = "#888899"
SUCCESS    = "#4caf7d"
DANGER     = "#e05c5c"
BORDER     = "#3a3a50"

FONT_TITLE = ("Helvetica", 18, "bold")
FONT_HEAD  = ("Helvetica", 12, "bold")
FONT_BODY  = ("Helvetica", 10)
FONT_SMALL = ("Helvetica", 9)


# ══════════════════════════════════════════════════════
#  Pomocné widgety
# ══════════════════════════════════════════════════════
class StyledButton(tk.Button):
    def __init__(self, parent, text, command, color=ACCENT, **kw):
        super().__init__(
            parent, text=text, command=command,
            bg=color, fg=BG, font=FONT_BODY,
            relief="flat", padx=12, pady=5,
            cursor="hand2", activebackground=color,
            activeforeground=BG, **kw
        )
        self.bind("<Enter>", lambda e: self.config(bg=self._lighten(color)))
        self.bind("<Leave>", lambda e: self.config(bg=color))

    @staticmethod
    def _lighten(hex_color: str) -> str:
        r, g, b = int(hex_color[1:3], 16), int(hex_color[3:5], 16), int(hex_color[5:7], 16)
        r, g, b = min(255, r + 30), min(255, g + 30), min(255, b + 30)
        return f"#{r:02x}{g:02x}{b:02x}"


class LabeledEntry(tk.Frame):
    """Label + Entry v jednom widgete."""
    def __init__(self, parent, label: str, width=22, **kw):
        super().__init__(parent, bg=SURFACE, **kw)
        tk.Label(self, text=label, bg=SURFACE, fg=TEXT_DIM,
                 font=FONT_SMALL).pack(anchor="w")
        self.var = tk.StringVar()
        self.entry = tk.Entry(self, textvariable=self.var, width=width,
                              bg=BG, fg=TEXT, insertbackground=TEXT,
                              relief="flat", font=FONT_BODY,
                              highlightthickness=1,
                              highlightbackground=BORDER,
                              highlightcolor=ACCENT)
        self.entry.pack(fill="x", ipady=4)

    def get(self) -> str:
        return self.var.get().strip()

    def set(self, value: str):
        self.var.set(str(value) if value is not None else "")

    def clear(self):
        self.var.set("")


ROW_ODD  = "#2a2a3d"
ROW_EVEN = "#242436"


class StyledTree(ttk.Treeview):
    """Treeview so zebra riadkami a vertikalnymi ciarami medzi kolonkami."""

    def __init__(self, parent, columns: list[str], **kw):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Bufet.Treeview",
                        background=ROW_ODD, foreground=TEXT,
                        fieldbackground=ROW_ODD, rowheight=28,
                        font=FONT_BODY)
        style.configure("Bufet.Treeview.Heading",
                        background="#16162a", foreground=ACCENT,
                        font=("Helvetica", 9, "bold"), relief="flat")
        style.map("Bufet.Treeview",
                  background=[("selected", ACCENT2)],
                  foreground=[("selected", TEXT)])

        super().__init__(parent, columns=columns, show="headings",
                         style="Bufet.Treeview", **kw)

        self.tag_configure("odd",  background=ROW_ODD,  foreground=TEXT)
        self.tag_configure("even", background=ROW_EVEN, foreground=TEXT)

        self._columns = columns
        self._sep_lines = []

        for col in columns:
            self.heading(col, text=f"  {col}",
                         command=lambda c=col: self._sort_by(c))
            self.column(col, width=120, anchor="w", minwidth=40)

        sb = tk.Scrollbar(parent, orient="vertical", command=self.yview,
                          bg=SURFACE, troughcolor=BG, width=10,
                          relief="flat", bd=0)
        self.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")

        self.bind("<Configure>", lambda e: self.after(50, self._draw_separators))

    def _draw_separators(self):
        for w in self._sep_lines:
            w.destroy()
        self._sep_lines = []

        parent = self.master
        try:
            tree_x = self.winfo_x()
            tree_y = self.winfo_y()
            h = self.winfo_height()
        except Exception:
            return
        if h < 4:
            return

        x_offset = 0
        for col in self._columns[:-1]:
            x_offset += self.column(col, "width")
            line = tk.Frame(parent, bg=BORDER, width=1, height=h)
            line.place(x=tree_x + x_offset, y=tree_y)
            self._sep_lines.append(line)

    def _sort_by(self, col):
        data = [(self.set(k, col), k) for k in self.get_children("")]
        try:
            data.sort(key=lambda x: float(x[0]))
        except ValueError:
            data.sort()
        for i, (_, k) in enumerate(data):
            self.move(k, "", i)
        self._restripe()

    def _restripe(self):
        for i, row in enumerate(self.get_children()):
            self.item(row, tags=("even" if i % 2 == 0 else "odd",))

    def clear(self):
        for row in self.get_children():
            self.delete(row)

    def load(self, rows: list[tuple]):
        self.clear()
        for i, row in enumerate(rows):
            tag = "even" if i % 2 == 0 else "odd"
            self.insert("", "end", values=row, tags=(tag,))


# ══════════════════════════════════════════════════════
#  TAB: Tovar
# ══════════════════════════════════════════════════════
class TovarTab(tk.Frame):
    def __init__(self, parent, repo: TovarRepo):
        super().__init__(parent, bg=BG)
        self.repo = repo
        self._build()
        self.refresh()

    def _build(self):
        # ── Horný panel (filtre + hľadanie) ─────────
        top = tk.Frame(self, bg=BG)
        top.pack(fill="x", padx=16, pady=(14, 6))

        tk.Label(top, text="Tovar", bg=BG, fg=TEXT,
                 font=FONT_TITLE).pack(side="left")

        right = tk.Frame(top, bg=BG)
        right.pack(side="right")

        tk.Label(right, text="Hľadať:", bg=BG, fg=TEXT_DIM,
                 font=FONT_SMALL).pack(side="left")
        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", lambda *_: self.refresh())
        tk.Entry(right, textvariable=self._search_var, width=18,
                 bg=SURFACE, fg=TEXT, insertbackground=TEXT,
                 relief="flat", font=FONT_BODY,
                 highlightthickness=1, highlightbackground=BORDER,
                 highlightcolor=ACCENT).pack(side="left", padx=(4, 12), ipady=3)

        tk.Label(right, text="Kategória:", bg=BG, fg=TEXT_DIM,
                 font=FONT_SMALL).pack(side="left")
        self._kat_var = tk.StringVar(value="Všetky")
        self._kat_cb = ttk.Combobox(right, textvariable=self._kat_var,
                                     width=13, state="readonly",
                                     font=FONT_BODY)
        self._kat_cb.pack(side="left", padx=(4, 12))
        self._kat_cb.bind("<<ComboboxSelected>>", lambda _: self.refresh())

        StyledButton(right, "Len dostupné", self._toggle_dostupne,
                     color=ACCENT2).pack(side="left", padx=4)
        self._dostupne_only = False

        # ── Treeview ─────────────────────────────────
        tree_frame = tk.Frame(self, bg=BG)
        tree_frame.pack(fill="both", expand=True, padx=16, pady=4)

        cols = ["ID", "Názov", "Cena (€)", "Množstvo", "Kategória"]
        self.tree = StyledTree(tree_frame, cols)
        self.tree.column("ID", width=40)
        self.tree.column("Cena (€)", width=80)
        self.tree.column("Množstvo", width=80)
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        # ── Formulár ─────────────────────────────────
        form = tk.LabelFrame(self, text=" Tovar ", bg=SURFACE, fg=ACCENT,
                             font=FONT_HEAD, bd=0, highlightthickness=1,
                             highlightbackground=BORDER)
        form.pack(fill="x", padx=16, pady=8)

        row1 = tk.Frame(form, bg=SURFACE)
        row1.pack(fill="x", padx=10, pady=8)

        self.f_nazov = LabeledEntry(row1, "Názov *", width=24)
        self.f_nazov.pack(side="left", padx=(0, 10))
        self.f_cena = LabeledEntry(row1, "Cena (€) *", width=10)
        self.f_cena.pack(side="left", padx=(0, 10))
        self.f_mnozstvo = LabeledEntry(row1, "Množstvo *", width=10)
        self.f_mnozstvo.pack(side="left", padx=(0, 10))
        self.f_kategoria = LabeledEntry(row1, "Kategória *", width=16)
        self.f_kategoria.pack(side="left")

        btns = tk.Frame(form, bg=SURFACE)
        btns.pack(pady=(0, 8))
        StyledButton(btns, "➕ Pridať", self._add).pack(side="left", padx=4)
        StyledButton(btns, "✏️ Uložiť zmeny", self._update, color=ACCENT2).pack(side="left", padx=4)
        StyledButton(btns, "🗑 Vymazať", self._delete, color=DANGER).pack(side="left", padx=4)
        StyledButton(btns, "✖ Zrušiť výber", self._clear_form, color=BORDER).pack(side="left", padx=4)

        self._selected_id = None

    def _toggle_dostupne(self):
        self._dostupne_only = not self._dostupne_only
        self.refresh()

    def refresh(self):
        query = self._search_var.get().strip() if hasattr(self, "_search_var") else ""
        kat = self._kat_var.get() if hasattr(self, "_kat_var") else "Všetky"

        if query:
            tovary = self.repo.search(query)
        elif self._dostupne_only:
            tovary = self.repo.filter_dostupne()
        elif kat and kat != "Všetky":
            tovary = self.repo.filter_by_kategoria(kat)
        else:
            tovary = self.repo.get_all()

        self.tree.load([(t.id, t.nazov, f"{t.cena:.2f}", t.mnozstvo, t.kategoria)
                        for t in tovary])

        # Obnov kategórie v comboboxe
        kategorie = ["Všetky"] + self.repo.get_kategorie()
        self._kat_cb["values"] = kategorie

    def _on_select(self, _=None):
        sel = self.tree.selection()
        if not sel:
            return
        vals = self.tree.item(sel[0])["values"]
        self._selected_id = vals[0]
        self.f_nazov.set(vals[1])
        self.f_cena.set(vals[2])
        self.f_mnozstvo.set(vals[3])
        self.f_kategoria.set(vals[4])

    def _parse_form(self):
        nazov = self.f_nazov.get()
        cena_str = self.f_cena.get()
        mnoz_str = self.f_mnozstvo.get()
        kat = self.f_kategoria.get()

        if not nazov:
            raise ValueError("Názov je povinný.")
        if not kat:
            raise ValueError("Kategória je povinná.")
        try:
            cena = float(cena_str.replace(",", "."))
        except ValueError:
            raise ValueError("Cena musí byť číslo (napr. 1.50).")
        try:
            mnoz = int(mnoz_str)
        except ValueError:
            raise ValueError("Množstvo musí byť celé číslo.")
        return Tovar(nazov=nazov, cena=cena, mnozstvo=mnoz, kategoria=kat)

    def _add(self):
        try:
            t = self._parse_form()
            self.repo.add(t)
            self._clear_form()
            self.refresh()
        except ValueError as e:
            messagebox.showerror("Chyba", str(e))

    def _update(self):
        if self._selected_id is None:
            messagebox.showwarning("Upozornenie", "Najprv vyber tovar v tabuľke.")
            return
        try:
            t = self._parse_form()
            t.id = self._selected_id
            self.repo.update(t)
            self._clear_form()
            self.refresh()
        except ValueError as e:
            messagebox.showerror("Chyba", str(e))

    def _delete(self):
        if self._selected_id is None:
            messagebox.showwarning("Upozornenie", "Najprv vyber tovar v tabuľke.")
            return
        if not messagebox.askyesno("Potvrdiť", "Naozaj vymazať tovar?"):
            return
        try:
            self.repo.delete(self._selected_id)
            self._clear_form()
            self.refresh()
        except ValueError as e:
            messagebox.showerror("Nedá sa vymazať", str(e))
        except Exception as e:
            messagebox.showerror("Chyba", f"Neočakávaná chyba:\n{e}")

    def _clear_form(self):
        self._selected_id = None
        for f in [self.f_nazov, self.f_cena, self.f_mnozstvo, self.f_kategoria]:
            f.clear()
        self.tree.selection_remove(self.tree.selection())


# ══════════════════════════════════════════════════════
#  TAB: Zákazníci
# ══════════════════════════════════════════════════════
class ZakaznikTab(tk.Frame):
    def __init__(self, parent, repo: ZakaznikRepo):
        super().__init__(parent, bg=BG)
        self.repo = repo
        self._build()
        self.refresh()

    def _build(self):
        top = tk.Frame(self, bg=BG)
        top.pack(fill="x", padx=16, pady=(14, 6))
        tk.Label(top, text="Zákazníci", bg=BG, fg=TEXT,
                 font=FONT_TITLE).pack(side="left")

        right = tk.Frame(top, bg=BG)
        right.pack(side="right")

        tk.Label(right, text="Hľadať:", bg=BG, fg=TEXT_DIM,
                 font=FONT_SMALL).pack(side="left")
        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", lambda *_: self.refresh())
        tk.Entry(right, textvariable=self._search_var, width=18,
                 bg=SURFACE, fg=TEXT, insertbackground=TEXT,
                 relief="flat", font=FONT_BODY,
                 highlightthickness=1, highlightbackground=BORDER,
                 highlightcolor=ACCENT).pack(side="left", padx=(4, 12), ipady=3)

        tk.Label(right, text="Trieda:", bg=BG, fg=TEXT_DIM,
                 font=FONT_SMALL).pack(side="left")
        self._trieda_var = tk.StringVar(value="Všetky")
        self._trieda_cb = ttk.Combobox(right, textvariable=self._trieda_var,
                                        width=10, state="readonly", font=FONT_BODY)
        self._trieda_cb.pack(side="left", padx=(4, 4))
        self._trieda_cb.bind("<<ComboboxSelected>>", lambda _: self.refresh())

        tree_frame = tk.Frame(self, bg=BG)
        tree_frame.pack(fill="both", expand=True, padx=16, pady=4)

        cols = ["ID", "Meno", "Trieda", "Email", "Telefón"]
        self.tree = StyledTree(tree_frame, cols)
        self.tree.column("ID", width=40)
        self.tree.column("Trieda", width=70)
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        form = tk.LabelFrame(self, text=" Zákazník ", bg=SURFACE, fg=ACCENT,
                             font=FONT_HEAD, bd=0, highlightthickness=1,
                             highlightbackground=BORDER)
        form.pack(fill="x", padx=16, pady=8)

        row1 = tk.Frame(form, bg=SURFACE)
        row1.pack(fill="x", padx=10, pady=8)

        self.f_meno = LabeledEntry(row1, "Meno *", width=20)
        self.f_meno.pack(side="left", padx=(0, 10))
        self.f_trieda = LabeledEntry(row1, "Trieda *", width=8)
        self.f_trieda.pack(side="left", padx=(0, 10))
        self.f_email = LabeledEntry(row1, "Email *", width=24)
        self.f_email.pack(side="left", padx=(0, 10))
        self.f_telefon = LabeledEntry(row1, "Telefón", width=14)
        self.f_telefon.pack(side="left")

        btns = tk.Frame(form, bg=SURFACE)
        btns.pack(pady=(0, 8))
        StyledButton(btns, "➕ Pridať", self._add).pack(side="left", padx=4)
        StyledButton(btns, "✏️ Uložiť zmeny", self._update, color=ACCENT2).pack(side="left", padx=4)
        StyledButton(btns, "🗑 Vymazať", self._delete, color=DANGER).pack(side="left", padx=4)
        StyledButton(btns, "✖ Zrušiť výber", self._clear_form, color=BORDER).pack(side="left", padx=4)

        self._selected_id = None

    def refresh(self):
        query = self._search_var.get().strip() if hasattr(self, "_search_var") else ""
        trieda = self._trieda_var.get() if hasattr(self, "_trieda_var") else "Všetky"

        if query:
            zakaznici = self.repo.search(query)
        elif trieda and trieda != "Všetky":
            zakaznici = self.repo.filter_by_trieda(trieda)
        else:
            zakaznici = self.repo.get_all()

        self.tree.load([(z.id, z.meno, z.trieda, z.email, z.telefon) for z in zakaznici])

        triedy = ["Všetky"] + self.repo.get_triedy()
        self._trieda_cb["values"] = triedy

    def _on_select(self, _=None):
        sel = self.tree.selection()
        if not sel:
            return
        vals = self.tree.item(sel[0])["values"]
        self._selected_id = vals[0]
        self.f_meno.set(vals[1])
        self.f_trieda.set(vals[2])
        self.f_email.set(vals[3])
        self.f_telefon.set(vals[4] or "")

    def _parse_form(self):
        meno = self.f_meno.get()
        trieda = self.f_trieda.get()
        email = self.f_email.get()
        telefon = self.f_telefon.get()
        if not meno:
            raise ValueError("Meno je povinné.")
        if not trieda:
            raise ValueError("Trieda je povinná.")
        return Zakaznik(meno=meno, trieda=trieda, email=email, telefon=telefon)

    def _add(self):
        try:
            self.repo.add(self._parse_form())
            self._clear_form()
            self.refresh()
        except ValueError as e:
            messagebox.showerror("Chyba", str(e))

    def _update(self):
        if self._selected_id is None:
            messagebox.showwarning("Upozornenie", "Najprv vyber zákazníka v tabuľke.")
            return
        try:
            z = self._parse_form()
            z.id = self._selected_id
            self.repo.update(z)
            self._clear_form()
            self.refresh()
        except ValueError as e:
            messagebox.showerror("Chyba", str(e))

    def _delete(self):
        if self._selected_id is None:
            messagebox.showwarning("Upozornenie", "Najprv vyber zákazníka.")
            return
        if not messagebox.askyesno("Potvrdiť", "Naozaj vymazať zákazníka?"):
            return
        try:
            self.repo.delete(self._selected_id)
            self._clear_form()
            self.refresh()
        except ValueError as e:
            messagebox.showerror("Nedá sa vymazať", str(e))
        except Exception as e:
            messagebox.showerror("Chyba", f"Neočakávaná chyba:\n{e}")

    def _clear_form(self):
        self._selected_id = None
        for f in [self.f_meno, self.f_trieda, self.f_email, self.f_telefon]:
            f.clear()
        self.tree.selection_remove(self.tree.selection())


# ══════════════════════════════════════════════════════
#  TAB: Objednávky
# ══════════════════════════════════════════════════════
class ObjednavkyTab(tk.Frame):
    def __init__(self, parent, obj_repo: ObjednavkaRepo,
                 tovar_repo: TovarRepo, zak_repo: ZakaznikRepo):
        super().__init__(parent, bg=BG)
        self.repo = obj_repo
        self.tovar_repo = tovar_repo
        self.zak_repo = zak_repo
        self._build()
        self.refresh()

    def _build(self):
        top = tk.Frame(self, bg=BG)
        top.pack(fill="x", padx=16, pady=(14, 6))
        tk.Label(top, text="Objednávky", bg=BG, fg=TEXT,
                 font=FONT_TITLE).pack(side="left")

        tree_frame = tk.Frame(self, bg=BG)
        tree_frame.pack(fill="both", expand=True, padx=16, pady=4)

        cols = ["ID", "Tovar", "Zákazník", "Trieda", "Množstvo", "Celkom (€)", "Dátum"]
        self.tree = StyledTree(tree_frame, cols)
        self.tree.column("ID", width=40)
        self.tree.column("Množstvo", width=70)
        self.tree.column("Celkom (€)", width=90)
        self.tree.pack(fill="both", expand=True)

        # ── Formulár novej objednávky ─────────────────
        form = tk.LabelFrame(self, text=" Nová objednávka ", bg=SURFACE, fg=ACCENT,
                             font=FONT_HEAD, bd=0, highlightthickness=1,
                             highlightbackground=BORDER)
        form.pack(fill="x", padx=16, pady=8)

        row1 = tk.Frame(form, bg=SURFACE)
        row1.pack(fill="x", padx=10, pady=8)

        tk.Label(row1, text="Tovar *", bg=SURFACE, fg=TEXT_DIM,
                 font=FONT_SMALL).pack(side="left")
        self._tovar_var = tk.StringVar()
        self._tovar_cb = ttk.Combobox(row1, textvariable=self._tovar_var,
                                       width=24, state="readonly", font=FONT_BODY)
        self._tovar_cb.pack(side="left", padx=(4, 16))

        tk.Label(row1, text="Zákazník *", bg=SURFACE, fg=TEXT_DIM,
                 font=FONT_SMALL).pack(side="left")
        self._zak_var = tk.StringVar()
        self._zak_cb = ttk.Combobox(row1, textvariable=self._zak_var,
                                     width=24, state="readonly", font=FONT_BODY)
        self._zak_cb.pack(side="left", padx=(4, 16))

        self.f_mnozstvo = LabeledEntry(row1, "Množstvo *", width=8)
        self.f_mnozstvo.pack(side="left")

        btns = tk.Frame(form, bg=SURFACE)
        btns.pack(pady=(0, 8))
        StyledButton(btns, "➕ Pridať objednávku", self._add).pack(side="left", padx=4)
        StyledButton(btns, "🗑 Vymazať vybranú", self._delete, color=DANGER).pack(side="left", padx=4)

        self._tovar_map = {}
        self._zak_map = {}

    def refresh(self):
        rows = self.repo.get_all_with_names(sort_by="datum", descending=True)
        self.tree.load([
            (r["id"], r["nazov_tovaru"], r["meno_zakaznika"],
             r["trieda"], r["mnozstvo"],
             f"{r['mnozstvo'] * r['cena']:.2f}",
             r["datum"])
            for r in rows
        ])

        # Obnov combobox pre tovar (len dostupné)
        tovary = self.tovar_repo.filter_dostupne()
        self._tovar_map = {f"{t.nazov} ({t.mnozstvo} ks)": t.id for t in tovary}
        self._tovar_cb["values"] = list(self._tovar_map.keys())

        # Obnov combobox pre zákazníkov
        zakaznici = self.zak_repo.get_all()
        self._zak_map = {f"{z.meno} — {z.trieda}": z.id for z in zakaznici}
        self._zak_cb["values"] = list(self._zak_map.keys())

    def _add(self):
        tovar_key = self._tovar_var.get()
        zak_key = self._zak_var.get()
        mnoz_str = self.f_mnozstvo.get()

        if not tovar_key:
            messagebox.showerror("Chyba", "Vyber tovar.")
            return
        if not zak_key:
            messagebox.showerror("Chyba", "Vyber zákazníka.")
            return
        try:
            mnoz = int(mnoz_str)
            if mnoz <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Chyba", "Množstvo musí byť kladné celé číslo.")
            return

        try:
            obj = Objednavka(
                id_tovaru=self._tovar_map[tovar_key],
                id_zakaznika=self._zak_map[zak_key],
                mnozstvo=mnoz
            )
            self.repo.add(obj)
            self.f_mnozstvo.clear()
            self._tovar_var.set("")
            self._zak_var.set("")
            self.refresh()
        except ValueError as e:
            messagebox.showerror("Chyba", str(e))

    def _delete(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Upozornenie", "Vyber objednávku v tabuľke.")
            return
        if not messagebox.askyesno("Potvrdiť", "Vymazať objednávku?"):
            return
        obj_id = self.tree.item(sel[0])["values"][0]
        try:
            self.repo.delete(obj_id)
            self.refresh()
        except ValueError as e:
            messagebox.showerror("Nedá sa vymazať", str(e))
        except Exception as e:
            messagebox.showerror("Chyba", f"Neočakávaná chyba:\n{e}")


# ══════════════════════════════════════════════════════
#  TAB: Štatistiky
# ══════════════════════════════════════════════════════
class StatistikyTab(tk.Frame):
    def __init__(self, parent, obj_repo: ObjednavkaRepo, tovar_repo: TovarRepo):
        super().__init__(parent, bg=BG)
        self.obj_repo = obj_repo
        self.tovar_repo = tovar_repo
        self._build()
        self.refresh()

    def _build(self):
        tk.Label(self, text="Štatistiky", bg=BG, fg=TEXT,
                 font=FONT_TITLE).pack(anchor="w", padx=16, pady=(14, 6))

        StyledButton(self, "🔄 Obnoviť", self.refresh).pack(anchor="w", padx=16, pady=(0, 8))

        paned = tk.PanedWindow(self, orient="horizontal", bg=BG,
                               sashwidth=6, sashrelief="flat")
        paned.pack(fill="both", expand=True, padx=16, pady=4)

        # Ľavá — predaj tovaru
        left = tk.Frame(paned, bg=BG)
        tk.Label(left, text="Top predaj tovaru", bg=BG, fg=ACCENT,
                 font=FONT_HEAD).pack(anchor="w", pady=(0, 4))
        lf = tk.Frame(left, bg=BG)
        lf.pack(fill="both", expand=True)
        cols_l = ["Tovar", "Kategória", "Objednávok", "Predaných ks"]
        self.tree_tovar = StyledTree(lf, cols_l)
        self.tree_tovar.pack(fill="both", expand=True)
        paned.add(left)

        # Pravá — výdavky zákazníkov
        right = tk.Frame(paned, bg=BG)
        tk.Label(right, text="Výdavky zákazníkov", bg=BG, fg=ACCENT,
                 font=FONT_HEAD).pack(anchor="w", pady=(0, 4))
        rf = tk.Frame(right, bg=BG)
        rf.pack(fill="both", expand=True)
        cols_r = ["Meno", "Trieda", "Objednávok", "Celkom (€)"]
        self.tree_zak = StyledTree(rf, cols_r)
        self.tree_zak.pack(fill="both", expand=True)
        paned.add(right)

        # Upozornenia — málo na sklade
        warn_frame = tk.LabelFrame(self, text=" ⚠ Málo na sklade ", bg=SURFACE,
                                   fg=DANGER, font=FONT_HEAD, bd=0,
                                   highlightthickness=1, highlightbackground=BORDER)
        warn_frame.pack(fill="x", padx=16, pady=8)
        wf = tk.Frame(warn_frame, bg=SURFACE)
        wf.pack(fill="x", padx=6, pady=6)
        cols_w = ["ID", "Názov", "Kategória", "Zostatok"]
        self.tree_warn = StyledTree(wf, cols_w)
        self.tree_warn.column("ID", width=40)
        self.tree_warn.column("Zostatok", width=80)
        self.tree_warn.pack(fill="x")

    def refresh(self):
        stats = self.obj_repo.get_statistiky_tovaru()
        self.tree_tovar.load([
            (r["nazov"], r["kategoria"], r["pocet_objednavok"], r["predanych_kusov"])
            for r in stats
        ])

        sumy = self.obj_repo.get_suma_by_zakaznik()
        self.tree_zak.load([
            (r["meno"], r["trieda"], r["pocet_objednavok"], f"{r['celkova_suma']:.2f}")
            for r in sumy
        ])

        malo = self.tovar_repo.filter_malo_na_sklade(10)
        self.tree_warn.load([
            (t.id, t.nazov, t.kategoria, t.mnozstvo) for t in malo
        ])


# ══════════════════════════════════════════════════════
#  Hlavné okno
# ══════════════════════════════════════════════════════
class BufetGUI:
    def __init__(self):
        self.db = Database("data/bufet.db")
        self.tovar_repo = TovarRepo(self.db)
        self.zak_repo = ZakaznikRepo(self.db)
        self.obj_repo = ObjednavkaRepo(self.db)
        self.pou_repo = PouzivatelRepo(self.db)

        self.tovar_repo.create_table()
        self.zak_repo.create_table()
        self.obj_repo.create_table()
        self.pou_repo.create_table()

        self.root = tk.Tk()
        self.root.title("Školský bufet")
        self.root.geometry("1100x720")
        self.root.configure(bg=BG)
        self.root.minsize(900, 600)

        self._build_menu()
        self._build_tabs()

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_menu(self):
        menubar = tk.Menu(self.root, bg=SURFACE, fg=TEXT,
                          activebackground=ACCENT, activeforeground=BG,
                          relief="flat", bd=0)
        self.root.config(menu=menubar)

        db_menu = tk.Menu(menubar, tearoff=0, bg=SURFACE, fg=TEXT,
                          activebackground=ACCENT, activeforeground=BG)
        menubar.add_cascade(label="Databáza", menu=db_menu)
        db_menu.add_command(label="💾 Uložiť zálohu...", command=self._save_db)
        db_menu.add_command(label="📂 Načítať zálohu...", command=self._load_db)
        db_menu.add_separator()
        db_menu.add_command(label="❌ Ukončiť", command=self._on_close)

    def _build_tabs(self):
        style = ttk.Style()
        style.configure("Bufet.TNotebook", background=BG, borderwidth=0)
        style.configure("Bufet.TNotebook.Tab",
                        background=SURFACE, foreground=TEXT_DIM,
                        padding=[14, 6], font=FONT_BODY)
        style.map("Bufet.TNotebook.Tab",
                  background=[("selected", ACCENT)],
                  foreground=[("selected", BG)])

        nb = ttk.Notebook(self.root, style="Bufet.TNotebook")
        nb.pack(fill="both", expand=True)

        self.tab_tovar = TovarTab(nb, self.tovar_repo)
        nb.add(self.tab_tovar, text="  🛒 Tovar  ")

        self.tab_zak = ZakaznikTab(nb, self.zak_repo)
        nb.add(self.tab_zak, text="  👥 Zákazníci  ")

        self.tab_obj = ObjednavkyTab(nb, self.obj_repo, self.tovar_repo, self.zak_repo)
        nb.add(self.tab_obj, text="  📋 Objednávky  ")

        self.tab_stats = StatistikyTab(nb, self.obj_repo, self.tovar_repo)
        nb.add(self.tab_stats, text="  📊 Štatistiky  ")

        # Pri prepnutí tabu obnoviť dáta
        nb.bind("<<NotebookTabChanged>>", self._on_tab_change)

    def _on_tab_change(self, event):
        nb = event.widget
        idx = nb.index(nb.select())
        tabs = [self.tab_tovar, self.tab_zak, self.tab_obj, self.tab_stats]
        if idx < len(tabs):
            tabs[idx].refresh()

    def _save_db(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".db",
            filetypes=[("SQLite databáza", "*.db"), ("Všetky súbory", "*.*")],
            title="Uložiť zálohu databázy"
        )
        if path:
            self.db.save(path)
            messagebox.showinfo("Hotovo", f"Záloha uložená:\n{path}")

    def _load_db(self):
        path = filedialog.askopenfilename(
            filetypes=[("SQLite databáza", "*.db"), ("Všetky súbory", "*.*")],
            title="Načítať zálohu databázy"
        )
        if path:
            if not messagebox.askyesno("Potvrdiť",
                                        "Načítanie nahradí aktuálnu databázu. Pokračovať?"):
                return
            self.db.load(path)
            for tab in [self.tab_tovar, self.tab_zak, self.tab_obj, self.tab_stats]:
                tab.refresh()
            messagebox.showinfo("Hotovo", "Databáza načítaná.")

    def _on_close(self):
        self.db.close()
        self.root.destroy()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    BufetGUI().run()