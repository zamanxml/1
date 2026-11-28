"""Build kompre_en.xml (English) from kompre.xml (Polish, Ceneo format).

- parameter names and categories: fixed dictionaries
- parameter values: exact dictionary, then phrase rules
- product names: word rules
- descriptions: one shared English text built from the offer's parameters
Everything else (ids, urls, prices, stock, images, SKU, EAN, Model, Producent) is copied unchanged.
Usage: python translate_en.py kompre.xml kompre_en.xml
"""
import re
import sys
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape, quoteattr

# ---------------------------------------------------------------- parameter names
NAMES = {
    "SKU": "SKU", "EAN": "EAN", "Producent": "Manufacturer", "Marka": "Brand", "Model": "Model",
    "W zestawie": "In the box", "Stan obudowy": "Housing condition",
    "Rodzaj karty graficznej": "Graphics card type", "Model karty graficznej": "Graphics card model",
    "Dysk": "Storage", "Dodatkowy dysk": "Additional drive", "Typ dysku": "Drive type",
    "Typ dysku twardego": "Drive type", "Pojemność dysku [GB]": "Drive capacity [GB]",
    "Ilość pamięci RAM": "RAM", "Wielkość pamięci RAM": "RAM", "Typ pamięci RAM": "RAM type",
    "Seria procesora": "Processor series", "Procesor": "Processor", "Ilość rdzeni": "Cores",
    "Liczba rdzeni procesora": "Processor cores", "Taktowanie": "Clock speed",
    "Taktowanie bazowe procesora [GHz]": "Processor base clock [GHz]",
    "Taktowanie maksymalne procesora [GHz]": "Processor max clock [GHz]",
    "Gniazdo procesora": "Processor socket", "Częstotliwość szyny": "Bus frequency",
    "Licencja": "License", "Typ licencji": "License type", "Typ Licencji": "License type",
    "Zainstalowany system": "Installed OS", "Zainstalowany System": "Installed OS",
    "System operacyjny": "Operating system",
    "Napęd": "Optical drive", "Typ napędu": "Optical drive type",
    "Stan ekranu": "Screen condition", "Przekątna ekranu": "Screen size",
    "Przekątna ekranu [\"]": "Screen size [\"]", "Przekątna ekranu (cale) [\"]": "Screen size (inches) [\"]",
    "Rozdzielczość ekranu": "Screen resolution", "Rozdzielczość natywna [px]": "Native resolution [px]",
    "Rozdzielczość (px)": "Resolution (px)", "Powłoka matrycy": "Screen finish",
    "Typ matrycy": "Panel type", "Jasność matrycy": "Panel brightness", "Jasność": "Brightness",
    "Kontrast": "Contrast", "Kąt widzenia": "Viewing angle",
    "Częstotliwość odświeżania": "Refresh rate", "Ekran dotykowy": "Touchscreen",
    "Złącza zewnętrzne": "External ports", "Złącza z tyłu": "Rear ports",
    "Złącza z boku": "Side ports", "Złącza wewnętrzne": "Internal slots", "Złącza": "Ports",
    "Kamera": "Webcam", "Gwarancja sprzedawcy": "Seller warranty", "Gwarancja": "Warranty",
    "Kondycja sprzętu": "Device condition", "Kondycja": "Condition", "Stan": "Condition",
    "Bateria": "Battery", "Klawiatura (ISO lub ANSI)": "Keyboard (ISO or ANSI)",
    "Układ klawiatury": "Keyboard layout", "Układ": "Layout",
    "Informacje dodatkowe": "Additional information", "Informacje Dodatkowe": "Additional information",
    "Informacje dodatkowe:": "Additional information",
    "Przeznaczenie": "Compatibility", "Kompatybilne modele": "Compatible models",
    "Rodzaj": "Type", "Typ": "Type", "Obudowa": "Case type", "Napięcie": "Voltage",
    "Podświetlenie": "Backlight", "Rodzaj podświetlania": "Backlight type",
    "Regulacja kąta nachylenia": "Tilt adjustment", "Regulacja wysokości": "Height adjustment",
    "Pivot": "Pivot", "Moc": "Power", "Kolor": "Colour", "Stopa w komplecie": "Stand included",
    "Wbudowany głośnik": "Built-in speaker", "Pojemność": "Capacity", "Interfejs": "Interface",
    "Karta Sieciowa": "Network card", "Długość": "Length",
    "Komunikacja bezprzewodowa": "Wireless", "Zasilanie": "Power supply",
}

# ---------------------------------------------------------------- categories
CATS = {
    "Laptopy": "Laptops", "Laptopy 14 cali": "14-inch laptops", "Laptopy 15 cali": "15-inch laptops",
    "Laptopy 17 cali": "17-inch laptops", "Laptopy Lenovo": "Lenovo laptops", "Laptopy Dell": "Dell laptops",
    "Obudowy, ramki i zaślepki do laptopów": "Laptop housings, bezels and covers",
    "Komputery": "Desktop computers", "Zasilacze do laptopów": "Laptop chargers", "Monitory": "Monitors",
    "Klawiatury do laptopów": "Laptop keyboards", "Baterie do laptopów": "Laptop batteries",
    "Okablowanie": "Cables", "Akcesoria komputerowe": "Computer accessories",
    "Torby na laptopa": "Laptop bags", "Pozostałe akcesoria komputertowe": "Other computer accessories",
    "Pozostałe akcesoria komputerowe": "Other computer accessories",
    "Stacje dokujące": "Docking stations", "Pozostałe części do laptopów": "Other laptop parts",
    "Modemy 3G/4G/5G do laptopów": "3G/4G/5G modems for laptops", "Części do Komputerów": "Desktop parts",
    "Tablety": "Tablets", "Usługi": "Services", "Matryce do laptopów": "Laptop screens",
    "Pamięć RAM do laptopów": "Laptop RAM", "Części do Laptopów": "Laptop parts",
    "Klawiatury komputerowe": "Keyboards", "Głośniki": "Speakers", "Urządzenia sieciowe": "Network devices",
    "Napędy do laptopów": "Laptop drives", "Oprogramowanie": "Software", "Procesory": "Processors",
    "Strefa Allegro": "Special offers", "Słuchawki": "Headphones", "Myszki komputerowe": "Computer mice",
    "Chromebooki": "Chromebooks",
}

# parameters whose values are codes / names and must stay as they are
KEEP = {"SKU", "EAN", "Model", "Producent", "Marka", "Procesor", "Kompatybilne modele"}

# ---------------------------------------------------------------- exact values
VALUES = {
    "Tak": "Yes", "TAK": "Yes", "tak": "Yes", "Nie": "No", "NIE": "No", "nie": "No",
    "Brak": "None", "brak": "None", "-": "-", "Inny": "Other", "Inny AMD": "Other AMD",
    "Inny Intel": "Other Intel", "Inny ilość": "Other", "Opcjonalnie": "Optional",
    "Zintegrowana": "Integrated", "Dedykowana": "Dedicated", "Tak, wbudowana": "Yes, built-in",
    "Matowa": "Matte", "Błyszcząca": "Glossy", "Półmatowa": "Semi-matte",
    "Beznapędowy": "None", "Nowy": "New", "Nowa": "New", "Używany": "Used",
    "Powystawowy / Leżak magazynowy": "Ex-display / old stock",
    "Bez wad": "No defects", "Brak wad": "No defects", "Ekran bez wad": "Screen without defects",
    "Bez wad matrycy": "No screen defects", "\"A\" Bez wad matrycy": "\"A\" no screen defects",
    "Bez wad - nowa matryca!": "No defects - new screen!",
    "Zasilacz z przewodem": "Charger with power cable", "Zasilacz z przewdoem": "Charger with power cable",
    "Zasilacz w zestawie": "Charger included", "Zasilacz": "Charger", "zasilacz": "Charger",
    "Zasilacz zamiennik": "Replacement charger", "Zasilacz zamiennik z przewodem": "Replacement charger with power cable",
    "Oryginalny zasilacz, ładowarka": "Original charger", "Oryginalny zasilacz z przewodem": "Original charger with power cable",
    "Brak okablowania": "No cables", "Brak przewodu zasilającego": "No power cable",
    "zamiennik": "Replacement", "Zamiennik": "Replacement", "Nowy zamiennik": "New replacement",
    "Fabrycznie nowy zamiennik": "Brand new replacement", "oryginał": "Original", "Oryginał": "Original",
    "Czarny": "Black", "czarny": "Black", "Czarna": "Black", "czarna": "Black", "Biały": "White", "biały": "White",
    "Srebrny": "Silver", "Szary": "Grey", "Wewnętrzny": "Internal", "wewnętrzna": "Internal",
    "zewnętrzna": "External", "Optyczna": "Optical", "Przewodowa": "Wired", "Bezprzewodowa": "Wireless",
    "WiFi na USB": "USB WiFi", "Touchpad z przyciskami": "Touchpad with buttons",
    "Pasek na ramię (Opcjonalnie)": "Shoulder strap (optional)",
    "Windows 10 lub 11 Pro": "Windows 10 or 11 Pro", "Windows 10 lub 11 Home": "Windows 10 or 11 Home",
    "Do laptopów i komputerów": "For laptops and desktops", "komputerowy": "Computer",
}

# ---------------------------------------------------------------- phrase rules (applied in order)
PHRASES = [
    # warranty
    (r"\b1 miesiąc\b", "1 month"), (r"\b(\d+) miesiące\b", r"\1 months"), (r"\b(\d+) miesięcy\b", r"\1 months"),
    (r"\bpisemna\b", "written"),
    # condition grades
    (r"laptop poleasingowy", "post-lease laptop"), (r"komputer poleasingowy", "post-lease computer"),
    (r"\bposleasingowy\b|\bpoleasingowy\b", "post-lease"), (r"\bKlasa\b", "Grade"),
    (r"w 100% sprawny", "100% working"), (r"gotowy do pracy", "ready to use"),
    (r"przetestowany", "tested"),
    # signs of use / screen condition
    (r"(?i)norm?alne,?\s*", "Normal "), (r"(?i)standardowe ", "Standard "),
    (r"(?i)ślady u[żz]ytkowania|slady u[żz]ytkowania", "signs of use"),
    (r"(?i)\bdelikatne\b", "light"), (r"(?i)\bmałe\b", "small"), (r"(?i)\bminimalne\b", "minimal"),
    (r"(?i)\bdrobne\b", "minor"), (r"(?i)\bmożliwe\b", "possible"), (r"(?i)\bmożliwy\b", "possible"),
    (r"(?i)występują ", ""), (r"(?i)\bposiada\b", "has"), (r"\bOdnowiona\b", "Refurbished"),
    (r"\bodnowiona\b", "refurbished"),
    (r"(?i)profesjonalnie (wykonany|przygotowany) skin", "professionally applied skin"),
    (r"(?i)profesjonalny skin", "professional skin"),
    (r"(?i)na klapie", "on the lid"), (r"(?i)na matrycy", "on the screen"),
    (r"(?i)ryski|rysy", "scratches"), (r"(?i)otarcia", "scuffs"),
    (r"(?i)poświat(ki|ka|y|a)|poświatki", "light bleed"), (r"(?i)plamki", "spots"),
    (r"(?i)mikro(?!fon)\s?", "micro-"), (r"(?i)przebarwienia", "discolouration"), (r"(?i)żółte", "yellow"),
    (r"(?i)typu-?\s?C|typ C", "Type-C"), (r"(?i)typu-?\s?A|typ A", "Type-A"),
    (r"(?i)miejsce na kartę SIM|gniazdo SIM", "SIM slot"),
    (r"(?i)typu ", "such as "), (r"(?i)powstałe głównie na skutek transportu", "mainly from transport"),
    (r"\blub\b", "or"), (r"\bna\b", "on"),
    # frequent free-text phrases
    (r"(?i)okrągły", "Round"), (r"(?i)prostokątny", "Rectangular"), (r"(?i)wtyk z igłą", "plug with pin"),
    (r"(?i)wtyk", "plug"), (r"(?i)bez igły", "Without pin"), (r"(?i)\bcienki\b", "thin"),
    (r"(?i)niebieska końcówka|niebieskim wtykiem", "blue tip"), (r"(?i)\bczarny\b", "black"),
    (r"(?i)\bżółty\b", "yellow"), (r"(?i)wysyłane losowo", "Shipped at random"),
    (r"(?i)klawiatura niepodświetlana", "Non-backlit keyboard"), (r"(?i)brak podświetlenia", "No backlight"),
    (r"(?i)brak trackpointa", "no trackpoint"), (r"(?i)obrót ekranu o 360 stopni", "360° screen rotation"),
    (r"(?i)ekran 360", "360 screen"), (r"(?i)przejściówka", "Adapter"), (r"(?i)odpinany przewód", "Detachable cable"),
    (r"(?i)brak koniczynki", "no cloverleaf cable"), (r"(?i)brak okablowania", "No cables"),
    (r"(?i)brak przewodu zasilającego", "No power cable"), (r"(?i)w zestawie", "included"),
    (r"(?i)możliwość zamontowania dodatkowego dysku", "Room for an additional drive"),
    (r"(?i)możliwość wyboru systemu między", "Choice of OS between"),
    (r"(?i)leżak magazynowy", "Old stock"), (r"(?i)z demontażu", "pulled from device"),
    (r"(?i)pasek na ramię", "Shoulder strap"), (r"(?i)zewnętrzna na USB", "external via USB"),
    (r"(?i)tabletów", "tablets"), (r"(?i)\bty[łl]\b", "rear"), (r"(?i)ślad po naklejce", "sticker residue"),
    (r"(?i)wyjście słuchawkowe/głośnikowe", "Headphone/speaker jack"), (r"(?i)czytnik smart card", "Smart Card reader"),
    (r"(?i)z funkcją", "with"), (r"(?i)złącze słuchawkowo-mikrofonowe", "headphone/microphone jack"),
    (r"(?i)\bw wersji\b", "in the"), (r"(?i)\boraz\b", "and"),
    # battery
    (r"Oryginalna, czas pracy", "Original, runtime"), (r"Oryginalna,", "Original,"),
    (r"\bod (\d)", r"from \1"), (r"\bdo (\d)", r"to \1"), (r"\bminimum\b|\bmin\.", "min."),
    (r"\(używana\)", "(used)"),
    # keyboard
    (r"spolszczona naklejkami", "Polish layout stickers"), (r"Podświetlana", "Backlit"),
    (r"Numeryczna", "Numeric keypad"),
    # ports / box contents
    (r"(?i)złącze stacji dokującej|złącze dokowania|gniazdo dokowania", "docking connector"),
    (r"(?i)czytnik kart pamięci", "memory card reader"), (r"(?i)czytnik kart", "card reader"),
    (r"Wyjście słuchawkowe/wejście mikrofonowe", "Headphone/microphone jack"),
    (r"(?i)złącze wielofunkcyjne audio", "audio combo jack"), (r"(?i)wejście/wyjście", "in/out"),
    (r"(?i)wejście zasilania", "power input"), (r"(?i)złącze zasilania", "power connector"),
    (r"(?i)słuchawki/mikrofon", "headphones/microphone"), (r"(?i)gniazdo audio", "audio jack"),
    (r"(?i)miejsce na kartę SIM|gniazdo SIM", "SIM slot"), (r"(?i)blokada", "lock slot"),
    (r"(?i)natywne RJ45 z adapterem", "native RJ45 with adapter"),
    (r"(?i)połączone z|ze złączem|przez", "with"), (r"(?i)które może również pełnić funkcję", "also works as"),
    (r"(?i)\(ładowanie\)", "(charging)"), (r"(?i)\bopcjonalny\b", "optional"),
    (r"\bz Thunderbolt", "with Thunderbolt"), (r"\bz DisplayPort", "with DisplayPort"),
    (r"\bz PowerShare", "with PowerShare"), (r"\bi Power Delivery", "and Power Delivery"),
    (r"\bszt\.", "pcs"), (r"\bszt\b", "pcs"),
    (r"(?i)przewód zasilający", "power cable"), (r"(?i)śruby i kołki montażowe", "mounting screws"),
    (r"(?i)adapter do SD", "SD adapter"),
    # graphics
    (r"Grafika UHD Intel", "Intel UHD Graphics"), (r"dla procesorów Intel (\d+) gen\.", r"for Intel \1th gen processors"),
    (r"\bgen\.", "gen."),
    # compatibility
    (r"(?i)^do laptopów", "For laptops"), (r"(?i)\bdo laptopów\b", "for laptops"), (r"(?i)\bkomputerów\b", "desktops"),
    (r"\bi\b", "and"), (r"\bz\b", "with"), (r"\bdo\b", "to"),
    # misc
    (r"\bcala\b|\bcali\b", "inch"),
]
PHRASES = [(re.compile(p), r) for p, r in PHRASES]

# ---------------------------------------------------------------- product name words
NAME_WORDS = [
    (r"\bDotykowy\b", "Touchscreen"), (r"\bOdnowiony\b", "Refurbished"),
    (r"\bNOWA\b|\bNowa\b|\bNowy\b|\bNowe\b|\bnowa\b|\bnowy\b", "New"),
    (r"\bOryginalny\b|\bOryginalna\b", "Original"), (r"\bKomputer\b", "Computer"),
    (r"\bZasilacz\b|\bzasilacz\b|\bŁadowarka\b", "Charger"), (r"\bMysz\b|\bmysz\b", "Mouse"),
    (r"\bTorba\b", "Bag"), (r"\bBateria\b", "Battery"), (r"\bStacja dokująca\b|\bSTACJA DOKUJĄCA\b", "Docking station"),
    (r"\bStacja\b", "Station"), (r"\bPrzewód\b|\bprzewód\b|\bKabel\b", "Cable"),
    (r"\bKlawiatura\b|\bklawiatura\b", "Keyboard"), (r"\bKlapa [Mm]atrycy\b", "Screen lid"), (r"\bKlapa\b", "Lid"), (r"\bRamka\b|\bramka\b", "Bezel"),
    (r"\bDolna\b|\bdolna\b", "Bottom"), (r"\bGórna\b", "Top"), (r"\bKadłubek\b", "Bottom case"),
    (r"\bPamięć\b|\bPAMIĘCI\b", "Memory"), (r"\bTaśma\b", "Ribbon cable"), (r"\bDysk\b", "Drive"),
    (r"\bUsługa:?", "Service:"), (r"\bMatryca\b|\bMatrycy\b", "Screen"), (r"\[POJEDYNCZY\]", "[SINGLE]"),
    (r"\bKieszeń\b", "Caddy"), (r"\bProcesor\b", "Processor"), (r"\bNaklejki\b|\bnaklejki\b", "Stickers"),
    (r"\bZAŚLEPKA\b|\bZaślepka\b|\bZaślepki\b", "Cover"), (r"\bPodświetlana\b", "Backlit"),
    (r"\bKarta\b", "Card"), (r"\bZestaw\b", "Set"), (r"\bGłośniki\b|\bGŁOŚNIKI\b", "Speakers"),
    (r"\bSłuchawki\b", "Headphones"), (r"\bPRZEJŚCIÓWKA\b|\bPrzejściówka\b", "Adapter"),
    (r"\bOsłona\b|\bOsłony\b", "Cover"), (r"\bNapęd\b|\bNAPĘD\b", "Drive"), (r"\bNAPĘDU\b", "drive"),
    (r"\bbezprzewodowa\b", "wireless"), (r"\bprzewodowa\b", "wired"), (r"\bsieciowy\b", "network"),
    (r"\bzasilający\b|\bzasilająca\b", "power"), (r"\bdokująca\b", "docking"), (r"\bserwerowy\b", "server"),
    (r"\bradiowy\b", "wireless"), (r"\bczarna\b", "black"), (r"\bsrebrna\b", "silver"),
    (r"\bśrubka\b", "screw"), (r"\bPodkładka\b", "Pad"), (r"\bsamochodowy\b", "car"),
    (r"\bŚcienny\b", "Wall"), (r"\bzakrzywiony\b", "curved"), (r"\bbezramkowy\b", "frameless"),
    (r"\bdo laptopa\b|\bdo lapotpa\b|\bna laptopa\b", "for laptop"), (r"\bdo klawiatury\b", "for keyboard"),
    (r"\bpod klawiaturę\b", "under keyboard"), (r"\bdo matrycy\b", "for screen"), (r"\bdo dysku\b", "for drive"),
    (r"\bmatrycy\b", "screen"), (r"\bdysku\b", "drive"), (r"\bklawiatury\b", "keyboard"),
    (r"\bzasilacza\b", "charger"), (r"\bZawiasów\b", "Hinges"), (r"\bbez\b", "without"),
    (r"\blub\b", "or"), (r"\bdla\b", "for"), (r"\bdo\b", "for"), (r"\bz\b", "with"), (r"\bi\b(?! ?-)", "and"),
    (r"\bw\b", "in"), (r"\bna\b", "on"), (r"\bcali\b|\bcala\b", "inch"),
]
NAME_WORDS = [(re.compile(p), r) for p, r in NAME_WORDS]
DECIMAL_INCH = re.compile(r'(\d+),(\d+)(?=\s*(?:"|”|cal|inch|V\b|A\b|W\b|Wh|mAh|mm|cm|kg|GHz|h\b|$|\s))')
REPEAT_WORD = re.compile(r"\b(\w+) \1\b", re.I)


def load_overrides():
    """tlumaczenia_en.csv next to this script: typ;parametr;ile;polski;angielski (filled rows win).
    typ: wartosc = parameter value, nazwa = product name, parametr = parameter name, kategoria = category."""
    import csv
    import os
    vals, names = {}, {}
    OVR_PARAMS.clear(); OVR_CATS.clear()
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tlumaczenia_en.csv")
    if not os.path.exists(path):
        return vals, names
    with open(path, encoding="utf-8-sig", newline="") as f:
        sample = f.read(4096)
        f.seek(0)
        delim = ";" if sample.count(";") >= sample.count(",") else ","
        for row in csv.DictReader(f, delimiter=delim):
            pl, en = (row.get("polski") or "").strip(), (row.get("angielski") or "").strip()
            if pl and en:
                typ = (row.get("typ") or "").strip().lower()
                target = (names if typ.startswith("naz") else OVR_PARAMS if typ.startswith("par")
                          else OVR_CATS if typ.startswith("kat") else vals)
                target[pl] = en
    return vals, names


OVR_PARAMS, OVR_CATS = {}, {}
OVR_VALUES, OVR_NAMES = load_overrides()


def tr_param(n):
    return OVR_PARAMS.get(n) or NAMES.get(n, n)


def tr_cat(c):
    return OVR_CATS.get(c) or CATS.get(c, c)


def tr_value(name, value):
    v = value.strip()
    if v in OVR_VALUES:
        return OVR_VALUES[v]
    if not v or name in KEEP:
        return value
    if v in VALUES:
        return VALUES[v]
    out = v
    for rx, rep in PHRASES:
        out = rx.sub(rep, out)
    out = DECIMAL_INCH.sub(r"\1.\2", out)
    out = re.sub(r"\s{2,}", " ", out).strip()
    return out[:1].upper() + out[1:] if out[:1].islower() and v[:1].isupper() else out


def tr_name(text):
    if text.strip() in OVR_NAMES:
        return OVR_NAMES[text.strip()]
    out = text
    for rx, rep in NAME_WORDS:
        out = rx.sub(rep, out)
    out = DECIMAL_INCH.sub(r"\1.\2", out)
    out = REPEAT_WORD.sub(r"\1", out)
    return re.sub(r"\s{2,}", " ", out).strip()


# ---------------------------------------------------------------- English descriptions
LAPTOP_CATS = {"Laptopy", "Laptopy 14 cali", "Laptopy 15 cali", "Laptopy 17 cali", "Laptopy Lenovo",
               "Laptopy Dell", "Chromebooki", "Tablety"}
RES_LABEL = {"1366 x 768": "HD", "1600 x 900": "HD+", "1920 x 1080": "Full HD", "1920 x 1200": "WUXGA",
             "2560 x 1440": "QHD", "2560 x 1600": "WQXGA", "3840 x 2160": "4K UHD", "3440 x 1440": "UWQHD",
             "1280 x 800": "WXGA", "1440 x 900": "WXGA+", "1680 x 1050": "WSXGA+", "2880 x 1800": "Retina"}

TESTED = ("Every unit is carefully tested before shipping: it goes through a series of diagnostic tests, "
          "cleaning and preparation, so you can be sure it works as it should.")


def _c(x):
    return (x or "").strip().rstrip(".").strip()


def _brand(x):
    x = _c(x)
    return x if len(x) <= 3 else x.title()


def _gb(x):
    m = re.search(r"(\d+)\s*GB", x or "", re.I)
    return int(m.group(1)) if m else 0


def _yes(x):
    return (x or "").strip().lower().startswith("yes")


def _who(g, kind):
    brand, model = _brand(g("Producent", "Marka")), _c(g("Model"))
    if not model:
        return f"This {brand + ' ' if brand else ''}{kind}"
    if brand and model.lower().startswith(brand.lower()):
        brand = ""
    return f"The {brand + ' ' if brand else ''}{model}"


def _a(word):
    return "an" if word[:1].upper() in "AEIOU" else "a"


def _and(items):
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]


def _keyboard(kb):
    parts = [p.strip() for p in kb.split(",") if p.strip()]
    base, pre, post = [], [], []
    for p in parts:
        if p.lower() == "backlit":
            pre.append("backlit")
        elif p.lower() == "numeric keypad":
            post.append(" with a numeric keypad")
        else:
            base.append(p)
    words = " ".join(pre + [", ".join(base) or "", "keyboard"]).replace("  ", " ").strip()
    return f"{_a(words)} {words}{''.join(post)}"


def _core_specs(g):
    """processor, memory, storage, graphics, OS - shared by laptops and desktops"""
    t = []
    proc, series = _c(g("Procesor")), _c(g("Seria procesora"))
    if proc or series:
        cpu = f"{series} processor ({proc})" if series and proc else (series or proc) + " processor"
        extra = []
        cores = _c(g("Ilość rdzeni", "Liczba rdzeni procesora"))
        if cores:
            extra.append(f"{cores} cores")
        if g("Taktowanie"):
            extra.append(f"a clock speed of {_c(g('Taktowanie'))}")
        art = "an" if cpu[:1].upper() in "AEIOU" else "a"
        t.append(f"It is powered by {art} {cpu}" + (" with " + " and ".join(extra) if extra else "") + ".")
    ram, rtype = _c(g("Ilość pamięci RAM", "Wielkość pamięci RAM")), _c(g("Typ pamięci RAM"))
    disk, dtype = _c(g("Dysk", "Pojemność dysku [GB]")), _c(g("Typ dysku", "Typ dysku twardego"))
    if ram or disk:
        parts = []
        if ram:
            parts.append(f"{ram} of {rtype + ' ' if rtype else ''}RAM")
        if disk:
            parts.append(f"a {disk} {dtype + ' ' if dtype else ''}drive")
        t.append("It has " + " and ".join(parts) + ".")
        n = _gb(ram)
        if n >= 16:
            t.append("That is plenty of memory for heavy multitasking, many browser tabs and demanding applications.")
        elif n >= 8:
            t.append("That is comfortable for office work, web browsing, online meetings and multitasking.")
        elif n:
            t.append("That is enough for basic office tasks, e-mail and web browsing.")
        if "SSD" in dtype.upper():
            t.append("The SSD makes the system boot and apps open quickly.")
    gpu, gtype = _c(g("Model karty graficznej")), _c(g("Rodzaj karty graficznej")).lower()
    if gpu:
        t.append(f"Graphics: {gpu}" + (f" ({gtype})" if gtype else "") + ".")
    os_ = _c(g("Zainstalowany system", "Zainstalowany System", "System operacyjny", "Licencja"))
    lic = _c(g("Typ licencji", "Typ Licencji"))
    if os_ and os_.lower() not in ("none", "no", "-"):
        t.append(f"It comes with {os_} installed" + (f" ({lic} license)" if lic else "") + ", ready to use out of the box.")
    return t


def _condition(g, with_screen=True, with_battery=True):
    rows = [("Condition", ("Kondycja", "Kondycja sprzętu", "Stan")), ("Housing", ("Stan obudowy",))]
    if with_screen:
        rows.append(("Screen", ("Stan ekranu",)))
    if with_battery:
        rows.append(("Battery", ("Bateria",)))
    return [f"{lbl}: {_c(g(*k))}." for lbl, k in rows if g(*k)]


def _desc_laptop(g, name, kind):
    touch = _yes(g("Ekran dotykowy"))
    who = _who(g, kind)
    if who.startswith("This"):
        intro = f"{who} is built for reliable, everyday work."
    elif kind == "tablet":
        intro = f"{who} is a {'touchscreen ' if touch else ''}tablet for work, study and entertainment."
    else:
        intro = f"{who} is a business-class {'touchscreen ' if touch else ''}{kind} built for reliable, everyday work."
    t = [f"{name}.", intro]
    t += _core_specs(g)
    size = _c(g("Przekątna ekranu", "Przekątna ekranu [\"]", "Przekątna ekranu (cale) [\"]"))
    res = _c(g("Rozdzielczość ekranu", "Rozdzielczość natywna [px]", "Rozdzielczość (px)"))
    if size or res:
        lab = RES_LABEL.get(res)
        fin = _c(g("Powłoka matrycy")).lower()
        s = f"The {size + ' ' if size else ''}{fin + ' ' if fin else ''}screen"
        if res:
            s += f" has a resolution of {res}" + (f" ({lab})" if lab else "")
        if touch:
            s += (" and" if res else "") + " supports touch control"
        t.append(s + ".")
        if fin == "matte":
            t.append("The matte finish reduces reflections, so it is comfortable to use near a window.")
    feats = []
    if _yes(g("Kamera")):
        feats.append("a built-in webcam for video calls")
    kb = _c(g("Klawiatura (ISO lub ANSI)", "Układ klawiatury"))
    if kb:
        feats.append(_keyboard(kb))
    if feats:
        t.append("It also has " + " and ".join(feats) + ".")
    ports = _c(g("Złącza zewnętrzne", "Złącza"))
    if ports:
        t.append(f"Ports: {ports}.")
    return t + _condition(g)


def _desc_desktop(g, name):
    case = _c(g("Obudowa"))
    t = [f"{name}.", f"{_who(g, 'computer')} is a business-class desktop computer" + (f" in {_a(case)} {case} case" if case else "") +
         ", built for reliable work in the office and at home."]
    t += _core_specs(g)
    for lbl, k in (("Ports", ("Złącza zewnętrzne", "Złącza")), ("Front/side ports", ("Złącza z boku",)),
                   ("Rear ports", ("Złącza z tyłu",))):
        if g(*k):
            t.append(f"{lbl}: {_c(g(*k))}.")
    slots = _c(g("Złącza wewnętrzne"))
    if slots:
        t.append(f"Internal slots: {slots}, so it is easy to upgrade.")
    return t + _condition(g, with_screen=False, with_battery=False)


def _desc_monitor(g, name):
    size = _c(g("Przekątna ekranu", "Przekątna ekranu [\"]", "Przekątna ekranu (cale) [\"]"))
    res = _c(g("Rozdzielczość ekranu", "Rozdzielczość natywna [px]", "Rozdzielczość (px)"))
    lab = RES_LABEL.get(res)
    t = [f"{name}.", f"{_who(g, 'monitor')} is a {size + ' ' if size else ''}business-class monitor, a great fit for office work and a home desk."]
    spec = []
    if res:
        spec.append(f"a resolution of {res}" + (f" ({lab})" if lab else ""))
    if g("Typ matrycy"):
        spec.append(f"a {_c(g('Typ matrycy'))} panel")
    if g("Częstotliwość odświeżania"):
        spec.append(f"a {_c(g('Częstotliwość odświeżania'))} refresh rate")
    if spec:
        t.append("It offers " + _and(spec) + ".")
    for lbl, k in (("Brightness", ("Jasność matrycy", "Jasność")), ("Contrast", ("Kontrast",)),
                   ("Viewing angle", ("Kąt widzenia",)), ("Screen finish", ("Powłoka matrycy",)),
                   ("Ports", ("Złącza", "Złącza zewnętrzne"))):
        if g(*k):
            t.append(f"{lbl}: {_c(g(*k))}.")
    adj = [lbl for lbl, k in (("tilt", "Regulacja kąta nachylenia"), ("height", "Regulacja wysokości"),
                              ("pivot", "Pivot")) if _yes(g(k))]
    if adj:
        t.append("The stand offers " + _and(adj) + " adjustment for comfortable, ergonomic work.")
    if g("Stopa w komplecie"):
        t.append(f"Stand included: {_c(g('Stopa w komplecie'))}.")
    if _yes(g("Wbudowany głośnik")):
        t.append("It has a built-in speaker.")
    return t + _condition(g, with_battery=False)


def _desc_other(g, name):
    t = [f"{name}."]
    for lbl, k in (("Type", ("Rodzaj", "Typ")), ("Compatibility", ("Przeznaczenie",)),
                   ("Compatible models", ("Kompatybilne modele",)), ("Manufacturer", ("Producent", "Marka")),
                   ("Model", ("Model",)), ("Colour", ("Kolor",)), ("Capacity", ("Pojemność",)),
                   ("Voltage", ("Napięcie",)), ("Power", ("Moc",)), ("Length", ("Długość",)),
                   ("Interface", ("Interfejs",)), ("Condition", ("Kondycja", "Kondycja sprzętu", "Stan")),
                   ("Additional information", ("Informacje dodatkowe", "Informacje Dodatkowe"))):
        v = _c(g(*k))
        if v:
            t.append(f"{lbl}: {v}.")
    return t


def build_desc(name_en, attrs, cat_pl, name_pl):
    """attrs: dict polish parameter name -> translated value"""
    def g(*keys):
        for k in keys:
            if attrs.get(k):
                return attrs[k]
        return ""

    name = _c(name_en)
    low = name_pl.strip().lower()
    device = True
    if cat_pl == "Monitory" or (low.startswith("monitor") and cat_pl == "Strefa Allegro"):
        t = _desc_monitor(g, name)
    elif cat_pl == "Komputery" or (low.startswith(("komputer", "terminal")) and cat_pl == "Strefa Allegro"):
        t = _desc_desktop(g, name)
    elif cat_pl in LAPTOP_CATS or (cat_pl == "Strefa Allegro" and "laptop" in low):
        t = _desc_laptop(g, name, "tablet" if cat_pl == "Tablety" else "laptop")
    else:
        t, device = _desc_other(g, name), False
    if g("W zestawie"):
        t.append(f"In the box: {_c(g('W zestawie'))}.")
    t.append(TESTED if device else "See the parameters for full details.")
    return " ".join(t)


def main(src, dst):
    root = ET.parse(src).getroot()
    out = ['<?xml version="1.0" encoding="UTF-8"?>']
    with open(src, encoding="utf-8") as f:
        head = f.read(600)
    m = re.search(r"<!-- Last updated: [^<>]*? -->", head)   # ta sama data co w polskim pliku
    if m:
        out.append(m.group(0))
    out.append("<offers>")
    for o in root.findall("o"):
        attr_str = " ".join(f"{k}={quoteattr(v)}" for k, v in o.attrib.items())
        out.append(f"  <o {attr_str}>")
        attrs_pl = {}
        attrs_el = o.find("attrs")
        translated = []
        if attrs_el is not None:
            for a in attrs_el.findall("a"):
                n = a.get("name", "")
                v = tr_value(n, a.text or "")
                attrs_pl.setdefault(n, v)
                translated.append((tr_param(n), v))
        cat = o.findtext("cat") or ""
        name_en = tr_name(o.findtext("name") or "")
        out.append(f"    <cat><![CDATA[{tr_cat(cat)}]]></cat>")
        name_en = name_en.replace("]]>", "]] >")
        out.append(f"    <name><![CDATA[{name_en}]]></name>")
        out.append(f"    <desc><![CDATA[{build_desc(name_en, attrs_pl, cat, o.findtext("name") or "")}]]></desc>")
        imgs = o.find("imgs")
        if imgs is not None:
            out.append("    <imgs>")
            for i in imgs:
                out.append(f"      <{i.tag} url={quoteattr(i.get('url', ''))}/>")
            out.append("    </imgs>")
        if translated:
            out.append("    <attrs>")
            for n, v in translated:
                v = v.replace("]]>", "]]&gt;")
                out.append(f"      <a name={quoteattr(n)}><![CDATA[{v}]]></a>")
            out.append("    </attrs>")
        out.append("  </o>")
    out.append("</offers>")
    text = "\n".join(out) + "\n"
    text = re.sub(r"QWERTY\s+PL\b", "QWERTY", text)  # English feed: no "PL" after QWERTY
    text = re.sub(r"\s*\((?:with )?Polish layout stickers\)|,?\s*(?:with )?Polish layout stickers", "", text, flags=re.I)
    with open(dst, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
