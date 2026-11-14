import json, time, urllib.parse, os, socket, ssl, gzip, http.client


def load_env(path="dane_dostepowe.env"):
    env = {}
    if os.path.exists(path):
        for l in open(path, encoding="utf-8"):
            l = l.strip()
            if l and not l.startswith("#") and "=" in l:
                k, v = l.split("=", 1); env[k.strip()] = v.strip().strip('"')
    for k in ("SHOPER_URL", "SHOPER_TOKEN"):
        if os.environ.get(k): env[k] = os.environ[k]
    if not env.get("SHOPER_TOKEN"):
        raise SystemExit("Brak SHOPER_TOKEN (sekret w GitHub albo dane_dostepowe.env).")
    env.setdefault("SHOPER_URL", "https://kompre.pl")
    return env


def _log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


class Shoper:
    """Klient REST Shopera z JEDNYM trwałym połączeniem (keep-alive) i kompresją gzip.
    Nawiązanie połączenia (handshake TLS) z serwerów GitHuba bywa bardzo wolne,
    więc robimy je raz, a nie przy każdym zapytaniu."""

    CONNECT_TIMEOUT = 15
    READ_TIMEOUT = 90

    def __init__(self, url, token):
        u = urllib.parse.urlparse(url.rstrip("/"))
        self.host = u.netloc
        self.prefix = (u.path or "") + "/webapi/rest"
        self.token = token
        self.conn = None
        self.calls = self.reconnects = 0
        self.ctx = ssl.create_default_context()

    def _connect(self):
        self.close()
        t = time.time()
        conn = http.client.HTTPSConnection(self.host, timeout=self.CONNECT_TIMEOUT, context=self.ctx)
        conn.connect()
        conn.sock.settimeout(self.READ_TIMEOUT)
        self.conn = conn
        self.reconnects += 1
        dt = time.time() - t
        if dt > 3:
            _log(f"  połączenie nawiązane w {dt:.0f} s")

    def close(self):
        if self.conn:
            try: self.conn.close()
            except Exception: pass
        self.conn = None

    def get(self, path, params=None):
        q = ""
        if params:
            q = "?" + "&".join(f"{k}={urllib.parse.quote(str(v))}" for k, v in params.items())
        headers = {"Authorization": "Bearer " + self.token, "Accept": "application/json",
                   "Accept-Encoding": "gzip", "User-Agent": "kompre-feed/1.0", "Connection": "keep-alive"}
        last = ""
        for attempt in range(8):
            try:
                if self.conn is None:
                    self._connect()
                t = time.time()
                self.conn.request("GET", self.prefix + path + q, headers=headers)
                r = self.conn.getresponse()
                body = r.read()
                if r.getheader("Content-Encoding", "").lower() == "gzip":
                    body = gzip.decompress(body)
                if r.will_close:
                    self.close()
                if r.status == 429 or r.status >= 500:
                    wait = int(r.getheader("Retry-After") or 0) or (3 + attempt * 3)
                    last = f"HTTP {r.status}"
                    _log(f"  {path}: {last} -> ponawiam za {wait} s (próba {attempt + 1})")
                    time.sleep(wait); continue
                if r.status >= 400:
                    raise RuntimeError(f"{path}: HTTP {r.status} {body.decode(errors='replace')[:200]}")
                self.calls += 1
                dt = time.time() - t
                if dt > 15:
                    _log(f"  wolna odpowiedź {path} ({dt:.0f} s)")
                return json.loads(body.decode())
            except (OSError, http.client.HTTPException, ssl.SSLError) as e:
                # zerwane / nienawiązane połączenie -> nowe połączenie i ponowienie
                last = f"{type(e).__name__}: {e}"
                self.close()
                _log(f"  {path}: {last} -> nowe połączenie (próba {attempt + 1})")
                time.sleep(min(2 + attempt * 2, 10)); continue
        raise RuntimeError(f"{path}: nie udało się po 8 próbach ({last})")

    def all(self, path, extra=None):
        out, page, t0 = [], 1, time.time()
        while True:
            p = {"limit": 50, "page": page}
            if extra: p.update(extra)
            d = self.get(path, p)
            out += d.get("list", [])
            pages = int(d.get("pages", 1))
            if page % 20 == 0:
                _log(f"  {path}: strona {page}/{pages} ({time.time() - t0:.0f} s)")
            if page >= pages: return out
            page += 1
            time.sleep(0.2)
