# /// script
# requires-python = ">=3.11,<3.13"
# dependencies = ["numpy", "pandas", "rasterio", "scipy", "matplotlib", "pyshp", "shapely"]
# ///
"""
World-Dungeon-Zugänge v3: 150.000 Zugänge auf Basis des GHSL-Bevölkerungsrasters.
(World dungeon entrances: 150,000 stairwells placed on the GHSL population grid. See README.md.)

Neu in v3 (für die Weltkarte in web/):
  Modell D „Vielfalt“: erst Regionen (gleich große Quadrate, --d-zelle km), dann Siedlungen darin.
       Region k bekommt N · R_k^γ / Σ R^γ (γ = --vielfalt, R_k = Einwohner der Region), innerhalb der Region
       nach Pop^0,85. γ < 1 dämpft Ballungsräume und gibt dünn besiedelten Gegenden (Grönland, Alaska,
       Lofoten …) mehr Zugänge. Siedlungen schon ab Dorf (Klasse 13) und --d-schwelle Einwohnern.
       Eigene Siedlungsliste und eigener Zufall, H bleibt dadurch genau wie in v2.
  CSV-Zusatzspalten je Zugang: region / region_en (Natural Earth), siedlung_pop, zugaenge_siedlung,
       umkreis_pop (9 × 9 km um den Zugang), dichte (Einwohner der 1-km-Zelle), klasse (GHSL-SMOD), abstand_km.
  Aufruf für die Weltkarte (lädt die Quellen nach cache/quellen, schreibt CSVs und Karten nach zugaenge/):
       uv run dungeon_zugaenge.py

Daten (JRC / EU-Kommission, 1 km, Mollweide, Stand 2025):
  GHS-POP   Einwohner je km²-Zelle
  GHS-SMOD  Siedlungsklasse je Zelle: 30 Stadtzentrum, 23/22 Stadtcluster, 21 Vorort, 13 Dorf, 12/11 ländlich
  GeoNames  nur für Ortsnamen und Länderkürzel

Ablauf:
  1. Siedlungen = zusammenhängende Zellen mit Klasse >= --min-klasse (ohne Vororte, die würden alles verketten)
  2. Einzugsgebiet: übrige Bevölkerung geht an die nächste Siedlung im Umkreis von --einzug km
  3. Modelle (auf Siedlungen inkl. Einzugsgebiet, ab 10k):
       B proportional | C ~ Wurzel | H Sockel 0,25 + Pop^0,85
     optional China-Bug: Gewicht chinesischer Siedlungen × --china
  4. Gedämpfter Zufall: gerundeter Fixanteil (1-z)·λ + Poisson(z·λ)
  5. Jeder Zugang bekommt Koordinaten: 1-km-Zelle innerhalb der Siedlung nach Einwohnern, darin ein 100-m-Feld nach
     dessen Einwohnern (GHS-POP 100 m, 5,3 GB; --grob = alte Streuung ±500 m ohne 100-m-Raster)

Aufruf:
  uv run dungeon_zugaenge.py [--daten cache/quellen] [--seed 42] [--zufall 0.25] [--china 1.0]
         [--min-klasse 22] [--einzug 25] [--modell H] [--karten zugaenge] [--regionen "Tokyo,Lagos"]
         [--vielfalt 0.45] [--d-zelle 100] [--d-schwelle 1000] [--d-klasse 13]
"""
import argparse
import shutil
import urllib.request
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
from rasterio.warp import transform as reproj
from rasterio.windows import Window
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from scipy.spatial import cKDTree

N_ZUGAENGE = 150_000
SCHWELLE = 10_000
SIEDLUNGSKLASSEN = (13, 22, 23, 30)  # werden in voller Auflösung gehalten
X0, Y0, ZELLE = -18_041_000, 9_000_000, 1000  # Raster-Ursprung (Mollweide, Meter)
BLOCK, AGG, GROB = 1000, 5, 50  # Lesezeilen, Einzugs-Aggregation (km), Weltkarten-Raster (km)
MOLL = "ESRI:54009"
GHSL = "https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/GHSL"
QUELLEN = {
    "pop": f"{GHSL}/GHS_POP_GLOBE_R2023A/GHS_POP_E2025_GLOBE_R2023A_54009_1000/V1-0/GHS_POP_E2025_GLOBE_R2023A_54009_1000_V1_0.zip",
    "pop100": f"{GHSL}/GHS_POP_GLOBE_R2023A/GHS_POP_E2025_GLOBE_R2023A_54009_100/V1-0/GHS_POP_E2025_GLOBE_R2023A_54009_100_V1_0.zip",
    "smod": f"{GHSL}/GHS_SMOD_GLOBE_R2023A/GHS_SMOD_E2025_GLOBE_R2023A_54009_1000/V2-0/GHS_SMOD_E2025_GLOBE_R2023A_54009_1000_V2_0.zip",
    "geonames": "https://download.geonames.org/export/dump/cities500.zip",
    "regionen": "https://naciscdn.org/naturalearth/10m/cultural/ne_10m_admin_1_states_provinces.zip",
}
STUFEN = [0, 10_000, 100_000, 500_000, 1_000_000, 5_000_000, np.inf]
STUFEN_NAMEN = ["<10k", "10k–100k", "100k–500k", "500k–1 Mio.", "1–5 Mio.", ">5 Mio."]
MODELLE = ["B", "C", "H"]
H_SOCKEL, H_EXPONENT = 0.25, 0.85  # Hybrid: Grundausstattung je Siedlung + leicht sublinear
KLASSEN = {30: "Stadtzentrum", 23: "dichte Stadt", 22: "Kleinstadt", 21: "Vorort", 13: "Dorf",
           12: "ländlich", 11: "sehr dünn besiedelt", 10: "Wasser"}


# ---------- Daten laden ----------

def hole(daten: Path, art: str) -> Path:
    """Lädt eine Quelle (falls nötig) und gibt den Pfad der entpackten Datei zurück."""
    muster = {"pop": "GHS_POP_*_54009_1000_*.tif", "pop100": "GHS_POP_*_54009_100_*.tif", "smod": "GHS_SMOD_*.tif",
              "geonames": "cities500.txt", "regionen": "ne_10m_admin_1_states_provinces.shp"}[art]
    treffer = sorted(daten.glob(muster))
    if not treffer:
        daten.mkdir(parents=True, exist_ok=True)
        print(f"Lade {art} …")
        zip_pfad = daten / f"{art}.zip"  # auf Platte statt im Speicher (100-m-Raster: 5,3 GB)
        with urllib.request.urlopen(QUELLEN[art]) as r, open(zip_pfad, "wb") as f:
            shutil.copyfileobj(r, f, 1 << 24)
        with zipfile.ZipFile(zip_pfad) as z:
            z.extractall(daten, [n for n in z.namelist() if n.endswith((".tif", ".txt", ".shp", ".shx", ".dbf", ".prj", ".cpg"))])
        zip_pfad.unlink()
        treffer = sorted(daten.glob(muster))
    return treffer[0]


def lese_raster(daten: Path) -> dict:
    """Liest POP+SMOD blockweise. Siedlungszellen bleiben 1 km, Rest wird auf 5 km summiert. Ergebnis wird gecacht."""
    cache = daten / "ghsl_cache.npz"
    if cache.exists():
        return dict(np.load(cache))

    teile = {k: [] for k in ("s_key", "s_pop", "s_cls", "r_row", "r_col", "r_pop")}
    with rasterio.open(hole(daten, "pop")) as rp, rasterio.open(hole(daten, "smod")) as rs:
        H, W = rp.shape
        Wp = -(-W // GROB) * GROB
        land, pop50 = [], []
        for r0 in range(0, H, BLOCK):
            n = min(BLOCK, H - r0)
            win = Window(0, r0, W, n)
            p = rp.read(1, window=win).astype(np.float32)
            p[p < 0] = 0
            s = rs.read(1, window=win)

            m = np.isin(s, SIEDLUNGSKLASSEN)
            rr, cc = np.nonzero(m)
            teile["s_key"].append((rr + r0).astype(np.int64) * W + cc)
            teile["s_pop"].append(p[m])
            teile["s_cls"].append(s[m].astype(np.int8))

            rest = np.pad(np.where(m, 0, p), ((0, 0), (0, Wp - W)))
            a = rest.reshape(n // AGG, AGG, Wp // AGG, AGG).sum((1, 3))
            br, bc = np.nonzero(a)
            teile["r_row"].append(br + r0 // AGG)
            teile["r_col"].append(bc)
            teile["r_pop"].append(a[br, bc])

            pp = np.pad(p, ((0, 0), (0, Wp - W)))
            pop50.append(pp.reshape(n // GROB, GROB, Wp // GROB, GROB).sum((1, 3)))
            ll = np.pad(s >= 11, ((0, 0), (0, Wp - W)))
            land.append(ll.reshape(n // GROB, GROB, Wp // GROB, GROB).any((1, 3)))

    d = {k: np.concatenate(v) for k, v in teile.items()}
    d.update(W=np.int64(W), H=np.int64(H), land50=np.vstack(land), pop50=np.vstack(pop50))
    np.savez(cache, **d)
    return d


def lade_orte(daten: Path, W: int) -> pd.DataFrame:
    """GeoNames-Orte mit Mollweide-Koordinaten und Rasterschlüssel."""
    cols = ["id", "name", "ascii", "alt", "lat", "lon", "fclass", "fcode", "cc", "cc2",
            "a1", "a2", "a3", "a4", "pop", "elev", "dem", "tz", "mod"]
    o = pd.read_csv(hole(daten, "geonames"), sep="\t", names=cols, usecols=["name", "lat", "lon", "fcode", "cc", "pop"],
                    quoting=3, keep_default_na=False)
    o = o[~o.fcode.isin({"PPLX", "PPLH", "PPLQ", "PPLW", "PPLCH"})].reset_index(drop=True)
    o["x"], o["y"] = reproj("EPSG:4326", MOLL, o.lon.tolist(), o.lat.tolist())
    o["key"] = ((Y0 - o.y) // ZELLE).astype(np.int64) * W + ((o.x - X0) // ZELLE).astype(np.int64)
    return o


# ---------- Siedlungen ----------

def zell_xy(key: np.ndarray, W: int) -> np.ndarray:
    """Rasterschlüssel → Mollweide-Koordinaten der Zellmitte."""
    return np.c_[X0 + (key % W + 0.5) * ZELLE, Y0 - (key // W + 0.5) * ZELLE]


def siedlungen(d: dict, orte: pd.DataFrame, min_klasse: int, einzug_km: float):
    """Labelt Siedlungen, ordnet Einzugsgebiete zu, benennt sie. Gibt (zellen, einheiten, abseits_pop) zurück."""
    W = int(d["W"])
    ist = d["s_cls"] >= min_klasse
    key, pop = d["s_key"][ist], d["s_pop"][ist]  # bereits zeilenweise sortiert

    # Zusammenhang über 8er-Nachbarschaft (4 Vorwärts-Richtungen genügen)
    col = key % W
    i_all, j_all = [], []
    for off, ok in ((1, col < W - 1), (W - 1, col > 0), (W, np.ones(len(key), bool)), (W + 1, col < W - 1)):
        nk = key + off
        j = np.searchsorted(key, nk)
        j[j >= len(key)] = 0
        hit = ok & (key[j] == nk)
        i_all.append(np.nonzero(hit)[0])
        j_all.append(j[hit])
    i, j = np.concatenate(i_all), np.concatenate(j_all)
    n_lab, lab = connected_components(coo_matrix((np.ones(len(i)), (i, j)), shape=(len(key),) * 2), directed=False)
    zellen = pd.DataFrame({"key": key, "pop": pop, "lab": lab})
    xy = zell_xy(key, W)
    zellen["x"], zellen["y"] = xy[:, 0], xy[:, 1]

    # Einzugsgebiet: 5-km-Blöcke + niedrigklassige Siedlungszellen → nächste Siedlungszelle
    rx = X0 + (d["r_col"] + 0.5) * AGG * ZELLE
    ry = Y0 - (d["r_row"] + 0.5) * AGG * ZELLE
    low = ~ist
    qx = np.r_[rx, zell_xy(d["s_key"][low], W)[:, 0]]
    qy = np.r_[ry, zell_xy(d["s_key"][low], W)[:, 1]]
    qp = np.r_[d["r_pop"], d["s_pop"][low]]
    dist, idx = cKDTree(xy).query(np.c_[qx, qy], distance_upper_bound=einzug_km * 1000, workers=-1)
    drin = np.isfinite(dist)
    einzug = np.bincount(lab[idx[drin]], weights=qp[drin], minlength=n_lab)

    e = pd.DataFrame({"kern_pop": np.bincount(lab, weights=pop, minlength=n_lab), "einzug_pop": einzug})
    e["pop"] = e.kern_pop + e.einzug_pop
    e["zellen"] = np.bincount(lab, minlength=n_lab)
    spitze = zellen.loc[zellen.groupby("lab")["pop"].idxmax()].set_index("lab")
    e["x"], e["y"] = spitze.x, spitze.y

    # Namen: größter GeoNames-Ort in der Siedlung, sonst nächster Ort (Name nur bis 30 km)
    pos = np.searchsorted(key, orte.key.to_numpy())
    pos[pos >= len(key)] = 0
    treffer = key[pos] == orte.key.to_numpy()
    o = orte[treffer].assign(lab=lab[pos[treffer]]).sort_values("pop", ascending=False).drop_duplicates("lab")
    e["name"], e["cc"] = None, None
    e.loc[o.lab, "name"], e.loc[o.lab, "cc"] = o.name.to_numpy(), o.cc.to_numpy()
    fehlt = e.name.isna().to_numpy()
    dist, nn = cKDTree(orte[["x", "y"]].to_numpy()).query(e.loc[fehlt, ["x", "y"]].to_numpy(), workers=-1)
    e.loc[fehlt, "cc"] = orte.cc.to_numpy()[nn]
    e.loc[fehlt, "name"] = np.where(dist < 30_000, "bei " + orte.name.to_numpy()[nn], "(namenlos)")
    e["stufe"] = pd.cut(e["pop"], STUFEN, labels=STUFEN_NAMEN, right=False)

    abseits = qp[~drin].sum()
    return zellen, e, abseits


# ---------- Modelle & Ziehung ----------

def erwartungswerte(e: pd.DataFrame, china: float) -> pd.DataFrame:
    """λ je Siedlung und Modell, China-Faktor eingerechnet, auf N_ZUGAENGE skaliert."""
    p = e["pop"].to_numpy(float)
    gross = p >= SCHWELLE
    faktor = np.where(e.cc.to_numpy() == "CN", china, 1.0)
    roh = {
        "B": np.where(gross, p, 0),
        "C": np.where(gross, np.sqrt(p), 0),
        "H": np.where(gross, p ** H_EXPONENT, 0),
    }
    for m, w in roh.items():
        w = w * faktor
        if m == "H":  # Sockel je Siedlung, Rest nach Gewicht
            sockel = H_SOCKEL * gross * faktor
            e[m] = sockel + w * (N_ZUGAENGE - sockel.sum()) / w.sum()
        else:
            e[m] = w * N_ZUGAENGE / w.sum()
    return e


def vielfalt(e: pd.DataFrame, gamma: float, zelle_km: float, schwelle: float) -> np.ndarray:
    """Modell D: λ je Siedlung über Regionen-Quadrate (flächentreu), Region ~ Pop^γ, darin ~ Pop^0,85."""
    p = e["pop"].to_numpy(float)
    gross = p >= schwelle
    z = zelle_km * 1000
    region = pd.factorize(pd.Series(((e.x - X0) // z).astype(np.int64) * 100_000 + ((Y0 - e.y) // z).astype(np.int64)))[0]
    r_pop = np.bincount(region, weights=np.where(gross, p, 0))
    r_lam = np.where(r_pop > 0, r_pop, 0) ** gamma
    r_lam *= N_ZUGAENGE / r_lam.sum()
    w = np.where(gross, p ** H_EXPONENT, 0)
    w_sum = np.bincount(region, weights=w)
    return np.where(gross, r_lam[region] * w / np.maximum(w_sum[region], 1e-9), 0)


def ziehe(lam: np.ndarray, z: float, rng: np.random.Generator) -> np.ndarray:
    """Gedämpfter Zufall: stochastisch gerundeter Fixanteil + Poisson-Restanteil."""
    fix = (1 - z) * lam
    basis = np.floor(fix) + (rng.random(len(lam)) < fix - np.floor(fix))
    return (basis + rng.poisson(z * lam)).astype(int)


def platziere(zellen: pd.DataFrame, e: pd.DataFrame, n: np.ndarray, rng: np.random.Generator,
              fein: tuple[Path, int] | None = None) -> pd.DataFrame:
    """Verteilt n[lab] Zugänge je Siedlung auf ihre Zellen (gewichtet nach Einwohnern). Mit fein = (GHS-POP 100 m, W) dann
    auf ein 100-m-Feld der Zelle nach dessen Einwohnern, sonst ±500 m Streuung in der Zelle."""
    z = zellen.sort_values("lab", kind="stable")
    w = z["pop"].to_numpy() + 1e-3  # leere Zellen nicht ganz ausschließen
    cum = np.cumsum(w)
    ende = np.searchsorted(z.lab.to_numpy(), np.arange(len(e)), side="right")
    hi = cum[ende - 1]
    lo = np.r_[0, hi[:-1]]
    lab = np.repeat(np.arange(len(e)), n)
    idx = np.searchsorted(cum, lo[lab] + rng.random(len(lab)) * (hi[lab] - lo[lab]))
    if fein:
        x, y = verfeinern(fein[0], z.key.to_numpy()[idx], fein[1], rng)
    else:
        x = z.x.to_numpy()[idx] + rng.uniform(-500, 500, len(idx))
        y = z.y.to_numpy()[idx] + rng.uniform(-500, 500, len(idx))
    lon, lat = reproj(MOLL, "EPSG:4326", x.tolist(), y.tolist())
    return pd.DataFrame({"lat": np.round(lat, 5), "lon": np.round(lon, 5), "x": x, "y": y, "siedlung": lab,
                         "name": e.name.to_numpy()[lab], "cc": e.cc.to_numpy()[lab]})


def anreichern(daten: Path, zg: pd.DataFrame, e: pd.DataFrame, n: np.ndarray, W: int) -> pd.DataFrame:
    """Zusatzspalten je Zugang: Siedlung, Umkreis (9 × 9 km), Zelle, SMOD-Klasse, Region, Abstand zum nächsten Zugang."""
    zg = zg.copy()
    zg["siedlung_pop"] = np.round(e["pop"].to_numpy()[zg.siedlung], -1).astype(np.int64)
    zg["zugaenge_siedlung"] = n[zg.siedlung]
    zeile = ((Y0 - zg.y) // ZELLE).astype(np.int64).to_numpy()
    spalte = ((zg.x - X0) // ZELLE).astype(np.int64).to_numpy()
    umkreis, dichte, klasse = np.zeros(len(zg)), np.zeros(len(zg)), np.zeros(len(zg), np.int16)
    R, B = 4, 400
    with rasterio.open(hole(daten, "pop")) as rp, rasterio.open(hole(daten, "smod")) as rs:
        H = rp.height
        for r0 in range(0, H, B):
            drin = np.nonzero((zeile >= r0) & (zeile < r0 + B))[0]
            if not len(drin):
                continue
            a, b = max(0, r0 - R), min(H, r0 + B + R)
            p = rp.read(1, window=Window(0, a, W, b - a)).astype(np.float64)
            p[p < 0] = 0
            s = rs.read(1, window=Window(0, r0, W, min(B, H - r0)))
            ii = np.zeros((p.shape[0] + 1, W + 1))
            ii[1:, 1:] = p.cumsum(0).cumsum(1)
            zr, zc = zeile[drin] - a, spalte[drin]
            y0, y1 = np.clip(zr - R, 0, p.shape[0]), np.clip(zr + R + 1, 0, p.shape[0])
            x0, x1 = np.clip(zc - R, 0, W), np.clip(zc + R + 1, 0, W)
            umkreis[drin] = ii[y1, x1] - ii[y0, x1] - ii[y1, x0] + ii[y0, x0]
            dichte[drin] = p[zr, zc]
            klasse[drin] = s[zeile[drin] - r0, zc]
    zg["umkreis_pop"] = np.round(umkreis, -1).astype(np.int64)
    zg["dichte"] = np.round(dichte).astype(np.int64)
    zg["klasse"] = klasse
    zg["region"], zg["region_en"] = regionen(daten, zg.lon.to_numpy(), zg.lat.to_numpy())
    zg["abstand_km"] = np.round(cKDTree(zg[["x", "y"]].to_numpy()).query(zg[["x", "y"]].to_numpy(), k=2)[0][:, 1] / 1000, 1)
    return zg


def regionen(daten: Path, lon: np.ndarray, lat: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Natural-Earth-Verwaltungsregion (Bundesland, Provinz …), deutscher und englischer Name; Küstenpunkte → nächste bis 0,2°."""
    import shapefile
    import shapely
    sf = shapefile.Reader(str(hole(daten, "regionen")), encoding="utf-8")
    recs = sf.records()
    de = np.array([(r["name_de"] or r["name"] or "").strip() for r in recs], dtype=object)
    en = np.array([(r["name_en"] or r["name"] or "").strip() for r in recs], dtype=object)
    baum = shapely.STRtree([shapely.geometry.shape(s.__geo_interface__) for s in sf.shapes()])
    punkte = shapely.points(lon, lat)
    idx = np.full(len(lon), -1)
    i, j = baum.query(punkte, predicate="within")
    idx[i] = j
    rest = np.nonzero(idx < 0)[0]
    if len(rest):
        i, j = baum.query_nearest(punkte[rest], max_distance=0.2)
        idx[rest[i]] = j
    leer = idx < 0
    return np.where(leer, "", de[idx]), np.where(leer, "", en[idx])


def vergleich(alt: pd.DataFrame, neu: pd.DataFrame, namen=("H", "D")):
    """Kennzahlen bisher/neu: Ballung, Länder, abgelegene Gegenden."""
    def kennzahlen(z):
        cc = z.cc.value_counts()
        s = z.groupby(["siedlung"]).size()
        sel = {
            "Grönland": z.cc == "GL", "Island": z.cc == "IS", "Färöer": z.cc == "FO", "Spitzbergen": z.cc == "SJ",
            "Alaska": (z.cc == "US") & (z.lat > 51) & (z.lon < -129),
            "Lofoten/Vesterålen": (z.cc == "NO") & z.lat.between(67.6, 69.4) & z.lon.between(12, 16.5),
            "Nordnorwegen": (z.cc == "NO") & (z.lat > 66), "Mongolei": z.cc == "MN", "Bhutan": z.cc == "BT",
            "Pazifikinseln": z.cc.isin(["FJ", "TO", "WS", "KI", "VU", "SB", "PF", "NC", "FM", "MH", "PW", "TV", "NR", "CK"]),
            "Australien außer 5 Großstädte": (z.cc == "AU") & ~z.name.isin(["Sydney", "Melbourne", "Brisbane", "Perth", "Adelaide"]),
            "Kanada nördl. 55°": (z.cc == "CA") & (z.lat > 55), "Russland östl. 60° O": (z.cc == "RU") & (z.lon > 60),
        }
        k = {"China + Indien": f"{cc.get('CN', 0) + cc.get('IN', 0):,}", "Top-10-Länder": f"{cc.head(10).sum() / len(z):.0%}",
             "Länder mit Zugang": len(cc), "Siedlungen mit Zugang": f"{len(s):,}", "größte Siedlung": int(s.max()),
             "Zugänge in Siedlungen ≥ 50": f"{s[s >= 50].sum() / len(z):.0%}"}
        k.update({n: int(m.sum()) for n, m in sel.items()})
        return k
    a, b = kennzahlen(alt), kennzahlen(neu)
    print(f"\nVergleich {namen[0]} → {namen[1]}:")
    for k in a:
        print(f"  {k:<32} {a[k]!s:>10}  →  {b[k]!s:>10}")
    for name, lat, lon in (("Shanghai", 31.23, 121.47), ("Guangzhou", 23.13, 113.26), ("Delhi", 28.61, 77.21),
                           ("Dhaka", 23.81, 90.41), ("Tokyo", 35.68, 139.69), ("Berlin", 52.52, 13.40)):
        f = lambda z: int(((z.lat - lat) ** 2 + ((z.lon - lon) * np.cos(np.radians(lat))) ** 2 < 0.45 ** 2).sum())
        print(f"  {name + ' ±50 km':<32} {f(alt):>10}  →  {f(neu):>10}")


def vergleichskarte(d: dict, alt: pd.DataFrame, neu: pd.DataFrame, pfad: Path, titel: tuple):
    """Zugänge je 50×50 km nebeneinander (Mollweide), gleiche Farbskala."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import LinearSegmentedColormap, ListedColormap, LogNorm

    blau = LinearSegmentedColormap.from_list("b", ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"])
    flaeche, landfarbe, tinte = "#fcfcfb", "#e6e5e1", "#1f1f1e"
    ny, nx = d["land50"].shape
    ext = [X0, X0 + nx * GROB * ZELLE, Y0 - ny * GROB * ZELLE, Y0]
    ylim = (reproj("EPSG:4326", MOLL, [0], [-56])[1][0], reproj("EPSG:4326", MOLL, [0], [80])[1][0])

    def raster(z):
        g = np.zeros((ny, nx))
        np.add.at(g, (((Y0 - z.y) // (GROB * ZELLE)).astype(int), ((z.x - X0) // (GROB * ZELLE)).astype(int)), 1)
        return g

    gs = [raster(alt), raster(neu)]
    vmax = max(g.max() for g in gs)
    fig, axes = plt.subplots(1, 2, figsize=(18, 5.6), facecolor=flaeche)
    fig.subplots_adjust(left=0.01, right=0.99, top=0.9, bottom=0.12, wspace=0.03)
    for ax, g, t in zip(axes, gs, titel):
        ax.set_facecolor(flaeche)
        ax.imshow(np.where(d["land50"], 1, np.nan), extent=ext, cmap=ListedColormap([landfarbe]), interpolation="nearest")
        im = ax.imshow(np.where(g > 0, g, np.nan), extent=ext, cmap=blau, norm=LogNorm(1, vmax), interpolation="nearest")
        ax.set_title(t, loc="left", color=tinte, fontsize=12)
        ax.set_ylim(*ylim)
        ax.set_xticks([]); ax.set_yticks([])
        for s in ax.spines.values():
            s.set_visible(False)
    cb = fig.colorbar(im, cax=fig.add_axes([0.32, 0.07, 0.36, 0.022]), orientation="horizontal")
    cb.set_label("Zugänge je 50×50 km / entrances per 50×50 km (log) · grau / grey = Land ohne Zugang / land without entrance",
                 color=tinte); cb.outline.set_visible(False)
    fig.savefig(pfad, dpi=130, bbox_inches="tight", facecolor=flaeche)
    plt.close(fig)


def schreibe_csv(zg: pd.DataFrame, pfad: Path):
    spalten = ["lat", "lon", "name", "cc", "region", "region_en", "siedlung_pop", "zugaenge_siedlung", "umkreis_pop", "dichte",
               "klasse", "abstand_km"]
    zg[spalten].to_csv(pfad, index=False)


def verfeinern(pfad: Path, key: np.ndarray, W: int, rng: np.random.Generator) -> tuple[np.ndarray, np.ndarray]:
    """Wählt im 1-km-Feld eines der 100 Felder à 100 m nach dessen Einwohnern (GHS-POP 100 m) und setzt den Zugang
    zufällig hinein. So landen Zugänge zwischen den Häusern statt am Ortsrand im Feld."""
    n = len(key)
    zeile, spalte = key // W, key % W
    u, dx, dy = rng.random(n), rng.random(n), rng.random(n)
    x, y = np.empty(n), np.empty(n)
    ordnung = np.lexsort((spalte, zeile))
    ks = key[ordnung]
    grenzen = np.flatnonzero(np.r_[True, ks[1:] != ks[:-1], True])
    with rasterio.Env(GDAL_CACHEMAX=2048), rasterio.open(pfad) as r:
        t = r.transform
        assert abs(t.a - ZELLE / 10) < 1e-6 and abs(t.c - X0) < 1 and abs(t.f - Y0) < 1, f"100-m-Raster passt nicht: {t}"
        for a, b in zip(grenzen[:-1], grenzen[1:]):
            gruppe = ordnung[a:b]
            zr, zc = int(zeile[gruppe[0]]), int(spalte[gruppe[0]])
            feld = r.read(1, window=Window(zc * 10, zr * 10, 10, 10), boundless=True, fill_value=0).astype(np.float64)
            feld = np.clip(feld, 0, None).ravel()
            if feld.sum() <= 0:
                feld[:] = 1
            j = np.minimum(np.searchsorted(np.cumsum(feld) / feld.sum(), u[gruppe], side="right"), 99)
            sr, sc = np.divmod(j, 10)
            x[gruppe] = X0 + (zc * 10 + sc + dx[gruppe]) * (ZELLE / 10)
            y[gruppe] = Y0 - (zr * 10 + sr + dy[gruppe]) * (ZELLE / 10)
    return x, y


# ---------- Ausgabe ----------

def report(e: pd.DataFrame, zellen: pd.DataFrame, zg: pd.DataFrame, orte: pd.DataFrame, abseits: float,
           modell: str, beispiele: list[str]):
    gesamt = e["pop"].sum() + abseits
    print(f"Siedlungen: {len(e):,} | davon >= 10k (inkl. Einzug): {(e['pop'] >= SCHWELLE).sum():,}")
    print(f"Bevölkerung: {gesamt / 1e9:.2f} Mrd. | in Siedlungskernen {e.kern_pop.sum() / gesamt:.0%}"
          f" | im Einzugsgebiet {e.einzug_pop.sum() / gesamt:.0%} | abseits {abseits / gesamt:.1%}\n")

    rows = []
    for stufe, g in e.groupby("stufe", observed=True):
        row = {"Stufe": stufe, "Siedlungen": len(g), "Bev. Mio.": round(g["pop"].sum() / 1e6)}
        for m in MODELLE:
            row[m] = g[f"{m}_sim"].sum()
            row[f"{m} ohne"] = f"{(g[f'{m}_sim'] == 0).mean():.0%}"
        rows.append(row)
    print("Zugänge je Stufe und Anteil Siedlungen OHNE Zugang:")
    print(pd.DataFrame(rows).set_index("Stufe").to_string())
    print("Summen:", {m: int(e[f"{m}_sim"].sum()) for m in MODELLE}, "\n")

    print("Top 15 Siedlungen:")
    top = e.nlargest(15, "pop").assign(Mio=lambda t: (t["pop"] / 1e6).round(1))
    print(top[["name", "cc", "Mio", "zellen"] + [f"{m}_sim" for m in MODELLE]].to_string(index=False), "\n")

    print(f"Länder-Top 10 (Modell {modell}):")
    print(zg.cc.value_counts().head(10).to_string(), "\n")

    print(f"Beispielorte (Siedlung | Zugänge der Siedlung B/C/H | Modell {modell}: Zugänge im Umkreis 3 km um den Ortskern):")
    zugang_baum = cKDTree(zg[["x", "y"]].to_numpy())
    zellen_baum = cKDTree(zellen[["x", "y"]].to_numpy())
    bsp = orte[orte.name.isin(beispiele)].sort_values("pop", ascending=False).drop_duplicates("name")
    for _, o in bsp.iterrows():
        n3 = len(zugang_baum.query_ball_point([o.x, o.y], 3000))
        s = e.loc[zellen.lab.iat[zellen_baum.query([o.x, o.y])[1]]]  # Siedlung der nächsten Siedlungszelle
        print(f"  {o['name']:<10} → {s['name']:<14} ({s['pop'] / 1e6:5.2f} Mio.)  "
              f"B {s.B_sim:>4}  C {s.C_sim:>4}  H {s.H_sim:>4}  |  3 km: {n3}")


def weltkarte(d: dict, e: pd.DataFrame, pfad: Path, z: float, china: float):
    """2x2 in Mollweide: Bevölkerung (Referenz) + Modelle B, C, H je 50×50-km-Zelle."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import LinearSegmentedColormap, LogNorm, ListedColormap

    blau = LinearSegmentedColormap.from_list("b", ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"])
    orange = LinearSegmentedColormap.from_list("o", ["#fde3d6", "#f6b294", "#eb6834", "#b8461c", "#7a2c0e"])
    flaeche, landfarbe, tinte, tinte2 = "#fcfcfb", "#e6e5e1", "#1f1f1e", "#6b6a66"
    ny, nx = d["land50"].shape
    ext = [X0, X0 + nx * GROB * ZELLE, Y0 - ny * GROB * ZELLE, Y0]
    ylim = (reproj("EPSG:4326", MOLL, [0], [-56])[1][0], reproj("EPSG:4326", MOLL, [0], [75])[1][0])

    def raster(werte):
        r = ((Y0 - e.y) // (GROB * ZELLE)).astype(int)
        c = ((e.x - X0) // (GROB * ZELLE)).astype(int)
        g = np.zeros((ny, nx))
        np.add.at(g, (r, c), werte)
        return g

    fig, axes = plt.subplots(2, 2, figsize=(16, 8.2), facecolor=flaeche)
    fig.subplots_adjust(left=0.01, right=0.99, top=0.9, bottom=0.12, wspace=0.03, hspace=0.14)
    china_txt = f", China-Bug ×{china}" if china != 1 else ""
    panels = [("Bevölkerung 2025 (Referenz)", d["pop50"], orange, LogNorm(100, d["pop50"].max())),
              ("B · proportional", raster(e.B_sim), blau, None), ("C · Wurzel", raster(e.C_sim), blau, None),
              ("H · Hybrid (Sockel + Pop^0,85)", raster(e.H_sim), blau, None)]
    vmax = max(p[1].max() for p in panels[1:])
    bilder = []
    for ax, (titel, g, cmap, norm) in zip(axes.flat, panels):
        ax.set_facecolor(flaeche)
        ax.imshow(np.where(d["land50"], 1, np.nan), extent=ext, cmap=ListedColormap([landfarbe]), interpolation="nearest")
        bilder.append(ax.imshow(np.where(g > 0, g, np.nan), extent=ext, cmap=cmap, norm=norm or LogNorm(1, vmax),
                                interpolation="nearest"))
        ax.set_title(titel, loc="left", color=tinte, fontsize=12)
        ax.set_ylim(*ylim)
        ax.set_xticks([]); ax.set_yticks([])
        for s in ax.spines.values():
            s.set_visible(False)
    for im, pos, label in ((bilder[0], [0.06, 0.06, 0.36, 0.016], "Einwohner je 50×50 km"),
                           (bilder[1], [0.56, 0.06, 0.36, 0.016], "Zugänge je 50×50 km")):
        cb = fig.colorbar(im, cax=fig.add_axes(pos), orientation="horizontal")
        cb.set_label(label + " (log)", color=tinte2); cb.outline.set_visible(False); cb.ax.tick_params(colors=tinte2)
    fig.suptitle(f"150.000 World-Dungeon-Zugänge auf Basis GHSL 2025 (Zufallsanteil z = {z}{china_txt})",
                 color=tinte, fontsize=15, x=0.01, ha="left")
    fig.text(0.01, -0.035, "Grau = Land ohne Zugang. Daten: GHSL POP/SMOD 2025 (JRC), Namen: GeoNames. Mollweide-Projektion (flächentreu).",
             color=tinte2, fontsize=9)
    fig.savefig(pfad, dpi=150, bbox_inches="tight", facecolor=flaeche)
    plt.close(fig)


def regionalkarte(daten: Path, orte: pd.DataFrame, zg: pd.DataFrame, ort: str, modell: str, pfad: Path, r_km=60):
    """Ausschnitt um einen Ort: Bevölkerungsdichte (1 km) + jeder Zugang als Punkt."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import LinearSegmentedColormap, LogNorm

    flaeche, tinte, tinte2, punkt = "#fcfcfb", "#1f1f1e", "#6b6a66", "#256abf"
    grau = LinearSegmentedColormap.from_list("g", ["#f1f0ed", "#c9c7c1", "#8f8d87"])
    from rasterio.crs import CRS
    from rasterio.transform import from_origin
    from rasterio.warp import Resampling, reproject, transform_bounds

    o = orte[orte.name == ort].nlargest(1, "pop").iloc[0]
    r = r_km * 1000
    lokal = CRS.from_proj4(f"+proj=laea +lat_0={o.lat} +lon_0={o.lon} +units=m")  # verzerrungsarm um den Ort
    p = np.zeros((2 * r_km, 2 * r_km), np.float32)
    with rasterio.open(hole(daten, "pop")) as rp:
        win = rp.window(*transform_bounds(lokal, MOLL, -r, -r, r, r, densify_pts=41)).round_offsets().round_lengths()
        reproject(rp.read(1, window=win), p, src_transform=rp.window_transform(win), src_crs=rp.crs, src_nodata=-200,
                  dst_transform=from_origin(-r, r, ZELLE, ZELLE), dst_crs=lokal, resampling=Resampling.average)
    p[p <= 0] = np.nan

    def lokal_km(df):
        x, y = reproj("EPSG:4326", lokal, df.lon.tolist(), df.lat.tolist())
        return np.asarray(x) / 1000, np.asarray(y) / 1000

    fig, ax = plt.subplots(figsize=(9, 9), facecolor=flaeche)
    ax.set_facecolor(flaeche)
    ax.imshow(p, extent=[-r_km, r_km, -r_km, r_km], cmap=grau, norm=LogNorm(80, 20_000), interpolation="nearest")
    band = 2 * r_km / 111  # grober Breitengrad-Vorfilter, exakt dann im lokalen System
    kand = zg[(zg.lat - o.lat).abs() < band]
    px, py = lokal_km(kand)
    drin = (np.abs(px) < r_km) & (np.abs(py) < r_km)
    pts = kand[drin]
    ax.scatter(px[drin], py[drin], s=14, c=punkt, edgecolors=flaeche, linewidths=0.8, zorder=3)
    kand = orte[((orte.lat - o.lat).abs() < band) & (orte["pop"] >= 15_000)]
    qx, qy = lokal_km(kand)
    nah = kand.assign(qx=qx, qy=qy)[(np.abs(qx) < r_km * 0.95) & (np.abs(qy) < r_km * 0.95)]
    gesetzt = []
    for _, q in nah.nlargest(25, "pop").iterrows():
        if len(gesetzt) >= 14 or any(np.hypot(q.qx - x, q.qy - y) < r_km / 6 for x, y in gesetzt):
            continue  # Labels nicht übereinander stapeln
        gesetzt.append((q.qx, q.qy))
        ax.annotate(q["name"], (q.qx, q.qy), xytext=(4, 4), textcoords="offset points",
                    fontsize=9, color=tinte, zorder=4,
                    bbox=dict(boxstyle="round,pad=0.15", fc=flaeche, ec="none", alpha=0.7))
    ax.set_xlim(-r_km, r_km); ax.set_ylim(-r_km, r_km); ax.set_aspect("equal")
    ax.tick_params(colors=tinte2, labelsize=8)
    for s in ax.spines.values():
        s.set_color("#d8d6d0")
    ax.set_xlabel("km", color=tinte2, fontsize=9)
    ax.set_title(f"{ort} ±{r_km} km · {len(pts)} Zugänge (Modell {modell})", loc="left", color=tinte, fontsize=13)
    fig.text(0.125, 0.04, "Punkte = Zugänge, Grau = Einwohnerdichte (1 km², log). Daten: GHSL 2025, GeoNames.",
             color=tinte2, fontsize=8)
    fig.savefig(pfad, dpi=150, bbox_inches="tight", facecolor=flaeche)
    plt.close(fig)


# ---------- Main ----------

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--daten", type=Path, default=Path(__file__).with_name("cache") / "quellen")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--zufall", type=float, default=0.25, help="0 = deterministisch, 1 = reines Poisson")
    ap.add_argument("--china", type=float, default=1.0, help="Gewichtsfaktor für Siedlungen in China (Übersetzer-Bug)")
    ap.add_argument("--min-klasse", type=int, default=22, choices=[13, 22, 23, 30],
                    help="13 = ab Dorf, 22 = ab Kleinstadt-Cluster, 30 = nur Stadtzentren")
    ap.add_argument("--einzug", type=float, default=25, help="max. Einzugsradius in km")
    ap.add_argument("--modell", default="H", choices=MODELLE, help="Modell für Koordinaten/Karten/CSV")
    ap.add_argument("--orte", default="Tokyo,Shanghai,Lagos,Berlin,Munich,New York City,Anchorage,Nuuk,Reykjavík")
    ap.add_argument("--karten", type=Path, default=Path(__file__).with_name("zugaenge"), help="Ordner für Karten + CSV")
    ap.add_argument("--regionen", default="Tokyo,Lagos")
    ap.add_argument("--grob", action="store_true", help="ohne 100-m-Raster platzieren (±500 m in der 1-km-Zelle)")
    ap.add_argument("--vielfalt", type=float, default=0.45, help="Modell D: Exponent γ je Region (1 = proportional)")
    ap.add_argument("--d-zelle", type=float, default=100, help="Modell D: Kantenlänge der Regionen in km")
    ap.add_argument("--d-schwelle", type=float, default=1000, help="Modell D: Mindestgröße einer Siedlung inkl. Einzug")
    ap.add_argument("--d-klasse", type=int, default=13, choices=[13, 22, 23, 30], help="Modell D: Siedlungen ab Klasse")
    a = ap.parse_args()

    d = lese_raster(a.daten)
    orte = lade_orte(a.daten, int(d["W"]))
    zellen, e, abseits = siedlungen(d, orte, a.min_klasse, a.einzug)
    e = erwartungswerte(e, a.china)
    rng = np.random.default_rng(a.seed)
    for m in MODELLE:
        e[f"{m}_sim"] = ziehe(e[m].to_numpy(), a.zufall, rng)
    fein = None if a.grob else (hole(a.daten, "pop100"), int(d["W"]))
    zg = platziere(zellen, e, e[f"{a.modell}_sim"].to_numpy(), rng, fein)

    report(e, zellen, zg, orte, abseits, a.modell, a.orte.split(","))

    # Modell D: eigene Siedlungsliste (ab Dorf) und eigener Zufall, damit die Ziehung oben unverändert bleibt
    zellen_d, e_d, abseits_d = siedlungen(d, orte, a.d_klasse, a.einzug)
    e_d["D"] = vielfalt(e_d, a.vielfalt, a.d_zelle, a.d_schwelle)
    rng_d = np.random.default_rng(a.seed + 1)
    n_d = ziehe(e_d["D"].to_numpy(), a.zufall, rng_d)
    zg_d = platziere(zellen_d, e_d, n_d, rng_d, fein)
    print(f"\nModell D (γ = {a.vielfalt}, Regionen {a.d_zelle:g} km, ab Klasse {a.d_klasse}, ab {a.d_schwelle:,.0f} Einw.):"
          f" {len(e_d):,} Siedlungen, {int(n_d.sum()):,} Zugänge")
    vergleich(zg, zg_d, (a.modell, "D"))

    if a.karten:
        a.karten.mkdir(parents=True, exist_ok=True)
        weltkarte(d, e, a.karten / "dungeon_weltkarte.png", a.zufall, a.china)
        vergleichskarte(d, zg, zg_d, a.karten / "dungeon_vergleich.png",
                        (f"{a.modell} · Hybrid", f"D · Vielfalt / Diversity (γ = {a.vielfalt}, {a.d_zelle:g} km)"))
        for ort in filter(None, a.regionen.split(",")):
            regionalkarte(a.daten, orte, zg, ort, a.modell, a.karten / f"dungeon_region_{ort.lower()}.png")
        W = int(d["W"])
        schreibe_csv(anreichern(a.daten, zg, e, e[f"{a.modell}_sim"].to_numpy(), W), a.karten / f"dungeon_zugaenge_{a.modell}.csv")
        schreibe_csv(anreichern(a.daten, zg_d, e_d, n_d, W), a.karten / "dungeon_zugaenge_D.csv")
        print(f"\nKarten + CSV in: {a.karten}")
