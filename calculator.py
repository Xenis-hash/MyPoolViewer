"""
MyPoolViewer — Calculation Engine  (Phase 2 — Refined)
=======================================================
Sizing rules based on Fluidra 2025 Commercial Catalog and:
  • EN 16713-1/2  (pool filtration systems)
  • EN 16582-1    (anti-entrapment for drain covers)
  • DIN 19643     (public pool water treatment)
  • ASHRAE        (indoor pool dehumidification)

Inputs  → PoolInputs dataclass
Outputs → CalculationResult dataclass + full Bill of Materials
"""

import csv
import math
import os
from dataclasses import dataclass, field
from typing import Optional

_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(_DIR, "master_pool_components.csv")


# ══════════════════════════════════════════════════════════════════════════════
# 1. DATA CLASSES
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class PoolInputs:
    width_m:      float
    length_m:     float
    depth_m:      float
    pool_type:    str          # 'skimmer' | 'overflow' | 'infinity'
    filtration:   str          # 'chlorine' | 'saltwater' | 'magnesium'
    indoor:       bool  = False
    heating:      bool  = False
    liner_style:  str   = "standard"   # 'standard'|'touch'|'ceramics'|'vogue'|'alive'|'3000'|'uni-basic'|'uni-plus'
    liner_color:  str   = "light-blue"
    drain_color:  str   = "white"      # 'white'|'beige'|'light-grey'|'anthracite'
    inlet_color:  str   = "white"
    grille_color: str   = "white"
    ladder_type:  str   = "standard"   # 'standard'|'pmr'|'overflow-1000'
    light_color:  str   = "rgbw"       # 'white'|'warm-white'|'tunable-white'|'rgb'|'rgbw'


@dataclass
class Component:
    row_type: str; category: str; subcategory: str; brand: str; model: str; code: str
    parent_codes: str
    flow_rate_min: Optional[float]; flow_rate_max: Optional[float]
    power_hp: Optional[float]; power_kw: Optional[float]
    filter_diameter_mm: Optional[float]; filtration_area_m2: Optional[float]
    filtration_velocity: Optional[float]; bed_depth_m: Optional[float]
    max_pressure_bar: Optional[float]; salinity_g_l: Optional[str]
    chlorine_output_g_h: Optional[float]; connection_mm: Optional[float]
    pool_volume_min: Optional[float]; pool_volume_max: Optional[float]
    quantity_rule: str; notes: str


@dataclass
class CalculationResult:
    volume_m3: float; surface_m2: float; perimeter_m: float
    turnover_hours: float; design_flow_m3h: float
    filter: Optional[Component] = None
    pump: Optional[Component] = None
    treatment: Optional[Component] = None
    valve_manifold: Optional[Component] = None
    filter_media: list = field(default_factory=list)
    strainer: Optional[Component] = None
    check_valve: Optional[Component] = None
    vibration_damper: Optional[Component] = None
    air_blower: Optional[Component] = None
    heater: Optional[Component] = None
    dehumidifier: Optional[Component] = None
    main_drains: list = field(default_factory=list)
    return_inlets: list = field(default_factory=list)
    overflow_grilles: list = field(default_factory=list)
    liner: Optional[Component] = None
    liner_accessories: list = field(default_factory=list)
    lighting: list = field(default_factory=list)
    light_niches: list = field(default_factory=list)
    light_transformer: Optional[Component] = None
    pool_surround: list = field(default_factory=list)
    automation: Optional[Component] = None
    robot_cleaner: Optional[Component] = None
    engine_room_m2: float = 0.0
    n_chlorinators: int = 1
    bom: list = field(default_factory=list)
    warnings: list = field(default_factory=list)


# ══════════════════════════════════════════════════════════════════════════════
# 2. CSV LOADER
# ══════════════════════════════════════════════════════════════════════════════

def _float_or_none(val: str) -> Optional[float]:
    """Parse float or range string like '20-30' (returns max value)."""
    try:
        v = (val or "").strip()
        if not v:
            return None
        if "-" in v and not v.startswith("-"):
            return max(float(p) for p in v.split("-") if p.strip())
        return float(v)
    except ValueError:
        return None


def load_components(csv_path: str = CSV_PATH) -> list:
    rows = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rows.append(Component(
                row_type=row["row_type"], category=row["category"],
                subcategory=row["subcategory"], brand=row["brand"],
                model=row["model"], code=row["code"],
                parent_codes=row["parent_codes"],
                flow_rate_min=_float_or_none(row["flow_rate_m3h_min"]),
                flow_rate_max=_float_or_none(row["flow_rate_m3h_max"]),
                power_hp=_float_or_none(row["power_hp"]),
                power_kw=_float_or_none(row["power_kw"]),
                filter_diameter_mm=_float_or_none(row["filter_diameter_mm"]),
                filtration_area_m2=_float_or_none(row["filtration_area_m2"]),
                filtration_velocity=_float_or_none(row["filtration_velocity_m3hm2"]),
                bed_depth_m=_float_or_none(row["bed_depth_m"]),
                max_pressure_bar=_float_or_none(row["max_pressure_bar"]),
                salinity_g_l=row["salinity_g_l"],
                chlorine_output_g_h=_float_or_none(row["chlorine_output_g_h"]),
                connection_mm=_float_or_none(row["connection_mm"]),
                pool_volume_min=_float_or_none(row["pool_volume_m3_min"]),
                pool_volume_max=_float_or_none(row["pool_volume_m3_max"]),
                quantity_rule=row["quantity_rule"], notes=row["notes"],
            ))
    return rows


# ══════════════════════════════════════════════════════════════════════════════
# 3. CONSTANTS & HELPERS
# ══════════════════════════════════════════════════════════════════════════════

TURNOVER_HOURS     = {"skimmer": 6.0, "overflow": 4.0, "infinity": 4.0}
FILTER_VELOCITY_CAP= {"skimmer": 50,  "overflow": 30,  "infinity": 30}
_AIRSCOURING_KW    = ("BEGUR", "NORMA", "TOR", "BLANES")

# Pump outlet connection diameter inferred from HP when not explicit in CSV
_PUMP_CONN_BY_HP = [(0.75,50),(1.5,50),(3.0,63),(5.5,75),(7.5,90),
                    (10.0,110),(15.0,125),(25.0,150),(999,200)]

def _pump_conn(pump: Component) -> int:
    if pump.connection_mm:
        return int(pump.connection_mm)
    hp = pump.power_hp or 1.0
    for hp_lim, conn in _PUMP_CONN_BY_HP:
        if hp <= hp_lim:
            return conn
    return 150

def _is_airscouring(f: Component) -> bool:
    return any(k in f.model for k in _AIRSCOURING_KW)

# Liner catalog — style key → (model name, default color codes)
LINER_STYLES = {
    "standard":  "Alkorplan 2000 Reinforced Membrane",
    "touch":     "Alkorplan Touch 2mm 1.65x21m",
    "ceramics":  "Alkorplan Ceramics 1.65x21m",
    "vogue":     "Alkorplan Vogue Reinforced",
    "alive":     "Alkorplan ALIVE Collection",
    "3000":      "Alkorplan 3000 Membrane",
    "uni-basic": "AstralPool UNI Basic",
    "uni-plus":  "AstralPool UNI Plus",
}

# Color codes for lights (suffix appended to base code 76600)
LIGHT_COLOR_CODES = {
    "white":        "76600",
    "warm-white":   "76600WW",
    "tunable-white":"76600TW",
    "rgb":          "76600M",
    "rgbw":         "76600MW",
}

# Available liner colors per style — displayed in UI as decorative palette
LINER_COLOR_PALETTE = {
    "touch":    ["elegance","relax","authentic","vanity","sublime","prestige","origin"],
    "alive":    ["prana-green","dhyana-blue","chandra-grey"],
    "ceramics": ["atenea","selene","etna"],
    "vogue":    ["vintage","urban","summer","tropical"],
    "standard": ["light-blue","anthracite","white","sand"],
    "3000":     ["light-blue","white","grey"],
    "uni-basic":["light-blue","white"],
    "uni-plus": ["light-blue","white","sand"],
}

# Overflow grille color options
GRILLE_COLOR_OPTIONS = ["white","grey","anthracite","beige"]
# Main drain color options
DRAIN_COLOR_OPTIONS  = ["white","beige","light-grey","anthracite"]
# Return inlet color options
INLET_COLOR_OPTIONS  = ["white","beige","light-grey","anthracite"]


# ══════════════════════════════════════════════════════════════════════════════
# 4. GEOMETRY & HYDRAULICS
# ══════════════════════════════════════════════════════════════════════════════

def compute_geometry(inp: PoolInputs):
    s = inp.width_m * inp.length_m
    v = s * inp.depth_m
    p = 2 * (inp.width_m + inp.length_m)
    return round(v,2), round(s,2), round(p,2)

def compute_design_flow(volume: float, pool_type: str):
    t = TURNOVER_HOURS.get(pool_type, 6.0)
    return t, round(volume / t, 2)


# ══════════════════════════════════════════════════════════════════════════════
# 5. EQUIPMENT SELECTORS
# ══════════════════════════════════════════════════════════════════════════════

def select_filter(comps, design_flow, pool_type):
    """
    Smallest adequate filter at target velocity cap.
    Preference: DIN airscouring (BEGUR/NORMA/TOR/BLANES) for overflow/infinity,
    standard laminated for skimmer. Bed depth 1.2 m preferred for DIN pools.
    """
    cap = FILTER_VELOCITY_CAP[pool_type]
    prefer_din = pool_type in ("overflow","infinity")
    candidates = []
    for c in comps:
        if c.row_type != "EQUIPMENT" or c.category != "FILTER":
            continue
        if not c.filtration_area_m2 or not c.filtration_velocity:
            continue
        max_flow = min(c.filtration_velocity, cap) * c.filtration_area_m2
        if max_flow < design_flow:
            continue
        is_din    = any(k in c.model for k in _AIRSCOURING_KW)
        mismatch  = int(prefer_din != is_din)
        depth     = c.bed_depth_m or 1.0
        candidates.append((max_flow, mismatch, -depth, c))
    if not candidates:
        # No single filter meets the flow — return the largest available (multiple units needed)
        all_filters = []
        for c in comps:
            if c.row_type != "EQUIPMENT" or c.category != "FILTER": continue
            if c.filtration_area_m2 and c.filtration_velocity:
                max_flow_c = c.filtration_area_m2 * c.filtration_velocity
                all_filters.append((max_flow_c, c))
        if all_filters:
            all_filters.sort(key=lambda x: x[0], reverse=True)
            return all_filters[0][1]  # return largest; caller adds warning
        return None
    candidates.sort(key=lambda x: x[:3])
    return candidates[0][3]


def select_pump(comps, design_flow, pool_type):
    """
    Smallest adequate pump with 10% headroom above design flow.
    Variable-speed pumps preferred for ErP compliance and energy savings.
    """
    min_flow = design_flow * 1.10
    candidates = []
    for c in comps:
        if c.row_type != "EQUIPMENT" or c.category != "PUMP":
            continue
        if not c.flow_rate_max or c.flow_rate_max < min_flow:
            continue
        is_vs = "Variable Speed" in c.subcategory or "VS" in c.model
        candidates.append((c.flow_rate_max, 0 if is_vs else 1, c))
    if not candidates:
        return None
    candidates.sort(key=lambda x: x[:2])
    return candidates[0][2]


def select_treatment(comps, volume_m3, design_flow, filtration_type):
    """
    Select water treatment. Returns (component, n_units).
    Chlorine demand = volume / 10 [g/h]. Multiple units if no single unit meets demand.
    chlorine   → pH/ORP controller (liquid dosing, no chlorinator)
    saltwater  → normal salinity electrolysis (5-6 g/L)
    magnesium  → low salinity electrolysis (2-2.5 g/L)
    """
    req = volume_m3 / 10.0

    if filtration_type == "chlorine":
        for c in comps:
            if c.row_type=="EQUIPMENT" and c.category=="WATER_TREATMENT":
                if "Controller" in c.model and "pH" in c.model:
                    return c, 1
        return None, 1

    subcats = (["Salt Electrolysis Normal"] if filtration_type == "saltwater"
               else ["Salt Electrolysis Low"])
    candidates = []
    for c in comps:
        if c.row_type != "EQUIPMENT" or c.category != "WATER_TREATMENT":
            continue
        if not any(s in c.subcategory for s in subcats):
            continue
        if c.flow_rate_min and design_flow < c.flow_rate_min:
            continue
        if not c.chlorine_output_g_h:
            continue
        candidates.append((c.chlorine_output_g_h, c))
    if not candidates:
        return None, 1
    candidates.sort(key=lambda x: x[0])
    for cap, c in candidates:
        if cap >= req:
            return c, 1
    # Need multiples of largest
    largest_cap, largest = candidates[-1]
    return largest, math.ceil(req / largest_cap)


def select_valve_manifold(comps, filter_comp):
    """5-valve manual manifold matched to filter outlet diameter."""
    if not filter_comp or not filter_comp.connection_mm:
        return None
    target = filter_comp.connection_mm
    manifolds = [c for c in comps
                 if c.row_type=="ACCESSORY" and c.category=="FILTER_ACCESSORY"
                 and "Manual 5V" in c.subcategory and c.connection_mm]
    exact = [m for m in manifolds if m.connection_mm == target]
    if exact:
        return exact[0]
    larger = [m for m in manifolds if m.connection_mm > target]
    return min(larger, key=lambda m: m.connection_mm) if larger else None


def select_filter_media(comps, filter_comp):
    """Sand + gravel (always). Anthracite for DIN airscouring filters. Perlite for FMR."""
    if not filter_comp:
        return []
    is_fmr = "FMR" in filter_comp.model
    media  = []
    for c in comps:
        if c.row_type != "ACCESSORY" or c.subcategory != "Filter Media":
            continue
        if is_fmr and c.code == "40001":
            media.append(c)
        elif not is_fmr and c.code in ("SAND-04-08","GRAVEL-1-2"):
            media.append(c)
        elif not is_fmr and c.code == "ANTHRACITE" and _is_airscouring(filter_comp):
            media.append(c)
    return media


def select_air_blower(comps, filter_comp, design_flow):
    """
    Air blower for airscouring filters (BEGUR, NORMA, TOR, BLANES).
    Required airflow ≈ 60 m³/h per m² filter area.
    Prefers 3-phase for commercial installations.
    """
    if not filter_comp or not _is_airscouring(filter_comp):
        return None
    req_air = (filter_comp.filtration_area_m2 or 0.5) * 60.0
    blowers = []
    for c in comps:
        if c.row_type=="ACCESSORY" and c.subcategory=="Air Blower":
            if c.flow_rate_max and c.flow_rate_max >= req_air:
                is_3ph = "3-phase" in c.notes
                blowers.append((c.flow_rate_max, 0 if is_3ph else 1, c))
    if not blowers:
        return None
    blowers.sort(key=lambda x: x[:2])
    return blowers[0][2]


def select_strainer(comps, pump_comp, design_flow):
    """Pump inlet strainer — Kivu/Aral Plus specific, else polyester GF by flow."""
    if not pump_comp:
        return None
    m = pump_comp.model.lower()
    # Kivu large centrifugal
    if "kivu" in m and any(x in pump_comp.code for x in ("56633","56634","56635","56637","56638","56639")):
        for c in comps:
            if c.code == "56733":
                return c
    # Aral Plus
    if "aral plus" in m:
        aral = [c for c in comps if c.row_type=="ACCESSORY" and "Aral Plus Strainer" in c.model
                and c.flow_rate_max and c.flow_rate_max >= design_flow]
        return min(aral, key=lambda c: c.flow_rate_max) if aral else None
    # General polyester
    conn = _pump_conn(pump_comp)
    for c in comps:
        if c.row_type=="ACCESSORY" and c.category=="PUMP_ACCESSORY":
            if ("Strainer GF" in c.subcategory or "Strainer SG" in c.subcategory):
                if c.connection_mm and c.connection_mm >= conn:
                    if c.flow_rate_max and c.flow_rate_max >= design_flow:
                        return c
    return None


def select_check_valve(comps, pump_comp):
    """Anti-return check valve ≥ pump outlet diameter, PN10."""
    if not pump_comp:
        return None
    conn = _pump_conn(pump_comp)
    vals = [c for c in comps if c.row_type=="ACCESSORY" and "Check Valve" in c.subcategory
            and c.connection_mm and c.connection_mm >= conn]
    return min(vals, key=lambda c: c.connection_mm) if vals else None


def select_vibration_damper(comps, pump_comp):
    """Polychloroprene vibration damper ≥ pump outlet diameter, PN10."""
    if not pump_comp:
        return None
    conn = _pump_conn(pump_comp)
    damps = [c for c in comps if c.row_type=="ACCESSORY" and "Vibration Damper" in c.subcategory
             and c.connection_mm and c.connection_mm >= conn]
    return min(damps, key=lambda c: c.connection_mm) if damps else None


def select_heater(comps, volume_m3, indoor):
    """
    Heat pump sized to pool volume (1 kW per 10 m³ minimum).
    Indoor → ProHeat IND (ducted centrifugal fan) preferred.
    Outdoor → full inverter preferred (best COP, ErP 2021 compliant).
    Excludes pure chillers.
    """
    req_kw = volume_m3 / 10.0
    candidates = []
    for c in comps:
        if c.row_type != "EQUIPMENT" or c.category != "HEATING":
            continue
        if not c.power_kw or c.power_kw < req_kw:
            continue
        if "Chiller" in c.subcategory and "Heat Pump" not in c.subcategory:
            continue
        is_ind = "Indoor" in c.subcategory or "IND" in c.model
        is_inv = "Inverter" in c.model or "Full Inverter" in c.subcategory
        pen = (0 if (indoor and is_ind) or (not indoor and not is_ind) else 3)
        candidates.append((c.power_kw, pen, 0 if is_inv else 1, c))
    if not candidates:
        # No single filter meets the flow — return the largest available (multiple units needed)
        all_filters = []
        for c in comps:
            if c.row_type != "EQUIPMENT" or c.category != "FILTER": continue
            if c.filtration_area_m2 and c.filtration_velocity:
                max_flow_c = c.filtration_area_m2 * c.filtration_velocity
                all_filters.append((max_flow_c, c))
        if all_filters:
            all_filters.sort(key=lambda x: x[0], reverse=True)
            return all_filters[0][1]  # return largest; caller adds warning
        return None
    candidates.sort(key=lambda x: x[:3])
    return candidates[0][3]


def select_dehumidifier(comps, surface_m2):
    """
    Indoor pool dehumidifier — ASHRAE: 0.15 l/h per m² pool surface.
    Standard model preferred (no electric heat / hot water coil option).
    CAE ducted for small pools, OMEGA for larger.
    """
    req = surface_m2 * 0.15
    candidates = []
    for c in comps:
        if c.row_type != "EQUIPMENT" or c.category != "DEHUMIDIFICATION":
            continue
        parts = c.model.split()
        cap = None
        for i, p in enumerate(parts):
            if p == "l/h" and i > 0:
                try: cap = float(parts[i-1])
                except: pass
        if not cap or cap < req:
            continue
        is_std = not any(x in c.model for x in ("Condenser","Electric Heat","Hot Water Coil"))
        candidates.append((cap, 0 if is_std else 1, c))
    if not candidates:
        return None
    candidates.sort(key=lambda x: x[:2])
    return candidates[0][2]


def select_main_drains(comps, design_flow, pool_type):
    """
    Minimum 2 main drains (EN 16582-1 anti-entrapment).
    Each drain: design_flow / 2. NORM/anti-vortex for overflow/infinity pools.
    """
    fpd = design_flow / 2.0
    prefer_norm = pool_type in ("overflow","infinity")
    candidates = []
    for c in comps:
        if c.row_type != "EQUIPMENT" or c.category != "POOL_SHELL":
            continue
        if "Main Drain" not in c.subcategory or not c.flow_rate_max:
            continue
        if c.flow_rate_max < fpd:
            continue
        is_norm = "NORM" in c.subcategory or "Anti-Vortex" in c.subcategory
        if prefer_norm and not is_norm:
            continue
        candidates.append((c.flow_rate_max, c))
    if not candidates:
        candidates = [(c.flow_rate_max, c) for c in comps
                      if c.row_type=="EQUIPMENT" and "Main Drain" in c.model
                      and c.flow_rate_max and c.flow_rate_max >= fpd]
    if not candidates:
        return []
    candidates.sort(key=lambda x: x[0])
    best = candidates[0][1]
    return [best, best]


def select_return_inlets(comps, design_flow, pool_type, surface_m2, inlet_color="white"):
    """
    1 inlet per 15 m² pool surface (min 2). Large-flow inlets for overflow/infinity.
    """
    n = max(2, math.ceil(surface_m2 / 15))
    fpn = design_flow / n
    if pool_type in ("overflow","infinity"):
        for c in comps:
            if c.code == "41520":
                return [c] * n
    for c in comps:
        if c.row_type=="EQUIPMENT" and c.category=="POOL_SHELL":
            if "Adjustable" in c.model and c.flow_rate_max and c.flow_rate_max >= fpn:
                return [c] * n
    fallback = [c for c in comps if c.row_type=="EQUIPMENT" and c.category=="POOL_SHELL"
                and "Return Inlet" in c.subcategory
                and (not c.flow_rate_max or c.flow_rate_max >= fpn)]
    return [fallback[0]] * n if fallback else []


def select_overflow_grilles(comps, pool_type, perimeter_m, grille_color="white"):
    """
    Overflow channel grilles for overflow/infinity pools.
    500mm longitudinal sections preferred; qty = ceil(perimeter / 0.5).
    """
    if pool_type not in ("overflow","infinity"):
        return []
    n = math.ceil(perimeter_m / 0.5)
    for code in ("28664","05582"):
        for c in comps:
            if c.row_type=="EQUIPMENT" and c.code == code:
                return [c] * n
    return []


# ══════════════════════════════════════════════════════════════════════════════
# 6. DECORATIVE SELECTORS
# ══════════════════════════════════════════════════════════════════════════════

def select_liner(comps, pool_type, liner_style="standard", liner_color="light-blue"):
    """
    Select pool liner / membrane by style.
    Overflow pools have no liner (wet-edge concrete + tile finish).

    Liner styles:
      standard  → Alkorplan 2000 (versatile, most common)
      touch     → Alkorplan Touch (premium 3D tactile embossing)
      ceramics  → Alkorplan Ceramics (mosaic-look, anti-slip)
      vogue     → Alkorplan Vogue (fashion-forward, strongest)
      alive     → Alkorplan ALIVE (eco, 3 nature colours)
      3000      → Alkorplan 3000 (lacquered multi-layer protection)
      uni-basic → AstralPool UNI Basic (budget entry)
      uni-plus  → AstralPool UNI Plus (budget mid)

    Available colors per style: see LINER_COLOR_PALETTE constant.
    """
    if pool_type == "overflow":
        return None   # overflow pools → tiled concrete, no membrane
    target = LINER_STYLES.get(liner_style.lower(), LINER_STYLES["standard"])
    for c in comps:
        if c.row_type=="EQUIPMENT" and c.category=="POOL_LINING" and c.model==target:
            return c
    for c in comps:
        if c.row_type=="EQUIPMENT" and c.category=="POOL_LINING":
            return c
    return None


def select_liner_accessories(comps, liner_comp):
    """
    Mandatory liner accessories: geotextile underlay, style-matched seam sealer, adhesive.
    """
    if not liner_comp:
        return []
    acc = []
    ml  = liner_comp.model.lower()

    # Geotextile underlay (always)
    for c in comps:
        if c.row_type=="ACCESSORY" and c.category=="POOL_LINING" and "Geotextile" in c.model:
            acc.append(c); break

    # Matched seam sealer
    kw = ("TOUCH" if "touch" in ml else "VOGUE" if "vogue" in ml
          else "ALIVE" if "alive" in ml else "CERAMICS" if "ceramics" in ml
          else "Alkorplus Seam Sealer")
    for c in comps:
        if c.row_type=="ACCESSORY" and c.category=="POOL_LINING":
            if kw in c.model and "Seam" in c.model:
                acc.append(c); break

    # Adhesive
    for c in comps:
        if c.row_type=="ACCESSORY" and c.category=="POOL_LINING" and "Adhesive" in c.model:
            acc.append(c); break

    return acc


def select_lighting(comps, surface_m2, light_color="rgbw"):
    """
    LumiPlus Flexi Connect lights. 1 per 25 m², min 2.
    Colors: white / warm-white / tunable-white / rgb / rgbw.
    All models are Fluidra Connect compatible and smartphone-controllable.
    """
    n    = max(2, math.ceil(surface_m2 / 25))
    code = LIGHT_COLOR_CODES.get(light_color.lower(), "76600MW")
    for c in comps:
        if c.row_type=="EQUIPMENT" and c.category=="POOL_LIGHTING" and c.code==code:
            return [c] * n
    for c in comps:
        if c.row_type=="EQUIPMENT" and c.category=="POOL_LIGHTING" and "Flexi Connect" in c.model:
            return [c] * n
    return []


def select_light_niches(comps, n_lights, pool_type):
    """
    Light niches: concrete 230mm for overflow/commercial; liner-insert for skimmer.
    """
    if not n_lights:
        return []
    code = "17805" if pool_type == "skimmer" else "00349"
    for c in comps:
        if c.row_type=="ACCESSORY" and c.code==code:
            return [c] * n_lights
    return []


def select_light_transformer(comps, n_lights, watts_each=27.0):
    """
    Transformer 230V→12VAC. 38 VA per Flexi Connect lamp.
    130VA → ≤3 lamps; 300VA → ≤7; 600VA → ≤15; multiples of 600VA above that.
    """
    if not n_lights:
        return None
    total_va = n_lights * watts_each / 0.7   # PF ≈ 0.7
    for max_va, code in [(130,"00383-4146"),(300,"71436"),(600,"00385-4146")]:
        if total_va <= max_va:
            for c in comps:
                if c.row_type=="ACCESSORY" and c.code==code:
                    return c
    for c in comps:
        if c.row_type=="ACCESSORY" and c.code=="00385-4146":
            return c
    return None


def select_pool_surround(comps, pool_type, ladder_type="standard"):
    """
    Mandatory pool surround per EN 13451-1/2 and public pool regulations.
    Includes: ladder (type-selectable), exit grab rails, entry shower tunnel,
    footbath, lifebuoy + holder.

    Ladder types:
      standard      → AISI-316L 2–5 step (general pools)
      pmr           → Disabled access non-slip (public/hotel pools)
      overflow-1000 → Designed for overflow channel edge
    """
    selected = []
    found    = set()
    lkw = {"standard":"Standard Pool Ladder","pmr":"PMR Public Ladder",
           "overflow-1000":"Overflow 1000 Ladder"}.get(ladder_type,"Standard Pool Ladder")

    for c in comps:
        if c.row_type!="EQUIPMENT" or c.category!="POOL_SURROUND":
            continue
        if "ladder" not in found and "Ladder" in c.subcategory and lkw in c.model and "2-step" in c.model:
            selected.append(c); found.add("ladder")
        elif "grab" not in found and "Grab Rail" in c.subcategory and "Exit" in c.model and "Embedded" in c.model:
            selected.append(c); found.add("grab")
        elif "shower" not in found and "Shower" in c.subcategory and "Tunnel" in c.model and "3 Heads" in c.model:
            selected.append(c); found.add("shower")
        elif "footbath" not in found and "Footbath" in c.subcategory:
            selected.append(c); found.add("footbath")
        elif "lifebuoy" not in found and "Life Saving" in c.subcategory and "Lifebuoy Ø" in c.model:
            selected.append(c); found.add("lifebuoy")
        elif "holder" not in found and "Life Saving" in c.subcategory and "Holder" in c.model:
            selected.append(c); found.add("holder")
    return selected


def select_automation(comps, pump_comp):
    """Connect & Go cabinet: VS cabinet for variable-speed pumps, SMART for fixed-speed."""
    if not pump_comp:
        return None
    hp = pump_comp.power_hp or 0
    if "VS" in pump_comp.model:
        for label, lim in [("3HP",3.5),("5.5HP",5.5),("7.5HP",99)]:
            if hp <= lim:
                for c in comps:
                    if c.row_type=="ACCESSORY" and "VS" in c.model and label in c.model:
                        return c
    for label, lim in [("3HP",3),("5.5HP",5.5),("7.5HP",7.5),("10HP",10),("12HP",99)]:
        if hp <= lim:
            for c in comps:
                if c.row_type=="ACCESSORY" and "SMART" in c.model and label in c.model:
                    return c
    return None


def select_robot_cleaner(comps, length_m):
    """Robot cleaner by pool length: ≤20m TRX-8500, ≤25m TRX-8700, ≤30m Arco, >30m Arcomax."""
    for lim, kw in [(20,"8500"),(25,"8700"),(30,"Arco"),(999,"Arcomax")]:
        if length_m <= lim:
            for c in comps:
                if c.row_type=="EQUIPMENT" and c.category=="CLEANING" and kw in c.model:
                    return c
    return None


# ══════════════════════════════════════════════════════════════════════════════
# 7. ENGINE ROOM ESTIMATOR
# ══════════════════════════════════════════════════════════════════════════════

def estimate_engine_room(r: CalculationResult) -> float:
    """
    Engine room floor area (m²) from equipment footprints + clearances.
    Filter footprint derived from tank cross-section + 0.8m all-round clearance.
    Minimum 6 m² regardless of pool size.
    """
    area = 0.0
    if r.filter:
        fa  = r.filter.filtration_area_m2 or 0.5
        dm  = math.sqrt(4 * fa / math.pi)       # tank diameter (m)
        area += (dm + 0.8) ** 2                  # square envelope + clearance
    if r.pump:
        area += 0.6 + (r.pump.power_hp or 3) * 0.06
    if r.treatment:
        area += 0.6 * r.n_chlorinators
    if r.heater:
        area += 0.8 + (r.heater.power_kw or 30) * 0.015
    if r.dehumidifier:
        area += 1.5
    area += 1.5   # chemical tanks + dosing
    area += 0.8   # automation cabinet
    area += 2.0   # walkways + clearance
    return round(max(area, 6.0), 1)


# ══════════════════════════════════════════════════════════════════════════════
# 8. BOM BUILDER
# ══════════════════════════════════════════════════════════════════════════════

def build_bom(r: CalculationResult) -> list:
    bom = []

    def add(c, qty=1, note=""):
        if c:
            bom.append({"category":c.category,"subcategory":c.subcategory,
                        "brand":c.brand,"model":c.model,"code":c.code,
                        "qty":qty,"note":note or c.notes})

    def add_list(lst, note=""):
        from collections import Counter
        if not lst: return
        counts = Counter(c.code for c in lst)
        seen   = set()
        for c in lst:
            if c.code not in seen:
                add(c, qty=counts[c.code], note=note)
                seen.add(c.code)

    add(r.filter,         note="Primary filter — sized to design flow / DIN velocity cap")
    add(r.valve_manifold, note="5-valve manual manifold — filter backwash circuit")
    add_list(r.filter_media, note="Filter media — quantities per catalog pp. 159–161")
    add(r.air_blower,     note="Air blower — airscouring (BEGUR/NORMA/TOR/BLANES filters)")
    add(r.pump,           note="Main circulation pump — 10% headroom, VS preferred (ErP)")
    add(r.strainer,       note="Pump inlet pre-strainer — impeller protection")
    add(r.check_valve,    note="Anti-return check valve — PN10")
    add(r.vibration_damper,note="Vibration damper (Polychloroprene) — PN10")
    add(r.treatment, qty=r.n_chlorinators,
        note="Water treatment" + (f" — {r.n_chlorinators}× parallel (AP PR-200 + TRI kit required)"
             if r.n_chlorinators > 1 else ""))
    add(r.heater,         note="Pool water heater — full inverter R32/R410A preferred")
    add(r.dehumidifier,   note="Indoor pool dehumidifier — ducted, Hygro Control supplied")
    add_list(r.main_drains,     note="Main drains — min 2 per EN 16582-1 anti-entrapment")
    add_list(r.return_inlets,   note="Wall return inlets — 1 per 15 m² pool surface")
    add_list(r.overflow_grilles,note="Overflow channel grilles — perimeter coverage")
    add(r.liner,          note="Pool lining membrane — measured and cut on site")
    add_list(r.liner_accessories, note="Liner installation accessories")
    add_list(r.lighting,         note="Underwater LED — 1 per 25 m², Fluidra Connect")
    add_list(r.light_niches,     note="Light niches — 1 per projector")
    add(r.light_transformer,     note="Lighting transformer 230V → 12VAC")
    add_list(r.pool_surround,    note="Mandatory pool surround — EN 13451-1/2")
    add(r.automation,    note="Pump automation cabinet — Connect & Go pre-wired")
    add(r.robot_cleaner, note="Automatic pool cleaner — sized to pool length")
    return bom


# ══════════════════════════════════════════════════════════════════════════════
# 9. MAIN ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

def calculate(inp: PoolInputs, csv_path: str = CSV_PATH) -> CalculationResult:
    """Full pool calculation pipeline — geometry → hydraulics → equipment → BOM."""
    comps = load_components(csv_path)
    volume, surface, perimeter = compute_geometry(inp)
    turnover, design_flow      = compute_design_flow(volume, inp.pool_type)

    r = CalculationResult(volume_m3=volume, surface_m2=surface, perimeter_m=perimeter,
                          turnover_hours=turnover, design_flow_m3h=design_flow)

    r.filter           = select_filter(comps, design_flow, inp.pool_type)
    r.pump             = select_pump(comps, design_flow, inp.pool_type)
    r.valve_manifold   = select_valve_manifold(comps, r.filter)
    r.filter_media     = select_filter_media(comps, r.filter)
    r.air_blower       = select_air_blower(comps, r.filter, design_flow)
    r.strainer         = select_strainer(comps, r.pump, design_flow)
    r.check_valve      = select_check_valve(comps, r.pump)
    r.vibration_damper = select_vibration_damper(comps, r.pump)

    r.treatment, r.n_chlorinators = select_treatment(
        comps, volume, design_flow, inp.filtration)

    if inp.heating:
        r.heater = select_heater(comps, volume, inp.indoor)
    if inp.indoor:
        r.dehumidifier = select_dehumidifier(comps, surface)

    r.main_drains      = select_main_drains(comps, design_flow, inp.pool_type)
    r.return_inlets    = select_return_inlets(comps, design_flow, inp.pool_type, surface, inp.inlet_color)
    r.overflow_grilles = select_overflow_grilles(comps, inp.pool_type, perimeter, inp.grille_color)

    r.liner              = select_liner(comps, inp.pool_type, inp.liner_style, inp.liner_color)
    r.liner_accessories  = select_liner_accessories(comps, r.liner)
    r.lighting           = select_lighting(comps, surface, inp.light_color)
    r.light_niches       = select_light_niches(comps, len(r.lighting), inp.pool_type)
    r.light_transformer  = select_light_transformer(comps, len(r.lighting))
    r.pool_surround      = select_pool_surround(comps, inp.pool_type, inp.ladder_type)
    r.automation         = select_automation(comps, r.pump)
    r.robot_cleaner      = select_robot_cleaner(comps, inp.length_m)
    r.engine_room_m2     = estimate_engine_room(r)
    r.bom                = build_bom(r)

    # Warnings
    if not r.filter:
        r.warnings.append("⚠ No filter found for this flow rate.")
    if not r.pump:
        r.warnings.append("⚠ No pump found for this flow rate.")
    if not r.treatment:
        r.warnings.append("⚠ No water treatment matched.")
    if r.n_chlorinators > 1:
        r.warnings.append(f"⚠ {r.n_chlorinators}× chlorinators in parallel required — AP PR-200 + TRI kit needed.")
    if inp.pool_type in ("overflow","infinity") and not r.overflow_grilles:
        r.warnings.append("⚠ Overflow grilles not selected — specify manually.")
    if inp.indoor and not r.dehumidifier:
        r.warnings.append("⚠ No dehumidifier matched — surface area may require multiple units.")
    if not r.check_valve:
        r.warnings.append("⚠ Check valve not matched — select manually by pipe size.")
    if not r.vibration_damper:
        r.warnings.append("⚠ Vibration damper not matched — select manually.")

    return r


# ══════════════════════════════════════════════════════════════════════════════
# 10. CLI TEST RUNNER
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    tests = [
        ("Small skimmer — chlorine — Touch liner",
         PoolInputs(4,8,1.4,"skimmer","chlorine",heating=True,
                    liner_style="touch",liner_color="elegance",
                    light_color="rgb",ladder_type="standard")),
        ("Hotel overflow — saltwater",
         PoolInputs(8,16,1.5,"overflow","saltwater",heating=True,
                    light_color="rgbw",ladder_type="overflow-1000")),
        ("Indoor infinity — magnesium — vogue liner",
         PoolInputs(6,12,1.5,"infinity","magnesium",indoor=True,heating=True,
                    liner_style="vogue",drain_color="anthracite",
                    light_color="warm-white",ladder_type="pmr")),
        ("Large competition — overflow — saltwater",
         PoolInputs(12.5,25,2.0,"overflow","saltwater",heating=True)),
    ]

    for name, inp in tests:
        r = calculate(inp)
        print(f"\n{'='*65}\n  {name}\n{'='*65}")
        print(f"  {inp.width_m}×{inp.length_m}×{inp.depth_m}m | "
              f"Vol={r.volume_m3}m³ | Flow={r.design_flow_m3h}m³/h | Turnover={r.turnover_hours}h")
        rows = [
            ("Filter",           r.filter),
            ("Pump",             r.pump),
            ("Treatment",        r.treatment),
            ("Manifold",         r.valve_manifold),
            ("Air Blower",       r.air_blower),
            ("Strainer",         r.strainer),
            ("Check Valve",      r.check_valve),
            ("Vib. Damper",      r.vibration_damper),
            ("Heater",           r.heater),
            ("Dehumidifier",     r.dehumidifier),
            ("Liner",            r.liner),
            ("Automation",       r.automation),
            ("Robot",            r.robot_cleaner),
        ]
        for label, comp in rows:
            val = comp.model if comp else "—"
            print(f"  {label:15s}: {val}")
        print(f"  {'Lighting':15s}: {len(r.lighting)}× "
              f"{r.lighting[0].model if r.lighting else '—'}")
        print(f"  {'Main Drains':15s}: {len(r.main_drains)}×")
        print(f"  {'Return Inlets':15s}: {len(r.return_inlets)}×")
        print(f"  {'Overflow Grilles':15s}: {len(r.overflow_grilles)} sections")
        print(f"  {'Engine Room':15s}: ~{r.engine_room_m2} m²")
        print(f"  {'BOM':15s}: {len(r.bom)} line items")
        if r.warnings:
            print("  WARNINGS:")
            for w in r.warnings: print(f"    {w}")
