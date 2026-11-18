# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "numcodecs", "pillow", "contourpy", "timezonefinder"]
# ///
"""Weltkarte der Dungeon-Zugänge mit dem Wetter beim Kollaps (Daten bauen).
(Builds the web map data: ERA5 weather at the collapse plus the entrance CSVs from zugaenge/. See README.md.)

Kollaps: Dienstag, 3. Januar 2023, 02:23 PST = 10:23 UTC (Wiki „Transformation“; das Jahr nennen die
Bücher nicht, 2023 ist das wahrscheinlichste). Wetter aus ERA5 (ECMWF/Copernicus, 0,25°, stündlich) über
Googles öffentliches ARCO-ERA5-Zarr; Momentanwerte linear zwischen 10 und 11 UTC, Niederschlag = Summe 10–11 UTC.

    uv run bauen.py [ordner]   (Ordner mit dungeon_zugaenge_<Modell>.csv, Standard zugaenge/, siehe dungeon_zugaenge.py)

Schreibt nach web/daten/, ERA5-Rohdaten liegen in cache/ (nicht im Git).
Ansehen: python3 -m http.server 8790 --directory web  →  http://127.0.0.1:8790
"""

import gzip
import json
import math
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import contourpy
import numcodecs
import numpy as np
from PIL import Image

HIER = Path(__file__).resolve().parent
CACHE = HIER / "cache"
AUS = HIER / "web" / "daten"
ORDNER = Path(sys.argv[1]) if len(sys.argv) > 1 else HIER / "zugaenge"
VERTEILUNGEN = {  # Reihenfolge = Knöpfe in der Karte
    "H": {"de": "Hybrid (H)", "en": "Hybrid (H)"},
    "D": {"de": "Vielfalt (D)", "en": "Diversity (D)"},
}
ZAHLEN = ["siedlung_pop", "zugaenge_siedlung", "umkreis_pop", "dichte", "klasse"]

BASIS = "https://storage.googleapis.com/gcp-public-data-arco-era5/ar/full_37-1h-0p25deg-chunk-1.zarr-v3"
KOLLAPS = datetime(2023, 1, 3, 10, 23, tzinfo=timezone.utc)
STUNDE = int((datetime(2023, 1, 3, 10, tzinfo=timezone.utc) - datetime(1900, 1, 1, tzinfo=timezone.utc)).total_seconds() // 3600)
W = KOLLAPS.minute / 60  # Anteil 11 UTC
NY, NX = 721, 1440  # Breite 90 … −90, Länge 0 … 359,75
ZMAX = 4  # Kacheln z0–z4 (0,088°/px, feiner als das 0,25°-Raster); MapLibre vergrößert darüber linear


# ---------------------------------------------------------------- ERA5

def lade(var, idx):
    CACHE.mkdir(parents=True, exist_ok=True)
    datei = CACHE / f"{var}_{idx}.blosc"
    if not datei.exists():
        url = f"{BASIS}/{var}/{idx}.0.0"
        print("  lade", var, idx)
        with urllib.request.urlopen(url, timeout=120) as r:
            datei.write_bytes(r.read())
    roh = numcodecs.Blosc().decode(datei.read_bytes())
    return np.nan_to_num(np.frombuffer(roh, "<f4").reshape(NY, NX).astype(np.float64))


def momentan(var):
    return lade(var, STUNDE) * (1 - W) + lade(var, STUNDE + 1) * W


def felder():
    print("ERA5 …")
    t2m = momentan("2m_temperature") - 273.15
    td = momentan("2m_dewpoint_temperature") - 273.15
    rh = 100 * np.exp(17.625 * td / (243.04 + td)) / np.exp(17.625 * t2m / (243.04 + t2m))
    tcc = momentan("total_cloud_cover") * 100
    u = momentan("10m_u_component_of_wind")
    v = momentan("10m_v_component_of_wind")
    boe = momentan("instantaneous_10m_wind_gust")
    msl = momentan("mean_sea_level_pressure") / 100
    sd = momentan("snow_depth")  # m Wasseräquivalent
    rsn = momentan("snow_density")
    schnee = np.where(rsn > 50, sd * 1000 / np.maximum(rsn, 50), 0) * 100  # cm
    # Akkumulationen gelten für die Stunde bis zum Zeitstempel → 11 UTC = 10–11 UTC
    tp = lade("total_precipitation", STUNDE + 1) * 1000  # mm/h
    sf = lade("snowfall", STUNDE + 1) * 1000
    art = lade("precipitation_type", STUNDE).round()  # 10 UTC liegt näher
    art = np.where(art == 0, lade("precipitation_type", STUNDE + 1).round(), art)
    art = np.where((art == 0) & (tp > 0), np.where(sf > tp * 0.5, 5, 1), art)
    art = np.where(tp > 0, art, 0)
    return dict(t2m=t2m, rh=np.clip(rh, 0, 100), tcc=np.clip(tcc, 0, 100), u=u, v=v, boe=boe, msl=msl,
                schnee=np.clip(schnee, 0, 6000), tp=np.clip(tp, 0, 600), art=art)


# ---------------------------------------------------------------- Sonne

def sonne(zeit):
    """Unter-Sonnen-Punkt (Breite, Länge) nach den NOAA-Näherungen."""
    n = zeit.timestamp() / 86400 + 2440587.5 - 2451545.0
    L = (280.460 + 0.9856474 * n) % 360
    g = math.radians((357.528 + 0.9856003 * n) % 360)
    lam = math.radians(L + 1.915 * math.sin(g) + 0.020 * math.sin(2 * g))
    eps = math.radians(23.439 - 0.0000004 * n)
    ra = math.degrees(math.atan2(math.cos(eps) * math.sin(lam), math.cos(lam)))
    dek = math.degrees(math.asin(math.sin(eps) * math.sin(lam)))
    gmst = (18.697374558 + 24.06570982441908 * n) % 24 * 15
    lon = (ra - gmst + 540) % 360 - 180
    return dek, lon


def sonnenhoehe(lat, lon, dek, slon):
    la, d = np.radians(lat), math.radians(dek)
    h = np.radians(lon - slon)
    return np.degrees(np.arcsin(np.sin(la) * math.sin(d) + np.cos(la) * math.cos(d) * np.cos(h)))


# ---------------------------------------------------------------- Farben (Stopps werden auch für die Legende exportiert)

FARBEN = {
    "temperatur": {"titel": "Temperatur 2 m", "einheit": "°C", "stopps": [
        [-40, [45, 0, 85, 255]], [-30, [95, 35, 165, 255]], [-20, [60, 75, 215, 255]], [-10, [55, 150, 240, 255]],
        [-2, [150, 215, 250, 255]], [0, [225, 240, 250, 255]], [2, [190, 235, 185, 255]], [10, [115, 200, 95, 255]],
        [15, [225, 220, 75, 255]], [20, [250, 170, 50, 255]], [25, [240, 110, 40, 255]], [30, [210, 40, 40, 255]],
        [40, [125, 0, 40, 255]]]},
    "wolken": {"titel": "Bewölkung", "einheit": "%", "stopps": [
        [0, [235, 240, 245, 0]], [20, [235, 240, 245, 40]], [50, [235, 240, 245, 110]], [80, [240, 243, 247, 175]],
        [100, [245, 247, 250, 215]]]},
    "regen": {"titel": "Regen", "einheit": "mm/h", "stopps": [
        [0.03, [120, 180, 255, 0]], [0.1, [120, 180, 255, 110]], [0.5, [80, 150, 255, 170]], [1, [55, 120, 250, 200]],
        [4, [30, 75, 225, 225]], [10, [140, 60, 220, 235]], [30, [230, 60, 160, 245]]]},
    "schneefall": {"titel": "Schneefall", "einheit": "mm/h", "stopps": [
        [0.03, [235, 240, 255, 0]], [0.1, [235, 240, 255, 130]], [0.5, [215, 225, 255, 185]], [1, [185, 200, 255, 215]],
        [3, [160, 150, 255, 235]], [8, [200, 110, 255, 245]]]},
    "eisregen": {"titel": "Gefrierender Regen", "einheit": "mm/h", "stopps": [
        [0.03, [255, 110, 180, 0]], [0.1, [255, 110, 180, 140]], [1, [245, 70, 150, 210]], [5, [220, 30, 110, 240]]]},
    "mischung": {"titel": "Schneeregen, Eiskörner", "einheit": "mm/h", "stopps": [
        [0.03, [255, 185, 90, 0]], [0.1, [255, 185, 90, 140]], [1, [250, 150, 60, 210]], [5, [235, 110, 30, 240]]]},
    "wind": {"titel": "Wind 10 m", "einheit": "km/h", "stopps": [
        [0, [50, 80, 160, 0]], [10, [60, 120, 200, 70]], [25, [60, 190, 160, 140]], [40, [230, 220, 80, 175]],
        [60, [240, 140, 40, 200]], [80, [220, 50, 50, 215]], [110, [200, 40, 200, 230]]]},
    "schnee": {"titel": "Schneedecke", "einheit": "cm", "stopps": [
        [0.5, [230, 240, 255, 0]], [1, [230, 240, 255, 120]], [10, [205, 222, 255, 185]], [30, [155, 185, 250, 215]],
        [100, [105, 125, 235, 230]], [300, [95, 60, 200, 240]]]},
    "nacht": {"titel": "Tag und Nacht", "einheit": "° Sonnenhöhe", "stopps": [
        [-18, [6, 10, 34, 150]], [-12, [6, 10, 34, 135]], [-6, [8, 14, 44, 105]], [0, [12, 20, 60, 45]], [3, [12, 20, 60, 0]]]},
}


def einfaerben(werte, stopps):
    x = np.array([s[0] for s in stopps], float)
    c = np.array([s[1] for s in stopps], float)
    return np.stack([np.interp(werte, x, c[:, k]) for k in range(4)], axis=-1)


# ---------------------------------------------------------------- Abtasten

def bilinear(f, lat, lon):
    r = np.clip((90 - lat) / 0.25, 0, NY - 1.000001)
    c = (lon % 360) / 0.25
    r0 = np.floor(r).astype(int)
    c0 = np.floor(c).astype(int) % NX
    c1 = (c0 + 1) % NX
    fr, fc = r - r0, c - np.floor(c)
    oben = f[r0, c0] * (1 - fc) + f[r0, c1] * fc
    unten = f[r0 + 1, c0] * (1 - fc) + f[r0 + 1, c1] * fc
    return oben * (1 - fr) + unten * fr


def naechster(f, lat, lon):
    r = np.clip(np.rint((90 - lat) / 0.25).astype(int), 0, NY - 1)
    c = np.rint((lon % 360) / 0.25).astype(int) % NX
    return f[r, c]


def kachel_gitter(z, x, y, n=256):
    i = (np.arange(n) + 0.5) / n
    gx = (x + i) / 2 ** z
    gy = (y + i) / 2 ** z
    lon = gx * 360 - 180
    lat = np.degrees(np.arctan(np.sinh(np.pi * (1 - 2 * gy))))
    return np.meshgrid(lat, lon, indexing="ij")


def kacheln(F, dek, slon):
    print("Kacheln …")
    wind = np.hypot(F["u"], F["v"]) * 3.6
    regen_art = {"regen": [1], "schneefall": [5, 6], "eisregen": [3, 12], "mischung": [7, 8]}
    for z in range(ZMAX + 1):
        for x in range(2 ** z):
            for y in range(2 ** z):
                lat, lon = kachel_gitter(z, x, y)
                bilder = {
                    "temperatur": einfaerben(bilinear(F["t2m"], lat, lon), FARBEN["temperatur"]["stopps"]),
                    "wolken": einfaerben(bilinear(F["tcc"], lat, lon), FARBEN["wolken"]["stopps"]),
                    "wind": einfaerben(bilinear(wind, lat, lon), FARBEN["wind"]["stopps"]),
                    "schnee": einfaerben(bilinear(F["schnee"], lat, lon), FARBEN["schnee"]["stopps"]),
                    "nacht": einfaerben(sonnenhoehe(lat, lon, dek, slon), FARBEN["nacht"]["stopps"]),
                }
                tp = bilinear(F["tp"], lat, lon)
                art = naechster(F["art"], lat, lon)
                nied = np.zeros(lat.shape + (4,))
                for name, codes in regen_art.items():
                    maske = np.isin(art, codes)
                    nied[maske] = einfaerben(tp[maske], FARBEN[name]["stopps"])
                bilder["niederschlag"] = nied
                for name, rgba in bilder.items():
                    ziel = AUS / "kacheln" / name / str(z) / str(x)
                    ziel.mkdir(parents=True, exist_ok=True)
                    Image.fromarray(rgba.round().astype(np.uint8), "RGBA").save(ziel / f"{y}.png", compress_level=6)
        print("  z", z)


# ---------------------------------------------------------------- Linien (Isobaren, 0-°C-Linie, Tag-Nacht-Grenze)

def glaetten(f, sigma):
    r = int(3 * sigma)
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / sigma) ** 2)
    k /= k.sum()
    g = np.apply_along_axis(lambda z: np.convolve(np.concatenate([z[-r:], z, z[:r]]), k, "valid"), 1, f)
    p = np.pad(g, ((r, r), (0, 0)), mode="edge")
    return np.apply_along_axis(lambda z: np.convolve(z, k, "valid"), 0, p)


def auf_180(f):
    """0 … 359,75 → −180 … 180 (Spalte 180 = −180 doppelt, damit die Linien an der Datumsgrenze schließen)."""
    g = np.roll(f, NX // 2, axis=1)
    return np.concatenate([g, g[:, :1]], axis=1)


def linien(f, stufen, eigenschaft, schritt=1, ndp=2):
    lon = np.arange(NX + 1)[::schritt] * 0.25 - 180
    lat = 90 - np.arange(NY)[::schritt] * 0.25
    g = auf_180(f)[::schritt, ::schritt]
    gen = contourpy.contour_generator(lon, lat, g)
    feats = []
    for s in stufen:
        for seg in gen.lines(s):
            if len(seg) < 4:
                continue
            seg = seg[np.abs(seg[:, 1]) <= 85.5]
            if len(seg) < 4:
                continue
            feats.append({"type": "Feature", "properties": {eigenschaft: s},
                          "geometry": {"type": "LineString", "coordinates": np.round(seg, ndp).tolist()}})
    return {"type": "FeatureCollection", "features": feats}


def druckzentren(msl):
    """Hochs und Tiefs: Extrem im Umkreis von ~10° und mindestens 4 hPa Abstand zum Ring darum."""
    g = auf_180(glaetten(msl, 4))[::4, ::4][:, :-1]  # 1°-Raster, −180 … 179
    ny, nx = g.shape
    r = 10
    pad = np.pad(g, ((r, r), (0, 0)), mode="edge")
    pad = np.concatenate([pad[:, -r:], pad, pad[:, :r]], axis=1)
    mx = np.full(g.shape, -np.inf)
    mn = np.full(g.shape, np.inf)
    ring = np.zeros(g.shape)
    n = 0
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            if dy * dy + dx * dx > r * r:
                continue
            s = pad[r + dy:r + dy + ny, r + dx:r + dx + nx]
            mx = np.maximum(mx, s)
            mn = np.minimum(mn, s)
            if dy * dy + dx * dx >= (r - 2) ** 2:
                ring += s
                n += 1
    ring /= n
    feats = []
    for typ, maske in (("H", (g >= mx) & (g - ring >= 4)), ("T", (g <= mn) & (ring - g >= 4))):
        for iy, ix in zip(*np.nonzero(maske)):
            iy, ix = int(iy), int(ix)
            lat = 90 - iy
            if abs(lat) > 80:
                continue
            feats.append({"type": "Feature", "properties": {"typ": typ, "hpa": int(round(g[iy, ix]))},
                          "geometry": {"type": "Point", "coordinates": [ix - 180, lat]}})
    return {"type": "FeatureCollection", "features": feats}


# ---------------------------------------------------------------- Raster für Mauszeiger und Zugänge

RASTER = [  # Name, Typ, Faktor (gespeichert = Wert * Faktor)
    ("t2m", "<i2", 10), ("rh", "u1", 1), ("tcc", "u1", 1), ("tp", "<u2", 100), ("art", "u1", 1),
    ("u", "<i2", 100), ("v", "<i2", 100), ("boe", "<u2", 100), ("schnee", "<u2", 1), ("msl", "<u2", 10),
]


def raster_schreiben(F):
    teile, kopf, pos = [], [], 0
    for name, typ, faktor in RASTER:
        a = np.rint(F[name] * faktor).astype(typ)
        b = a.tobytes()
        kopf.append({"name": name, "typ": typ, "faktor": faktor, "start": pos})
        pad = (-len(b)) % 4
        teile.append(b + b"\0" * pad)
        pos += len(b) + pad
    (AUS / "wetter.bin.gz").write_bytes(gzip.compress(b"".join(teile), 6, mtime=0))  # ohne Zeitstempel: gleiche Daten = gleiche Datei
    return kopf


# ---------------------------------------------------------------- Zugänge

def zugaenge(modell, csv_pfad, tf):
    import csv
    with csv_pfad.open(encoding="utf-8") as f:
        zeilen = list(csv.DictReader(f))
    zonen, zone_idx, tz = [], {}, []
    for z in zeilen:
        lat, lon = float(z["lat"]), float(z["lon"])
        name = tf.timezone_at(lng=lon, lat=lat) or f"Etc/GMT{-round(lon / 15):+d}"
        if name not in zone_idx:
            versatz = KOLLAPS.astimezone(ZoneInfo(name)).utcoffset().total_seconds() / 60
            zone_idx[name] = len(zonen)
            zonen.append([name, int(versatz)])
        tz.append(zone_idx[name])
    daten = {
        "lat": [round(float(z["lat"]), 5) for z in zeilen],
        "lon": [round(float(z["lon"]), 5) for z in zeilen],
        "name": [z["name"] for z in zeilen],
        "cc": [z["cc"] for z in zeilen],
        "tz": tz,
        "zonen": zonen,
        "quelle": csv_pfad.name,
    }
    if "region" in zeilen[0]:
        paare = sorted({(z["region"], z.get("region_en") or z["region"]) for z in zeilen})
        r_idx = {r: i for i, r in enumerate(paare)}
        daten["regionen"] = [list(r) for r in paare]  # [deutsch, englisch]
        daten["region"] = [r_idx[(z["region"], z.get("region_en") or z["region"])] for z in zeilen]
        for k in ZAHLEN:
            daten[k] = [int(float(z[k])) for z in zeilen]
        daten["abstand_km"] = [float(z["abstand_km"]) for z in zeilen]
    (AUS / f"zugaenge_{modell}.json").write_text(json.dumps(daten, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"  {modell}: {len(zeilen)} Zugänge, {len(zonen)} Zeitzonen")


def alle_zugaenge():
    from timezonefinder import TimezoneFinder
    print("Zugänge …")
    tf = TimezoneFinder()
    da = []
    for modell, titel in VERTEILUNGEN.items():
        pfad = ORDNER / f"dungeon_zugaenge_{modell}.csv"
        if pfad.exists():
            zugaenge(modell, pfad, tf)
            da.append({"modell": modell, "titel": titel})
    if not da:
        raise SystemExit(f"Keine dungeon_zugaenge_<Modell>.csv in {ORDNER}")
    return da


def schreibe_json(name, obj):
    (AUS / name).write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def main():
    AUS.mkdir(parents=True, exist_ok=True)
    F = felder()
    dek, slon = sonne(KOLLAPS)
    print(f"Sonne über {dek:.2f}°, {slon:.2f}°")
    verteilungen = alle_zugaenge()
    kopf = raster_schreiben(F)
    print("Linien …")
    schreibe_json("isobaren.geojson", linien(glaetten(F["msl"], 2), list(range(940, 1064, 4)), "hpa", schritt=2))
    schreibe_json("druckzentren.geojson", druckzentren(F["msl"]))
    schreibe_json("nullgrad.geojson", linien(glaetten(F["t2m"], 1.5), [0], "grad", schritt=2))
    lat = np.linspace(90, -90, NY)[:, None]
    lon = (np.arange(NX) * 0.25)[None, :]
    schreibe_json("terminator.geojson", linien(sonnenhoehe(lat, lon, dek, slon), [0], "grad", schritt=4))
    schreibe_json("wetter.json", {
        "kollaps": KOLLAPS.isoformat(), "sonne": {"dek": dek, "lon": slon}, "ny": NY, "nx": NX,
        "raster": kopf, "farben": FARBEN, "verteilungen": verteilungen,
        "quelle": "ERA5 (Copernicus Climate Change Service/ECMWF) via ARCO-ERA5 (Google Research)",
    })
    kacheln(F, dek, slon)
    print("fertig →", AUS)


if __name__ == "__main__":
    main()
