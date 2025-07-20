import streamlit as st
import datetime
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import rasterio
import io

st.set_page_config(page_title="NDVI PDF Report Generator (Web)")

def generate_pdf_report(arr, metadata_text):
    pdf_buffer = io.BytesIO()
    with PdfPages(pdf_buffer) as pdf:
        fig, axs = plt.subplots(1, 2, figsize=(11.69, 8.27))  # A4 landscape

        # NDVI Map Preview
        ax_map = axs[0]
        ax_map.imshow(arr, cmap='RdYlGn')
        ax_map.set_title("NDVI Map Preview")
        ax_map.axis("off")

        # Metadata text
        ax_meta = axs[1]
        ax_meta.axis("off")
        ax_meta.text(0, 1, metadata_text, verticalalignment="top", fontsize=10)

        plt.tight_layout()
        pdf.savefig(fig)
        plt.close()

    pdf_buffer.seek(0)
    return pdf_buffer

def process_ndvi_raster(file_bytes, filename):
    with rasterio.MemoryFile(file_bytes) as memfile:
        with memfile.open() as src:
            arr = src.read(1).astype(float)
            nodata = src.nodata
            if nodata is not None:
                arr[arr == nodata] = np.nan

            spatial_ref = src.crs.to_string() if src.crs else "Unknown"
            extent = src.bounds if src.bounds else None
            transform = src.transform if src.transform else None
            pixel_area = abs(transform[0] * transform[4]) if transform else 1

    valid_arr = arr[~np.isnan(arr)]
    area_m2 = valid_arr.size * pixel_area
    area_ha = area_m2 / 10000
    mean_val = np.nanmean(valid_arr)
    min_val = np.nanmin(valid_arr)
    max_val = np.nanmax(valid_arr)

    metadata_text = (
        f"Projection: {spatial_ref}\n"
        f"Extent (xmin, ymin, xmax, ymax): "
        f"{extent.left:.2f}, {extent.bottom:.2f}, {extent.right:.2f}, {extent.top:.2f}\n"
        f"Area: {area_m2:,.2f} m² ({area_ha:.2f} ha)\n"
        f"Mean NDVI: {mean_val:.4f}\n"
        f"Min NDVI: {min_val:.4f}\n"
        f"Max NDVI: {max_val:.4f}\n"
        f"Processed on: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )

    return arr, metadata_text

st.title("🌱 NDVI PDF Report Generator (Web)")

if "processed_reports" not in st.session_state:
    st.session_state.processed_reports = {}

tab1, tab2 = st.tabs(["Process New NDVI", "Previously Processed"])

with tab1:
    uploaded_file = st.file_uploader("Upload NDVI GeoTIFF", type=["tif", "tiff"])
    if uploaded_file is not None:
        with st.spinner("Processing NDVI raster..."):
            arr, metadata_text = process_ndvi_raster(uploaded_file.read(), uploaded_file.name)

            pdf_buffer = generate_pdf_report(arr, metadata_text)

            # Save to session_state
            key = f"{uploaded_file.name}_{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}"
            st.session_state.processed_reports[key] = {
                "pdf": pdf_buffer,
                "metadata": metadata_text,
                "arr": arr
            }

        st.success(f"Processed: {uploaded_file.name}")

        st.image(arr, cmap='RdYlGn', caption="NDVI Map Preview")

        st.text_area("NDVI Metadata", metadata_text, height=200)

        st.download_button(
            label="Download PDF Report",
            data=pdf_buffer,
            file_name=f"{key}_report.pdf",
            mime="application/pdf",
            key=f"download_{key}"
        )

with tab2:
    if not st.session_state.processed_reports:
        st.info("No previously processed NDVI reports found in this session.")
    else:
        selected_key = st.selectbox("Select a dataset to view", list(st.session_state.processed_reports.keys()))

        report = st.session_state.processed_reports[selected_key]

        st.image(report["arr"], cmap='RdYlGn', caption="NDVI Map Preview")

        st.text_area("NDVI Metadata", report["metadata"], height=200)

        st.download_button(
            label="Download PDF Report",
            data=report["pdf"],
            file_name=f"{selected_key}_report.pdf",
            mime="application/pdf",
            key=f"download_prev_{selected_key}"
        )

        if st.button("Delete This Report", key=f"delete_{selected_key}"):
            del st.session_state.processed_reports[selected_key]
            st.experimental_rerun()
