"""Generator kompre.xml prosto z API Shopera (format Ceneo: offers/o).

Uruchomienie:  python generuj_feed.py [plik_wyjściowy] [poprzedni_feed.xml]
Dane dostępowe: dane_dostepowe.env (lokalnie) albo zmienne środowiskowe
SHOPER_URL i SHOPER_TOKEN (GitHub Actions, z sekretów).

Jak działa (żeby nie pobierać wszystkiego za każdym razem):
- produkty WIDOCZNE w sklepie: pełne dane (cena, stan, parametry) przy każdym uruchomieniu,
  zdjęcia tylko dla nowych/edytowanych od ostatniego razu (reszta z poprzedniego pliku),
- produkty UKRYTE i USUNIĘTE: zostają z poprzedniego pliku ze stanem 0,
- FULL=1 (niedziela w nocy) albo brak poprzedniego pliku: pełne pobranie wszystkiego
  (też nowe ukryte produkty i ich dane).
"""
import os, sys, time, json
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from xml.sax.saxutils import quoteattr
from shoper_api import Shoper, load_env
import opisy

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "kompre.xml")
PREV = sys.argv[2] if len(sys.argv) > 2 else OUT
FULL = os.environ.get("FULL") == "1"
DESC_LIMIT = 700  # tylko dla zapasowego stałego opisu (gdy szablon nic nie złoży)
MAX_IMGS = None  # bez limitu: wszystkie widoczne zdjęcia z Shopera


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def cdata(text):
    text = (text or "").replace("]]>", "]]]]><![CDATA[>")
    return f"<![CDATA[{text}]]>"


def price_str(v):
    s = f"{float(v):.2f}"
    return s.rstrip("0").rstrip(".")


DATA_DIR = os.environ.get("DATA_DIR") or os.path.dirname(os.path.abspath(OUT))  # stan.json + zmiany/
STATE = os.path.join(DATA_DIR, "stan.json")


def load_state():
    try:
        return json.load(open(STATE, encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_state(state):
    with open(STATE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=1)


def load_prev(path):
    """Poprzedni feed -> {id: oferta}. Brak pliku = pusty słownik."""
    if not os.path.exists(path):
        return {}
    out = {}
    for o in ET.parse(path).getroot().findall("o"):
        out[o.get("id")] = {
            "id": o.get("id"), "url": o.get("url"), "price": o.get("price"),
            "stock": int(o.get("stock") or 0),
            "cat": o.findtext("cat") or "", "name": o.findtext("name") or "",
            "desc": o.findtext("desc") or "",
            "imgs": [e.get("url") for e in o.findall("imgs/*")],
            "attrs": [(a.get("name"), a.text or "") for a in o.findall("attrs/a")],
        }
    return out


def emit(o):
    stock = o["stock"]
    avail, basket = ("1", "1") if stock > 0 else ("99", "0")
    lines = [f'  <o id="{o["id"]}" url={quoteattr(o["url"])} price="{o["price"]}" '
             f'avail="{avail}" stock="{stock}" basket="{basket}">',
             f"    <cat>{cdata(o['cat'])}</cat>",
             f"    <name>{cdata(o['name'])}</name>",
             f"    <desc>{cdata(o['desc'])}</desc>"]
    if o["imgs"]:
        lines.append("    <imgs>")
        for i, u in enumerate(o["imgs"][:MAX_IMGS]):
            lines.append(f'      <{"main" if i == 0 else "i"} url={quoteattr(u)}/>')
        lines.append("    </imgs>")
    lines.append("    <attrs>")
    for n, v in o["attrs"]:
        lines.append(f"      <a name={quoteattr(n)}>{cdata(v)}</a>")
    lines.append("    </attrs>")
    lines.append("  </o>")
    return lines


class Builder:
    def __init__(self, api):
        self.api = api
        cfg = api.get("/application-config")
        self.shop_url = cfg["shop_url"]
        self.gfx_base = cfg["technical_url"].rstrip("/") + "/userdata/public/gfx/"
        self.template = open(os.path.join(HERE, "szablon_opisu.txt"), encoding="utf-8").read()
        self.desc_templates = opisy.load_templates()
        log("kategorie, producenci, atrybuty…")
        self.cats = {c["category_id"]: c["translations"]["pl_PL"]["name"] for c in api.all("/categories")}
        self.producers = {p["producer_id"]: p["name"] for p in api.all("/producers")}
        self.attr_names = {a["attribute_id"]: a["name"].strip() for a in api.all("/attributes")}

    def images_for(self, ids):
        res = {}
        ids = list(ids)
        for i in range(0, len(ids), 100):
            chunk = [int(x) for x in ids[i:i + 100]]
            for g in self.api.all("/product-images", {"filters": json.dumps({"product_id": {"IN": chunk}})}):
                res.setdefault(g["product_id"], []).append(g)
        return res

    def offer(self, p, imgs, visible):
        st = p["stock"]
        tr = p["translations"].get("pl_PL") or next(iter(p["translations"].values()))
        pid = p["product_id"]
        name = tr["name"]
        imgs = sorted((g for g in imgs if str(g.get("hidden")) != "1"),
                      key=lambda g: (int(g.get("main") or 0) != 1, int(g.get("order") or 0), int(g["gfx_id"])))
        attrs = {}
        if p.get("producer_id") and str(p["producer_id"]) in self.producers:
            attrs["Producent"] = self.producers[str(p["producer_id"])]
        if p.get("code"):
            attrs["SKU"] = p["code"]
        if p.get("ean"):
            attrs["EAN"] = p["ean"]
        for group in (p.get("attributes") or {}).values():
            if not isinstance(group, dict):
                continue
            for aid, val in group.items():
                n = self.attr_names.get(str(aid))
                val = val.strip() if isinstance(val, str) else val
                if n and val not in ("", None, []) and n not in attrs:
                    attrs[n] = str(val)
        first = ["Producent", "SKU", "EAN"]
        order = [k for k in first if k in attrs] + sorted(k for k in attrs if k not in first)
        attr_list = [(k, attrs[k]) for k in order]
        cat = self.cats.get(str(p.get("category_id")), "")
        desc = opisy.build(self.desc_templates, name, cat, attr_list) or ('"' + name + '" ' + self.template)[:DESC_LIMIT]
        return {
            "id": pid,
            "url": tr.get("permalink") or f"{self.shop_url}/pl/p/{pid}",
            "price": price_str(st["price"]),
            "stock": int(float(st["stock"] or 0)) if visible else 0,
            "cat": cat,
            "name": name,
            "desc": desc,
            "imgs": [f'{self.gfx_base}{g["unic_name"]}.{g["extension"]}' for g in imgs],
            "attrs": attr_list,
        }


CHANGES_DIR = os.path.join(DATA_DIR, "zmiany")
CHANGES_COLS = ["czas", "typ", "id", "nazwa", "kategoria", "cena_stara", "cena_nowa", "zmiana_proc",
                "stan_stary", "stan_nowy", "url", "zdjecie"]
NEW_DAYS = 14        # produkt dodany w Shoperze w ostatnich 14 dniach = "nowy", a nie "wrocil"
KEEP_DAYS = 180      # ile dni dziennika trzymać


def write_changelog(prev, offers, full, existing, visible):
    """Porównuje poprzedni feed z nowym i dopisuje zdarzenia do zmiany/RRRR-MM-DD.csv.
    Typy: nowy, wrocil, wyprzedany, ukryty, usuniety, obnizka, podwyzka."""
    import csv
    from zoneinfo import ZoneInfo
    now = datetime.now(ZoneInfo("Europe/Warsaw"))
    if not prev:
        log("dziennik zmian: brak poprzedniego feedu, pomijam")
        return
    recent = (now - timedelta(days=NEW_DAYS)).strftime("%Y-%m-%d")
    rows = []

    def row(typ, o, p=None, extra=None):
        r = {"czas": now.strftime("%Y-%m-%d %H:%M"), "typ": typ, "id": o["id"], "nazwa": o["name"],
             "kategoria": o["cat"], "cena_stara": p["price"] if p else "", "cena_nowa": o["price"],
             "zmiana_proc": "", "stan_stary": p["stock"] if p else "", "stan_nowy": o["stock"],
             "url": o["url"], "zdjecie": o["imgs"][0] if o["imgs"] else ""}
        r.update(extra or {})
        rows.append(r)

    for pid, o in offers.items():
        p = prev.get(pid)
        added = (full.get(pid) or {}).get("add_date") or ""
        if p is None:
            if o["stock"] > 0:
                row("nowy", o)
            continue
        if p["stock"] <= 0 < o["stock"]:
            row("nowy" if added >= recent else "wrocil", o, p)
        elif p["stock"] > 0 >= o["stock"]:
            typ = "usuniety" if pid not in existing else ("ukryty" if pid not in visible else "wyprzedany")
            row(typ, o, p)
        try:
            po, pn = float(p["price"]), float(o["price"])
        except (TypeError, ValueError):
            continue
        if o["stock"] > 0 and abs(pn - po) >= 0.01:
            proc = f"{(pn - po) / po * 100:+.1f}" if po else ""
            row("obnizka" if pn < po else "podwyzka", o, p, {"zmiana_proc": proc})

    os.makedirs(CHANGES_DIR, exist_ok=True)
    path = os.path.join(CHANGES_DIR, now.strftime("%Y-%m-%d") + ".csv")
    new_file = not os.path.exists(path)
    if rows:
        with open(path, "a", encoding="utf-8-sig" if new_file else "utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=CHANGES_COLS, delimiter=";")
            if new_file:
                w.writeheader()
            w.writerows(rows)
    cnt = {}
    for r in rows:
        cnt[r["typ"]] = cnt.get(r["typ"], 0) + 1
    log(f"dziennik zmian: {len(rows)} zdarzeń {cnt} -> {path if rows else '(brak zmian)'}")

    cutoff = (now - timedelta(days=KEEP_DAYS)).strftime("%Y-%m-%d")
    for fn in os.listdir(CHANGES_DIR):
        if fn.endswith(".csv") and fn[:10] < cutoff:
            os.remove(os.path.join(CHANGES_DIR, fn))


def main():
    env = load_env(os.path.join(HERE, "dane_dostepowe.env"))
    api = Shoper(env["SHOPER_URL"], env["SHOPER_TOKEN"])
    prev = load_prev(PREV)
    log(f"poprzedni feed: {len(prev)} ofert ({PREV})")
    global FULL
    if not prev:
        log("brak poprzedniego feedu -> pierwsze uruchomienie, pełne pobranie z Shopera")
        FULL = True
    b = Builder(api)

    if FULL:
        log("TRYB PEŁNY: wszystkie produkty…")
        full = api.all("/products")
    else:
        log("produkty widoczne w sklepie…")
        full = api.all("/products", {"filters": json.dumps({"translations.pl_PL.active": "1"})})
    full = {p["product_id"]: p for p in full}
    visible = {pid for pid, p in full.items()
               if str((p["translations"].get("pl_PL") or {}).get("active")) == "1"}
    log(f"  pobrano {len(full)}, widocznych {len(visible)}")

    if FULL:
        existing = set(full)          # pełna lista już jest, nie trzeba osobnego zapytania
    else:
        # Bez listy wszystkich produktów (oszczędza ~70 zapytań). Sprawdzamy pojedynczo tylko
        # te, które w poprzednim pliku były na stanie, a zniknęły z widocznych:
        # ukryty (istnieje) czy usunięty (404). Nowe ukryte produkty dojdą w pełnym pobraniu.
        existing = set(full)
        gone = [pid for pid, o in prev.items() if o["stock"] > 0 and pid not in full]
        if gone:
            log(f"sprawdzam {len(gone)} produktów, które zniknęły z widocznych…")
        for pid in gone:
            try:
                api.get(f"/products/{pid}")
                existing.add(pid)
            except RuntimeError as e:
                if "HTTP 404" not in str(e):
                    raise

    # Zdjęcia: TYLKO dla produktów widocznych w sklepie (ukryte mają stan 0, zdjęcia zbędne).
    # Tryb pełny: wszystkie widoczne; normalnie tylko nowe w feedzie albo edytowane od
    # ostatniego uruchomienia (edit_date wg zegara sklepu; odkrycie produktu też zmienia datę).
    state = load_state()
    watermark = state.get("edit_watermark")
    if FULL or not watermark:
        need_imgs = set(visible)
    else:
        need_imgs = {pid for pid in visible
                     if pid not in prev or not prev[pid]["imgs"]
                     or (full[pid].get("edit_date") or "") >= watermark}
    log(f"zdjęcia: pobieram dla {len(need_imgs)} produktów, reszta z poprzedniego feedu…")
    images = b.images_for(need_imgs)

    offers = {}
    for pid, p in full.items():
        if p["stock"].get("active") != "1" and pid in visible:
            visible.discard(pid)
        o = b.offer(p, images.get(pid, []), pid in visible)
        if pid not in need_imgs:
            o["imgs"] = prev[pid]["imgs"] if pid in prev else []
        offers[pid] = o
    kept = 0
    for pid, o in prev.items():
        if pid in offers:
            continue
        offers[pid] = dict(o, stock=0)   # ukryte lub usunięte: zostają ze stanem 0
        kept += 1

    from zoneinfo import ZoneInfo
    now_pl = datetime.now(ZoneInfo("Europe/Warsaw"))
    # data aktualizacji jako komentarz XML: czytelna dla człowieka, czytniki feedów ją pomijają
    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           f"<!-- Last updated: {now_pl:%Y-%m-%d %H:%M} (UTC{now_pl.utcoffset().seconds // 3600:+d}) -->",
           "<offers>"]
    for pid in sorted(offers, key=int):
        out += emit(offers[pid])
    out.append("</offers>")

    in_stock = sum(1 for o in offers.values() if o["stock"] > 0)
    if len(offers) < 100 or (prev and in_stock < 0.3 * sum(1 for o in prev.values() if o["stock"] > 0)):
        sys.exit(f"Podejrzany wynik ({len(offers)} ofert, {in_stock} na stanie) — nie nadpisuję feedu.")

    if os.environ.get("NO_CHANGELOG") != "1":
        write_changelog(prev, offers, full, existing, visible)

    tmp = OUT + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(out) + "\n")
    os.replace(tmp, OUT)
    # znak wodny: najnowsza edycja widziana w tym przebiegu, cofnięta o 1 h zapasu
    edits = [p.get("edit_date") for p in full.values() if p.get("edit_date")]
    if edits:
        wm = max(edits)
        try:
            wm = (datetime.strptime(wm, "%Y-%m-%d %H:%M:%S") - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            pass
        if not watermark or wm > watermark:
            state["edit_watermark"] = wm
    if FULL:
        state["last_full"] = time.strftime("%Y-%m-%d %H:%M:%S")
    save_state(state)
    log(f"zapisano {len(offers)} ofert ({in_stock} na stanie; z poprzedniego feedu: "
        f"{kept} ukrytych/usuniętych ze stanem 0) -> {OUT}")


if __name__ == "__main__":
    main()
