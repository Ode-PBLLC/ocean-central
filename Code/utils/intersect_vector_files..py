import geopandas as gpd
from pathlib import Path

def intersect_ecosystem_with_mpa(
    ecosystem_path: str,
    mpa_path: str,
    out_intersection: str | None = None,
):
    """
    Compute the geometric intersection (ecosystem ∩ MPA)
    and optionally save as GeoJSON.

    - Intersection geometries & attributes come from ECOSYSTEM layer.
    - No area calculations.
    """

    # Load datasets
    gdf_ecosystem = gpd.read_file(ecosystem_path)
    gdf_mpa       = gpd.read_file(mpa_path)

    # If ecosystem is empty, return empty result
    if gdf_ecosystem.empty:
        print("Ecosystem dataset is empty.")
        return gpd.GeoDataFrame(geometry=[])

    # Fast bounding-box prefilter
    pref_idx = gpd.sjoin(
        gdf_mpa[["geometry"]],
        gdf_ecosystem[["geometry"]],
        predicate="intersects",
        how="inner"
    )["index_right"].unique()

    if len(pref_idx) == 0:
        print("No intersections found.")
        return gpd.GeoDataFrame(geometry=[])

    gdf_ecosystem_pref = gdf_ecosystem.loc[pref_idx]

    # Exact intersection — ecosystem first so resulting geometry/attrs come from ecosystem
    inter = gpd.overlay(gdf_ecosystem_pref, gdf_mpa, how="intersection")

    # Keep only ecosystem attributes + geometry
    inter = inter[gdf_ecosystem_pref.columns]

    # Optional output
    if out_intersection:
        out_path = Path(out_intersection)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        inter.to_file(out_path, driver="GeoJSON")
        print(f"Saved intersection to: {out_path}")

    print(f"Intersection features: {len(inter)}")
    return inter


if __name__ == "__main__":
    # User input for paths
    ecosystem_path = input("Path to ecosystem file: ").strip()
    mpa_path       = input("Path to protected areas file: ").strip()
    out_geojson    = input("Output GeoJSON path (leave empty to skip saving): ").strip()

    if out_geojson == "":
        out_geojson = None

    result = intersect_ecosystem_with_mpa(
        ecosystem_path=ecosystem_path,
        mpa_path=mpa_path,
        out_intersection=out_geojson,
    )

    print(result)

