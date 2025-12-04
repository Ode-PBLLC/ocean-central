import rasterio
from rasterio.features import shapes
import geopandas as gpd
from shapely.geometry import shape


def raster_vector_intersection_stats(
    raster_path: str,
    vector_path: str,
    vector_layer: str | None = None,
    out_raster_union: str | None = "raster_gt0_union.geojson",
    out_intersection: str | None = "raster_vector_intersection.geojson",
    area_crs: str = "ESRI:54009",
):
    """
    Compute intersection between a raster mask (values > 0) and a vector layer,
    and print areas + percentage.

    Parameters
    ----------
    raster_path : str
        Path to the raster file.
    vector_path : str
        Path to the vector file (e.g. shapefile, GeoPackage, GeoJSON).
    vector_layer : str or None, optional
        Layer name for multi-layer formats (e.g. GeoPackage). If None,
        uses the default layer for the file.
    out_raster_union : str or None, optional
        Output path for the union of raster>0 polygons (GeoJSON). If None, not saved.
    out_intersection : str or None, optional
        Output path for the intersection polygons (GeoJSON). If None, not saved.
    area_crs : str, optional
        Equal-area CRS used to compute areas (default: ESRI:54009, Mollweide).

    Returns
    -------
    result : geopandas.GeoDataFrame
        Intersection GeoDataFrame.
    stats : dict
        Dictionary with 'raster_area', 'vector_area', 'percentage'.
    """

    # -------------------------------------------------------------------
    # 1. Read polygons
    # -------------------------------------------------------------------
    if vector_layer:
        poly_gdf = gpd.read_file(vector_path, layer=vector_layer)
    else:
        poly_gdf = gpd.read_file(vector_path)
    print("Polygons read")

    # -------------------------------------------------------------------
    # 2. Build polygons from raster cells where raster > 0
    # -------------------------------------------------------------------
    with rasterio.open(raster_path) as src:
        data = src.read(1)
        transform = src.transform
        nodata = src.nodata
        raster_crs = src.crs

        # mask = True where raster value > 0
        mask = data > 0
        if nodata is not None:
            mask &= (data != nodata)

        # Extract raster>0 regions as polygons
        raster_geoms = []
        for geom, val in shapes(data, mask=mask, transform=transform):
            # val is the raster value; we only care about geometry
            raster_geoms.append(shape(geom))

    print("Raster polygons created")

    # Merge all raster>0 polygons into one
    raster_union = gpd.GeoSeries(raster_geoms, crs=raster_crs).unary_union
    raster_union_gdf = gpd.GeoDataFrame(geometry=[raster_union], crs=raster_crs)

    # Optional: save union polygon
    if out_raster_union is not None:
        raster_union_gdf.to_file(out_raster_union, driver="GeoJSON")
        print(f"Saved raster>0 union to {out_raster_union}")

    # -------------------------------------------------------------------
    # 3. Reproject polygons if needed
    # -------------------------------------------------------------------
    if poly_gdf.crs != raster_union_gdf.crs:
        poly_gdf = poly_gdf.to_crs(raster_union_gdf.crs)
        print(f"Reprojected vectors to {raster_union_gdf.crs}")

    # -------------------------------------------------------------------
    # 4. Intersect polygons with raster>0 area
    # -------------------------------------------------------------------
    result = gpd.overlay(poly_gdf, raster_union_gdf, how="intersection")

    # Save intersection (optional)
    if out_intersection is not None:
        result.to_file(out_intersection, driver="GeoJSON")
        print(f"Saved intersection to {out_intersection}")

    print(result.head())

    # -------------------------------------------------------------------
    # 5. Area calculations in equal-area CRS
    # -------------------------------------------------------------------
    # Raster mask area (>0) in equal-area CRS
    raster_union_moll = raster_union_gdf.to_crs(area_crs)
    raster_area = raster_union_moll.geometry.area.iloc[0]
    print(f"Raster mask area (>0): {raster_area:,.2f} (in {area_crs})")

    # Dissolve vectors into one polygon and compute area in equal-area CRS
    # Change area calculations as needed - these were done for KBA, light pollution, heatwave intersections
    result_diss = result.dissolve()
    result_diss_moll = result_diss.to_crs(area_crs)
    result_area = result_diss_moll.geometry.area.iloc[0]

    vector_diss = poly_gdf.dissolve()
    vector_diss_moll = vector_diss.to_crs(area_crs)
    vector_area = vector_diss_moll.geometry.area.iloc[0]

    percentage_vector = (result_area / vector_area) * 100 if raster_area != 0 else float("nan")
    percentage_raster = (result_area/raster_area)*100 #if raster_area != 0 else float("nan")

    # Print stats
    print(f"Total dissolved vector area: {vector_area:,.2f} (in {area_crs})")
    print(f"Intersected area:{result_area}")
    print(f"Percentage of intersection area over total vector area: {percentage_vector:.2f}%")
    print(f"Percentage of vector intersection area over total raster area: {percentage_raster:.2f}%")


    stats = {
        "raster_area": float(raster_area),
        "vector_area": float(vector_area),
        "percentage": float(percentage_vector),
    }

    return result, stats


def main():
    print("\n--- Raster/Vector Intersection Tool ---")

    raster_path = input("Enter raster path: ").strip()
    vector_path = input("Enter vector path: ").strip()

    vector_layer = input("Vector layer (press Enter if none): ").strip()
    vector_layer = vector_layer if vector_layer else None

    out_raster_union = input(
        "Output raster-union file (GeoJSON) — press Enter to skip: "
    ).strip()
    out_raster_union = out_raster_union if out_raster_union else None

    out_intersection = input(
        "Output intersection file (GeoJSON) — press Enter to skip: "
    ).strip()
    out_intersection = out_intersection if out_intersection else None

    print("\nRunning analysis...\n")

    result, stats = raster_vector_intersection_stats(
        raster_path=raster_path,
        vector_path=vector_path,
        vector_layer=vector_layer,
        out_raster_union=out_raster_union,
        out_intersection=out_intersection,
    )

    print("\n--- RESULTS ---")
    print(stats)


# Run the tool when executed as a script
if __name__ == "__main__":
    main()
