'use strict';
/* Weltkarte der Dungeon-Zugänge mit dem Wetter beim Kollaps / World map of the dungeon entrances with the weather
   at the collapse. Daten / data: ../bauen.py, ../dungeon_zugaenge.py */

const BASIS = location.href.replace(/[#?].*$/, '').replace(/[^/]*$/, '');
const DATEN = BASIS + 'daten/';
const RAD = Math.PI / 180;
const WETTER = ['temperatur', 'wolken', 'niederschlag', 'wind', 'schnee'];
const OPAZITAET = { temperatur: 0.62, wolken: 0.85, niederschlag: 0.95, wind: 0.8, schnee: 0.85, nacht: 1 };
const SCHNEEARTEN = new Set([5, 6, 7, 8]);
const REPO = 'https://github.com/ScumDivision/dcc_entrance_map';

// ------------------------------------------------------------ Sprachen

const SPRACHEN = {
  de: {
    lokal: 'de-DE',
    ost: 'O',
    t: {
      titel: 'Dungeon-Zugänge beim Kollaps',
      datum: 'Dienstag, 3. Januar 2023',
      zeiten: '02:23 PST · 11:23 MEZ · 15:53 Indien · 18:23 Peking',
      einklappen: 'Bedienfeld ein-/ausklappen',
      verteilung: 'Verteilung', suche: 'Ort suchen …', alleLaender: 'Alle Länder',
      wetter: 'Wetter', keins: 'keins', temperatur: 'Temperatur', wolken: 'Bewölkung', niederschlag: 'Niederschlag',
      wind: 'Wind', schnee: 'Schneedecke',
      sZugaenge: 'Zugänge', sNacht: 'Tag und Nacht', sWindfeld: 'Windströmung', sIsobaren: 'Isobaren, Hochs und Tiefs',
      sNullgrad: '0-°C-Linie',
      karte: 'Karte', dunkel: 'Dunkel', hell: 'Hell', satellit: 'Satellit', globus: 'Globus', flach: 'Flach',
      hilfe: 'Ab mittlerer Zoomstufe sind die Zugänge einzeln anklickbar: Siedlung, Bevölkerung, Ortszeit und Wetter. ' +
        'Die Leiste unten zeigt das Wetter unter dem Mauszeiger.',
      modelle: '<b>Hybrid (H)</b>: Siedlungen ab Kleinstadt, Zugänge ~ Einwohner<sup>0,85</sup> plus ein Sockel je Siedlung. ' +
        '<b>Vielfalt (D)</b>: erst bekommen Regionen von 100 × 100 km einen Anteil ~ Einwohner<sup>0,45</sup>, dann die ' +
        'Siedlungen darin, schon ab Dorfgröße. Ballungsräume verlieren etwa 60 %, dünn besiedelte Gegenden gewinnen.',
      wetterInfo: 'Wetter: ERA5-Reanalyse (ECMWF/Copernicus, 0,25° ≈ 28 km), Momentanwerte zwischen 10 und 11 UTC ' +
        'interpoliert, Niederschlag als Summe 10–11 UTC. Zeitpunkt nach Buch 1 (2:23 Uhr PST, Dienstag, 3. Januar); ' +
        'das Jahr nennen die Bücher nicht, 2023 ist das wahrscheinlichste.',
      fan: `Inoffizielles Fanprojekt, nicht verbunden mit Matt Dinniman oder den Verlagen von Dungeon Crawler Carl. ` +
        `Code und Daten: <a href="${REPO}" target="_blank" rel="noopener">GitHub</a>.`,
      quelle: (datei, n, wetter) => `Zugänge: ${datei} (${n}). Bevölkerung: GHSL 2025 (JRC, CC BY 4.0), Namen: ` +
        `GeoNames (CC BY 4.0), Regionen: Natural Earth. Wetter: ${wetter}.`,
      laden: 'Lade Daten …',
      fehlt: e => `Daten fehlen: ${e} – erst „uv run bauen.py“ ausführen.`,
      summe: 'Summe 10–11 UTC',
      weltweit: 'Zugänge weltweit', inLand: land => `Zugänge in ${land}`,
      stat: ['Tageslicht', 'Dämmerung', 'Nacht', 'Frost', 'Niederschlag', 'davon Schnee', 'Schneedecke', 'Sturmböen'],
      mittel: (t, kalt, warm) => `Mittel ${t} °C · kältester ${kalt} · wärmster ${warm}`,
      zugang: 'Zugang', wetterKollaps: 'Wetter beim Kollaps', namenlos: 'Siedlung ohne Ortsnamen',
      siedlungIn: (region, land) => `Siedlung in ${region} (${land})`, namenlosLand: land => `Siedlung ohne Ortsnamen (${land})`,
      namenlosInfo: 'Die Bevölkerungsdaten zeigen hier eine Siedlung, aber das Ortsverzeichnis GeoNames kennt im Umkreis ' +
        'von 30 km keinen Ortsnamen. Oft sind das Goldgräber- oder Flüchtlingslager oder verstreute Weiler.',
      zSiedlung: 'Siedlung', zUmgebung: 'Umgebung', zNaechster: 'Nächster', zOrtszeit: 'Ortszeit',
      siedlung: (pop, n, je) => `${pop} Einw. mit Umland, ${n} ${n === '1' ? 'Zugang' : 'Zugänge'} (≈ ${je} je Zugang)`,
      umgebung: (u, d, k) => `${u} Einw. im Umkreis von 5 km; am Zugang ${d} Einw./km² (${k})`,
      naechster: km => `Zugang in ${km} km`, naechsterNah: 'Zugang weniger als 100 m entfernt',
      ortszeit: (uhr, utc, zone, von, bis) => `${uhr} (${utc}, ${zone}), Treppe offen ${von}–${bis}`,
      wSonne: 'Sonne', wLuft: 'Luft', wHimmel: 'Himmel', wNieder: 'Niederschlag', wWind: 'Wind', wSchnee: 'Schneedecke',
      ueber: g => `${g}° über dem Horizont`, unter: g => `${g}° unter dem Horizont`,
      luft: (t, rh, p) => `${t} °C, Feuchte ${rh} %, ${p} hPa`,
      nieder: (art, mm) => `${art}, ${mm} mm in der Stunde`, spuren: 'Spuren (unter 0,1 mm in der Stunde)', keiner: 'keiner',
      still: 'still', windWert: (k, r, b) => `${k} km/h aus ${r}, Böen ${b} km/h`, windStill: b => `still, Böen ${b} km/h`,
      gletscherKurz: 'Inlandeis/Gletscher', keine: 'keine',
      zeigerWind: 'Wind', zeigerSchnee: 'Schnee',
    },
    arten: { 1: 'Regen', 3: 'gefrierender Regen', 5: 'Schnee', 6: 'nasser Schnee', 7: 'Schneeregen', 8: 'Eiskörner',
      12: 'gefrierender Nieselregen' },
    richtungen: ['N', 'NO', 'O', 'SO', 'S', 'SW', 'W', 'NW'],
    tage: ['So', 'Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa'],
    klassen: { 30: 'Stadtzentrum', 23: 'dichte Stadt', 22: 'Kleinstadt', 21: 'Vorort', 13: 'Dorf', 12: 'ländlich',
      11: 'sehr dünn besiedelt', 10: 'Wasser' },
    himmel: ['klar', 'heiter', 'wolkig', 'stark bewölkt', 'bedeckt'],
    wind: ['windstill', 'schwacher Wind', 'mäßiger Wind', 'frischer Wind', 'starker Wind', 'stürmischer Wind', 'Sturm',
      'schwerer Sturm', 'orkanartiger Sturm'],
    licht: ['Tageslicht', 'tief stehende Sonne', 'Dämmerung', 'späte Dämmerung', 'Nacht'],
    niederschlag(art, stufe, eis) {
      if (stufe === 0) return eis ? 'vereinzelt Eiskörner' : `ein wenig ${art}`;
      if (eis) return ['', 'leichte', 'mäßige', 'kräftige'][stufe] + ' Eiskörner';
      return ['', 'leichter', 'mäßiger', 'kräftiger'][stufe] + ' ' + art;
    },
    nebel: 'Nebel möglich',
    windAus: (wort, r) => `${wort} aus ${r}`,
    boeen: b => `Böen bis ${b} km/h`,
    gletscher: ' Inlandeis oder Gletscher.',
    schneeLiegt: cm => ` ${cm} cm Schnee liegen.`,
    millionen: (x) => `${x} Mio.`,
    legende: { temperatur: 'Temperatur 2 m', wolken: 'Bewölkung', regen: 'Regen', schneefall: 'Schneefall',
      eisregen: 'Gefrierender Regen', mischung: 'Schneeregen, Eiskörner', wind: 'Wind 10 m', schnee: 'Schneedecke' },
    modellInfo: {
      H: 'Hybrid: Siedlungen ab Kleinstadt, Zugänge ~ Einwohner^0,85 plus Sockel je Siedlung',
      D: 'Vielfalt: erst 100-km-Regionen ~ Einwohner^0,45, dann Siedlungen ab Dorfgröße',
    },
  },

  en: {
    lokal: 'en-GB',
    ost: 'E',
    t: {
      titel: 'Dungeon entrances at the collapse',
      datum: 'Tuesday, 3 January 2023',
      zeiten: '02:23 PST · 11:23 CET · 15:53 India · 18:23 Beijing',
      einklappen: 'Show/hide panel',
      verteilung: 'Distribution', suche: 'Search place …', alleLaender: 'All countries',
      wetter: 'Weather', keins: 'none', temperatur: 'Temperature', wolken: 'Clouds', niederschlag: 'Precipitation',
      wind: 'Wind', schnee: 'Snow cover',
      sZugaenge: 'Entrances', sNacht: 'Day and night', sWindfeld: 'Wind flow', sIsobaren: 'Isobars, highs and lows',
      sNullgrad: '0 °C line',
      karte: 'Map', dunkel: 'Dark', hell: 'Light', satellit: 'Satellite', globus: 'Globe', flach: 'Flat',
      hilfe: 'From medium zoom on, every entrance can be clicked: settlement, population, local time and weather. ' +
        'The bar at the bottom shows the weather under the cursor.',
      modelle: '<b>Hybrid (H)</b>: settlements from small-town size, entrances ~ population<sup>0.85</sup> plus a base ' +
        'share per settlement. <b>Diversity (D)</b>: first, regions of 100 × 100 km get a share ~ population<sup>0.45</sup>, ' +
        'then the settlements within, down to village size. Big agglomerations lose about 60 %, sparsely populated areas gain.',
      wetterInfo: 'Weather: ERA5 reanalysis (ECMWF/Copernicus, 0.25° ≈ 28 km), instantaneous values interpolated ' +
        'between 10 and 11 UTC, precipitation as the 10–11 UTC total. Time as in book 1 (2:23 AM PST, Tuesday, ' +
        '3 January); the books never name the year, 2023 is the most likely.',
      fan: `Unofficial fan project, not affiliated with Matt Dinniman or the publishers of Dungeon Crawler Carl. ` +
        `Code and data: <a href="${REPO}" target="_blank" rel="noopener">GitHub</a>.`,
      quelle: (datei, n, wetter) => `Entrances: ${datei} (${n}). Population: GHSL 2025 (JRC, CC BY 4.0), names: ` +
        `GeoNames (CC BY 4.0), regions: Natural Earth. Weather: ${wetter}.`,
      laden: 'Loading data …',
      fehlt: e => `Data missing: ${e} – run “uv run bauen.py” first.`,
      summe: 'total 10–11 UTC',
      weltweit: 'entrances worldwide', inLand: land => `entrances in ${land}`,
      stat: ['Daylight', 'Twilight', 'Night', 'Frost', 'Precipitation', 'of which snow', 'Snow cover', 'Storm gusts'],
      mittel: (t, kalt, warm) => `Mean ${t} °C · coldest ${kalt} · warmest ${warm}`,
      zugang: 'Entrance', wetterKollaps: 'Weather at the collapse', namenlos: 'Settlement without a place name',
      siedlungIn: (region, land) => `Settlement in ${region} (${land})`,
      namenlosLand: land => `Settlement without a place name (${land})`,
      namenlosInfo: 'The population data shows a settlement here, but the GeoNames gazetteer has no place name within ' +
        '30 km. Often these are gold-mining or refugee camps, or scattered hamlets.',
      zSiedlung: 'Settlement', zUmgebung: 'Surroundings', zNaechster: 'Nearest', zOrtszeit: 'Local time',
      siedlung: (pop, n, je) => `${pop} people incl. surroundings, ${n} ${n === '1' ? 'entrance' : 'entrances'} ` +
        `(≈ ${je} per entrance)`,
      umgebung: (u, d, k) => `${u} people within 5 km; ${d} people/km² at the entrance (${k})`,
      naechster: km => `entrance ${km} km away`, naechsterNah: 'entrance less than 100 m away',
      ortszeit: (uhr, utc, zone, von, bis) => `${uhr} (${utc}, ${zone}), stairwell open ${von}–${bis}`,
      wSonne: 'Sun', wLuft: 'Air', wHimmel: 'Sky', wNieder: 'Precipitation', wWind: 'Wind', wSchnee: 'Snow cover',
      ueber: g => `${g}° above the horizon`, unter: g => `${g}° below the horizon`,
      luft: (t, rh, p) => `${t} °C, humidity ${rh} %, ${p} hPa`,
      nieder: (art, mm) => `${art}, ${mm} mm per hour`, spuren: 'traces (under 0.1 mm per hour)', keiner: 'none',
      still: 'calm', windWert: (k, r, b) => `${k} km/h from ${r}, gusts ${b} km/h`, windStill: b => `calm, gusts ${b} km/h`,
      gletscherKurz: 'ice sheet/glacier', keine: 'none',
      zeigerWind: 'Wind', zeigerSchnee: 'Snow',
    },
    arten: { 1: 'rain', 3: 'freezing rain', 5: 'snow', 6: 'wet snow', 7: 'sleet', 8: 'ice pellets', 12: 'freezing drizzle' },
    richtungen: ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'],
    tage: ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'],
    klassen: { 30: 'urban centre', 23: 'dense town', 22: 'small town', 21: 'suburb', 13: 'village', 12: 'rural',
      11: 'very sparsely populated', 10: 'water' },
    himmel: ['clear', 'mostly clear', 'partly cloudy', 'mostly cloudy', 'overcast'],
    wind: ['calm', 'light wind', 'moderate wind', 'fresh wind', 'strong wind', 'near gale', 'gale', 'strong gale', 'storm'],
    licht: ['daylight', 'low sun', 'twilight', 'late twilight', 'night'],
    niederschlag(art, stufe, eis) {
      if (stufe === 0) return eis ? 'a few ice pellets' : `a little ${art}`;
      return ['', 'light', 'moderate', 'heavy'][stufe] + ' ' + art;
    },
    nebel: 'fog possible',
    windAus: (wort, r) => `${wort} from ${r}`,
    boeen: b => `gusts up to ${b} km/h`,
    gletscher: ' Ice sheet or glacier.',
    schneeLiegt: cm => ` ${cm} cm of snow on the ground.`,
    millionen: (x) => `${x} million`,
    legende: { temperatur: 'Temperature 2 m', wolken: 'Cloud cover', regen: 'Rain', schneefall: 'Snowfall',
      eisregen: 'Freezing rain', mischung: 'Sleet, ice pellets', wind: 'Wind 10 m', schnee: 'Snow cover' },
    modellInfo: {
      H: 'Hybrid: settlements from small-town size, entrances ~ population^0.85 plus a base share per settlement',
      D: 'Diversity: first 100 km regions ~ population^0.45, then settlements down to village size',
    },
  },
};

const zustand = { grundkarte: 'dunkel', projektion: 'globe', wetter: 'niederschlag', land: '', verteilung: 'D',
  sprache: (navigator.language || 'en').toLowerCase().startsWith('de') ? 'de' : 'en',
  zugaenge: true, nacht: true, windfeld: false, isobaren: false, nullgrad: false };
try { Object.assign(zustand, JSON.parse(localStorage.getItem('weltkarte') || '{}')); } catch { /* egal */ }
function merken() { try { localStorage.setItem('weltkarte', JSON.stringify(zustand)); } catch { /* egal */ } }

let L = SPRACHEN[zustand.sprache] || SPRACHEN.en;
let LAENDER = new Intl.DisplayNames([zustand.sprache], { type: 'region' });

let META, Z, GEO, karte, popup, windfeld;
const R = {};
const basisStile = {};
const gruppen = new Map(); // "name|cc" → [Index]
let werte; // je Zugang vorberechnet

const zahl = (x, n = 0) => x.toLocaleString(L.lokal, { minimumFractionDigits: n, maximumFractionDigits: n });
const landName = cc => { try { return LAENDER.of(cc) || cc; } catch { return cc || '?'; } };
const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const gross = s => (s ? s[0].toUpperCase() + s.slice(1) : s);

// ------------------------------------------------------------ Daten

async function ladeJson(name) {
  const r = await fetch(DATEN + name);
  if (!r.ok) throw new Error(`${name}: ${r.status}`);
  return r.json();
}

async function ladeRaster() {
  let buf = await (await fetch(DATEN + 'wetter.bin.gz')).arrayBuffer();
  const kopf = new Uint8Array(buf, 0, 2);
  if (kopf[0] === 0x1f && kopf[1] === 0x8b) {
    const strom = new Blob([buf]).stream().pipeThrough(new DecompressionStream('gzip'));
    buf = await new Response(strom).arrayBuffer();
  }
  const n = META.ny * META.nx;
  const TYP = { '<i2': Int16Array, '<u2': Uint16Array, u1: Uint8Array };
  for (const k of META.raster) R[k.name] = { a: new TYP[k.typ](buf, k.start, n), f: k.faktor };
}

function sonnenhoehe(lat, lon) {
  const d = META.sonne.dek * RAD, la = lat * RAD, h = (lon - META.sonne.lon) * RAD;
  return Math.asin(Math.sin(la) * Math.sin(d) + Math.cos(la) * Math.cos(d) * Math.cos(h)) / RAD;
}

function probe(lat, lon) {
  const NX = META.nx, NY = META.ny;
  const r = Math.min(NY - 1.000001, Math.max(0, (90 - lat) / 0.25));
  const c = (((lon % 360) + 360) % 360) / 0.25;
  const r0 = Math.floor(r), fr = r - r0, cf = Math.floor(c), fc = c - cf;
  const c0 = cf % NX, c1 = (c0 + 1) % NX;
  const i00 = r0 * NX + c0, i01 = r0 * NX + c1, i10 = i00 + NX, i11 = i01 + NX;
  const bil = n => {
    const { a, f } = R[n];
    return ((a[i00] * (1 - fc) + a[i01] * fc) * (1 - fr) + (a[i10] * (1 - fc) + a[i11] * fc) * fr) / f;
  };
  const u = bil('u'), v = bil('v');
  const t = bil('t2m');
  let art = R.art.a[Math.round(r) * NX + (Math.round(c) % NX)];
  const tp = bil('tp');
  if (!art && tp >= 0.05) art = t < 0.5 ? 5 : 1;
  return { t, rh: bil('rh'), wolken: bil('tcc'), tp, art, u, v, wind: Math.hypot(u, v) * 3.6, boe: bil('boe') * 3.6,
    schnee: bil('schnee'), druck: bil('msl'), sonne: sonnenhoehe(lat, lon) };
}

function wind(lat, lon) {
  const NX = META.nx, NY = META.ny;
  const r = Math.min(NY - 1.000001, Math.max(0, (90 - lat) / 0.25));
  const c = (((lon % 360) + 360) % 360) / 0.25;
  const r0 = r | 0, fr = r - r0, cf = Math.floor(c), fc = c - cf;
  const c0 = cf % NX, c1 = (c0 + 1) % NX;
  const i00 = r0 * NX + c0, i01 = r0 * NX + c1, i10 = i00 + NX, i11 = i01 + NX;
  const U = R.u.a, V = R.v.a;
  return [((U[i00] * (1 - fc) + U[i01] * fc) * (1 - fr) + (U[i10] * (1 - fc) + U[i11] * fc) * fr) / 100,
    ((V[i00] * (1 - fc) + V[i01] * fc) * (1 - fr) + (V[i10] * (1 - fc) + V[i11] * fc) * fr) / 100];
}

// ------------------------------------------------------------ Texte

const istSchnee = w => SCHNEEARTEN.has(w.art);
const richtung = (u, v) => L.richtungen[Math.round(((Math.atan2(-u, -v) / RAD + 360) % 360) / 45) % 8];
const artName = w => L.arten[w.art] || L.arten[1];
const himmel = p => L.himmel[p < 10 ? 0 : p < 30 ? 1 : p < 60 ? 2 : p < 90 ? 3 : 4];
const windWort = k => {
  const i = [2, 12, 29, 50, 62, 75, 89, 103].findIndex(g => k < g);
  return L.wind[i < 0 ? 8 : i];
};
const licht = e => L.licht[e > 6 ? 0 : e > 0 ? 1 : e > -6 ? 2 : e > -12 ? 3 : 4];

function niederschlag(w) {
  if (w.tp < 0.1) return '';
  const grenzen = istSchnee(w) ? [0.3, 1.5] : [1, 4];
  const stufe = w.tp < 0.2 ? 0 : w.tp < grenzen[0] ? 1 : w.tp < grenzen[1] ? 2 : 3;
  return L.niederschlag(artName(w), stufe, w.art === 8);
}

function satz(w) {
  const teile = [licht(w.sonne), himmel(w.wolken)];
  const n = niederschlag(w);
  if (n) teile.push(n);
  else if (w.rh >= 97 && w.wind < 15) teile.push(L.nebel);
  teile.push(`${zahl(w.t, 1)} °C`);
  teile.push(w.wind < 2 ? L.wind[0] : L.windAus(windWort(w.wind), richtung(w.u, w.v)));
  if (w.boe >= 50) teile.push(L.boeen(zahl(w.boe)));
  let s = gross(teile.join(', ')) + '.';
  if (w.schnee >= 300) s += L.gletscher;
  else if (w.schnee >= 1) s += L.schneeLiegt(zahl(w.schnee));
  return s;
}

function koordinaten(lat, lon) {
  lon = ((lon + 540) % 360) - 180;
  return `${zahl(Math.abs(lat), 2)}° ${lat >= 0 ? 'N' : 'S'}, ${zahl(Math.abs(lon), 2)}° ${lon >= 0 ? L.ost : 'W'}`;
}

function uhr(versatzMin, mitTag = true) {
  const d = new Date(Date.parse(META.kollaps) + versatzMin * 60000);
  const hm = `${String(d.getUTCHours()).padStart(2, '0')}:${String(d.getUTCMinutes()).padStart(2, '0')}`;
  return mitTag ? `${L.tage[d.getUTCDay()]} ${hm}` : hm;
}

function utcText(m) {
  const v = m < 0 ? '−' : '+', a = Math.abs(m);
  return `UTC${v}${Math.floor(a / 60)}${a % 60 ? ':' + String(a % 60).padStart(2, '0') : ''}`;
}

function leute(n) {
  if (n >= 1e6) return L.millionen(zahl(n / 1e6, n >= 1e7 ? 1 : 2));
  if (n >= 1e4) return zahl(Math.round(n / 100) * 100);
  return zahl(n);
}

function wetterTabelle(w) {
  const t = L.t;
  const nied = w.tp >= 0.1 ? t.nieder(gross(artName(w)), zahl(w.tp, w.tp < 1 ? 2 : 1))
    : w.tp >= 0.02 ? t.spuren : t.keiner;
  const schnee = w.schnee >= 300 ? t.gletscherKurz : w.schnee >= 1 ? `${zahl(w.schnee)} cm` : t.keine;
  const sonne = w.sonne >= 0 ? t.ueber(zahl(w.sonne)) : t.unter(zahl(-w.sonne));
  const windText = w.wind < 2 ? t.windStill(zahl(w.boe)) : t.windWert(zahl(w.wind), richtung(w.u, w.v), zahl(w.boe));
  return `
    <tr><td>${t.wSonne}</td><td>${sonne}</td></tr>
    <tr><td>${t.wLuft}</td><td>${t.luft(zahl(w.t, 1), zahl(w.rh), zahl(w.druck))}</td></tr>
    <tr><td>${t.wHimmel}</td><td>${himmel(w.wolken)} (${zahl(w.wolken)} %)</td></tr>
    <tr><td>${t.wNieder}</td><td>${nied}</td></tr>
    <tr><td>${t.wWind}</td><td>${windText}</td></tr>
    <tr><td>${t.wSchnee}</td><td>${schnee}</td></tr>`;
}

function zugangTabelle(i) {
  if (!Z.siedlung_pop) return '';
  const t = L.t, pop = Z.siedlung_pop[i], n = Z.zugaenge_siedlung[i], km = Z.abstand_km[i];
  return `
    <tr><td>${t.zSiedlung}</td><td>${t.siedlung(leute(pop), zahl(n), leute(Math.round(pop / Math.max(n, 1))))}</td></tr>
    <tr><td>${t.zUmgebung}</td><td>${t.umgebung(leute(Z.umkreis_pop[i]), zahl(Z.dichte[i]), L.klassen[Z.klasse[i]] || '?')}</td></tr>
    <tr><td>${t.zNaechster}</td><td>${km < 0.1 ? t.naechsterNah : t.naechster(zahl(km, km < 10 ? 1 : 0))}</td></tr>`;
}

function regionName(i) {
  if (!Z.regionen) return '';
  const r = Z.regionen[Z.region[i]];
  return Array.isArray(r) ? (zustand.sprache === 'de' ? r[0] : r[1]) : r;
}

function zugangHtml(i) {
  const t = L.t, w = probe(Z.lat[i], Z.lon[i]);
  const [zone, versatz] = Z.zonen[Z.tz[i]];
  const name = anzeigeName(Z.name[i], i);
  const land = landName(Z.cc[i]);
  const region = land.startsWith(regionName(i)) ? '' : regionName(i);
  return `<div class="pop">
    <h3>${esc(name)}</h3>
    <div class="unter">${region ? esc(region) + ', ' : ''}${esc(land)} · ${koordinaten(Z.lat[i], Z.lon[i])}</div>
    ${Z.name[i] === NAMENLOS ? `<div class="weitere">${t.namenlosInfo}</div>` : ''}
    <h4>${t.zugang}</h4>
    <table>
      ${zugangTabelle(i)}
      <tr><td>${t.zOrtszeit}</td><td>${t.ortszeit(uhr(versatz), utcText(versatz), esc(zone), uhr(versatz + 7, false),
        uhr(versatz + 67, false))}</td></tr>
    </table>
    <h4>${t.wetterKollaps}</h4>
    <div class="satz">${satz(w)}</div>
    <table>${wetterTabelle(w)}</table>
  </div>`;
}

// ------------------------------------------------------------ Kartenstil

const beschriftung = () => ['coalesce', ['get', zustand.sprache === 'de' ? 'name:de' : 'name:en'], ['get', 'name:latin'],
  ['get', 'name']];

async function ladeBasis(name) {
  if (basisStile[name]) return basisStile[name];
  const quelle = name === 'hell' ? 'positron' : 'dark';
  const s = await (await fetch('https://tiles.openfreemap.org/styles/' + quelle)).json();
  let stil = s;
  if (name === 'satellit') {
    stil = { ...s, sources: { ...s.sources, esri: { type: 'raster', tileSize: 256, maxzoom: 19,
      tiles: ['https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}'],
      attribution: 'Imagery © Esri, Maxar, Earthstar Geographics' } },
    layers: [{ id: 'esri', type: 'raster', source: 'esri' },
      ...s.layers.filter(l => l.type === 'symbol' || l.id.startsWith('boundary'))] };
  }
  basisStile[name] = stil;
  return stil;
}

const sicht = an => (an ? 'visible' : 'none');
const landFilter = () => (zustand.land ? ['==', ['get', 'cc'], zustand.land] : null);
const filterTeil = () => (zustand.land ? { filter: landFilter() } : {});
const hell = () => zustand.grundkarte === 'hell';

function baueStil() {
  const s = structuredClone(basisStile[zustand.grundkarte]);
  for (const l of s.layers) {
    const tf = l.layout && l.layout['text-field'];
    if (tf && JSON.stringify(tf).includes('name')) l.layout['text-field'] = beschriftung();
  }
  s.projection = { type: zustand.projektion };
  s.sky = { 'atmosphere-blend': ['interpolate', ['linear'], ['zoom'], 0, 1, 5, 1, 7, 0] };
  const strich = hell() ? 'rgba(40,50,80,' : 'rgba(255,255,255,';
  const wetter = [];
  for (const n of [...WETTER, 'nacht']) {
    s.sources['w-' + n] = { type: 'raster', tileSize: 256, maxzoom: 4, tiles: [`${DATEN}kacheln/${n}/{z}/{x}/{y}.png`] };
    const paint = { 'raster-opacity': OPAZITAET[n], 'raster-resampling': 'linear', 'raster-fade-duration': 0 };
    if (n === 'wolken' && hell()) paint['raster-brightness-max'] = 0.6;
    if (n === 'nacht' && hell()) paint['raster-opacity'] = 0.75;
    wetter.push({ id: 'w-' + n, type: 'raster', source: 'w-' + n, paint,
      layout: { visibility: sicht(n === 'nacht' ? zustand.nacht : zustand.wetter === n) } });
  }
  s.sources['w-temperatur'].attribution = 'Weather: ERA5, Copernicus/ECMWF · Population: GHSL (JRC)';
  for (const n of ['isobaren', 'druckzentren', 'nullgrad', 'terminator'])
    s.sources[n] = { type: 'geojson', data: `${DATEN}${n}.geojson` };
  const leer = { type: 'FeatureCollection', features: [] };
  s.sources.zugaenge = { type: 'geojson', data: leer };
  s.sources.auswahl = { type: 'geojson', data: leer };
  const linien = [
    { id: 'nullgrad', type: 'line', source: 'nullgrad', layout: { visibility: sicht(zustand.nullgrad) },
      paint: { 'line-color': hell() ? '#2b6cd6' : '#8fd0ff', 'line-width': 1.6, 'line-dasharray': [3, 2] } },
    { id: 'terminator', type: 'line', source: 'terminator', layout: { visibility: sicht(zustand.nacht) },
      paint: { 'line-color': 'rgba(255,190,110,0.55)', 'line-width': 1 } },
    { id: 'isobaren', type: 'line', source: 'isobaren', layout: { visibility: sicht(zustand.isobaren) },
      paint: { 'line-color': strich + '0.5)', 'line-width': ['case', ['==', ['%', ['get', 'hpa'], 20], 0], 1.4, 0.7] } },
  ];
  const vor = s.layers.findIndex(l => l.id.startsWith('boundary') || (l.type === 'symbol' && l.id !== 'water_name'));
  s.layers.splice(vor < 0 ? s.layers.length : vor, 0, ...wetter, ...linien);
  const hoch = zustand.sprache === 'de' ? ['H', 'T'] : ['H', 'L'];
  s.layers.push(
    { id: 'isobaren-zahl', type: 'symbol', source: 'isobaren', layout: { visibility: sicht(zustand.isobaren),
      'symbol-placement': 'line', 'symbol-spacing': 320, 'text-field': ['to-string', ['get', 'hpa']],
      'text-font': ['Noto Sans Regular'], 'text-size': 10 },
    paint: { 'text-color': strich + '0.85)', 'text-halo-color': hell() ? '#fff' : '#0d1018', 'text-halo-width': 1.2 } },
    { id: 'druckzentren', type: 'symbol', source: 'druckzentren', layout: { visibility: sicht(zustand.isobaren),
      'text-field': ['format', ['match', ['get', 'typ'], 'H', hoch[0], hoch[1]], { 'font-scale': 1.5 }, '\n', {},
        ['to-string', ['get', 'hpa']], { 'font-scale': 0.7 }],
      'text-font': ['Noto Sans Bold'], 'text-size': 15, 'text-allow-overlap': true, 'text-line-height': 1 },
    paint: { 'text-color': ['match', ['get', 'typ'], 'H', '#5fa8ff', '#ff6b5f'],
      'text-halo-color': hell() ? '#fff' : '#0d1018', 'text-halo-width': 1.5 } },
    { id: 'zugaenge-dichte', type: 'heatmap', source: 'zugaenge', maxzoom: 9, ...filterTeil(),
      layout: { visibility: sicht(zustand.zugaenge) },
      paint: {
        'heatmap-weight': 1,
        'heatmap-intensity': ['interpolate', ['linear'], ['zoom'], 0, 0.012, 2, 0.04, 4, 0.15, 6, 0.5, 9, 1.4],
        'heatmap-radius': ['interpolate', ['linear'], ['zoom'], 0, 2, 2, 3.5, 4, 7, 6, 14, 9, 22],
        'heatmap-color': ['interpolate', ['linear'], ['heatmap-density'],
          0, 'rgba(0,0,0,0)', 0.04, 'rgba(140,50,20,0.35)', 0.2, 'rgba(210,80,25,0.65)', 0.45, 'rgba(255,140,45,0.85)',
          0.75, 'rgba(255,205,110,0.95)', 1, 'rgba(255,248,220,1)'],
        'heatmap-opacity': ['interpolate', ['linear'], ['zoom'], 4, 0.9, 7, 0] } },
    { id: 'zugaenge-punkte', type: 'circle', source: 'zugaenge', minzoom: 3.5, ...filterTeil(),
      layout: { visibility: sicht(zustand.zugaenge) },
      paint: {
        'circle-radius': ['interpolate', ['linear'], ['zoom'], 4, 1.5, 8, 3.5, 12, 6],
        'circle-color': '#ffb347',
        'circle-stroke-color': '#2a1606',
        'circle-stroke-width': ['interpolate', ['linear'], ['zoom'], 5, 0, 8, 1],
        'circle-opacity': ['interpolate', ['linear'], ['zoom'], 3.5, 0, 5.5, 0.92],
        'circle-stroke-opacity': ['interpolate', ['linear'], ['zoom'], 3.5, 0, 5.5, 0.92] } },
    { id: 'auswahl', type: 'circle', source: 'auswahl',
      paint: { 'circle-radius': ['interpolate', ['linear'], ['zoom'], 2, 4, 10, 9], 'circle-color': 'rgba(0,0,0,0)',
        'circle-stroke-color': '#fff', 'circle-stroke-width': 2 } },
  );
  return s;
}

function befuelleQuellen() {
  karte.getSource('zugaenge')?.setData(GEO);
}

async function stilWechseln() {
  await ladeBasis(zustand.grundkarte);
  karte.once('style.load', () => { befuelleQuellen(); markiere(letzteAuswahl); });
  karte.setStyle(baueStil(), { diff: false });
  windfeld?.farben();
}

// ------------------------------------------------------------ Windströmung

class Windfeld {
  constructor(map, canvas) {
    this.map = map;
    this.cv = canvas;
    map.getCanvasContainer().appendChild(canvas); // unter Popups und Bedienelementen
    this.ctx = canvas.getContext('2d');
    this.an = false;
    this.teile = [];
    this.bewegt = true;
    map.on('move', () => { this.bewegt = true; });
    addEventListener('resize', () => this.groesse());
    this.groesse();
    this.farben();
  }

  groesse() {
    const dpr = devicePixelRatio || 1;
    this.w = innerWidth; this.h = innerHeight;
    this.cv.width = this.w * dpr; this.cv.height = this.h * dpr;
    this.cv.style.width = this.w + 'px'; this.cv.style.height = this.h + 'px';
    this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    const n = Math.min(7000, Math.round(this.w * this.h / 260));
    this.teile = Array.from({ length: n }, () => this.neu({}));
    this.bewegt = true;
  }

  farben() {
    this.palette = hell()
      ? ['rgba(30,45,80,0.35)', 'rgba(30,45,80,0.6)', 'rgba(20,35,70,0.85)', 'rgba(150,40,20,0.95)']
      : ['rgba(255,255,255,0.3)', 'rgba(255,255,255,0.55)', 'rgba(255,255,255,0.85)', 'rgba(255,215,140,0.95)'];
  }

  neu(p) {
    const ll = this.map.unproject([Math.random() * this.w, Math.random() * this.h]);
    p.lon = ll.lng; p.lat = ll.lat; p.alter = 40 + Math.random() * 60; p.px = null;
    return p;
  }

  sichtbar(p) {
    if (this.map.getProjection()?.type !== 'globe' || this.map.getZoom() > 5) return true;
    const c = this.map.getCenter();
    const a = p.lat * RAD, b = c.lat * RAD;
    return Math.sin(a) * Math.sin(b) + Math.cos(a) * Math.cos(b) * Math.cos((p.lon - c.lng) * RAD) > 0.12;
  }

  start() {
    if (this.an) return;
    this.an = true;
    this.bewegt = true;
    const schleife = () => { if (this.an) { this.schritt(); requestAnimationFrame(schleife); } };
    requestAnimationFrame(schleife);
  }

  stop() {
    this.an = false;
    this.ctx.clearRect(0, 0, this.w, this.h);
  }

  schritt() {
    const ctx = this.ctx;
    if (this.bewegt) {
      ctx.clearRect(0, 0, this.w, this.h);
      for (const p of this.teile) p.px = null;
      this.bewegt = false;
    } else {
      ctx.globalCompositeOperation = 'destination-in';
      ctx.fillStyle = 'rgba(0,0,0,0.92)';
      ctx.fillRect(0, 0, this.w, this.h);
      ctx.globalCompositeOperation = 'source-over';
    }
    const k = 0.13 * 360 / (512 * 2 ** this.map.getZoom());
    const eimer = [[], [], [], []];
    for (const p of this.teile) {
      if (--p.alter < 0) { this.neu(p); continue; }
      const [u, v] = wind(p.lat, p.lon);
      p.lon += u * k / Math.max(0.15, Math.cos(p.lat * RAD));
      p.lat += v * k;
      if (Math.abs(p.lat) > 84 || !this.sichtbar(p)) { this.neu(p); continue; }
      const q = this.map.project([p.lon, p.lat]);
      if (q.x < -30 || q.x > this.w + 30 || q.y < -30 || q.y > this.h + 30) { this.neu(p); continue; }
      if (p.px !== null && Math.abs(q.x - p.px) < 40 && Math.abs(q.y - p.py) < 40) {
        const s = Math.hypot(u, v) * 3.6;
        eimer[s < 15 ? 0 : s < 35 ? 1 : s < 60 ? 2 : 3].push(p.px, p.py, q.x, q.y);
      }
      p.px = q.x; p.py = q.y;
    }
    ctx.lineWidth = 1.25;
    eimer.forEach((e, i) => {
      if (!e.length) return;
      ctx.strokeStyle = this.palette[i];
      ctx.beginPath();
      for (let j = 0; j < e.length; j += 4) { ctx.moveTo(e[j], e[j + 1]); ctx.lineTo(e[j + 2], e[j + 3]); }
      ctx.stroke();
    });
  }
}

// ------------------------------------------------------------ Legende

const SKALEN = {
  temperatur: { log: false, marken: [-40, -20, 0, 20, 40] },
  wolken: { log: false, marken: [0, 50, 100] },
  wind: { log: false, marken: [0, 25, 50, 75, 100] },
  schnee: { log: true, marken: [1, 10, 100, 300] },
  regen: { log: true, marken: [0.1, 1, 10] },
  schneefall: { log: true, marken: [0.1, 1, 8] },
  eisregen: { log: true, marken: [0.1, 1, 5] },
  mischung: { log: true, marken: [0.1, 1, 5] },
};

function legendeReihe(name) {
  const f = META.farben[name], sk = SKALEN[name];
  const xs = f.stopps.map(s => s[0]);
  const lo = xs[0], hi = xs[xs.length - 1];
  const pos = v => {
    const t = sk.log ? (Math.log(Math.max(v, 1e-3)) - Math.log(lo)) / (Math.log(hi) - Math.log(lo)) : (v - lo) / (hi - lo);
    return Math.max(0, Math.min(1, t)) * 100;
  };
  const verlauf = f.stopps.map(([v, c]) => `rgba(${c[0]},${c[1]},${c[2]},${(c[3] / 255).toFixed(2)}) ${pos(v).toFixed(1)}%`).join(',');
  const marken = sk.marken.map(v => `<span style="position:absolute;left:${pos(v)}%;transform:translateX(-${pos(v)}%)">${zahl(v, v > 0 && v < 1 ? 1 : 0)}</span>`).join('');
  return `<div class="reihe"><div class="titel"><span>${L.legende[name]}</span><span>${f.einheit}</span></div>
    <div class="verlauf"><i style="background:linear-gradient(to right,${verlauf})"></i></div>
    <div class="marken" style="position:relative;height:14px">${marken}</div></div>`;
}

function legende() {
  const el = document.getElementById('legende');
  const w = zustand.wetter;
  if (!w) { el.innerHTML = ''; return; }
  const namen = w === 'niederschlag' ? ['regen', 'schneefall', 'eisregen', 'mischung'] : [w];
  el.innerHTML = namen.map(legendeReihe).join('') +
    (w === 'niederschlag' ? `<div class="marken" style="margin-top:-2px">${L.t.summe}</div>` : '');
}

// ------------------------------------------------------------ Statistik, Suche, Länder

let letzteAuswahl = [];

function markiere(idx) {
  letzteAuswahl = idx;
  karte.getSource('auswahl')?.setData({ type: 'FeatureCollection', features: idx.slice(0, 500).map(i => ({
    type: 'Feature', geometry: { type: 'Point', coordinates: [Z.lon[i], Z.lat[i]] }, properties: {} })) });
}

function vorberechnen() {
  const n = Z.lat.length;
  werte = { t: new Float32Array(n), e: new Float32Array(n), tp: new Float32Array(n), art: new Uint8Array(n),
    boe: new Float32Array(n), schnee: new Float32Array(n) };
  for (let i = 0; i < n; i++) {
    const w = probe(Z.lat[i], Z.lon[i]);
    werte.t[i] = w.t; werte.e[i] = w.sonne; werte.tp[i] = w.tp; werte.art[i] = w.art;
    werte.boe[i] = w.boe; werte.schnee[i] = w.schnee;
  }
}

function auswahlIndizes() {
  const idx = [];
  for (let i = 0; i < Z.cc.length; i++) if (!zustand.land || Z.cc[i] === zustand.land) idx.push(i);
  return idx;
}

function statistik() {
  const idx = auswahlIndizes();
  const n = idx.length;
  let tag = 0, daemm = 0, frost = 0, nied = 0, schneefall = 0, decke = 0, sturm = 0, summe = 0, kalt = idx[0], warm = idx[0];
  for (const i of idx) {
    const e = werte.e[i];
    if (e > 0) tag++; else if (e > -12) daemm++;
    if (werte.t[i] < 0) frost++;
    if (werte.tp[i] >= 0.1) { nied++; if (SCHNEEARTEN.has(werte.art[i])) schneefall++; }
    if (werte.schnee[i] >= 1) decke++;
    if (werte.boe[i] >= 75) sturm++;
    summe += werte.t[i];
    if (werte.t[i] < werte.t[kalt]) kalt = i;
    if (werte.t[i] > werte.t[warm]) warm = i;
  }
  const t = L.t;
  const reihe = (titel, x) => `<tr><td>${titel}</td><td><div class="balken"><i style="width:${n ? x / n * 100 : 0}%"></i></div></td>
    <td class="zahl">${n ? zahl(x / n * 100) : 0} %</td></tr>`;
  const ort = i => `<a href="#" data-i="${i}">${esc(anzeigeName(Z.name[i], i))}</a> (${zahl(werte.t[i], 1)} °C)`;
  const [s0, s1, s2, s3, s4, s5, s6, s7] = t.stat;
  document.getElementById('statistik').innerHTML = n ? `
    <div class="gesamt">${zahl(n)} <small>${zustand.land ? esc(t.inLand(landName(zustand.land))) : t.weltweit}</small></div>
    <table>
      ${reihe(s0, tag)}${reihe(s1, daemm)}${reihe(s2, n - tag - daemm)}
      ${reihe(s3, frost)}${reihe(s4, nied)}${reihe(s5, schneefall)}
      ${reihe(s6, decke)}${reihe(s7, sturm)}
    </table>
    <p class="klein" style="margin:8px 0 0;color:var(--leise)">${t.mittel(zahl(summe / n, 1), ort(kalt), ort(warm))}</p>` : '';
  document.querySelectorAll('#statistik a[data-i]').forEach(a => a.addEventListener('click', ev => {
    ev.preventDefault();
    zeigeZugang(+a.dataset.i);
  }));
}

function grenzen(idx) {
  const la = idx.map(i => Z.lat[i]).sort((a, b) => a - b), lo = idx.map(i => Z.lon[i]).sort((a, b) => a - b);
  const q = (a, p) => a[Math.min(a.length - 1, Math.max(0, Math.round(p * (a.length - 1))))];
  const r = idx.length > 50 ? 0.02 : 0;
  return [[q(lo, r), q(la, r)], [q(lo, 1 - r), q(la, 1 - r)]];
}

function zeigeZugang(i) {
  markiere([i]);
  karte.flyTo({ center: [Z.lon[i], Z.lat[i]], zoom: Math.max(karte.getZoom(), 9), speed: 1.6 });
  karte.once('moveend', () => oeffnePopup(i));
}

function zeigeGruppe(idx, ringe = true) {
  if (idx.length === 1) return zeigeZugang(idx[0]);
  markiere(ringe ? idx : []);
  popup?.remove();
  karte.fitBounds(grenzen(idx), { padding: 60, maxZoom: 11, speed: 1.6 });
}

function laenderFuellen() {
  const zaehler = new Map();
  for (const cc of Z.cc) zaehler.set(cc, (zaehler.get(cc) || 0) + 1);
  const sel = document.getElementById('land');
  sel.length = 0;
  sel.add(new Option(L.t.alleLaender, ''));
  [...zaehler].map(([cc, n]) => [cc, landName(cc), n]).sort((a, b) => a[1].localeCompare(b[1], zustand.sprache))
    .forEach(([cc, name, n]) => sel.add(new Option(`${name} (${zahl(n)})`, cc)));
  if (!zaehler.has(zustand.land)) zustand.land = '';
  sel.value = zustand.land;
}

function laenderListe() {
  const sel = document.getElementById('land');
  laenderFuellen();
  sel.addEventListener('change', () => {
    zustand.land = sel.value;
    merken();
    for (const id of ['zugaenge-dichte', 'zugaenge-punkte']) karte.setFilter(id, landFilter());
    statistik();
    markiere([]);
    if (zustand.land) zeigeGruppe(auswahlIndizes(), false);
    else karte.flyTo({ center: [15, 30], zoom: 1.6 });
  });
}

const normal = s => s.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();

// Die Liste nutzt bei Großstädten englische Namen (GeoNames) → deutsche Namen finden sie auch.
const DEUTSCHE_NAMEN = { München: 'Munich', Nürnberg: 'Nuremberg', Wien: 'Vienna', Rom: 'Rome', Moskau: 'Moscow',
  Warschau: 'Warsaw', Prag: 'Prague', Mailand: 'Milan', Lissabon: 'Lisbon', Kopenhagen: 'Copenhagen', Brüssel: 'Brussels',
  Athen: 'Athens', Kiew: 'Kyiv', Peking: 'Beijing', Kairo: 'Cairo', Genf: 'Geneva', Venedig: 'Venice', Neapel: 'Naples',
  Florenz: 'Florence', Bukarest: 'Bucharest', Belgrad: 'Belgrade', 'Mexiko-Stadt': 'Mexico City', Teheran: 'Tehran',
  'Sankt Petersburg': 'Saint Petersburg', Tokio: 'Tokyo', Damaskus: 'Damascus', Bagdad: 'Baghdad', Kapstadt: 'Cape Town',
  Krakau: 'Krakow', Danzig: 'Gdansk', Breslau: 'Wroclaw', Posen: 'Poznan', Stettin: 'Szczecin', Pressburg: 'Bratislava',
  Laibach: 'Ljubljana', Lüttich: 'Liege', Antwerpen: 'Antwerp', 'Den Haag': 'The Hague', Sevilla: 'Seville',
  Saragossa: 'Zaragoza', 'Neu-Delhi': 'New Delhi', Bombay: 'Mumbai', Kalkutta: 'Kolkata', Singapur: 'Singapore' };
const ENGLISCH_DEUTSCH = Object.fromEntries(Object.entries(DEUTSCHE_NAMEN).map(([de, en]) => [en, de]));
const mitDeutsch = name => (zustand.sprache === 'de' && ENGLISCH_DEUTSCH[name] ? `${name} (${ENGLISCH_DEUTSCH[name]})` : name);
const NAMENLOS = '(namenlos)'; // so steht es in den Daten
// Ohne Ortsnamen: Region und Land in den Titel (i fehlt in der Suche, die ganze Gruppen zeigt)
function anzeigeName(name, i) {
  if (name !== NAMENLOS) return mitDeutsch(name);
  if (i === undefined) return L.t.namenlos;
  const land = landName(Z.cc[i]), region = regionName(i);
  return region && !land.startsWith(region) ? L.t.siedlungIn(region, land) : L.t.namenlosLand(land);
}

function suche() {
  const feld = document.getElementById('suche'), liste = document.getElementById('treffer');
  let eintraege = null, treffer = [], aktiv = 0, stand = null;
  const zeichnen = () => {
    liste.innerHTML = treffer.map((t, j) => `<li data-j="${j}" class="${j === aktiv ? 'aktiv' : ''}">${esc(anzeigeName(t.name))}
      <span>${esc(landName(t.cc))}${t.idx.length > 1 ? ' · ' + zahl(t.idx.length) : ''}</span></li>`).join('');
    liste.classList.toggle('offen', treffer.length > 0);
  };
  const waehle = t => { liste.classList.remove('offen'); feld.value = anzeigeName(t.name); zeigeGruppe(t.idx); };
  feld.addEventListener('input', () => {
    const q = normal(feld.value.trim());
    aktiv = 0;
    if (q.length < 2) { treffer = []; zeichnen(); return; }
    if (stand !== Z) {
      stand = Z;
      eintraege = [...gruppen].map(([k, idx]) => ({ k, idx, name: Z.name[idx[0]], cc: Z.cc[idx[0]], n: normal(Z.name[idx[0]]) }));
    }
    const begriffe = [q, ...Object.entries(DEUTSCHE_NAMEN)
      .filter(([de]) => q.length >= 3 && normal(de).startsWith(q)).map(([, en]) => normal(en))];
    const rang = e => {
      const ohne = e.n.startsWith('bei ') ? e.n.slice(4) : e.n;
      return begriffe.includes(ohne) ? 0 : begriffe.some(b => ohne.startsWith(b)) ? 1 : 2;
    };
    treffer = eintraege.filter(e => begriffe.some(b => e.n.includes(b)))
      .sort((a, b) => rang(a) - rang(b) || (a.n.startsWith('bei ') - b.n.startsWith('bei ')) || b.idx.length - a.idx.length)
      .slice(0, 40);
    zeichnen();
  });
  feld.addEventListener('keydown', ev => {
    if (!treffer.length) return;
    if (ev.key === 'ArrowDown') { aktiv = Math.min(treffer.length - 1, aktiv + 1); zeichnen(); ev.preventDefault(); }
    if (ev.key === 'ArrowUp') { aktiv = Math.max(0, aktiv - 1); zeichnen(); ev.preventDefault(); }
    if (ev.key === 'Enter') waehle(treffer[aktiv]);
    if (ev.key === 'Escape') liste.classList.remove('offen');
  });
  liste.addEventListener('mousedown', ev => {
    const li = ev.target.closest('li');
    if (li) { ev.preventDefault(); waehle(treffer[+li.dataset.j]); }
  });
  feld.addEventListener('blur', () => setTimeout(() => liste.classList.remove('offen'), 100));
}

// ------------------------------------------------------------ Bedienung

let popupIndex = null;

function oeffnePopup(i) {
  popup?.remove();
  popupIndex = i;
  popup = new maplibregl.Popup({ maxWidth: '380px', focusAfterOpen: false })
    .setLngLat([Z.lon[i], Z.lat[i]]).setHTML(zugangHtml(i)).addTo(karte);
  popup.on('close', () => { if (popupIndex === i) popupIndex = null; });
}

function texteSetzen() {
  const t = L.t;
  document.documentElement.lang = zustand.sprache;
  document.title = t.titel;
  document.querySelectorAll('[data-t]').forEach(el => { el.textContent = t[el.dataset.t]; });
  document.querySelectorAll('[data-t-html]').forEach(el => { el.innerHTML = t[el.dataset.tHtml]; });
  document.querySelectorAll('[data-t-ph]').forEach(el => { el.placeholder = t[el.dataset.tPh]; });
  document.querySelectorAll('[data-t-title]').forEach(el => { el.title = t[el.dataset.tTitle]; });
  document.querySelectorAll('#verteilung button').forEach(b => {
    const v = META.verteilungen.find(x => x.modell === b.dataset.wert);
    b.textContent = v.titel[zustand.sprache] || v.titel.en;
    b.title = L.modellInfo[v.modell] || '';
  });
  if (Z) document.getElementById('quelle').textContent = t.quelle(Z.quelle, zahl(Z.lat.length), META.quelle);
}

function spracheWechseln() {
  L = SPRACHEN[zustand.sprache];
  LAENDER = new Intl.DisplayNames([zustand.sprache], { type: 'region' });
  texteSetzen();
  laenderFuellen();
  statistik();
  legende();
  if (popupIndex !== null) popup.setHTML(zugangHtml(popupIndex));
  stilWechseln();
}

function bedienung() {
  const panel = document.getElementById('panel');
  const rand = () => karte.setPadding({ left: innerWidth > 640 && !panel.classList.contains('zu') ? 340 : 0, top: 0, right: 0, bottom: 0 });
  document.getElementById('einklappen').addEventListener('click', () => { panel.classList.toggle('zu'); rand(); });
  rand();

  for (const r of document.querySelectorAll('input[name=wetter]')) {
    r.checked = r.value === zustand.wetter;
    r.addEventListener('change', () => {
      zustand.wetter = r.value;
      merken();
      for (const n of WETTER) karte.setLayoutProperty('w-' + n, 'visibility', sicht(n === zustand.wetter));
      legende();
    });
  }

  const schalter = {
    zugaenge: ['zugaenge-dichte', 'zugaenge-punkte'],
    nacht: ['w-nacht', 'terminator'],
    isobaren: ['isobaren', 'isobaren-zahl', 'druckzentren'],
    nullgrad: ['nullgrad'],
  };
  for (const name of ['zugaenge', 'nacht', 'windfeld', 'isobaren', 'nullgrad']) {
    const box = document.getElementById('s-' + name);
    box.checked = zustand[name];
    box.addEventListener('change', () => {
      zustand[name] = box.checked;
      merken();
      if (name === 'windfeld') zustand.windfeld ? windfeld.start() : windfeld.stop();
      else for (const id of schalter[name]) karte.setLayoutProperty(id, 'visibility', sicht(zustand[name]));
    });
  }

  const knopfgruppe = (id, schluessel, wenn) => {
    const g = document.getElementById(id);
    const setze = () => g.querySelectorAll('button').forEach(b => b.classList.toggle('an', b.dataset.wert === zustand[schluessel]));
    setze();
    g.addEventListener('click', ev => {
      const b = ev.target.closest('button');
      if (!b || b.dataset.wert === zustand[schluessel]) return;
      zustand[schluessel] = b.dataset.wert;
      merken();
      setze();
      wenn();
    });
  };
  knopfgruppe('sprache', 'sprache', spracheWechseln);
  knopfgruppe('grundkarte', 'grundkarte', stilWechseln);
  knopfgruppe('projektion', 'projektion', () => karte.setProjection({ type: zustand.projektion }));
  knopfgruppe('verteilung', 'verteilung', async () => {
    popup?.remove();
    await ladeVerteilung(zustand.verteilung);
    befuelleQuellen();
    markiere([]);
    laenderFuellen();
    for (const id of ['zugaenge-dichte', 'zugaenge-punkte']) karte.setFilter(id, landFilter());
    statistik();
  });

  const zeiger = document.getElementById('zeiger');
  karte.on('mousemove', ev => {
    const { lat, lng } = ev.lngLat;
    if (Math.abs(lat) > 89) { zeiger.style.display = 'none'; return; }
    const w = probe(lat, lng);
    const n = niederschlag(w);
    zeiger.innerHTML = `<span>${koordinaten(lat, lng)}</span> · ${zahl(w.t, 1)} °C · ${himmel(w.wolken)}` +
      (n ? ` · ${n} (${zahl(w.tp, 1)} mm/h)` : '') +
      ` · ${L.t.zeigerWind} ${zahl(w.wind)} km/h${w.wind >= 2 ? ' ' + richtung(w.u, w.v) : ''}` +
      (w.schnee >= 1 ? ` · ${L.t.zeigerSchnee} ${w.schnee >= 300 ? '> 3 m' : zahl(w.schnee) + ' cm'}` : '') +
      ` · <span>${licht(w.sonne)}</span>`;
    zeiger.style.display = 'block';
  });
  karte.getCanvas().addEventListener('mouseleave', () => { zeiger.style.display = 'none'; });

  karte.on('mouseenter', 'zugaenge-punkte', () => { karte.getCanvas().style.cursor = 'pointer'; });
  karte.on('mouseleave', 'zugaenge-punkte', () => { karte.getCanvas().style.cursor = ''; });
  karte.on('click', ev => {
    const p = ev.point;
    const f = karte.getLayer('zugaenge-punkte') && zustand.zugaenge
      ? karte.queryRenderedFeatures([[p.x - 6, p.y - 6], [p.x + 6, p.y + 6]], { layers: ['zugaenge-punkte'] }) : [];
    if (!f.length) return;
    f.sort((a, b) => {
      const d = g => { const q = karte.project(g.geometry.coordinates); return (q.x - p.x) ** 2 + (q.y - p.y) ** 2; };
      return d(a) - d(b);
    });
    const i = f[0].properties.i;
    markiere([i]);
    oeffnePopup(i);
  });
}

// ------------------------------------------------------------ Start

async function ladeVerteilung(modell) {
  Z = await ladeJson(`zugaenge_${modell}.json`);
  GEO = { type: 'FeatureCollection', features: Z.lat.map((lat, i) => ({ type: 'Feature', id: i,
    geometry: { type: 'Point', coordinates: [Z.lon[i], lat] }, properties: { i, cc: Z.cc[i] } })) };
  gruppen.clear();
  Z.name.forEach((n, i) => {
    const k = n + '|' + Z.cc[i];
    if (!gruppen.has(k)) gruppen.set(k, []);
    gruppen.get(k).push(i);
  });
  vorberechnen();
  document.getElementById('quelle').textContent = L.t.quelle(Z.quelle, zahl(Z.lat.length), META.quelle);
}

async function start() {
  const laden = document.getElementById('laden');
  laden.textContent = L.t.laden;
  try {
    META = await ladeJson('wetter.json');
    const modelle = META.verteilungen.map(v => v.modell);
    if (!modelle.includes(zustand.verteilung)) zustand.verteilung = modelle[modelle.length - 1];
    document.getElementById('verteilung').innerHTML = META.verteilungen
      .map(v => `<button data-wert="${v.modell}"></button>`).join('');
    await Promise.all([ladeRaster(), ladeBasis(zustand.grundkarte)]);
    await ladeVerteilung(zustand.verteilung);
  } catch (e) {
    laden.textContent = L.t.fehlt(e.message);
    throw e;
  }
  texteSetzen();

  karte = new maplibregl.Map({ container: 'karte', style: baueStil(), center: [15, 30], zoom: 1.6,
    attributionControl: { compact: true }, maxPitch: 0 });
  karte.addControl(new maplibregl.NavigationControl({ visualizePitch: false }), 'top-right');
  karte.addControl(new maplibregl.ScaleControl({ unit: 'metric' }), 'bottom-right');
  karte.once('load', () => { befuelleQuellen(); laden.classList.add('weg'); });
  windfeld = new Windfeld(karte, document.getElementById('windfeld'));
  if (zustand.windfeld) windfeld.start();
  laenderListe();
  statistik();
  legende();
  suche();
  bedienung();
  window.weltkarte = { karte, probe, zustand, Z: () => Z };
}

start();
