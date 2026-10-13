#!/usr/bin/env python3
"""
Surveille les pages ENIAD listées dans watcher/sources.json (lancé automatiquement par GitHub Actions).
 - télécharge les PDF d'emploi du temps, les lit (tableau JOUR x CRÉNEAU) et écrit data/timetables.json
 - détecte les liens / PDF nouveaux ou modifiés -> data/timetables.json (docs, news) + data/events.json
 - écrit data/.notify.json si quelque chose mérite une notification push (utilisé par admin/ci-push.js)
Ne plante jamais le site : en cas d'erreur réseau, les données précédentes sont conservées.
"""
import hashlib, io, json, os, re, sys, time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse, unquote

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
FEED = DATA / "timetables.json"
EVENTS = DATA / "events.json"
NOTIFY = DATA / ".notify.json"
UA = "EduVault-watcher/1.0 (suivi personnel de l'emploi du temps; contact: github)"
DAYS = ["LUNDI", "MARDI", "MERCREDI", "JEUDI", "VENDREDI", "SAMEDI", "DIMANCHE"]
TIME_RE = re.compile(r"^([A-ZÉÈ]{2,8})?\s*\(?\s*(\d{1,2})[h:](\d{2})\s*[-–à]\s*(\d{1,2})[h:](\d{2})\s*\)?$")
GROUP_RE = re.compile(r"^[A-Z]{2,6}\d?(\s*[·,/&-]\s*[A-Z]{2,6}\d?)*$")


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def hh(h, m):
    return f"{int(h):02d}:{m}"


def sha(b):
    return hashlib.sha256(b).hexdigest()[:16]


# ------------------------------------------------------------------ lecture du PDF
def parse_cell(cell, day):
    """Une case = un ou plusieurs blocs : titre (1+ lignes), groupes, Prof., salle, TYPE (hh:mm-hh:mm)."""
    if not cell:
        return []
    lines = [l.strip() for l in cell.split("\n") if l.strip()]
    if not lines or all(l in "—-–" for l in lines):
        return []
    blocks, cur = [], []
    for l in lines:
        cur.append(l)
        if TIME_RE.match(l):
            blocks.append(cur)
            cur = []
    out = []
    for b in blocks:
        m = TIME_RE.match(b[-1])
        typ = (m.group(1) or "").strip()
        s, e = hh(m.group(2), m.group(3)), hh(m.group(4), m.group(5))
        body = b[:-1]
        prof = room = groups = ""
        pi = next((i for i, l in enumerate(body) if re.match(r"^(Prof|Pr|Dr)\b\.?", l, re.I)), None)
        if pi is not None:
            prof = re.sub(r"^(Prof|Pr|Dr)\b\.?\s*", "", body[pi], flags=re.I).strip()
            room = " ".join(body[pi + 1:]).strip()
            head = body[:pi]
        else:
            room = body[-1] if len(body) > 1 else ""
            head = body[:-1] if len(body) > 1 else body
        if head and (GROUP_RE.match(head[-1]) or "·" in head[-1]) and len(head) > 1:
            groups = head[-1]
            head = head[:-1]
        title = " ".join(head).strip()
        week = "all"
        w = re.search(r"\(?\bsem(?:aine)?\.?\s*([AB])\b\)?", title, re.I)
        if w:
            week = w.group(1).upper()
            title = re.sub(r"\(?\bsem(?:aine)?\.?\s*[AB]\b\)?", "", title, flags=re.I).strip()
        if not title or title in "—-–":
            continue
        out.append({"m": title, "p": prof, "g": groups, "t": typ, "d": day, "s": s, "e": e, "r": room, "w": week})
    return out


def parse_pdf(data):
    """Retourne {classe: {"sem": str, "sessions": [...]}} (vide si ce n'est pas un emploi du temps)."""
    import pdfplumber
    res = {}
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            head = [l.strip() for l in text.split("\n")[:10]]
            if not any("JOUR" in l.upper() for l in text.split("\n")[:12]):
                continue
            sem = ""
            for l in head:
                if re.search(r"session|semestre", l, re.I):
                    sem = l
            cls = ""
            for l in head:
                if re.fullmatch(r"[A-Z]{2,6}\s?\d", l) or re.fullmatch(r"[A-Z]{2,6}\d(\s*[-/]\s*[A-Z]{2,6}\d)*", l):
                    cls = l.replace(" ", "")
                    break
            sessions = []
            for t in page.extract_tables():
                for row in t:
                    if not row or not row[0]:
                        continue
                    day = row[0].strip().upper().replace("É", "E")
                    day = next((d for d in DAYS if d == day), None)
                    if not day:
                        continue
                    for cell in row[1:]:
                        sessions += parse_cell(cell, day)
            if sessions:
                key = cls or "INCONNU"
                res.setdefault(key, {"sem": sem, "sessions": []})["sessions"] += sessions
    for v in res.values():
        v["sessions"].sort(key=lambda x: (DAYS.index(x["d"]), x["s"], x["m"]))
        v["hash"] = sha(json.dumps(v["sessions"], sort_keys=True, ensure_ascii=False).encode())
    return res


# ------------------------------------------------------------------ pages web
def get(url, binary=False, retries=3):
    last = None
    for i in range(retries):
        try:
            r = requests.get(url, headers={"User-Agent": UA, "Accept-Language": "fr"}, timeout=40)
            r.raise_for_status()
            if binary and len(r.content) > 25_000_000:
                raise RuntimeError("fichier trop gros")
            return r.content  # octets : BeautifulSoup détecte l'encodage lui-même
        except Exception as e:
            last = e
            time.sleep(3 * (i + 1))
    raise last


def scan_page(url):
    html = get(url, binary=True)
    soup = BeautifulSoup(html, "html.parser")
    title = (soup.title.string or "").strip() if soup.title else url
    items, seen = [], set()
    main = soup.find("main") or soup.find(id=re.compile("content|main", re.I)) or soup
    for a in main.find_all("a", href=True):
        href = urljoin(url, a["href"].split("#")[0])
        if not href.startswith("http") or href in seen:
            continue
        txt = " ".join(a.get_text(" ").split()) or unquote(Path(urlparse(href).path).name)
        pdf = href.lower().split("?")[0].endswith(".pdf") or "/sites/default/files/" in href.lower()
        same = urlparse(href).netloc == urlparse(url).netloc
        if not (pdf or same):
            continue
        # on ignore la navigation générique du site (menu, langues...)
        if a.find_parent(["nav", "header", "footer"]):
            continue
        seen.add(href)
        items.append({"t": txt[:160], "u": href, "pdf": bool(pdf)})
    return title, items


def load_feed():
    try:
        return json.loads(FEED.read_text(encoding="utf-8"))
    except Exception:
        return {"v": 1, "tables": {}, "docs": [], "news": [], "baseline": False}


def diff_sessions(old, new):
    k = lambda s: (s["m"], s["d"], s["s"], s["e"])
    o, n = {k(s): s for s in old}, {k(s): s for s in new}
    add = [n[x] for x in n if x not in o]
    rem = [o[x] for x in o if x not in n]
    chg = [(o[x], n[x]) for x in n if x in o and (o[x]["r"] != n[x]["r"] or o[x]["p"] != n[x]["p"])]
    return add, rem, chg


def describe(cls, add, rem, chg):
    parts = []
    for s in add[:3]:
        parts.append(f"+ {s['m']} {s['d'][:3].lower()} {s['s']}-{s['e']}")
    for s in rem[:3]:
        parts.append(f"- {s['m']} {s['d'][:3].lower()} {s['s']}")
    for a, b in chg[:3]:
        parts.append(f"~ {b['m']} : {a['r'] or '?'} → {b['r'] or '?'}")
    extra = len(add) + len(rem) + len(chg) - len(parts)
    if extra > 0:
        parts.append(f"… (+{extra})")
    return f"Emploi du temps {cls} modifié : " + " ; ".join(parts)


def main():
    DATA.mkdir(exist_ok=True)
    src = json.loads((ROOT / "watcher" / "sources.json").read_text(encoding="utf-8"))
    feed = load_feed()
    first_run = not feed.get("baseline")
    events, notify = [], []
    ts = now()
    status = {"ts": ts, "ok": [], "err": []}
    known_docs = {d["u"]: d for d in feed.get("docs", [])}
    known_news = {n["u"]: n for n in feed.get("news", [])}
    known_pages = set(feed.get("pages", []))

    for page in src.get("pages", []):
        try:
            title, items = scan_page(page)
        except Exception as e:
            status["err"].append(f"{page}: {e}")
            print("✗", page, e)
            continue
        status["ok"].append(page)
        fr = first_run or page not in known_pages   # page jamais vue : on mémorise sans notifier
        known_pages.add(page)
        print(f"✓ {page} : {len(items)} lien(s)")
        for it in items:
            if it["pdf"]:
                try:
                    data = get(it["u"], binary=True)
                except Exception as e:
                    status["err"].append(f"{it['u']}: {e}")
                    continue
                h = sha(data)
                try:
                    tables = parse_pdf(data)
                except Exception as e:
                    tables = {}
                    status["err"].append(f"lecture PDF {it['u']}: {e}")
                prev = known_docs.get(it["u"])
                doc = {"t": it["t"], "u": it["u"], "page": page, "h": h, "first": prev["first"] if prev else ts, "changed": ts if (prev and prev["h"] != h) else (prev or {}).get("changed", "")}
                if not prev and not fr and not tables:
                    events.append({"ts": ts, "k": "doc", "t": it["t"], "u": it["u"]})
                    notify.append(("Nouveau document ENIAD", it["t"]))
                elif prev and prev["h"] != h and not tables:
                    events.append({"ts": ts, "k": "doc-changed", "t": it["t"], "u": it["u"]})
                    notify.append(("Document ENIAD mis à jour", it["t"]))
                known_docs[it["u"]] = doc
                for cls, tb in tables.items():
                    old = feed["tables"].get(cls)
                    entry = {"sem": tb["sem"], "hash": tb["hash"], "src": it["u"], "sessions": tb["sessions"], "changed": (old or {}).get("changed", ts), "checked": ts}
                    if not old:
                        entry["changed"] = ts
                        if not fr:
                            events.append({"ts": ts, "k": "tt-new", "cls": cls, "t": f"Emploi du temps {cls} publié"})
                            notify.append((f"Emploi du temps {cls} publié", it["t"]))
                    elif old["hash"] != tb["hash"]:
                        add, rem, chg = diff_sessions(old["sessions"], tb["sessions"])
                        entry["changed"] = ts
                        txt = describe(cls, add, rem, chg)
                        events.append({"ts": ts, "k": "tt-changed", "cls": cls, "t": txt})
                        notify.append((f"Emploi du temps {cls} mis à jour", txt))
                    feed["tables"][cls] = entry
                    print(f"   · {cls}: {len(tb['sessions'])} séances ({'inchangé' if old and old['hash']==tb['hash'] else 'NOUVEAU/MODIFIÉ'})")
            else:
                prev = known_news.get(it["u"])
                if not prev:
                    known_news[it["u"]] = {"t": it["t"], "u": it["u"], "page": page, "first": ts}
                    if not fr:
                        events.append({"ts": ts, "k": "news", "t": it["t"], "u": it["u"]})
                        notify.append(("Nouveau sur le site ENIAD", it["t"]))

    # on ne garde que 150 liens/200 docs récents (fichier léger)
    feed["docs"] = sorted(known_docs.values(), key=lambda d: d["first"], reverse=True)[:200]
    feed["news"] = sorted(known_news.values(), key=lambda d: d["first"], reverse=True)[:150]
    feed["pages"] = sorted(known_pages)
    feed["v"] = 1
    feed["checked"] = ts if status["ok"] else feed.get("checked", "")
    feed["status"] = {"ok": len(status["ok"]), "err": status["err"][:5]}
    if status["ok"]:
        feed["baseline"] = True
    # on n'écrit que si quelque chose a vraiment changé (pas de commit inutile) : on compare sans les horodatages de contrôle
    def core(f):
        g = json.loads(json.dumps(f))
        g.pop("checked", None)
        for t in g.get("tables", {}).values():
            t.pop("checked", None)
        return g
    old_text = FEED.read_text(encoding="utf-8") if FEED.exists() else "{}"
    try:
        old_core = core(json.loads(old_text))
    except Exception:
        old_core = {}
    if core(feed) != old_core:
        FEED.write_text(json.dumps(feed, ensure_ascii=False, indent=1), encoding="utf-8")
        print("→ data/timetables.json mis à jour")
    else:
        print("→ rien de nouveau")
    if events:
        try:
            old_ev = json.loads(EVENTS.read_text(encoding="utf-8"))
        except Exception:
            old_ev = []
        EVENTS.write_text(json.dumps((events + old_ev)[:60], ensure_ascii=False, indent=1), encoding="utf-8")
    if notify:
        t, b = notify[0] if len(notify) == 1 else (f"{len(notify)} nouveautés ENIAD", " | ".join(x[1] for x in notify[:3]))
        NOTIFY.write_text(json.dumps({"title": t, "body": b[:300]}, ensure_ascii=False), encoding="utf-8")
    elif NOTIFY.exists():
        NOTIFY.unlink()
    if not status["ok"] and src.get("pages"):
        print("⚠ Aucune page n'a pu être lue (site indisponible ou bloqué) : données précédentes conservées.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
