"""Opisy produktów z parametrów według szablonów w szablony_opisow.txt (zasady opisane w tym pliku)."""
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
EMPTY = {"", "brak", "nie", "-", "inny", "inna", "niezdefiniowany", "n/a", "none"}
PLACEHOLDER = re.compile(r"\{([^{}|]+)(?:\|([^{}]+))?\}")
SENTENCE_END = re.compile(r"(?<=[.!?])\s+")


def _key(name):
    return name.strip().rstrip(":").strip().lower()


def load_templates(path=os.path.join(HERE, "szablony_opisow.txt")):
    """-> {kategoria: [akapit, ...]} gdzie akapit = [[zdanie, alternatywa, ...], ...]"""
    templates, cats, buf = {}, None, []

    def flush():
        if cats is None:
            return
        paras = [p for p in re.split(r"\n\s*\n", "\n".join(buf).strip()) if p.strip()]
        parsed = []
        for p in paras:
            groups = []
            for s in SENTENCE_END.split(" ".join(p.split())):
                if s.startswith("||") and groups:
                    groups[-1].append(s[2:].strip())
                elif s:
                    groups.append([s])
            parsed.append(groups)
        for c in cats:
            templates[c] = parsed

    for line in open(path, encoding="utf-8"):
        line = line.rstrip("\n")
        if line.lstrip().startswith("#"):
            continue
        m = re.fullmatch(r"\s*\[(.+)\]\s*", line)
        if m:
            flush()
            cats, buf = [c.strip() for c in m.group(1).split(";")], []
        else:
            buf.append(line)
    flush()
    return templates


def _value(raw, mod, name):
    v = (raw or "").strip()
    if _key(v) in EMPTY or v.lower().startswith("brak"):
        return None
    if mod == "tak":
        return "" if v.lower().startswith("tak") else None
    if mod == "k":
        v = v.split(",")[0]
        v = re.sub(r"\s*-\s*", "-", v)
    v = v.strip().rstrip(".!;,").strip()
    if not v:
        return None
    if name == "producent" and v.isupper() and len(v) > 3:
        v = v.capitalize()
    if mod == "m" and len(v) > 1 and v[0].isupper() and not v[1].isupper():
        v = v[0].lower() + v[1:]
    return v


def _fill(sentence, attrs):
    missing = False

    def rep(m):
        nonlocal missing
        name, mod = _key(m.group(1)), (m.group(2) or "").strip().lower()
        v = _value(attrs.get(name), mod, name)
        if v is None:
            missing = True
            return ""
        return v

    out = PLACEHOLDER.sub(rep, sentence)
    return None if missing else re.sub(r"\s{2,}", " ", out).strip()


def build(templates, name, cat, attrs):
    """attrs: lista (nazwa, wartość). Zwraca opis albo "" gdy nic się nie złożyło."""
    tpl = templates.get(cat) or templates.get("*")
    if not tpl:
        return ""
    a = {"nazwa": name}
    for n, v in attrs:
        a.setdefault(_key(n), v)
    paras = []
    for groups in tpl:
        sentences = []
        for alts in groups:
            for s in alts:
                f = _fill(s, a)
                if f:
                    sentences.append(f)
                    break
        if sentences:
            paras.append(" ".join(sentences))
    return "\n\n".join(paras)
