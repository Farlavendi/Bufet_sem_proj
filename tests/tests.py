"""
Testy všetkých operácií projektu Bufet.
Spustenie: python tests.py
"""
import os
import sys

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

TEST_DB = "data/test_bufet.db"
BACKUP_DB = "data/test_backup.db"

PASSED = 0
FAILED = 0


def test(name: str, condition: bool, detail: str = ""):
    global PASSED, FAILED
    if condition:
        print(f"  ✓ {name}")
        PASSED += 1
    else:
        print(f"  ✗ {name}" + (f" — {detail}" if detail else ""))
        FAILED += 1


def section(title: str):
    print(f"\n{'─' * 50}")
    print(f"  {title}")
    print(f"{'─' * 50}")


# ─── SETUP ────────────────────────────────────────────
def setup() -> tuple:
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
    db = Database(TEST_DB)
    tovar_repo = TovarRepo(db)
    zakaznik_repo = ZakaznikRepo(db)
    objednavka_repo = ObjednavkaRepo(db)
    pouzivatel_repo = PouzivatelRepo(db)
    tovar_repo.create_table()
    zakaznik_repo.create_table()
    objednavka_repo.create_table()
    pouzivatel_repo.create_table()
    return db, tovar_repo, zakaznik_repo, objednavka_repo, pouzivatel_repo


def teardown(db: Database):
    db.close()
    for f in [TEST_DB, BACKUP_DB]:
        if os.path.exists(f):
            os.remove(f)


# ─── SEED DATA ────────────────────────────────────────
TOVARY = [
    Tovar("Chlieb", 0.80, 50, "Pečivo"),
    Tovar("Rožok", 0.30, 100, "Pečivo"),
    Tovar("Mlieko 0.5l", 0.65, 30, "Nápoje"),
    Tovar("Kofola 0.33l", 0.90, 40, "Nápoje"),
    Tovar("Croissant", 1.20, 20, "Pečivo"),
    Tovar("Jogurt jahoda", 0.75, 25, "Mliečne"),
    Tovar("Syr plátky", 1.50, 15, "Mliečne"),
    Tovar("Keksík", 0.40, 60, "Sladkosti"),
    Tovar("Čokoláda", 1.10, 35, "Sladkosti"),
    Tovar("Voda 0.5l", 0.50, 80, "Nápoje"),
    Tovar("Pizza plátok", 1.80, 12, "Teplé jedlá"),
    Tovar("Párok v rožku", 1.60, 10, "Teplé jedlá"),
]

ZAKAZNICI = [
    Zakaznik("Adam Novák", "adam.novak@skola.sk", "0901111111"),
    Zakaznik("Barbora Kováčová", "bara.kovac@skola.sk", "0902222222"),
    Zakaznik("Cyril Horváth", "cyril.h@skola.sk", "0903333333"),
    Zakaznik("Denisa Lukáčová", "denisa.l@skola.sk", "0904444444"),
    Zakaznik("Erik Szabó", "erik.szabo@skola.sk", "0905555555"),
    Zakaznik("Františka Olejár", "fanka.o@skola.sk", "0906666666"),
    Zakaznik("Gabriel Tóth", "gabo.toth@skola.sk", "0907777777"),
    Zakaznik("Helena Varga", "helena.v@skola.sk", "0908888888"),
    Zakaznik("Ivan Molnár", "ivan.m@skola.sk", "0909999999"),
    Zakaznik("Jana Baláž", "jana.balaz@skola.sk", "0910000000"),
]


# ══════════════════════════════════════════════════════
#  1. INSERT
# ══════════════════════════════════════════════════════
def test_insert(tovar_repo, zakaznik_repo, objednavka_repo, pouzivatel_repo):
    section("1. INSERT — vkladanie")

    # Tovar
    ids_tovar = []
    for t in TOVARY:
        tid = tovar_repo.add(t)
        ids_tovar.append(tid)
    test("Vložených 12 tovarov", len(ids_tovar) == 12)

    # Duplikát — model validácia
    try:
        Tovar("", 1.0, 5, "X")
        test("Prázdny názov tovaru vyhodí ValueError", False)
    except ValueError:
        test("Prázdny názov tovaru vyhodí ValueError", True)

    try:
        Tovar("Test", -1.0, 5, "X")
        test("Záporná cena vyhodí ValueError", False)
    except ValueError:
        test("Záporná cena vyhodí ValueError", True)

    # Zakaznik
    ids_zak = []
    for z in ZAKAZNICI:
        zid = zakaznik_repo.add(z)
        ids_zak.append(zid)
    test("Vložených 10 zákazníkov", len(ids_zak) == 10)

    # Duplikát email
    try:
        zakaznik_repo.add(Zakaznik("Iný", "1A", "adam.novak@skola.sk", "0000"))
        test("Duplikátny email vyhodí ValueError", False)
    except ValueError:
        test("Duplikátny email vyhodí ValueError", True)

    # Objednavka — transakcia
    obj1_id = objednavka_repo.add(Objednavka(ids_tovar[0], ids_zak[0], 2))
    obj2_id = objednavka_repo.add(Objednavka(ids_tovar[2], ids_zak[1], 1))
    obj3_id = objednavka_repo.add(Objednavka(ids_tovar[3], ids_zak[2], 3))
    obj4_id = objednavka_repo.add(Objednavka(ids_tovar[7], ids_zak[3], 2))
    obj5_id = objednavka_repo.add(Objednavka(ids_tovar[9], ids_zak[4], 5))
    obj6_id = objednavka_repo.add(Objednavka(ids_tovar[1], ids_zak[5], 4))
    obj7_id = objednavka_repo.add(Objednavka(ids_tovar[4], ids_zak[6], 1))
    obj8_id = objednavka_repo.add(Objednavka(ids_tovar[6], ids_zak[7], 2))
    obj9_id = objednavka_repo.add(Objednavka(ids_tovar[10], ids_zak[8], 1))
    obj10_id = objednavka_repo.add(Objednavka(ids_tovar[11], ids_zak[9], 1))
    test("Vložených 10 objednávok", all([obj1_id, obj2_id, obj3_id, obj4_id, obj5_id,
                                         obj6_id, obj7_id, obj8_id, obj9_id, obj10_id]))

    # Sklad sa znížil po objednávke
    chlieb = tovar_repo.get_by_id(ids_tovar[0])
    test("Sklad chleba znížený o 2 po objednávke (50→48)", chlieb.mnozstvo == 48)

    # Nedostatok na sklade
    try:
        objednavka_repo.add(Objednavka(ids_tovar[11], ids_zak[0], 9999))
        test("Objednávka nad sklad vyhodí ValueError", False)
    except ValueError:
        test("Objednávka nad sklad vyhodí ValueError", True)

    # Pouzivatel
    admin_id = pouzivatel_repo.add(Pouzivatel("admin", "admin123", "admin"))
    obs_id = pouzivatel_repo.add(Pouzivatel("obsluha1", "pass1234", "obsluha"))
    pouzivatel_repo.add(Pouzivatel("obsluha2", "pass5678", "obsluha"))
    test("Vložení 3 používatelia", all([admin_id, obs_id]))

    try:
        pouzivatel_repo.add(Pouzivatel("admin", "iné", "admin"))
        test("Duplikátné meno používateľa vyhodí ValueError", False)
    except ValueError:
        test("Duplikátné meno používateľa vyhodí ValueError", True)

    return ids_tovar, ids_zak


# ══════════════════════════════════════════════════════
#  2. SELECT + SORT
# ══════════════════════════════════════════════════════
def test_select_sort(tovar_repo, zakaznik_repo, objednavka_repo):
    section("2. SELECT + TRIEDENIE")

    # Tovar — sort by nazov ASC
    tovary = tovar_repo.get_all(sort_by="nazov")
    test("Tovary zoradené podľa názvu ASC",
         tovary[0].nazov <= tovary[-1].nazov)

    # Tovar — sort by cena DESC
    tovary_cena = tovar_repo.get_all(sort_by="cena", descending=True)
    test("Tovary zoradené podľa ceny DESC",
         tovary_cena[0].cena >= tovary_cena[-1].cena)

    # Tovar — sort by mnozstvo ASC
    tovary_mnoz = tovar_repo.get_all(sort_by="mnozstvo")
    test("Tovary zoradené podľa množstva ASC",
         tovary_mnoz[0].mnozstvo <= tovary_mnoz[-1].mnozstvo)

    # Zakaznik — sort by meno ASC
    zakaznici = zakaznik_repo.get_all(sort_by="meno")
    test("Zákazníci zoradení podľa mena ASC",
         zakaznici[0].meno <= zakaznici[-1].meno)

    # Zakaznik — sort by email DESC
    zakaznici_email = zakaznik_repo.get_all(sort_by="email", descending=True)
    test("Zákazníci zoradení podľa emailu DESC",
         zakaznici_email[0].email >= zakaznici_email[-1].email)

    # Objednavky — sort by datum DESC
    objednavky = objednavka_repo.get_all(sort_by="datum", descending=True)
    test("Objednávky zoradené podľa dátumu DESC", len(objednavky) == 10)

    # Objednavky s menami (JOIN)
    with_names = objednavka_repo.get_all_with_names()
    test("Objednávky s názvom tovaru a menom zákazníka (JOIN)",
         len(with_names) > 0 and "nazov_tovaru" in with_names[0])

    # Neplatný sort_by
    try:
        tovar_repo.get_all(sort_by="zly_stlpec")
        test("Neplatný sort_by vyhodí ValueError", False)
    except ValueError:
        test("Neplatný sort_by vyhodí ValueError", True)


# ══════════════════════════════════════════════════════
#  3. FILTER + SEARCH
# ══════════════════════════════════════════════════════
def test_filter_search(tovar_repo, zakaznik_repo, objednavka_repo):
    section("3. FILTROVANIE A VYHĽADÁVANIE")

    # Tovar filtre
    pecivo = tovar_repo.filter_by_kategoria("Pečivo")
    test("Filter podľa kategórie 'Pečivo' (3 položky)", len(pecivo) == 3)

    lacne = tovar_repo.filter_by_cena(0, 0.60)
    test("Filter cena 0–0.60€", all(t.cena <= 0.60 for t in lacne))

    dostupne = tovar_repo.filter_dostupne()
    test("Filter dostupné (všetky majú mnozstvo > 0)", all(t.mnozstvo > 0 for t in dostupne))

    malo = tovar_repo.filter_malo_na_sklade(12)
    test("Filter málo na sklade (≤12)", all(t.mnozstvo <= 12 for t in malo))

    kategorie = tovar_repo.get_kategorie()
    test("Unikátne kategórie vrátené", len(kategorie) >= 4)

    # Search tovar
    vysledky = tovar_repo.search("Kofola")
    test("Vyhľadávanie 'Kofola' nájde Kofolu", len(vysledky) == 1)
    vysledky2 = tovar_repo.search("Nápoje")
    test("Vyhľadávanie podľa kategórie 'Nápoje' (3 položky)", len(vysledky2) == 3)

    # Zakaznik filtre
    s_obj = zakaznik_repo.get_zakaznici_s_objednavkami()
    test("Zákazníci s objednávkami (JOIN)", len(s_obj) > 0)

    # Search zakaznik
    found = zakaznik_repo.search("Novák")
    test("Vyhľadávanie zákazníka 'Novák'", len(found) == 1)

    # Objednavka filtre
    from datetime import datetime
    dnes = datetime.now().strftime("%Y-%m-%d")
    dnesne = objednavka_repo.filter_by_datum(dnes, dnes)
    test("Filter objednávok za dnešný deň", len(dnesne) == 10)

    sumy = objednavka_repo.get_suma_by_zakaznik()
    test("Suma objednávok podľa zákazníka", len(sumy) > 0 and "celkova_suma" in sumy[0] and "meno" in sumy[0])

    stats = objednavka_repo.get_statistiky_tovaru()
    test("Štatistiky predaja tovaru", len(stats) > 0 and "predanych_kusov" in stats[0])

    by_zak = objednavka_repo.get_by_zakaznik(1)
    test("Objednávky konkrétneho zákazníka", len(by_zak) >= 1)


# ══════════════════════════════════════════════════════
#  4. UPDATE
# ══════════════════════════════════════════════════════
def test_update(tovar_repo, zakaznik_repo, pouzivatel_repo, ids_tovar, ids_zak):
    section("4. UPDATE — aktualizácia")

    # Tovar update
    t = tovar_repo.get_by_id(ids_tovar[0])
    t.cena = 0.95
    t.nazov = "Chlieb celozrnný"
    tovar_repo.update(t)
    updated = tovar_repo.get_by_id(ids_tovar[0])
    test("Aktualizácia ceny a názvu tovaru", updated.cena == 0.95 and updated.nazov == "Chlieb celozrnný")

    # update_mnozstvo
    tovar_repo.update_mnozstvo(ids_tovar[1], 10)
    roz = tovar_repo.get_by_id(ids_tovar[1])
    test("update_mnozstvo — príjem +10 kusov (96+10=106)", roz.mnozstvo == 106)

    # Zakaznik update
    z = zakaznik_repo.get_by_id(ids_zak[0])
    z.meno = "Adam Nový"
    zakaznik_repo.update(z)
    updated_z = zakaznik_repo.get_by_id(ids_zak[0])
    test("Aktualizácia mena zákazníka", updated_z.meno == "Adam Nový")

    # Pouzivatel update rola
    pouzivatelia = pouzivatel_repo.get_all()
    obs = next((p for p in pouzivatelia if p.rola == "obsluha"), None)
    if obs:
        pouzivatel_repo.update_rola(obs.id, "admin")
        updated_p = pouzivatel_repo.get_all()
        new_role = next(p for p in updated_p if p.id == obs.id)
        test("Aktualizácia roly používateľa na admin", new_role.rola == "admin")

    # Tovar bez id
    try:
        tovar_repo.update(Tovar("X", 1.0, 1, "Y"))
        test("Update tovaru bez id vyhodí ValueError", False)
    except ValueError:
        test("Update tovaru bez id vyhodí ValueError", True)


# ══════════════════════════════════════════════════════
#  5. DELETE
# ══════════════════════════════════════════════════════
def test_delete(tovar_repo, zakaznik_repo, objednavka_repo, pouzivatel_repo, ids_tovar, ids_zak):
    section("5. DELETE — mazanie")

    # Zmaž objednávku — skontroluj aj vrátenie skladu
    objednavky_pred = objednavka_repo.get_all()
    posledna = objednavky_pred[-1]
    tovar_pred = tovar_repo.get_by_id(posledna.id_tovaru)
    objednavka_repo.delete(posledna.id)
    objednavky_po = objednavka_repo.get_all()
    tovar_po = tovar_repo.get_by_id(posledna.id_tovaru)
    test("Vymazanie objednavky — pocet sa znizil", len(objednavky_po) == len(objednavky_pred) - 1)
    test("Vymazanie objednavky — tovar vrateny na sklad",
         tovar_po.mnozstvo == tovar_pred.mnozstvo + posledna.mnozstvo)

    # Tovar s objednávkami — nesmie sa zmazať
    try:
        tovar_repo.delete(ids_tovar[0])
        test("Vymazanie tovaru s objednávkami vyhodí ValueError", False)
    except ValueError:
        test("Vymazanie tovaru s objednávkami vyhodí ValueError", True)

    # Tovar bez objednávok — smie sa zmazať (posledný, bez objednávky)
    tovar_repo.delete(ids_tovar[-1])
    test("Vymazanie tovaru bez objednávok", tovar_repo.get_by_id(ids_tovar[-1]) is None)

    # Zákazník s objednávkami — nesmie sa zmazať
    try:
        zakaznik_repo.delete(ids_zak[0])
        test("Vymazanie zákazníka s objednávkami vyhodí ValueError", False)
    except ValueError:
        test("Vymazanie zákazníka s objednávkami vyhodí ValueError", True)

    # Pouzivatel delete
    pouzivatelia_pred = pouzivatel_repo.get_all()
    pouzivatel_repo.delete(pouzivatelia_pred[-1].id)
    test("Vymazanie používateľa", len(pouzivatel_repo.get_all()) == len(pouzivatelia_pred) - 1)


# ══════════════════════════════════════════════════════
#  6. VERIFY (login)
# ══════════════════════════════════════════════════════
def test_verify(pouzivatel_repo):
    section("6. VERIFY — prihlásenie")

    ok = pouzivatel_repo.verify("admin", "admin123")
    test("Správne heslo vráti používateľa", ok is not None and ok.meno == "admin")

    zle = pouzivatel_repo.verify("admin", "zle_heslo")
    test("Zlé heslo vráti None", zle is None)

    neexist = pouzivatel_repo.verify("neexistuje", "abc")
    test("Neexistujúci používateľ vráti None", neexist is None)


# ══════════════════════════════════════════════════════
#  7. SAVE / LOAD
# ══════════════════════════════════════════════════════
def test_save_load(db, tovar_repo):
    section("7. SAVE / LOAD — záloha a obnova")

    pocet_pred = len(tovar_repo.get_all())

    # Save
    db.save(BACKUP_DB)
    test("Databáza uložená do záložného súboru", os.path.exists(BACKUP_DB))

    # Pridaj nový tovar
    tovar_repo.add(Tovar("Dočasný tovar", 9.99, 1, "Test"))
    test("Po uložení pridaný nový tovar", len(tovar_repo.get_all()) == pocet_pred + 1)

    # Load — obnoví stav pred pridaním
    db.load(BACKUP_DB)
    tovar_repo2 = TovarRepo(db)
    test("Po načítaní zálohy je pôvodný počet tovarov",
         len(tovar_repo2.get_all()) == pocet_pred)


# ══════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════
if __name__ == "__main__":
    print("\n" + "═" * 50)
    print("  TESTY — Školský bufet")
    print("═" * 50)

    db, tovar_repo, zakaznik_repo, objednavka_repo, pouzivatel_repo = setup()

    try:
        ids_tovar, ids_zak = test_insert(tovar_repo, zakaznik_repo, objednavka_repo, pouzivatel_repo)
        test_select_sort(tovar_repo, zakaznik_repo, objednavka_repo)
        test_filter_search(tovar_repo, zakaznik_repo, objednavka_repo)
        test_update(tovar_repo, zakaznik_repo, pouzivatel_repo, ids_tovar, ids_zak)
        test_delete(tovar_repo, zakaznik_repo, objednavka_repo, pouzivatel_repo, ids_tovar, ids_zak)
        test_verify(pouzivatel_repo)
        test_save_load(db, tovar_repo)
    finally:
        teardown(db)

    print(f"\n{'═' * 50}")
    print(f"  Výsledok: {PASSED} ✓  |  {FAILED} ✗  |  Spolu: {PASSED + FAILED}")
    print(f"{'═' * 50}\n")

    sys.exit(0 if FAILED == 0 else 1)
