"""Raport braków w tłumaczeniu na angielski.

Uruchomienie: python raport_tlumaczen.py 1.xml raport/braki_tlumaczen.csv

Sprawdza produkty NA STANIE: nazwy parametrów, kategorie, wartości parametrów i nazwy produktów,
które po tłumaczeniu (translate_en.py) nadal wyglądają na polskie (polskie znaki albo typowe
polskie słowa). Wynik ma ten sam układ co tlumaczenia_en.csv: wystarczy wpisać kolumnę
"angielski" i przekleić wiersze do tlumaczenia_en.csv.
"""
import csv
import os
import re
import sys
import xml.etree.ElementTree as ET

import translate_en as T

PL_CHARS = re.compile(r"[ąćęłńóśźżĄĆĘŁŃÓŚŹŻ]")
PL_WORDS = re.compile(r"\b(brak|oraz|lub|dla|bez|jest|nie|tak|przy|zestawie|szt|sztuk|nowy|nowa|nowe|"
                      r"używany|używana|czarny|czarna|biały|biała|srebrny|srebrna|szary|szara|zasilacz|"
                      r"przewód|przewodem|kabel|wersja|możliwe|możliwy|drobne|ślady|wada|wady|wtyk|"
                      r"gniazdo|złącze|ładowarka|bateria|klawiatura|obudowa|matryca|uwaga)\b", re.I)


def polish(text):
    return bool(text) and bool(PL_CHARS.search(text) or PL_WORDS.search(text))


def main(src, dst):
    found = {}   # (typ, parametr, polski) -> [ile, przykładowe id, obecne tłumaczenie]

    def add(typ, param, pl, now, pid):
        k = (typ, param, pl)
        if k not in found:
            found[k] = [0, pid, now]
        found[k][0] += 1

    offers = [o for o in ET.parse(src).getroot().findall("o") if (o.get("stock") or "0") != "0"]
    for o in offers:
        pid = o.get("id")
        cat = o.findtext("cat") or ""
        if cat and cat not in T.CATS and cat not in T.OVR_CATS:
            add("kategoria", "", cat, T.tr_cat(cat), pid)
        name = (o.findtext("name") or "").strip()
        en = T.tr_name(name)
        if polish(en):
            add("nazwa", "", name, en, pid)
        for a in o.findall("attrs/a"):
            n, v = a.get("name") or "", (a.text or "").strip()
            if n not in T.NAMES and n not in T.OVR_PARAMS:
                add("parametr", "", n, n, pid)
            if not v or n in T.KEEP:
                continue
            ev = T.tr_value(n, v)
            if polish(ev):
                add("wartosc", n, v, ev, pid)

    order = {"kategoria": 0, "parametr": 1, "wartosc": 2, "nazwa": 3}
    rows = sorted(found.items(), key=lambda kv: (order[kv[0][0]], -kv[1][0], kv[0][1], kv[0][2]))
    os.makedirs(os.path.dirname(os.path.abspath(dst)), exist_ok=True)
    with open(dst, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["typ", "parametr", "ile", "polski", "angielski", "obecnie_w_feedzie_en", "przyklad_id"])
        for (typ, param, pl), (cnt, pid, now) in rows:
            w.writerow([typ, param, cnt, pl, "", now, pid])
    by = {}
    for (typ, _, _), _v in rows:
        by[typ] = by.get(typ, 0) + 1
    print(f"Raport tłumaczeń: {len(offers)} produktów na stanie, braków: {len(rows)} {by} -> {dst}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
