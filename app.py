import streamlit as st
import rasterio
import numpy as np
import matplotlib.pyplot as plt
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
import os
from datetime import datetime
from rasterio.plot import show
from rasterio.transform import xy
from pyproj import CRS

# Setup a results folder
RESULTS_DIR = "results"
os.makedirs(RESULTS_DIR, exist_ok=True)

st.set_page_config(page_title="NDVI Analyzer", layout="wide")
st.title("🌱 NDVI Report Generator (Streamlit Version)")

# Upload a GeoTIFF
uploaded_file = st.file_uploader("Upload your NDVI GeoTIFF file", type=["tif", "tiff"])

if uploaded_file:
    try:
        # Read uploaded bytes
        tif_bytes = uploaded_file.read()
        dataset = rasterio.open(BytesIO(tif_bytes))

        st.success("✅ File loaded successfully!")

        # Check number of bands
        if dataset.count != 1:
            st.warning("⚠️ This file has more than 1 band. Please upload a single-band NDVI GeoTIFF.")
        else:
            ndvi = dataset.read(1)
            ndvi = np.where((ndvi < -1) | (ndvi > 1), np.nan, ndvi)

            # Show NDVI preview
            fig, ax = plt.subplots()
            img = ax.imshow(ndvi, cmap='RdYlGn', vmin=-1, vmax=1)
            ax.set_title("NDVI Preview")
            fig.colorbar(img, ax=ax, shrink=0.6)
            st.pyplot(fig)

            # Extract metadata
            bounds = dataset.bounds
            crs = CRS.from_user_input(dataset.crs)
            resolution = dataset.res
            stats = {
                "Min NDVI": np.nanmin(ndvi),
                "Max NDVI": np.nanmax(ndvi),
                "Mean NDVI": np.nanmean(ndvi),
                "CRS": crs.to_string(),
                "Resolution": f"{resolution[0]:.2f} x {resolution[1]:.2f} m",
                "Bounds": bounds
            }

            # Show metadata
            st.subheader("📊 NDVI Statistics")
            for key, value in stats.items():
                st.write(f"**{key}:** {value}")

            # Save NDVI PNG preview
            png_buffer = BytesIO()
            fig.savefig(png_buffer, format='png')
            png_buffer.seek(0)

            # Generate PDF Report
            pdf_path = os.path.join(RESULTS_DIR, f"{uploaded_file.name}_NDVI_Report.pdf")
            c = canvas.Canvas(pdf_path, pagesize=letter)
            c.drawString(100, 750, "NDVI Analysis Report")
            c.drawString(100, 735, f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            y = 700
            for key, value in stats.items():
                c.drawString(100, y, f"{key}: {value}")
                y -= 15
            c.drawImage(ImageReader(png_buffer), 100, 400, width=400, height=250)
            c.save()

            with open(pdf_path, "rb") as pdf_file:
                st.download_button(
                    label="📥 Download NDVI Report (PDF)",
                    data=pdf_file,
                    file_name=os.path.basename(pdf_path),
                    mime="application/pdf"
                )

    except Exception as e:
        st.error(f"❌ Error processing file: {e}")
