import math
import os
os.environ.pop("PROJ_LIB", None)
os.environ.pop("GDAL_DATA", None)

import geopandas as gpd
import rasterio
from rasterio.transform import from_origin
from rasterio.features import rasterize
from rasterio.warp import calculate_default_transform, reproject, Resampling
import numpy as np

def shapefile_to_raster(
    shp_path,
    out_raster_path,
    pixel_size_m=5000,
    attribute=None,
    target_crs=None,
    nodata=0,
    all_touched=True
):
    """
    Convert a vector shapefile to a 5 km raster, then reproject to EPSG:4326.
    """

    # --- allow large GeoJSON files ---
    os.environ["OGR_GEOJSON_MAX_OBJ_SIZE"] = "0"

    # 1. Read shapefile
    gdf = gpd.read_file(shp_path)

    if gdf.empty:
        raise ValueError("Shapefile has no features.")

    # 2. Reproject vector for rasterization (must be in meters)
    if target_crs is not None:
        gdf = gdf.to_crs(target_crs)

    # 3. Determine raster dimensions
    minx, miny, maxx, maxy = gdf.total_bounds

    width = math.ceil((maxx - minx) / pixel_size_m)
    height = math.ceil((maxy - miny) / pixel_size_m)

    # 4. Affine transform for raster
    transform = from_origin(minx, maxy, pixel_size_m, pixel_size_m)

    # 5. Prepare shapes for rasterize()
    if attribute is not None:
        shapes = [
            (geom, value)
            for geom, value in zip(gdf.geometry, gdf[attribute])
        ]
        dtype = "float32"
    else:
        shapes = [(geom, 1) for geom in gdf.geometry]
        dtype = "uint8"

    # 6. Rasterize in projected CRS
    raster_array = rasterize(
        shapes=shapes,
        out_shape=(height, width),
        transform=transform,
        fill=nodata,
        all_touched=all_touched,
        dtype=dtype
    )

    # 7. Profile for intermediate raster in projected CRS
    profile = {
        "driver": "GTiff",
        "height": height,
        "width": width,
        "count": 1,
        "dtype": raster_array.dtype,
        "crs": gdf.crs,
        "transform": transform,
        "nodata": nodata
    }

    # 8. Reproject raster to EPSG:4326
    dst_crs = "EPSG:4326"

    transform_4326, width_4326, height_4326 = calculate_default_transform(
        profile["crs"],
        dst_crs,
        profile["width"],
        profile["height"],
        *gdf.total_bounds
    )

    dst_array = np.zeros((height_4326, width_4326), dtype=dtype)

    reproject(
        source=raster_array,
        destination=dst_array,
        src_transform=profile["transform"],
        src_crs=profile["crs"],
        dst_transform=transform_4326,
        dst_crs=dst_crs,
        resampling=Resampling.nearest,
        src_nodata=nodata,
        dst_nodata=nodata
    )

    # 9. Write final raster in EPSG:4326
    final_profile = profile.copy()
    final_profile.update({
        "crs": dst_crs,
        "transform": transform_4326,
        "height": height_4326,
        "width": width_4326
    })

    with rasterio.open(out_raster_path, "w", **final_profile) as dst:
        dst.write(dst_array, 1)

    print(f"Raster written to {out_raster_path} with final CRS EPSG:4326")


if __name__ == "__main__":
    # Ask user for inputs
    shp_path = input("Enter the path to the vector file (e.g., .shp, .gpkg): ").strip()
    out_raster_path = input("Enter output raster filename (e.g., output.tif): ").strip()

    shapefile_to_raster(
        shp_path=shp_path,
        out_raster_path=out_raster_path,
        pixel_size_m=5000,
        attribute=None,
        target_crs="EPSG:3857"
    )
