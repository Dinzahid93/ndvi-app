import streamlit as st
import rasterio
import numpy as np
import matplotlib.pyplot as plt
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from pyproj import CRS
import os
from datetime import datetime

st.set_page_config(page_title="NDVI Report Generator", layout="wide")
st.title("🌿 NDVI Report Generator")

uploaded_file = st.file_uploader("Upload a single-band NDVI .tif", type=["tif", "tiff"])
if uploaded_file:
    try:
        tif_bytes = uploaded_file.read()
        ds = rasterio.open(BytesIO(tif_bytes))

        if ds.count != 1:
            st.error("❌ Please upload a single-band NDVI .tif")
        else:
            ndvi = ds.read(1)
            ndvi = np.where((ndvi < -1) | (ndvi > 1), np.nan, ndvi)
            bounds = ds.bounds
            crs = CRS.from_user_input(ds.crs).to_string()
            stats = {
                "Min": float(np.nanmin(ndvi)),
                "Max": float(np.nanmax(ndvi)),
                "Mean": float(np.nanmean(ndvi)),
                "CRS": crs,
                "Bounds": bounds
            }

            fig, ax = plt.subplots()
            img = ax.imshow(ndvi, cmap='RdYlGn', vmin=-1, vmax=1)
            ax.set_title("NDVI Preview")
            ax.axis("off")
            fig.colorbar(img, ax=ax, shrink=0.5)
            st.pyplot(fig)

            st.subheader("📊 NDVI Statistics")
            st.write(f"- **Min**: {stats['Min']:.3f}")
            st.write(f"- **Max**: {stats['Max']:.3f}")
            st.write(f"- **Mean**: {stats['Mean']:.3f}")
            st.write(f"- **CRS**: {stats['CRS']}")
            st.write(f"- **Bounds**: {stats['Bounds']}")

            buffer = BytesIO()
            pdf = canvas.Canvas(buffer, pagesize=letter)
            pdf.drawString(50, 750, "NDVI Analysis Report")
            pdf.drawString(50, 735, f"File: {uploaded_file.name}")
            y = 720
            for k in ["Min", "Max", "Mean", "CRS"]:
                pdf.drawString(50, y, f"{k}: {stats[k]}")
                y -= 15
            pdf.drawImage(BytesIO(buf:=BytesIO()), 50, 400, width=400, height=300)  # placeholder
            pdf.showPage()
            pdf.save()
            buffer.seek(0)

            st.download_button(
                "📥 Download PDF",
                data=buffer.getvalue(),
                file_name=f"NDVI_Report_{uploaded_file.name}.pdf",
                mime="application/pdf"
            )
    except Exception as e:
        st.error(f"Error: {e}")
