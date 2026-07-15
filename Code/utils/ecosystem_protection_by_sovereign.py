#!/usr/bin/env python3
"""
Per-sovereign protection of ecosystem extents (raster or vector), in Mollweide (ESRI:54009).

Overlays each ecosystem with the EEZ+Land-by-sovereign layer and the WDPA MPA/OECM layer,
reporting per-sovereign extent and the share within MPAs / OECMs / either, plus a global
rollup. Protected and jurisdiction layers are prepared once (Mollweide, buffer0) and cached
to geoparquet, then reused across every input.

  python ecosystem_protection_by_sovereign.py --raster <eco1.shp> [<eco2.tif> ...]

Outputs per input (charts_2026/): <stem>_protection_by_sovereign.csv/.gpkg,
<stem>_ecosystem_extent.json, <stem>_protection.json.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from rasterio.features import shapes
from shapely import set_precision, union_all
from shapely.errors import GEOSException
from shapely.geometry import shape

AREA_CRS = "ESRI:54009"  # Mollweide (World), equal-area
OUT_CRS = "EPSG:4326"


def log(m: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


def runion(geoms):
    """union_all, retrying on GEOS non-noded-intersection errors by snapping to a
    progressively coarser grid (<=1 m in Mollweide is negligible for km² areas)."""
    try:
        return union_all(geoms)
    except GEOSException:
        for gs in (1e-3, 1e-2, 1e-1, 1.0):
            try:
                return union_all(set_precision(np.asarray(geoms, dtype=object), gs))
            except GEOSException:
                continue
        raise


def fix(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    # buffer(0) repairs validity and coerces to polygons. NOTE: it inflates antimeridian-
    # crossing degree-circle polygons after reprojection to Mollweide — this is fine for the
    # coastal/EEZ layers here (none cross the dateline pathologically) but NOT for the seamount
    # base-area vector, which is computed separately (see docs / QGIS method) at ~16.4%.
    gdf = gdf.copy()
    gdf["geometry"] = gdf.geometry.buffer(0)
    return gdf[~gdf.geometry.is_empty & gdf.geometry.notna()]


def cached(cache: Path, src: Path, build):
    """Return a geoparquet cache, rebuilding if missing or older than `src`."""
    if cache.exists() and cache.stat().st_mtime >= src.stat().st_mtime:
        log(f"  cache hit: {cache.name}")
        return gpd.read_parquet(cache)
    gdf = build()
    cache.parent.mkdir(parents=True, exist_ok=True)
    gdf.to_parquet(cache)
    log(f"  cached -> {cache.name}")
    return gdf


def dissolve_area(ov: gpd.GeoDataFrame, by: str = "sovereign") -> pd.Series:
    if ov.empty:
        return pd.Series(dtype=float)
    rows = {k: runion(sub.geometry.values).area / 1e6 for k, sub in ov.groupby(by, sort=False)}
    return pd.Series(rows, name="km2")


def total_km2(gdf: gpd.GeoDataFrame) -> float:
    if gdf.empty:
        return 0.0
    return float(runion(gdf.geometry.values).area / 1e6)


def collapse_high_seas(df: pd.DataFrame, base_col: str, global_total: float | None = None,
                       dp: int = 1) -> pd.DataFrame:
    """Merge the per-sea 'High Seas of X' rows into one 'High Seas' row (regions are
    disjoint, so km² sum exactly); recompute % columns from the summed totals."""
    m = df["sovereign"].astype(str).str.startswith("High Seas")
    if "iso_sov1" in df.columns:
        m = m | df["iso_sov1"].isna()
    if int(m.sum()) == 0:
        return df
    hs, eez = df[m], df[~m]
    row = {c: round(float(hs[c].sum()), dp) for c in df.columns if c.endswith("_km2")}
    row["sovereign"] = "High Seas"
    if "iso_sov1" in df.columns:
        row["iso_sov1"] = None
    if "is_high_seas" in df.columns:
        row["is_high_seas"] = True
    base = row.get(base_col, 0.0)
    for c in df.columns:
        if c.endswith("_pct") and c != "pct_of_global_ecosystem":
            row[c] = round(row[c[:-4] + "_km2"] / base * 100, dp) if base else 0.0
    if "pct_of_global_ecosystem" in df.columns and global_total:
        row["pct_of_global_ecosystem"] = round(row["ecosystem_km2"] / global_total * 100, dp)
    return pd.concat([eez, pd.DataFrame([row])], ignore_index=True)


VECTOR_EXT = {".shp", ".gpkg", ".geojson", ".json", ".fgb"}


def vectorize(raster: Path) -> gpd.GeoDataFrame:
    """Polygons of raster cells with value > 0, in AREA_CRS (cells don't overlap)."""
    with rasterio.open(raster) as src:
        data = src.read(1)
        mask = data > 0
        if src.nodata is not None:
            mask &= (data != src.nodata)
        geoms = [shape(g) for g, _ in shapes(data, mask=mask, transform=src.transform)]
        rcrs = src.crs
    log(f"  {len(geoms):,} cell-polygons")
    g = gpd.GeoDataFrame(geometry=geoms, crs=rcrs).to_crs(AREA_CRS)
    return fix(g)


def load_ecosystem(path: Path):
    """Return (eco polygons in AREA_CRS, is_raster). Raster -> vectorize cells (value>0,
    non-overlapping). Vector -> read (multi)polygons directly, kept as parts for
    index-friendly overlays (overlap handled by union/dissolve where area is computed)."""
    if path.suffix.lower() in VECTOR_EXT:
        g = gpd.read_file(path).to_crs(AREA_CRS)
        g = g[g.geometry.geom_type.isin(["Polygon", "MultiPolygon"])]
        # make_valid (not buffer0) for the ECOSYSTEM only: buffer0 inflates antimeridian-
        # crossing degree-circle polygons (seamount bases ~3x) after reprojection; make_valid
        # + dropping the resulting non-polygon collection artifacts repairs them. Identical for
        # coastal ecosystems (no pathological crossers). Juris/protected keep buffer0 (fix()),
        # whose complex multipolygons must NOT be dropped.
        g["geometry"] = g.geometry.make_valid()
        g = g[~g.geometry.is_empty & g.geometry.notna()]
        g = g[g.geometry.geom_type.isin(["Polygon", "MultiPolygon"])]
        log(f"  {len(g):,} polygon features (vector)")
        return g[["geometry"]], False
    return vectorize(path), True


def process(raster: Path, juris: gpd.GeoDataFrame, prot: gpd.GeoDataFrame, repo: Path) -> None:
    stem = raster.stem
    log(f"=== {stem} ===")
    log("Loading ecosystem extent ...")
    eco, is_raster = load_ecosystem(raster)
    eco["eco_km2"] = eco.geometry.area / 1e6
    # raster cells sum exactly; vector polygons may overlap, so dissolve for true area
    global_eco_km2 = float(eco["eco_km2"].sum() if is_raster
                           else runion(eco.geometry.values).area / 1e6)
    log(f"  total global ecosystem extent = {global_eco_km2:,.0f} km²")

    log("Overlay: ecosystem × jurisdictions ...")
    eez_eco = gpd.overlay(juris, eco[["geometry"]], how="intersection", keep_geom_type=True)
    eez_eco["eco_km2"] = eez_eco.geometry.area / 1e6
    eco_by_sov = (eez_eco.groupby("sovereign")["eco_km2"].sum() if is_raster
                  else dissolve_area(eez_eco, by="sovereign"))

    log("Overlay: protected × ecosystem ...")
    prot_eco = gpd.overlay(prot, eco[["geometry"]], how="intersection", keep_geom_type=True)
    log("Overlay: (protected ∩ ecosystem) × jurisdictions ...")
    prot_eco_sov = gpd.overlay(prot_eco, juris[["sovereign", "geometry"]],
                               how="intersection", keep_geom_type=True)

    mpa = dissolve_area(prot_eco_sov[prot_eco_sov["PA_DEF"] == "1"])
    oecm = dissolve_area(prot_eco_sov[prot_eco_sov["PA_DEF"] == "0"])
    comb = dissolve_area(prot_eco_sov)

    df = juris[["sovereign", "iso_sov1"]].drop_duplicates("sovereign").copy()
    df["is_high_seas"] = df["iso_sov1"].isna()
    df["ecosystem_km2"] = df["sovereign"].map(eco_by_sov).fillna(0.0)
    df["mpa_km2"] = df["sovereign"].map(mpa).fillna(0.0)
    df["oecm_km2"] = df["sovereign"].map(oecm).fillna(0.0)
    df["combined_km2"] = df["sovereign"].map(comb).fillna(0.0)
    e = df["ecosystem_km2"].values
    # share of the GLOBAL ecosystem extent that sits in this EEZ
    df["pct_of_global_ecosystem"] = (e / global_eco_km2 * 100).round(1) if global_eco_km2 else 0.0
    # share of THIS EEZ's ecosystem that is protected
    for t in ("mpa", "oecm", "combined"):
        df[f"{t}_pct"] = np.where(e > 0, df[f"{t}_km2"] / e * 100, 0.0).round(1)
    for c in ["ecosystem_km2", "mpa_km2", "oecm_km2", "combined_km2"]:
        df[c] = df[c].round(1)
    # keep high-seas rows even at 0 extent so collapse always emits a High Seas row
    df = df[(df["ecosystem_km2"] > 0) | df["is_high_seas"]].sort_values("ecosystem_km2", ascending=False)
    df = collapse_high_seas(df, "ecosystem_km2", global_eco_km2)  # 26 high-seas seas -> 1

    out_csv = repo / f"charts_2026/{stem}_protection_by_sovereign.csv"
    out_gpkg = repo / f"charts_2026/{stem}_protection_by_sovereign.gpkg"
    out_extent = repo / f"charts_2026/{stem}_ecosystem_extent.json"
    out_prot = repo / f"charts_2026/{stem}_protection.json"
    df.to_csv(out_csv, index=False)
    # geometry per sovereign, high-seas seas dissolved into one "High Seas"
    grp = np.where(eez_eco["iso_sov1"].isna() | eez_eco["sovereign"].astype(str).str.startswith("High Seas"),
                   "High Seas", eez_eco["sovereign"])
    tmp = eez_eco.assign(sovereign=grp)
    gg = gpd.GeoDataFrame(
        [{"sovereign": k, "geometry": runion(sub.geometry.values)}
         for k, sub in tmp.groupby("sovereign", sort=False)], crs=eez_eco.crs)
    gout = gpd.GeoDataFrame(
        gg.merge(df.drop(columns=[c for c in ["is_high_seas"] if c in df.columns]),
                 on="sovereign", how="right"),
        geometry="geometry", crs=eez_eco.crs)
    out_gpkg.unlink(missing_ok=True)  # overwrite cleanly (avoid appending a stale layer)
    gout.to_crs(OUT_CRS).to_file(out_gpkg, driver="GPKG", layer=stem[:60])

    in_eez = float(df.loc[~df["is_high_seas"], "ecosystem_km2"].sum())
    in_hs = float(df.loc[df["is_high_seas"], "ecosystem_km2"].sum())
    g = global_eco_km2 or 1.0
    # JSON 1: ecosystem extent (Fig-2 / Fig-3 facts) — kept separate from protection
    extent = {
        "ecosystem": stem, "area_crs": AREA_CRS,
        "total_global_ecosystem_km2": round(global_eco_km2, 1),
        "within_eez_km2": round(in_eez, 1),
        "pct_of_global_in_eez": round(in_eez / g * 100, 1),
        "within_high_seas_km2": round(in_hs, 1),
        "pct_of_global_in_high_seas": round(in_hs / g * 100, 1),
    }
    # JSON 2: protection (Fig-6 facts)
    protection = {
        "ecosystem": stem, "area_crs": AREA_CRS,
        "total_global_ecosystem_km2": round(global_eco_km2, 1),
        "within_protected_combined_km2": round(total_km2(prot_eco), 1),
        "within_protected_mpa_km2": round(total_km2(prot_eco[prot_eco["PA_DEF"] == "1"]), 1),
        "within_protected_oecm_km2": round(total_km2(prot_eco[prot_eco["PA_DEF"] == "0"]), 1),
    }
    protection["pct_of_global_protected"] = round(protection["within_protected_combined_km2"] / g * 100, 1)
    out_extent.write_text(json.dumps(extent, indent=2))
    out_prot.write_text(json.dumps(protection, indent=2))
    log(f"  wrote {out_csv.name}, {out_gpkg.name}, {out_extent.name}, {out_prot.name}")
    print(f"  total={global_eco_km2:,.0f} km² | in EEZ {extent['pct_of_global_in_eez']:.1f}% "
          f"| protected {protection['pct_of_global_protected']:.1f}% of extent")


def main() -> int:
    repo = Path("/Users/laura/Projects/ocean-central")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--raster", type=Path, nargs="+", required=True,
                    help="One or more binary ecosystem presence rasters (value 1 = present).")
    ap.add_argument("--jurisdictions", type=Path,
                    default=repo / "sandbox/overlay_polygons/eez_land_by_sovereign_3857.gpkg")
    ap.add_argument("--protected", type=Path,
                    # one-row-per-PA (chopped pieces dissolved) -> far fewer overlay inputs
                    default=repo / "data/wdpa_gee/wdpa_gee_202511_protected_dissolved.gpkg")
    args = ap.parse_args()
    for p in [args.jurisdictions, args.protected, *args.raster]:
        if not p.exists():
            print(f"ERROR: not found: {p}", file=sys.stderr)
            return 1

    cache = repo / "charts_2026/_cache"

    def build_juris():
        log("Preparing jurisdictions (Mollweide, buffer0) ...")
        j = gpd.read_file(args.jurisdictions).to_crs(AREA_CRS)
        j = j.rename(columns={"ISO_SOV1": "iso_sov1"})[["sovereign", "iso_sov1", "geometry"]]
        return fix(j)

    def build_prot():
        log("Preparing protected (Mollweide, all PA_DEF tiers, buffer0) — slow, cached after ...")
        pa = gpd.read_file(args.protected).to_crs(AREA_CRS)
        pa["PA_DEF"] = pa["PA_DEF"].astype(str).str.strip()
        # NO MARINE filter: the new layer is the all-PA (GIS_M_AREA>0, incl marine-sliver) +
        # OECM set built upstream; tiering keys off PA_DEF (1=MPA, 0=OECM). Keep everything.
        return fix(pa)[["PA_DEF", "geometry"]]

    juris = cached(cache / "juris_moll.parquet", args.jurisdictions, build_juris)
    prot = cached(cache / "protected_moll.parquet", args.protected, build_prot)
    log(f"jurisdictions={len(juris)}, protected={len(prot)}")

    for r in args.raster:
        process(r, juris, prot, repo)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())