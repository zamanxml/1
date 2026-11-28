"""Porównanie dwóch feedów: python porownaj.py stary.xml nowy.xml"""
import sys, collections, xml.etree.ElementTree as ET


def load(path):
    out = {}
    for o in ET.parse(path).getroot().findall("o"):
        out[o.get("id")] = {
            **{k: o.get(k) for k in ("url", "price", "avail", "stock", "basket")},
            "cat": o.findtext("cat"), "name": o.findtext("name"), "desc": o.findtext("desc"),
            "imgs": [e.get("url") for e in o.findall("imgs/*")],
            "attrs": [(a.get("name"), (a.text or "").strip()) for a in o.findall("attrs/a")],
        }
    return out


old, new = load(sys.argv[1]), load(sys.argv[2])
print(f"stary: {len(old)} ofert, nowy: {len(new)} ofert")
print(f"tylko w starym: {len(old.keys() - new.keys())}, tylko w nowym: {len(new.keys() - old.keys())}")
common = sorted(old.keys() & new.keys(), key=int)
diffs = collections.Counter(); ex = {}
for i in common:
    a, b = old[i], new[i]
    for k in a:
        va, vb = a[k], b[k]
        if k == "attrs":
            if set(va) != set(vb): k2 = "attrs(treść)"
            elif va != vb: k2 = "attrs(kolejność)"
            else: continue
        elif va != vb: k2 = k
        else: continue
        diffs[k2] += 1
        ex.setdefault(k2, []).append((i, va, vb))
print(f"wspólne: {len(common)}")
for k, n in diffs.most_common():
    print(f"\n== {k}: {n} różnic")
    for i, va, vb in ex[k][:3]:
        if k.startswith("attrs"):
            sa, sb = set(va), set(vb)
            print(f"  id {i}: tylko stary {sorted(sa - sb)[:4]} | tylko nowy {sorted(sb - sa)[:4]}")
        else:
            print(f"  id {i}: stary={str(va)[:150]!r}\n         nowy ={str(vb)[:150]!r}")
