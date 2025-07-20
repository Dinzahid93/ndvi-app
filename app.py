import streamlit as st
import os
import datetime
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import rasterio
import io
import shutil

# Directory to save processed reports (server-side)
processed_reports_dir = "processed_reports"
os.makedirs(processed_reports_dir, exist_ok=True)

def generate_pdf_report(folder_path):
    meta_path = os.path.join(folder_path, "metadata.txt")
    img_path = os.path.join(folder_path, "preview.png")
    tif_path = None

    for f in os.listdir(folder_path):
        if f.lower().endswith(".tif"):
            tif_path = os.path.join(folder_path, f)
            break

    with open(meta_path, "r") as f:
        metadata_text = f.read()

    img = plt.imread(img_path)

    arr = None
    if tif_path:
        with rasterio.open(tif_path) as src:
            arr = src.read(1).astype(float)
            nodata = src.nodata
            if nodata is not None:
                arr[arr == nodata] = np.nan

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
        if arr is not None:
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
        else:
            ax_hist.text(0.5, 0.5, "Histogram data not found", ha='center', va='center')

        # Blank subplot bottom right
        axs[1, 1].axis("off")

        plt.tight_layout()
        pdf.savefig(fig)
        plt.close()

    pdf_buffer.seek(0)
    return pdf_buffer

def process_ndvi_raster(tif_file, folder_name):
    folder_path = os.path.join(processed_reports_dir, folder_name)
    os.makedirs(folder_path, exist_ok=True)

    # Save uploaded tif inside folder
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

    # Save preview PNG
    plt.figure(figsize=(6,6))
    plt.imshow(arr, cmap='RdYlGn')
    plt.title("NDVI Map Preview")
    plt.axis("off")
    preview_path = os.path.join(folder_path, "preview.png")
    plt.savefig(preview_path)
    plt.close()

    # Save metadata
    metadata_text = (
        f"Projection: {spatial_ref}\n"
        f"Extent (xmin, ymin, xmax, ymax): {extent.left:.2f}, {extent.bottom:.2f}, "
        f"{extent.right:.2f}, {extent.top:.2f}\n"
        f"Area: {area_m2:,.2f} m² ({area_ha:.2f} ha)\n"
        f"Mean NDVI: {mean_val:.4f}\n"
        f"Min NDVI: {min_val:.4f}\n"
        f"Max NDVI: {max_val:.4f}\n"
        f"Processed on: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )
    with open(os.path.join(folder_path, "metadata.txt"), "w") as f:
        f.write(metadata_text)

    return folder_path

st.title("🌱 NDVI PDF Report Generator (Web)")

tab1, tab2 = st.tabs(["Process New NDVI", "Previously Processed"])

with tab1:
    uploaded_file = st.file_uploader("Upload NDVI GeoTIFF", type=["tif", "tiff"], accept_multiple_files=False)
    if uploaded_file is not None:
        timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        clean_name = os.path.splitext(uploaded_file.name)[0].replace(" ", "_")
        folder_name = f"{clean_name}_{timestamp}"

        with st.spinner("Processing NDVI raster..."):
            folder_path = process_ndvi_raster(uploaded_file, folder_name)
        st.success(f"Processed: {folder_name}")

        preview_img_path = os.path.join(folder_path, "preview.png")
        st.image(preview_img_path, caption="NDVI Map Preview")

        with open(os.path.join(folder_path, "metadata.txt"), "r") as f:
            st.text_area("NDVI Metadata", f.read(), height=200)

        pdf_buffer = generate_pdf_report(folder_path)
        st.download_button(
            label="Download PDF Report",
            data=pdf_buffer,
            file_name=f"{folder_name}_report.pdf",
            mime="application/pdf",
            key=f"download_{folder_name}"
        )

with tab2:
    all_processed = sorted([f for f in os.listdir(processed_reports_dir) if os.path.isdir(os.path.join(processed_reports_dir, f))], reverse=True)
    if not all_processed:
        st.info("No previously processed NDVI reports found.")
    else:
        selected_folder = st.selectbox("Select a dataset to view", all_processed)
        folder_path = os.path.join(processed_reports_dir, selected_folder)

        if st.button("Delete Selected Dataset"):
            shutil.rmtree(folder_path)
            st.success(f"Deleted: {selected_folder}")
            st.experimental_rerun()

        preview_img_path = os.path.join(folder_path, "preview.png")
        st.image(preview_img_path, caption="NDVI Map Preview")

        with open(os.path.join(folder_path, "metadata.txt"), "r") as f:
            st.text_area("NDVI Metadata", f.read(), height=200)

        pdf_buffer = generate_pdf_report(folder_path)
        st.download_button(
            label="Download PDF Report",
            data=pdf_buffer,
            file_name=f"{selected_folder}_report.pdf",
            mime="application/pdf",
            key=f"download_{selected_folder}"
        )
