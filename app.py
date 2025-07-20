import matplotlib.pyplot as plt
import datetime
import os
import rasterio
import numpy as np

def process_ndvi_raster(tif_file, folder_name, processed_reports_dir):
    folder_path = os.path.join(processed_reports_dir, folder_name)
    os.makedirs(folder_path, exist_ok=True)

    # Save uploaded TIFF
    uploaded_tif_path = os.path.join(folder_path, folder_name + ".tif")
    with open(uploaded_tif_path, "wb") as out_file:
        out_file.write(tif_file.read())

    with rasterio.open(uploaded_tif_path) as src:
        arr = src.read(1).astype(float)
        nodata = src.nodata
        if nodata is not None:
            arr[arr == nodata] = np.nan

        spatial_ref = src.crs.to_string()
        extent = src.bounds
        transform = src.transform
        pixel_area = abs(transform[0] * transform[4])

    valid_arr = arr[~np.isnan(arr)]
    area_m2 = valid_arr.size * pixel_area
    area_ha = area_m2 / 10000
    mean_val = np.nanmean(valid_arr)
    min_val = np.nanmin(valid_arr)
    max_val = np.nanmax(valid_arr)

    # Save preview PNG with colormap and colorbar
    fig, ax = plt.subplots(figsize=(6, 6))
    cax = ax.imshow(arr, cmap='RdYlGn')
    ax.set_title("NDVI Map Preview")
    ax.axis("off")
    fig.colorbar(cax, ax=ax, fraction=0.046, pad=0.04)

    preview_path = os.path.join(folder_path, "preview.png")
    fig.savefig(preview_path, bbox_inches='tight', dpi=150)
    plt.close(fig)

    # Save metadata text
    metadata_text = (
        f"Projection: {spatial_ref}\n"
        f"Extent (xmin, ymin, xmax, ymax): {extent.left:.2f}, {extent.bottom:.2f}, {extent.right:.2f}, {extent.top:.2f}\n"
        f"Area: {area_m2:,.2f} m² ({area_ha:.2f} ha)\n"
        f"Mean NDVI: {mean_val:.4f}\n"
        f"Min NDVI: {min_val:.4f}\n"
        f"Max NDVI: {max_val:.4f}\n"
        f"Processed on: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )
    with open(os.path.join(folder_path, "metadata.txt"), "w") as f:
        f.write(metadata_text)

    return folder_path
