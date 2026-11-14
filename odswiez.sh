#!/usr/bin/env bash
# Jedno odświeżenie feedu (uruchamiane przez .github/workflows/refresh.yml).
#
# Zaplanowane przebiegi GitHuba bywają opóźnione albo pominięte, dlatego nic nie zależy
# od tego, o której dokładnie przebieg wystartuje:
#   - pełne pobranie: pierwszy przebieg w niedzielę, jeśli w niedzielę jeszcze go nie było (albo ręcznie: full),
#   - porównanie trzech plików: pierwszy przebieg po 6:00 PL, jeśli dziś jeszcze go nie było (albo ręcznie: porownaj).
# Bezpieczeństwo: gdy coś się nie uda, nic nie jest publikowane i zostaje poprzedni plik.
# Publikacja nie nadpisze plików wgranych do repo w trakcie przebiegu (--force-with-lease).
set -uo pipefail

[ -n "${SHOPER_URL:-}" ] || export SHOPER_URL=https://kompre.pl
export DATA_DIR="$PWD"
FULL_INPUT="${FULL_INPUT:-false}"
PORO_INPUT="${PORO_INPUT:-false}"
git config user.name "github-actions[bot]"
git config user.email "41898282+github-actions[bot]@users.noreply.github.com"

log() { echo "== $(TZ=Europe/Warsaw date '+%H:%M:%S') PL: $*"; }

want_full() {
  [ "$FULL_INPUT" = "true" ] && return 0
  [ "$(date -u +%u)" = "7" ] || return 1
  last=$(python3 -c "import json; print(json.load(open('stan.json')).get('last_full', '')[:10])" 2>/dev/null || true)
  [ "$last" != "$(date -u +%F)" ]
}

want_compare() {
  [ "$PORO_INPUT" = "true" ] && return 0
  [ "$((10#$(TZ=Europe/Warsaw date +%H)))" -ge 6 ] || return 1
  [ ! -f "porownanie/$(TZ=Europe/Warsaw date +%F).txt" ]
}

generate() {
  rm -f /tmp/prev.xml
  [ -f 1.xml ] && cp 1.xml /tmp/prev.xml
  python3 generuj_feed.py /tmp/new.xml /tmp/prev.xml || return 1
  python3 -c "import xml.etree.ElementTree as E; E.parse('/tmp/new.xml')" || return 1
  cp /tmp/new.xml 1.xml
  if python3 translate_en.py 1.xml /tmp/en.xml && python3 -c "import xml.etree.ElementTree as E; E.parse('/tmp/en.xml')"; then
    cp /tmp/en.xml 1_en.xml
  else
    echo "::warning::English feed failed, keeping previous 1_en.xml"
  fi
  if [ "$FULL" = "1" ]; then
    python3 raport_tlumaczen.py 1.xml raport/braki_tlumaczen.csv || echo "::warning::Translation report failed"
  fi
}

# Porównanie: źródło (adres tylko w sekrecie SOURCE_URL), odbicie zamanxml/feed i nowy plik.
# Pliki źródła i odbicia są tylko CZYTANE, nic w nich nie zmieniamy.
compare() {
  mkdir -p porownanie
  out="porownanie/$(TZ=Europe/Warsaw date +%Y-%m-%d).txt"
  rm -f /tmp/src.xml /tmp/mirror.xml /tmp/src.err
  curl -fsSL --retry 3 -o /tmp/src.xml "${SOURCE_URL:-}" 2>/dev/null || echo "nie udało się pobrać pliku źródłowego" > /tmp/src.err
  curl -fsSL --retry 3 -o /tmp/mirror.xml https://raw.githubusercontent.com/zamanxml/feed/main/kompre.xml || true
  {
    echo "Porównanie feedów, $(TZ=Europe/Warsaw date '+%Y-%m-%d %H:%M') czasu PL"
    echo "ZRODLO = oryginalny feed, ODBICIE = zamanxml/feed/kompre.xml, NOWY = ten repo, 1.xml (z Shopera)"
    [ -f /tmp/src.err ] && cat /tmp/src.err
    for pair in "ZRODLO:/tmp/src.xml ODBICIE:/tmp/mirror.xml" "ZRODLO:/tmp/src.xml NOWY:1.xml" "ODBICIE:/tmp/mirror.xml NOWY:1.xml"; do
      set -- $pair; a=${1%%:*}; fa=${1#*:}; b=${2%%:*}; fb=${2#*:}
      echo; echo "################ $a  vs  $b ################"
      if [ -s "$fa" ] && [ -s "$fb" ]; then python3 porownaj.py "$fa" "$fb" 2>&1 | sed "s/stary=/$a=/; s/nowy =/$b=/; s/^stary:/$a:/; s/, nowy:/, $b:/; s/tylko w starym/tylko w $a/; s/tylko w nowym/tylko w $b/; s/tylko stary/tylko $a/; s/tylko nowy/tylko $b/"
      else echo "brak jednego z plików"; fi
    done
  } > "$out"
  cp "$out" porownanie/najnowsze.txt
  head -40 "$out"
}

publish() {
  touch .nojekyll
  rm -rf __pycache__
  git add -A
  if git diff --cached --quiet; then log "bez zmian, nic nie publikuję"; return 0; fi
  git checkout -q --orphan "pub_$(date +%s)"
  git add -A
  git commit -q -m "update $(date -u +%Y-%m-%dT%H:%MZ)"
  # wypychamy tylko jeśli main nadal wskazuje na wersję, od której zaczęliśmy;
  # jeśli w międzyczasie ktoś wgrał pliki, ten przebieg niczego nie nadpisuje (następny weźmie nową wersję)
  if git push -q --force-with-lease="main:$BASE" origin HEAD:main; then
    log "opublikowano"
  else
    echo "::warning::main zmienił się w trakcie przebiegu (np. wgrane pliki), publikację pomijam, zrobi ją następny przebieg"
  fi
}

BASE=$(git rev-parse HEAD)
if want_full; then FULL=1; else FULL=0; fi
export FULL
log "odświeżenie (pełne: $FULL)"
if ! generate; then
  echo "::error::Generowanie nie powiodło się, zostaje poprzedni plik"
  exit 1
fi
if want_compare; then
  log "porównanie trzech plików"
  compare || echo "::warning::Comparison failed"
fi
publish
