#!/usr/bin/env python3
"""Generate the vacs dataset for Brazil (dataset/SB) from the VATBRZ EuroScope sectorfiles.

Usage:
    python dataset/SB/_generator/generate.py [path/to/VatBrz]

The VatBrz directory must contain one unpacked sectorfile per FIR (SBAO, SBAZ, SBBS, SBCW, SBRE),
each with its .ese file and NavData/icao.txt.

Rules (agreed with the VATBRZ staff):
- One vacs station per Brazilian position; ATIS and TMU positions are skipped.
- Neighbouring FIR positions are not created, their existing stations are only referenced in the profile.
- Coverage comes from the OWNER lines of the .ese [AIRSPACE] section. For each sector, only the .ese of
  the FIR owning the sector (prefix of the sector name) is used.
- When a position falls back to different positions depending on the sector, the fallback seen in most
  sectors wins and the remaining positions are appended in order of appearance.
- Ground chain: DEL > RMP > GND > TWR, then up the TWR coverage (APP > CTR).
- Secondary positions (e.g. SBBR_N_TWR, SBSP_H_TWR, SBXP_DEP) are children of the main position.
- Towers without any sector take the coverage of the lowest sector containing the aerodrome, skipping
  the towers of other aerodromes.
- A single national tabbed profile (SB): one tab per FIR with CTR keys and one key per TMA opening a
  subpage with its APP, TWR and ground stations, plus a tab for neighbouring stations.
"""

import json
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

DEFAULT_SECTORFILES = Path(r"F:\VATSIM\Euroscope\EuroScope\VatBrz")
OUTPUT_DIR = Path(__file__).resolve().parent.parent

PROFILE_ID = "SB"
BRAZIL_PREFIXES = ("SB", "SD", "SI", "SJ", "SN", "SS", "SW")
SKIPPED_FACILITIES = {"ATIS", "TMU"}
VALID_FACILITIES = {"RMP", "DEL", "GND", "TWR", "APP", "DEP", "CTR", "FSS", "RDO", "FMP"}

FIRS = {
    "SBAZ": "Amazônico",
    "SBBS": "Brasília",
    "SBCW": "Curitiba",
    "SBRE": "Recife",
    "SBAO": "Atlântico",
}

# Stations of neighbouring FIRs already present in the dataset, shown in the "Vizinhos" tab.
NEIGHBOUR_STATIONS = [
    ("SARR_CTR", ["SARR", "CTR"]),
    ("SARL_APP", ["SARL", "APP"]),
    ("SARI_TWR", ["SARI", "TWR"]),
    ("FAJO_FSS", ["FAJO", "FSS"]),
    ("FAJO_1_FSS", ["FAJO", "1 FSS"]),
    ("FAJO_2_FSS", ["FAJO", "2 FSS"]),
    ("FAJO_3_FSS", ["FAJO", "3 FSS"]),
    ("AFRC_FSS", ["AFRC", "FSS"]),
    ("AFRW_FSS", ["AFRW", "FSS"]),
]

COLORS = {
    "CTR": "azure",
    "FSS": "azure",
    "APP": "steel",
    "DEP": "cadet",
    "TWR": "lagoon",
    "GND": "lilac",
    "RMP": "taupe",
    "DEL": "clay",
}

GROUND_ORDER = ["DEL", "RMP", "GND"]  # DEL > RMP > GND > TWR
PAGE_ROWS = 6


# --------------------------------------------------------------------------------------------------
# Parsing
# --------------------------------------------------------------------------------------------------


def read_lines(path):
    return path.read_text(encoding="cp1252").splitlines()


def parse_coord(value):
    """Parse a EuroScope coordinate like S022.04.28.202 into decimal degrees."""
    hemi, rest = value[0], value[1:]
    deg, minutes, sec, frac = rest.split(".")
    result = int(deg) + int(minutes) / 60 + float(f"{sec}.{frac}") / 3600
    return -result if hemi in "SW" else result


def parse_ese(path):
    positions = []
    sectorlines = defaultdict(list)
    sectors = []
    section = None
    current_line = None
    current_sector = None

    for raw in read_lines(path):
        line = raw.strip()
        if not line or line.startswith(";"):
            continue
        if line.startswith("[") and line.endswith("]"):
            section = line
            continue

        if section == "[POSITIONS]":
            parts = line.split(":")
            if len(parts) >= 7:
                positions.append(
                    {
                        "id": parts[0].upper(),
                        "frequency": parts[2],
                        "ident": parts[3],
                        "prefix": parts[5].upper(),
                        "facility": parts[6].upper(),
                    }
                )
        elif section == "[AIRSPACE]":
            key, _, value = line.partition(":")
            if key == "SECTORLINE":
                current_line = value
                current_sector = None
            elif key == "COORD" and current_line is not None:
                lat, lon = value.split(":")[:2]
                sectorlines[current_line].append((parse_coord(lat), parse_coord(lon)))
            elif key == "SECTOR":
                name, low, high = value.split(":")[:3]
                current_sector = {"name": name, "low": int(low), "high": int(high), "owners": [], "borders": []}
                sectors.append(current_sector)
                current_line = None
            elif key == "OWNER" and current_sector is not None:
                current_sector["owners"] = [o for o in value.split(":") if o]
            elif key == "BORDER" and current_sector is not None:
                current_sector["borders"] = [b for b in value.split(":") if b]
            elif key in ("DISPLAY", "ALTOWNER", "DEPAPT", "ARRAPT", "ACTIVE", "GUEST"):
                pass
            else:
                current_line = None

    return positions, sectorlines, sectors


def parse_airports(path):
    airports = {}
    for line in path.read_text(encoding="cp1252").splitlines():
        parts = line.split("\t")
        if len(parts) >= 3:
            try:
                airports[parts[0].strip().upper()] = (float(parts[1]), float(parts[2]))
            except ValueError:
                continue
    return airports


def build_polygon(border_ids, sectorlines):
    """Chain the sectorlines of a sector border into a closed ring of points."""
    segments = [list(sectorlines[b]) for b in border_ids if sectorlines.get(b)]
    if not segments:
        return None
    ring = segments.pop(0)
    while segments:
        end = ring[-1]
        best = None
        for i, seg in enumerate(segments):
            for reverse in (False, True):
                start = seg[-1] if reverse else seg[0]
                dist = abs(start[0] - end[0]) + abs(start[1] - end[1])
                if best is None or dist < best[0]:
                    best = (dist, i, reverse)
        _, i, reverse = best
        seg = segments.pop(i)
        ring.extend(reversed(seg) if reverse else seg)
    return ring


def point_in_polygon(point, polygon):
    lat, lon = point
    inside = False
    j = len(polygon) - 1
    for i in range(len(polygon)):
        lat_i, lon_i = polygon[i]
        lat_j, lon_j = polygon[j]
        if (lon_i > lon) != (lon_j > lon):
            cross = (lat_j - lat_i) * (lon - lon_i) / (lon_j - lon_i) + lat_i
            if lat < cross:
                inside = not inside
        j = i
    return inside


def polygon_area(polygon):
    return abs(
        sum(polygon[i][0] * polygon[i - 1][1] - polygon[i - 1][0] * polygon[i][1] for i in range(len(polygon)))
        / 2
    )


# --------------------------------------------------------------------------------------------------
# Model
# --------------------------------------------------------------------------------------------------


def is_brazilian(position_id):
    return position_id.startswith(BRAZIL_PREFIXES)


def icao_of(position_id):
    return position_id.split("_")[0]


def suffix_of(position_id):
    """Middle part of a callsign, e.g. SBXP_T3_APP -> T3."""
    parts = position_id.split("_")
    return "_".join(parts[1:-1])


def normalize_frequency(freq):
    return f"{float(freq):07.3f}"


def load(sectorfiles):
    positions = {}
    sectors = []
    airports = {}

    for fir in FIRS:
        fir_dir = sectorfiles / fir
        ese_files = sorted(fir_dir.glob("*.ese"))
        if len(ese_files) != 1:
            sys.exit(f"Expected exactly one .ese file in {fir_dir}, found {len(ese_files)}")
        ese_positions, sectorlines, ese_sectors = parse_ese(ese_files[0])

        ident_map = {}
        for pos in ese_positions:
            ident_map.setdefault(pos["ident"], pos["id"])
            positions.setdefault(pos["id"], pos)

        for sector in ese_sectors:
            owner_fir = sector["name"].split("·")[0]
            if owner_fir != fir:
                continue  # only the .ese of the FIR owning the sector is authoritative
            missing = [o for o in sector["owners"] if o not in ident_map]
            if missing:
                print(f"WARN {fir}: sector {sector['name']} references unknown idents {missing}")
            sector["fir"] = fir
            sector["chain"] = [ident_map[o] for o in sector["owners"] if o in ident_map]
            sector["polygon"] = build_polygon(sector["borders"], sectorlines)
            sectors.append(sector)

        icao_file = fir_dir / fir / "NavData" / "icao.txt"
        if icao_file.exists():
            for icao, coords in parse_airports(icao_file).items():
                airports.setdefault(icao, coords)

    return positions, sectors, airports


def resolve(positions, sectors, airports):
    stations = {
        pid: pos
        for pid, pos in positions.items()
        if is_brazilian(pid) and pos["facility"] not in SKIPPED_FACILITIES
    }
    for pid, pos in stations.items():
        if pos["facility"] not in VALID_FACILITIES:
            sys.exit(f"Unsupported facility {pos['facility']} for {pid}")

    # Fallback chains from the sector owners
    tails = defaultdict(Counter)
    first_seen = defaultdict(dict)
    fir_votes = defaultdict(Counter)
    for sector in sectors:
        chain = [p for p in sector["chain"] if p in stations]
        for i, pid in enumerate(chain):
            tail = tuple(chain[i + 1 :])
            tails[pid][tail] += 1
            first_seen[pid].setdefault(tail, len(first_seen[pid]))
            fir_votes[pid][sector["fir"]] += 2 if i == 0 else 1

    coverage = {}  # position -> ordered fallback list (excluding itself)
    fir_of = {}
    report = defaultdict(list)

    for pid, counter in tails.items():
        ordered = sorted(counter, key=lambda t: (-counter[t], first_seen[pid][t]))
        merged = []
        for tail in ordered:
            merged.extend(p for p in tail if p not in merged and p != pid)
        coverage[pid] = merged
        fir_of[pid] = fir_votes[pid].most_common(1)[0][0]
        if len(counter) > 1:
            report["ambiguous"].append(
                f"{pid}: " + " | ".join(f"{' > '.join(t) or '-'} ({counter[t]}x)" for t in ordered)
                + f"\n    => {' > '.join(merged)}"
            )

    def main_tower(icao):
        if f"{icao}_TWR" in stations:
            return f"{icao}_TWR"
        towers = sorted(p for p in stations if icao_of(p) == icao and stations[p]["facility"] == "TWR")
        return towers[0] if towers else None

    parents = {}

    # Secondary TWR and DEP positions not present in any sector
    for pid, pos in stations.items():
        if pid in coverage:
            continue
        icao = icao_of(pid)
        if pos["facility"] == "TWR" and main_tower(icao) in coverage and main_tower(icao) != pid:
            parents[pid] = main_tower(icao)
            report["secondary"].append(f"{pid} -> {parents[pid]}")
        elif pos["facility"] == "DEP" and f"{icao}_APP" in stations:
            parents[pid] = f"{icao}_APP"
            report["secondary"].append(f"{pid} -> {parents[pid]}")

    # Towers without sectors: lowest sector containing the aerodrome
    for pid, pos in stations.items():
        if pid in coverage or pid in parents or pos["facility"] not in ("TWR", "APP", "CTR", "FSS"):
            continue
        icao = icao_of(pid)
        point = airports.get(icao)
        if point is None:
            report["unresolved"].append(f"{pid}: aerodrome {icao} has no coordinates")
            continue
        candidates = [
            s for s in sectors if s["polygon"] and s["chain"] and point_in_polygon(point, s["polygon"])
        ]
        candidates = [s for s in candidates if any(p in stations for p in s["chain"])]
        if not candidates:
            report["unresolved"].append(f"{pid}: no sector contains {icao} {point}")
            continue
        best = min(candidates, key=lambda s: (s["low"], s["high"], polygon_area(s["polygon"])))
        # Towers of other aerodromes do not cover this one, start at the APP/CTR above them
        chain = [p for p in best["chain"] if p in stations and stations[p]["facility"] != "TWR"]
        coverage[pid] = chain
        fir_of[pid] = best["fir"]
        report["geographic"].append(f"{pid}: {best['name']} -> {' > '.join(chain)}")

    # Ground chain DEL > RMP > GND > TWR
    for pid, pos in stations.items():
        if pid in coverage or pid in parents or pos["facility"] not in GROUND_ORDER:
            continue
        icao = icao_of(pid)
        level = GROUND_ORDER.index(pos["facility"])
        parent = None
        for facility in GROUND_ORDER[level + 1 :]:
            if f"{icao}_{facility}" in stations:
                parent = f"{icao}_{facility}"
                break
        parent = parent or main_tower(icao)
        if parent is None:
            report["unresolved"].append(f"{pid}: no TWR at {icao}")
            continue
        parents[pid] = parent

    for pid in stations:
        if pid not in coverage and pid not in parents:
            report["unresolved"].append(f"{pid}: no coverage found, only covered by itself")
            coverage[pid] = []

    # Expand parents into coverage lists
    def full_chain(pid, seen=()):
        if pid in parents:
            parent = parents[pid]
            return [pid] + [p for p in full_chain(parent, seen + (pid,)) if p != pid]
        return [pid] + coverage[pid]

    chains = {pid: dedupe(full_chain(pid)) for pid in stations}

    def resolve_fir(pid):
        if pid in fir_of:
            return fir_of[pid]
        return resolve_fir(parents[pid]) if pid in parents else None

    firs = {pid: resolve_fir(pid) for pid in stations}
    for pid, fir in firs.items():
        if fir is None:
            report["unresolved"].append(f"{pid}: FIR unknown")

    return stations, chains, parents, firs, report


def dedupe(items):
    result = []
    for item in items:
        if item not in result:
            result.append(item)
    return result


# --------------------------------------------------------------------------------------------------
# Output
# --------------------------------------------------------------------------------------------------


FACILITY_RANK = {"CTR": 0, "FSS": 0, "APP": 1, "DEP": 2, "TWR": 3, "GND": 4, "RMP": 5, "DEL": 6}


def sort_key(pid, stations):
    return (FACILITY_RANK[stations[pid]["facility"]], icao_of(pid), suffix_of(pid) != "", pid)


def toml_list(values):
    return "[" + ", ".join(f'"{v}"' for v in values) + "]"


def write_stations(stations, chains, firs, path):
    lines = []
    for fir in FIRS:
        members = sorted((p for p in stations if firs[p] == fir), key=lambda p: sort_key(p, stations))
        if not members:
            continue
        lines.append(f"# --- {fir} {FIRS[fir]} ---")
        for pid in members:
            chain = chains[pid]
            lines.append("[[stations]]")
            lines.append(f'id = "{pid}"')
            # Use parent_id when the fallback is exactly the coverage of the next station
            if len(chain) > 1 and chains[chain[1]] == chain[1:]:
                lines.append(f'parent_id = "{chain[1]}"')
                lines.append(f"controlled_by = {toml_list([pid])}")
            else:
                lines.append(f"controlled_by = {toml_list(chain)}")
            lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8", newline="\n")


def write_positions(stations, firs, path):
    lines = []
    for fir in FIRS:
        members = sorted((p for p in stations if firs[p] == fir), key=lambda p: sort_key(p, stations))
        if not members:
            continue
        lines.append(f"# --- {fir} {FIRS[fir]} ---")
        for pid in members:
            pos = stations[pid]
            lines.append("[[positions]]")
            lines.append(f'id = "{pid}"')
            lines.append(f"prefixes = {toml_list([pos['prefix']])}")
            lines.append(f'frequency = "{normalize_frequency(pos["frequency"])}"')
            lines.append(f'facility_type = "{pos["facility"]}"')
            lines.append(f'profile_id = "{PROFILE_ID}"')
            lines.append(f"default_call_sources = {toml_list([pid])}")
            lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8", newline="\n")


def key(pid, stations):
    pos = stations[pid]
    middle = suffix_of(pid).replace("_", " ")
    label = f"{middle} {pos['facility']}".strip()
    return {
        "label": [icao_of(pid), label, normalize_frequency(pos["frequency"])],
        "color": COLORS[pos["facility"]],
        "station_id": pid,
    }


def blank():
    return {"label": []}


def columns_to_keys(columns, rows):
    """Lay out columns of keys (column-major grid), splitting long columns."""
    keys = []
    for column in columns:
        for start in range(0, len(column), rows):
            chunk = column[start : start + rows]
            keys.extend(chunk + [blank()] * (rows - len(chunk)))
    return keys


def chunk_column(items, rows):
    return [items[i : i + rows] for i in range(0, len(items), rows)] or [[]]


def build_profile(stations, chains, firs):
    def tma_of(pid):
        """APP sub-sectors (e.g. SBGR_F_APP) belong to the TMA of the last APP in their chain."""
        if not suffix_of(pid):
            return icao_of(pid)
        apps = [p for p in chains[pid] if stations[p]["facility"] == "APP"]
        return icao_of(apps[-1]) if apps else icao_of(pid)

    def nearest_app(pid):
        for p in chains[pid][1:]:
            if stations[p]["facility"] == "APP":
                return tma_of(p)
        return None

    tabs = []
    for fir, name in FIRS.items():
        members = [p for p in stations if firs[p] == fir]
        if not members:
            continue

        enroute = sorted(
            (p for p in members if stations[p]["facility"] in ("CTR", "FSS")), key=lambda p: sort_key(p, stations)
        )
        terminals = sorted({tma_of(p) for p in members if stations[p]["facility"] in ("APP", "DEP")})

        # Aerodromes grouped under their TMA (or "Outros")
        aerodromes = defaultdict(lambda: defaultdict(list))
        for p in members:
            if stations[p]["facility"] in ("TWR", "GND", "RMP", "DEL"):
                tower = p
                while stations[tower]["facility"] != "TWR" and len(chains[tower]) > 1:
                    tower = chains[tower][1]
                group = nearest_app(tower) if stations[tower]["facility"] == "TWR" else None
                aerodromes[group if group in terminals else None][icao_of(p)].append(p)

        def aerodrome_columns(group):
            columns = []
            for icao in sorted(aerodromes[group]):
                items = sorted(aerodromes[group][icao], key=lambda p: sort_key(p, stations))
                columns.extend(chunk_column([key(p, stations) for p in items], PAGE_ROWS))
            return columns

        main_columns = chunk_column([key(p, stations) for p in enroute], PAGE_ROWS)

        tma_keys = []
        for tma in terminals:
            units = sorted(
                (p for p in members if tma_of(p) == tma and stations[p]["facility"] in ("APP", "DEP")),
                key=lambda p: sort_key(p, stations),
            )
            columns = chunk_column([key(p, stations) for p in units], PAGE_ROWS) + aerodrome_columns(tma)
            tma_keys.append(
                {
                    "label": [tma, "APP"],
                    "color": COLORS["APP"],
                    "page": {"rows": PAGE_ROWS, "keys": columns_to_keys(columns, PAGE_ROWS)},
                }
            )
        if aerodromes[None]:
            tma_keys.append(
                {
                    "label": ["Outros", "AD"],
                    "color": COLORS["TWR"],
                    "page": {"rows": PAGE_ROWS, "keys": columns_to_keys(aerodrome_columns(None), PAGE_ROWS)},
                }
            )

        columns = main_columns + chunk_column(tma_keys, PAGE_ROWS)
        tabs.append({"label": [fir, name], "page": {"rows": PAGE_ROWS, "keys": columns_to_keys(columns, PAGE_ROWS)}})

    neighbours = [
        {"label": label, "color": COLORS[sid.rsplit("_", 1)[1]], "station_id": sid} for sid, label in NEIGHBOUR_STATIONS
    ]
    tabs.append(
        {
            "label": ["Vizinhos"],
            "page": {"rows": PAGE_ROWS, "keys": columns_to_keys(chunk_column(neighbours, PAGE_ROWS), PAGE_ROWS)},
        }
    )

    return {"id": PROFILE_ID, "type": "Tabbed", "tabs": tabs}


def check_ambiguous_matching(stations):
    """vacs cannot pick a position when frequency, facility and prefix are all shared."""
    groups = defaultdict(list)
    for pid, pos in stations.items():
        groups[(normalize_frequency(pos["frequency"]), pos["facility"], pos["prefix"])].append(pid)
    return [f"{' / '.join(sorted(ids))} share {k}" for k, ids in groups.items() if len(ids) > 1]


def format_output():
    """Format the output with the repository prettier setup (npm ci), as required by CI."""
    repo_root = OUTPUT_DIR.parent.parent
    pattern = f"{OUTPUT_DIR.relative_to(repo_root).as_posix()}/**/*.{{json,toml}}"
    try:
        subprocess.run(
            ["npx", "--no-install", "prettier", "--write", pattern],
            cwd=repo_root,
            check=True,
            capture_output=True,
            shell=sys.platform == "win32",
        )
    except (OSError, subprocess.CalledProcessError):
        print("WARN prettier not available, run `npm ci && npm run format` in the repository root")


def main():
    sectorfiles = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_SECTORFILES
    positions, sectors, airports = load(sectorfiles)
    stations, chains, parents, firs, report = resolve(positions, sectors, airports)

    write_positions(stations, firs, OUTPUT_DIR / "positions.toml")
    write_stations(stations, chains, firs, OUTPUT_DIR / "stations.toml")
    profiles_dir = OUTPUT_DIR / "profiles"
    profiles_dir.mkdir(exist_ok=True)
    profile = build_profile(stations, chains, firs)
    (profiles_dir / f"{PROFILE_ID}.json").write_text(
        json.dumps(profile, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )

    format_output()
    report["prefix matching"] = check_ambiguous_matching(stations)

    counts = Counter(stations[p]["facility"] for p in stations)
    print(f"{len(stations)} stations/positions: " + ", ".join(f"{k}={v}" for k, v in sorted(counts.items())))
    for fir in FIRS:
        print(f"  {fir}: {sum(1 for p in stations if firs[p] == fir)}")
    for title, entries in report.items():
        if entries:
            print(f"\n## {title} ({len(entries)})")
            for entry in entries:
                print(f"  {entry}")


if __name__ == "__main__":
    main()
