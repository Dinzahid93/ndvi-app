import streamlit as st
import rasterio
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import os
import datetime
import base64

# Setup
st.set_page_config(page_title="NDVI Report Dashboard", layout="wide")
st.sidebar.title("📤 Upload NDVI Raster")
st.sidebar.write("Upload NDVI .tif file\n\nLimit 200MB per file • TIF, TIFF")

# Global storage (in memory)
if "ndvi_reports" not in st.session_state:
    st.session_state["ndvi_reports"] = []

# File uploader
uploaded_file = st.sidebar.file_uploader("Upload NDVI .tif file", type=["tif", "tiff"])

if uploaded_file is not None:
    try:
        # Read file into BytesIO buffer
        tif_bytes = uploaded_file.read()
        tif_stream = BytesIO(tif_bytes)

        with rasterio.open(tif_stream) as src:
            ndvi = src.read(1)
            ndvi = np.ma.masked_invalid(ndvi)
            meta = src.meta

        # Compute NDVI stats
        ndvi_mean = float(np.mean(ndvi))
        ndvi_min = float(np.min(ndvi))
        ndvi_max = float(np.max(ndvi))
        ndvi_std = float(np.std(ndvi))

        # Plot NDVI
        fig, ax = plt.subplots()
        cmap = plt.cm.YlGn
        cax = ax.imshow(ndvi, cmap=cmap, vmin=-1, vmax=1)
        fig.colorbar(cax, ax=ax, label="NDVI")
        ax.set_title("NDVI Visualization")
        ax.axis("off")

        # Save plot as image buffer
        img_buf = BytesIO()
        fig.savefig(img_buf, format="png", bbox_inches='tight')
        plt.close(fig)
        img_buf.seek(0)

        # Generate PDF report
        report_buf = BytesIO()
        pdf = canvas.Canvas(report_buf, pagesize=letter)
        pdf.setTitle("NDVI Report")
        pdf.drawString(50, 750, f"NDVI Report")
        pdf.drawString(50, 735, f"File: {uploaded_file.name}")
        pdf.drawString(50, 720, f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        pdf.drawString(50, 695, f"Mean NDVI: {ndvi_mean:.3f}")
        pdf.drawString(50, 680, f"Min NDVI: {ndvi_min:.3f}")
        pdf.drawString(50, 665, f"Max NDVI: {ndvi_max:.3f}")
        pdf.drawString(50, 650, f"Std Dev: {ndvi_std:.3f}")
        pdf.showPage()
        pdf.save()
        report_buf.seek(0)

        # Encode for download
        report_b64 = base64.b64encode(report_buf.getvalue()).decode()
        report_link = f'<a href="data:application/pdf;base64,{report_b64}" download="NDVI_Report_{uploaded_file.name}.pdf">📄 Download PDF Report</a>'

        # Save session state
        st.session_state["ndvi_reports"].append({
            "filename": uploaded_file.name,
            "mean": ndvi_mean,
            "min": ndvi_min,
            "max": ndvi_max,
            "std": ndvi_std,
            "plot": img_buf,
            "pdf": report_link
        })

        st.success(f"✅ Processed {uploaded_file.name}")
    except Exception as e:
        st.error(f"❌ Failed to process the file. Reason: {str(e)}")

# MAIN UI
st.markdown("## 🌿 NDVI Report Dashboard")
st.markdown("### 🗂️ NDVI Report History")

if len(st.session_state["ndvi_reports"]) == 0:
    st.info("📂 No NDVI reports yet. Upload a .tif file to begin.")
else:
    for i, report in enumerate(reversed(st.session_state["ndvi_reports"])):
        col1, col2 = st.columns([2, 3])
        with col1:
            st.image(report["plot"], caption=report["filename"], use_column_width=True)
        with col2:
            st.markdown(f"**🗂️ File:** `{report['filename']}`")
            st.markdown(f"- **Mean NDVI:** `{report['mean']:.3f}`")
            st.markdown(f"- **Min NDVI:** `{report['min']:.3f}`")
            st.markdown(f"- **Max NDVI:** `{report['max']:.3f}`")
            st.markdown(f"- **Std Dev:** `{report['std']:.3f}`")
            st.markdown(report["pdf"], unsafe_allow_html=True)
