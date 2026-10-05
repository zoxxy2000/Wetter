#!/usr/bin/env python3
"""Holt Zusatzdaten vom DWD, die eine Web-App nicht direkt im Browser abrufen darf,
und legt sie als daten/lage.json neben die App. Läuft als GitHub-Aktion.

- Waldbrandgefahrenindex (WBI) und Graslandfeuerindex (GLFI) einer DWD-Station
- Pollenflug-Gefahrenindex (alle Regionen, die App wählt aus)
- Biowetter / Gefahrenindizes für Wetterfühlige (alle Gebiete)

Nur Python-Standardbibliothek, keine Installation nötig.
"""
import datetime as dt
import html.parser
import json
import os
import re
import sys
import urllib.request

# ---------------------------------------------------------------- Einstellungen
FEUER_STATION = "Bückeburg"   # so, wie die Station in der DWD-Tabelle heißt
FEUER_LAND = "NI"             # Tabelle des Bundeslandes: NI = Niedersachsen, NW = NRW, ...
URL_WBI = f"https://www.dwd.de/DWD/warnungen/agrar/wbx/wbx_tab_alle_{FEUER_LAND}.html"
URL_GLFI = f"https://www.dwd.de/DWD/warnungen/agrar/glfi/glfi_tab_alle_{FEUER_LAND}.html"
LAENDER = ["BB", "BE", "BW", "BY", "HB", "HE", "HH", "MV", "NI", "NW", "RP", "SH", "SL", "SN", "ST", "TH"]
URL_TAB = "https://www.dwd.de/DWD/warnungen/agrar/{art}/{art}_tab_alle_{land}.html"   # art: wbx oder glfi
URL_STATIONEN = "https://opendata.dwd.de/climate_environment/CDC/observations_germany/climate/daily/kl/recent/KL_Tageswerte_Beschreibung_Stationen.txt"
URL_POLLEN = "https://opendata.dwd.de/climate_environment/health/alerts/s31fg.json"
URL_BIO = "https://opendata.dwd.de/climate_environment/health/alerts/biowetter.json"
ZIEL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "daten", "lage.json")


def hole(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": "Wetter-App (GitHub-Aktion)"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        roh = r.read()
        zs = r.headers.get_content_charset() or "utf-8"
    try:
        return roh.decode(zs)
    except UnicodeDecodeError:
        return roh.decode("latin-1")


class Tabellen(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.zeilen, self._z, self._c = [], None, None

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self._z = []
        elif tag in ("td", "th") and self._z is not None:
            self._c = []

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self._c is not None:
            self._z.append(" ".join("".join(self._c).split()))
            self._c = None
        elif tag == "tr" and self._z is not None:
            self.zeilen.append(self._z)
            self._z = None

    def handle_data(self, data):
        if self._c is not None:
            self._c.append(data)


def feuer_tabelle(html_text, station):
    p = Tabellen()
    p.feed(html_text)
    tage = []
    for z in p.zeilen:  # Kopfzeile mit Datumsangaben suchen
        d = [c for c in z if re.search(r"\d{1,2}\.\d{1,2}\.", c)]
        if len(d) >= 2:
            tage = [re.search(r"\d{1,2}\.\d{1,2}\.", c).group(0) for c in d]
            break
    kern = station.split(",")[0].strip().lower()
    for z in p.zeilen:
        idx = next((i for i, c in enumerate(z) if kern in (c or "").lower()), None)
        if idx is None:
            continue
        stufen = [int(c.strip()) for c in z[idx + 1:] if (c or "").strip() in ("1", "2", "3", "4", "5")]
        if stufen:
            return stufen[:5], tage[:len(stufen[:5])]
    return [], tage


def norm(name):
    n = name.lower()
    for a, b in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss")):
        n = n.replace(a, b)
    return re.sub(r"[^a-z0-9]", "", n)


def alle_zeilen(html_text):
    """Alle Stationen einer Tabelle: {Name: [Stufen]} und die Datumsangaben"""
    p = Tabellen()
    p.feed(html_text)
    tage, out = [], {}
    for z in p.zeilen:
        d = [c for c in z if re.search(r"\d{1,2}\.\d{1,2}\.", c)]
        if len(d) >= 2 and not tage:
            tage = [re.search(r"\d{1,2}\.\d{1,2}\.", c).group(0) for c in d]
            continue
        idx = next((i for i, c in enumerate(z) if re.search(r"[A-Za-zÄÖÜäöü]{3}", c or "")), None)
        if idx is None:
            continue
        stufen = [int(c.strip()) for c in z[idx + 1:] if (c or "").strip() in ("1", "2", "3", "4", "5")]
        if stufen:
            out[z[idx].strip()] = stufen[:5]
    return out, tage


def stationsliste():
    """DWD-Stationen mit Koordinaten: {normierter Name: (lat, lon, Name)}"""
    txt = hole(URL_STATIONEN, 60)
    st = {}
    for zeile in txt.splitlines():
        m = re.match(r"^\s*(\d+)\s+(\d{8})\s+(\d{8})\s+(-?\d+)\s+([\d.]+)\s+([\d.]+)\s+(.+?)\s{2,}", zeile)
        if not m:
            continue
        name, bis = m.group(7).strip(), m.group(3)
        k = norm(name)
        if k not in st or bis > st[k][3]:
            st[k] = (float(m.group(5)), float(m.group(6)), name, bis)
    return st


def koordinaten(name, st):
    k = norm(name)
    if k in st:
        return st[k][:2]
    kurz = norm(re.split(r"[(/,]", name)[0])
    for schluessel, v in st.items():
        if schluessel == kurz or schluessel.startswith(kurz) or kurz.startswith(schluessel):
            return v[:2]
    return (None, None)


def alle_feuerstationen():
    st = {}
    try:
        st = stationsliste()
        print(f"Stationsliste: {len(st)} Stationen")
    except Exception as e:
        print("WARNUNG Stationsliste:", e, file=sys.stderr)
    stationen, tage = {}, []
    for land in LAENDER:
        for art, feld in (("wbx", "wbi"), ("glfi", "glfi")):
            try:
                werte, t = alle_zeilen(hole(URL_TAB.format(art=art, land=land), 30))
            except Exception:
                continue
            tage = tage or t
            for name, stufen in werte.items():
                e = stationen.setdefault(name, {"name": name, "land": land, "wbi": [], "glfi": []})
                e[feld] = stufen
    liste = []
    for e in stationen.values():
        lat, lon = koordinaten(e["name"], st) if st else (None, None)
        e["lat"], e["lon"] = lat, lon
        liste.append(e)
    mit = sum(1 for e in liste if e["lat"] is not None)
    print(f"Feuerindizes: {len(liste)} Stationen, davon {mit} mit Koordinaten")
    return liste, tage


def kompakt_pollen(j):
    return {
        "stand": j.get("last_update"), "naechste": j.get("next_update"),
        "regionen": [{
            "id": c["partregion_id"] if c.get("partregion_id", -1) > 0 else c.get("region_id"),
            "name": c.get("partregion_name") or c.get("region_name"),
            "pollen": {k: [v.get("today"), v.get("tomorrow"), v.get("dayafter_to")] for k, v in (c.get("Pollen") or {}).items()},
        } for c in j.get("content", [])],
    }


def kompakt_bio(j):
    per = ["today_morning", "today_afternoon", "tomorrow_morning", "tomorrow_afternoon",
           "dayafter_to_morning", "dayafter_to_afternoon"]
    return {
        "stand": j.get("last_update"),
        "zonen": [{
            "id": z.get("id"), "name": z.get("name"),
            "perioden": [{
                "k": k, "date": z[k].get("date"), "name": z[k].get("name"),
                "effekte": [[e.get("name"), e.get("value")] for e in z[k].get("effect", [])],
                "rat": [[r.get("name"), r.get("value")] for r in z[k].get("recomms", [])],
            } for k in per if z.get(k)],
        } for z in j.get("zone", [])],
    }


def main():
    jetzt = dt.datetime.now(dt.timezone(dt.timedelta(hours=1)))
    try:
        import zoneinfo
        jetzt = dt.datetime.now(zoneinfo.ZoneInfo("Europe/Berlin"))
    except Exception:
        pass
    alt = {}
    if os.path.exists(ZIEL):
        try:
            alt = json.load(open(ZIEL, encoding="utf-8"))
        except Exception:
            alt = {}
    out = {"stand": jetzt.strftime("%d.%m.%Y %H:%M"), "feuer": None, "pollen": None, "bio": None}
    fehler = []

    try:
        wbi, tage = feuer_tabelle(hole(URL_WBI), FEUER_STATION)
        glfi, tage2 = feuer_tabelle(hole(URL_GLFI), FEUER_STATION)
        out["feuer"] = {"station": FEUER_STATION, "wbi": wbi, "glfi": glfi, "tage": tage or tage2,
                        "stand": jetzt.strftime("%d.%m. %H:%M")}
        print(f"Feuer {FEUER_STATION}: WBI={wbi} GLFI={glfi} Tage={tage or tage2}")
    except Exception as e:
        fehler.append(f"Feuerindex: {e}")
        out["feuer"] = alt.get("feuer")

    try:
        liste, tage = alle_feuerstationen()
        if out["feuer"] is None:
            out["feuer"] = {"station": FEUER_STATION, "wbi": [], "glfi": [], "tage": tage, "stand": jetzt.strftime("%d.%m. %H:%M")}
        out["feuer"]["stationen"] = liste
        out["feuer"]["tage"] = out["feuer"].get("tage") or tage
    except Exception as e:
        fehler.append(f"Feuerstationen: {e}")

    try:
        out["pollen"] = kompakt_pollen(json.loads(hole(URL_POLLEN)))
        print(f"Pollen: {len(out['pollen']['regionen'])} Regionen, Stand {out['pollen']['stand']}")
    except Exception as e:
        fehler.append(f"Pollen: {e}")
        out["pollen"] = alt.get("pollen")

    try:
        out["bio"] = kompakt_bio(json.loads(hole(URL_BIO)))
        print(f"Biowetter: {len(out['bio']['zonen'])} Gebiete, Stand {out['bio']['stand']}")
    except Exception as e:
        fehler.append(f"Biowetter: {e}")
        out["bio"] = alt.get("bio")

    os.makedirs(os.path.dirname(ZIEL), exist_ok=True)
    with open(ZIEL, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    for m in fehler:
        print("WARNUNG", m, file=sys.stderr)
    print("Geschrieben:", os.path.normpath(ZIEL))


if __name__ == "__main__":
    main()
