import streamlit as st
import datetime
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import rasterio
import io
import os

def generate_pdf_report(tif_path, metadata_text):
    with rasterio.open(tif_path) as src:
        arr = src.read(1).astype(float)
        nodata = src.nodata
        if nodata is not None:
            arr[arr == nodata] = np.nan

    img_buffer = io.BytesIO()
    plt.figure(figsize=(6,6))
    plt.imshow(arr, cmap='RdYlGn')
    plt.title("NDVI Map Preview")
    plt.axis("off")
    plt.savefig(img_buffer, format='png')
    plt.close()
    img_buffer.seek(0)
    img = plt.imread(img_buffer)

    pdf_buffer = io.BytesIO()
    with PdfPages(pdf_buffer) as pdf:
        fig, axs = plt.subplots(2, 2, figsize=(11.69, 8.27))  # A4 landscape

        # NDVI Map Preview
        ax_map = axs[0, 0]
        ax_map.imshow(img)
        ax_map.set_title("NDVI Map Preview")
        ax_map.axis("off")

        # Metadata text
        ax_meta = axs[0, 1]
        ax_meta.axis("off")
        ax_meta.text(0, 1, metadata_text, verticalalignment="top", fontsize=10)

        # Histogram
        ax_hist = axs[1, 0]
        valid_arr = arr[~np.isnan(arr)]
        ax_hist.hist(valid_arr.flatten(), bins=30, color='green', alpha=0.7)
        mean_val = np.nanmean(valid_arr)
        min_val = np.nanmin(valid_arr)
        max_val = np.nanmax(valid_arr)
        ax_hist.axvline(mean_val, color='blue', linestyle='--', label=f"Mean: {mean_val:.3f}")
        ax_hist.axvline(min_val, color='red', linestyle=':', label=f"Min: {min_val:.3f}")
        ax_hist.axvline(max_val, color='orange', linestyle=':', label=f"Max: {max_val:.3f}")
        ax_hist.set_title("NDVI Histogram")
        ax_hist.set_xlabel("NDVI Value")
        ax_hist.set_ylabel("Pixel Count")
        ax_hist.legend(fontsize=8)

        # Blank subplot bottom right
        axs[1, 1].axis("off")

        plt.tight_layout()
        pdf.savefig(fig)
        plt.close()

    pdf_buffer.seek(0)
    return pdf_buffer

def process_ndvi_raster(tif_file):
    # Save uploaded file temporarily to read metadata
    temp_path = f"temp_{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}.tif"
    with open(temp_path, "wb") as out_file:
        out_file.write(tif_file.read())

    with rasterio.open(temp_path) as src:
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

    metadata_text = (
        f"Projection: {spatial_ref}\n"
        f"Extent (xmin, ymin, xmax, ymax): {extent.left:.2f}, {extent.bottom:.2f}, {extent.right:.2f}, {extent.top:.2f}\n"
        f"Area: {area_m2:,.2f} m² ({area_ha:.2f} ha)\n"
        f"Mean NDVI: {mean_val:.4f}\n"
        f"Min NDVI: {min_val:.4f}\n"
        f"Max NDVI: {max_val:.4f}\n"
        f"Processed on: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )

    return temp_path, metadata_text

st.title("🌱 NDVI PDF Report Generator (Web)")

uploaded_file = st.file_uploader("Upload NDVI GeoTIFF", type=["tif", "tiff"], accept_multiple_files=False)

if uploaded_file is not None:
    with st.spinner("Processing NDVI raster..."):
        tif_path, metadata_text = process_ndvi_raster(uploaded_file)

    st.success(f"Processed: {uploaded_file.name}")

    # Show metadata text area with unique key
    st.text_area("NDVI Metadata", metadata_text, height=200, key=f"meta_{uploaded_file.name}")

    # Show NDVI Map Preview
    with rasterio.open(tif_path) as src:
        arr = src.read(1)
    st.image(arr, clamp=True, caption="NDVI Map Preview")

    # Generate PDF and download button
    pdf_buffer = generate_pdf_report(tif_path, metadata_text)
    st.download_button(
        label="Download PDF Report",
        data=pdf_buffer,
        file_name=f"{os.path.splitext(uploaded_file.name)[0]}_report.pdf",
        mime="application/pdf",
        key=f"download_{uploaded_file.name}"
    )

    # Clean up temp file after session ends
    import atexit
    def cleanup():
        try:
            os.remove(tif_path)
        except FileNotFoundError:
            pass
    atexit.register(cleanup)
