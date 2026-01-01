import streamlit as st
import requests
from PIL import Image
import io
import time
import os
import threading
import queue

# Try importing watchdog, handle if not installed
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False

# ==========================================
# ⚙️ CONFIGURATION
# ==========================================
API_URL = "http://127.0.0.1:8000/predict"

st.set_page_config(
    page_title="OcularAI | Advanced Diagnostics",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================
# 🎨 CUSTOM CSS (Medical Theme)
# ==========================================
st.markdown("""
    <style>
    /* Main Background */
    .main {
        background-color: #f8fafc;
    }
    
    /* Headings */
    h1, h2, h3 {
        color: #0f172a;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    
    /* Metric Cards */
    div.css-1r6slb0.e1tzin5v2 {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    
    /* Upload Area */
    .stFileUploader {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 10px;
        border: 1px dashed #cbd5e1;
    }

    /* Buttons */
    .stButton>button {
        width: 100%;
        background-color: #2563eb;
        color: white;
        border: none;
        padding: 0.75rem 1rem;
        border-radius: 0.5rem;
        font-weight: 600;
        transition: all 0.2s;
    }
    .stButton>button:hover {
        background-color: #1d4ed8;
        box-shadow: 0 4px 6px -1px rgba(37, 99, 235, 0.5);
    }

    /* Success/Error Messages */
    .stAlert {
        border-radius: 8px;
    }
    
    /* Custom Card Style */
    .disease-card {
        background-color: white;
        padding: 25px;
        border-radius: 15px;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
        margin-bottom: 20px;
        border-left: 5px solid #3b82f6;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 🧠 EXTENDED DISEASE DATABASE
# ==========================================
DISEASE_DB = {
    "Normal": {
        "tag": "Healthy",
        "desc": "A healthy retina with no signs of lesions, bleeding, or nerve damage. The macula and optic disc appear clear.",
        "symptoms": ["Clear, sharp vision", "No pain or discomfort", "Normal night vision"],
        "causes": ["N/A"],
        "treatments": ["Routine eye exams (1-2 years)", "UV protection", "Healthy diet"],
        "prevention": ["Wear sunglasses", "20-20-20 rule for screens"],
        "color": "green"
    },
    "Cataract": {
        "tag": "Lens Clouding",
        "desc": "Clouding of the eye's natural lens, causing blurry vision like looking through a foggy window.",
        "symptoms": ["Cloudy/blurry vision", "Faded colors", "Glare/Halos around lights", "Poor night vision"],
        "causes": ["Aging", "Diabetes", "UV Exposure", "Smoking"],
        "treatments": ["Surgery (IOL Replacement)", "Brighter lighting (early stage)"],
        "prevention": ["Quit smoking", "Manage diabetes", "Antioxidant-rich diet"],
        "color": "blue"
    },
    "Glaucoma": {
        "tag": "Optic Nerve Damage",
        "desc": "Damage to the optic nerve, often caused by abnormally high pressure. Known as the 'silent thief of vision'.",
        "symptoms": ["Patchy blind spots", "Tunnel vision", "Severe eye pain (Acute)", "Nausea"],
        "causes": ["High eye pressure", "Family history", "Age (>60)"],
        "treatments": ["Prescription eye drops", "Laser treatment", "Microsurgery"],
        "prevention": ["Regular screenings", "Exercise", "Eye protection"],
        "color": "orange"
    },
    "Diabetic Retinopathy": {
        "tag": "Retinal Vessel Damage",
        "desc": "Complication of diabetes where high blood sugar damages retinal blood vessels.",
        "symptoms": ["Floaters (spots)", "Fluctuating vision", "Dark areas", "Vision loss"],
        "causes": ["Uncontrolled diabetes", "High blood pressure", "High cholesterol"],
        "treatments": ["Control blood sugar", "Laser photocoagulation", "Anti-VEGF injections"],
        "prevention": ["Strict sugar control", "Annual screening", "Healthy blood pressure"],
        "color": "red"
    }
}

# ==========================================
# 🤖 WATCHDOG HANDLER (For Live Monitor)
# ==========================================
if WATCHDOG_AVAILABLE:
    class ImageEventHandler(FileSystemEventHandler):
        """Logs new image files detected in the folder."""
        def __init__(self, queue):
            self.queue = queue

        def on_created(self, event):
            if not event.is_directory:
                filename = event.src_path
                if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                    self.queue.put(filename)

# ==========================================
# 📄 SIDEBAR
# ==========================================
with st.sidebar:
    st.markdown("<h1 style='text-align: left; font-size: 24px;'>AI Diagnostic Assistant</h1>", unsafe_allow_html=True)
    st.caption("Final Year Project (2025)")
    
    st.markdown("---")
    
    # Navigation using radio buttons
    # Added "Live Monitor" option
    page = st.radio(
        "Visits", 
        ["Diagnosis Dashboard", "Disease Encyclopedia"],
        index=0
    )
# ==========================================
# 🏠 PAGE 1: DIAGNOSIS DASHBOARD
# ==========================================
if page == "Diagnosis Dashboard":
    # Header
    st.markdown("""
        <div style='background-color: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); margin-bottom: 20px;'>
            <h1 style='margin:0; color: #1e293b;'>AI Diagnostic Assistant</h1>
            <p style='margin:0; color: #64748b;'>Upload retinal fundus scans for automated disease detection.</p>
        </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([1, 1.2])

    # Left Column: Upload
    with col1:
        st.markdown("### 1. Upload Scan")
        uploaded_file = st.file_uploader("Upload Image (JPG/PNG)", type=["jpg", "png", "jpeg"])
        
        if uploaded_file:
            # Show preview
            image = Image.open(uploaded_file)
            st.image(image, caption="Uploaded Fundus Scan", use_container_width=True)
            
            # Action Button
            st.markdown("<br>", unsafe_allow_html=True)
            analyze_btn = st.button("Run Diagnosis", type="primary", use_container_width=True)
        else:
            # Empty state
            st.info("Please upload a fundus image to begin.")
            st.markdown("""
                <div style='text-align: center; padding: 40px; background-color: white; border-radius: 10px; border: 2px dashed #e2e8f0;'>
                    <p style='color: #94a3b8;'>No image selected</p>
                </div>
            """, unsafe_allow_html=True)

    # Right Column: Results
    with col2:
        st.markdown("### 2. Clinical Report")
        
        if uploaded_file and analyze_btn:
            with st.spinner('AI is analyzing retinal patterns...'):
                try:
                    # Prepare file
                    img_bytes = io.BytesIO()
                    image.save(img_bytes, format=image.format)
                    img_bytes = img_bytes.getvalue()
                    
                    files = {"file": img_bytes}
                    
                    # Call API
                    response = requests.post(API_URL, files=files)
                    
                    if response.status_code == 200:
                        data = response.json()
                        result_class = data['class']
                        confidence = data['confidence'] * 100
                        scores = data.get('scores', {})
                        
                        # --- DISPLAY LOGIC ---
                        
                        # Determine Styling
                        if result_class == "Normal":
                            banner_color = "#dcfce7" # green-100
                            text_color = "#166534"   # green-800
                            border_color = "#22c55e" # green-500
                        elif confidence < 75.0:
                            banner_color = "#fef9c3" # yellow-100
                            text_color = "#854d0e"   # yellow-800
                            border_color = "#eab308" # yellow-500
                            result_class = "Inconclusive / Unknown"
                        else:
                            banner_color = "#fee2e2" # red-100
                            text_color = "#991b1b"   # red-800
                            border_color = "#ef4444" # red-500

                        # Result Card
                        st.markdown(f"""
                            <div style='background-color: {banner_color}; border-left: 6px solid {border_color}; padding: 20px; border-radius: 8px; margin-bottom: 20px;'>
                                <p style='color: {text_color}; font-weight: bold; margin: 0; font-size: 14px; text-transform: uppercase; letter-spacing: 1px;'>Detected Condition</p>
                                <h2 style='color: {text_color}; margin: 5px 0; font-size: 28px;'>{result_class}</h2>
                                <p style='color: {text_color}; margin: 0; font-size: 16px;'>Confidence: <strong>{confidence:.1f}%</strong></p>
                            </div>
                        """, unsafe_allow_html=True)

                        # Detailed Scores
                        st.markdown("#### Differential Diagnosis")
                        for disease, score in scores.items():
                            score_pct = score * 100
                            st.write(f"**{disease}**")
                            # Custom progress bar color logic isn't native in st.progress, using standard
                            st.progress(int(score_pct))
                            st.caption(f"Probability: {score_pct:.1f}%")

                        # Disclaimer
                        st.warning("Medical Disclaimer: This result is generated by an AI model (VGG19). It is not a substitute for professional medical advice. Please consult an ophthalmologist.")
                        
                    else:
                        st.error(f"Server Error: {response.text}")

                except Exception as e:
                    st.error(f"Connection Failed: {str(e)}")
                    st.info("Tip: Ensure your Flask backend (`api.py`) is running in a separate terminal.")
        
        elif not uploaded_file:
            st.write("Waiting for upload...")
        else:
            st.info("Click **Run Diagnosis** to generate the report.")

# ==========================================
# 📚 PAGE 2: ENCYCLOPEDIA
# ==========================================
elif page == "Disease Encyclopedia":
    st.title("Disease Knowledge Base")
    
    # Disease Selection Tabs
    tab1, tab2, tab3, tab4 = st.tabs(["Normal Eye", "Cataract", "Glaucoma", "Diabetic Retinopathy"])
    
    tabs = [tab1, tab2, tab3, tab4]
    diseases = ["Normal", "Cataract", "Glaucoma", "Diabetic Retinopathy"]
    
    for i, disease_name in enumerate(diseases):
        with tabs[i]:
            info = DISEASE_DB[disease_name]
            
            # Header
            st.markdown(f"""
                <div class="disease-card" style="border-left-color: {info['color']};">
                    <h2 style="color: #333;">{disease_name} <span style="font-size: 14px; background-color: #f1f5f9; padding: 4px 8px; border-radius: 12px; color: #64748b; vertical-align: middle;">{info['tag']}</span></h2>
                    <p style="font-size: 16px; line-height: 1.6; color: #333;">{info['desc']}</p>
                </div>
            """, unsafe_allow_html=True)
            
            col_a, col_b = st.columns(2)
            
            with col_a:
                st.markdown("#### Symptoms")
                for s in info['symptoms']:
                    st.markdown(f"- {s}")
                    
                st.markdown("#### Causes / Risk Factors")
                for c in info['causes']:
                    st.markdown(f"- {c}")

            with col_b:
                st.markdown("#### Treatment Options")
                for t in info['treatments']:
                    st.markdown(f"- {t}")

                st.markdown("#### Prevention")
                for p in info['prevention']:
                    st.markdown(f"- {p}")
