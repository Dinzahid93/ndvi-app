import streamlit as st
import rasterio
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.cm as cm
from matplotlib.backends.backend_pdf import PdfPages
import io
import os
import json
import datetime
from PIL import Image

# -------------------- INITIAL SETUP --------------------
st.set_page_config(page_title="NDVI Report Dashboard", layout="wide")
st.title("🌿 NDVI Report Dashboard")

# Make folders
os.makedirs("results", exist_ok=True)
os.makedirs("results/previews", exist_ok=True)
os.makedirs("results/pdfs", exist_ok=True)
records_path = "results/records.json"

# Load existing record list
if os.path.exists(records_path):
    with open(records_path, "r") as f:
        record_list = json.load(f)
else:
    record_list = []

# -------------------- UPLOAD & PROCESSING --------------------
st.sidebar.header("📤 Upload NDVI Raster")
uploaded_file = st.sidebar.file_uploader("Upload NDVI .tif file", type=["tif", "tiff"])

if uploaded_file is not None:
    try:
        # Read raster
        with rasterio.open(uploaded_file) as src:
            arr = src.read(1).astype("float32")
            arr[arr == src.nodata] = np.nan
            transform = src.transform
            crs = src.crs.to_string()
            extent = src.bounds
            pixel_area = abs(transform[0] * transform[4])

        # Stats
        valid_arr = arr[~np.isnan(arr)]
        area_m2 = valid_arr.size * pixel_area
        area_ha = area_m2 / 10000
        mean_val = float(np.nanmean(valid_arr))
        min_val = float(np.nanmin(valid_arr))
        max_val = float(np.nanmax(valid_arr))

        # Normalize + apply colormap
        ndvi_min, ndvi_max = -1.0, 1.0
        norm_arr = (arr - ndvi_min) / (ndvi_max - ndvi_min)
        norm_arr = np.clip(norm_arr, 0, 1)
        colored_img = cm.RdYlGn(norm_arr)

        # Generate unique filenames
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = os.path.splitext(uploaded_file.name)[0]
        preview_name = f"{base_name}_{timestamp}.png"
        pdf_name = f"{base_name}_{timestamp}.pdf"

        preview_path = os.path.join("results/previews", preview_name)
        pdf_path = os.path.join("results/pdfs", pdf_name)

        # Save preview image
        plt.imsave(preview_path, colored_img)

        # Generate and save PDF report
        with PdfPages(pdf_path) as pdf:
            fig, axs = plt.subplots(2, 2, figsize=(11.69, 8.27))  # A4

            axs[0, 0].imshow(colored_img)
            axs[0, 0].set_title("NDVI Map Preview")
            axs[0, 0].axis("off")

            axs[0, 1].hist(valid_arr.flatten(), bins=30, color='green', alpha=0.7)
            axs[0, 1].axvline(mean_val, color='blue', linestyle='--', label=f"Mean: {mean_val:.3f}")
            axs[0, 1].axvline(min_val, color='red', linestyle=':', label=f"Min: {min_val:.3f}")
            axs[0, 1].axvline(max_val, color='orange', linestyle=':', label=f"Max: {max_val:.3f}")
            axs[0, 1].legend()
            axs[0, 1].set_title("NDVI Histogram")

            axs[1, 0].axis("off")
            metadata = [
                f"File: {uploaded_file.name}",
                f"Projection: {crs}",
                f"Extent (UTM):",
                f"  Xmin: {extent.left:.2f}",
                f"  Xmax: {extent.right:.2f}",
                f"  Ymin: {extent.bottom:.2f}",
                f"  Ymax: {extent.top:.2f}",
                f"Area: {area_m2:,.2f} m² ({area_ha:.2f} ha)",
                f"NDVI Mean: {mean_val:.3f}",
                f"NDVI Min: {min_val:.3f}",
                f"NDVI Max: {max_val:.3f}",
                f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            ]
            axs[1, 0].text(0, 1, "\n".join(metadata), fontsize=9, va='top')
            axs[1, 1].axis("off")

            plt.tight_layout()
            pdf.savefig(fig)
            plt.close()

        # Save metadata
        new_record = {
            "id": len(record_list) + 1,
            "filename": uploaded_file.name,
            "preview_path": preview_path,
            "pdf_path": pdf_path,
            "timestamp": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "mean": mean_val,
            "min": min_val,
            "max": max_val,
            "area_m2": area_m2,
            "area_ha": area_ha,
            "crs": crs,
            "extent": {
                "xmin": extent.left,
                "xmax": extent.right,
                "ymin": extent.bottom,
                "ymax": extent.top
            }
        }

        record_list.append(new_record)
        with open(records_path, "w") as f:
            json.dump(record_list, f, indent=2)

        st.success("✅ NDVI processed and saved successfully!")

    except Exception as e:
        st.error(f"❌ Error processing file: {e}")

# -------------------- SHOW RESULTS --------------------
st.subheader("📜 NDVI Report History")

if record_list:
    for record in reversed(record_list):
        col1, col2 = st.columns([1, 2])
        with col1:
            st.image(record["preview_path"], caption=record["filename"], width=220)
        with col2:
            st.markdown(f"**🕒 Date**: {record['timestamp']}")
            st.markdown(f"**📐 Area**: {record['area_m2']:,.2f} m² ({record['area_ha']:.2f} ha)")
            st.markdown(f"**📊 NDVI**: Mean={record['mean']:.3f}, Min={record['min']:.3f}, Max={record['max']:.3f}")
            st.markdown(f"**🗺️ Projection**: {record['crs']}")
            st.markdown(f"**📌 Extent**: Xmin={record['extent']['xmin']:.2f}, Xmax={record['extent']['xmax']:.2f}, "
                        f"Ymin={record['extent']['ymin']:.2f}, Ymax={record['extent']['ymax']:.2f}")
            with open(record["pdf_path"], "rb") as f:
                st.download_button(
                    label="📥 Download PDF Report",
                    data=f,
                    file_name=os.path.basename(record["pdf_path"]),
                    mime="application/pdf"
                )
else:
    st.info("📂 No NDVI reports yet. Upload a .tif file to begin.")
