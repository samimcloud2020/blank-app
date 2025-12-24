# streamlit_app.py
import asyncio
import streamlit as st
from datetime import date
from main import PatientContext, Runner, doctor_agent, InputGuardrailTripwireTriggered, Prescription, GeneralAdvice

st.set_page_config(page_title="🩺 AI Doctor - Rourkela", page_icon="🩺", layout="centered")

# === BEAUTIFUL WELCOME & PROFESSIONAL DESIGN ===
st.markdown("""
<style>
    .big-title {
        font-size: 80px !important; 
        font-weight: 900; 
        background: linear-gradient(90deg, #00c9ff, #92fe9d); 
        -webkit-background-clip: text; 
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin: 20px 0 10px 0;
        letter-spacing: 4px;
    }
    .welcome-box {
        background: linear-gradient(135deg, #667eea, #764ba2); 
        padding: 50px; 
        border-radius: 30px; 
        color: white; 
        text-align: center;
        box-shadow: 0 20px 50px rgba(102,126,234,0.4);
        margin: 40px 0;
        border: 4px solid #a78bfa;
    }
    .sidebar-title {
        background: linear-gradient(90deg, #ff7e5f, #feb47b); 
        padding: 20px; 
        border-radius: 20px; 
        text-align: center; 
        color: white; 
        font-size: 28px; 
        font-weight: bold;
        box-shadow: 0 10px 30px rgba(255,126,95,0.4);
        margin-bottom: 20px;
    }
    .label-bold {
        font-weight: bold; 
        color: #1e3a8a; 
        font-size: 18px; 
        margin-bottom: 8px;
    }
    .sidebar .sidebar-content {
        background: linear-gradient(180deg, #e0e7ff, #c7d2fe); 
        border-radius: 25px; 
        padding: 20px;
        box-shadow: 0 10px 30px rgba(165,180,252,0.3);
    }
    .stTextInput > label, .stSelectbox > label, .stNumberInput > label, .stMultiSelect > label {
        font-weight: bold !important;
        color: #1e40af !important;
        font-size: 18px !important;
    }
    .stTextInput > div > div > input, .stSelectbox > div > div > select {
        background-color: white !important;
        border: 2px solid #6366f1 !important;
        border-radius: 12px !important;
        font-size: 16px !important;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "current_prescription" not in st.session_state:
    st.session_state.current_prescription = None
if "consultation_started" not in st.session_state:
    st.session_state.consultation_started = False

# === LEFT SIDEBAR - BOLD & COLORFUL ===
with st.sidebar:
    st.markdown("<div class='sidebar-title'>👤 Patient Profile</div>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center; color:#4c1d95; font-size:16px; margin-bottom:30px;'>Enter your details to begin</p>", unsafe_allow_html=True)

    st.markdown("<div class='label-bold'>📝 Full Name</div>", unsafe_allow_html=True)
    name = st.text_input("", value="S K Patel", placeholder="Enter your full name", label_visibility="collapsed")

    st.markdown("<div class='label-bold'>🎂 Age</div>", unsafe_allow_html=True)
    age = st.number_input("", min_value=1, max_value=120, value=46, label_visibility="collapsed")

    st.markdown("<div class='label-bold'>⚧ Gender</div>", unsafe_allow_html=True)
    gender = st.selectbox("", ["Male", "Female", "Other"], label_visibility="collapsed")

    st.markdown("<div class='label-bold'>😷 Current Symptoms</div>", unsafe_allow_html=True)
    symptoms = st.multiselect("", [
        "Fever", "Headache", "Cold & Cough", "Sore Throat", "Body Pain", "Acidity",
        "Allergy", "Stomach Upset", "Loose Motion", "Vomiting", "Weakness"
    ], label_visibility="collapsed")
    other = st.text_input("Other symptoms?", placeholder="Type here if not listed", label_visibility="collapsed")
    all_symptoms = symptoms + ([other] if other else [])

    st.markdown("<div class='label-bold'>⚠️ Allergies</div>", unsafe_allow_html=True)
    allergies = st.text_input("", value="dust", placeholder="e.g., penicillin, dust", label_visibility="collapsed")

    st.markdown("<div class='label-bold'>💊 Current Medicines</div>", unsafe_allow_html=True)
    current_meds = st.text_input("", value="paracetamol", placeholder="List any ongoing medicines", label_visibility="collapsed")

    # Build patient context
    patient_context = PatientContext(
        patient_id=name or "Patient",
        age=age,
        gender=gender,
        current_symptoms=all_symptoms,
        medical_history=[],
        allergies=[a.strip() for a in allergies.split(",") if a.strip()],
        current_medications=[m.strip() for m in current_meds.split(",") if m.strip()]
    )

# === MAIN PAGE - INITIAL WELCOME SCREEN ===
if not st.session_state.consultation_started and len(st.session_state.messages) == 0:
    st.markdown("<div class='big-title'>🩺 AI DOCTOR</div>", unsafe_allow_html=True)
    
    st.markdown("""
    <div class='welcome-box'>
        <h1 style='font-size:48px; margin:0; color:white;'>VIRTUAL HEALTH CLINIC</h1>
        <h2 style='font-size:36px; margin:20px 0 10px 0; color:#fbbf24;'>Rourkela, Odisha, India</h2>
        <p style='font-size:22px; margin:15px 0; color:#e0e7ff;'>
            Your Trusted AI Physician • Available 24/7 • Safe & Caring
        </p>
        <p style='font-size:18px; margin:20px 0 0 0; color:#c7d2fe;'>
            Fill your details on the left and start chatting below to get your personalized consultation and prescription
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Chat input to start consultation
    if prompt := st.chat_input("🩺 Describe your symptoms or ask for medicine to begin consultation..."):
        st.session_state.consultation_started = True
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.rerun()

else:
    # === FULL CONSULTATION MODE ===
    st.markdown("<h2 style='text-align:center; color:#1e3a8a; margin:40px 0 20px 0; font-weight:bold;'>Your Personalized Consultation</h2>", unsafe_allow_html=True)

    col1, col2 = st.columns([1.4, 2.6])
    today = date.today().strftime("%d %B %Y")

    with col1:
        st.markdown(f"""
        <div style='background: linear-gradient(to bottom, #dbeafe, #bfdbfe); border-left: 12px solid #2563eb; padding: 30px; border-radius: 20px; box-shadow: 0 12px 35px rgba(37,99,235,0.2);'>
            <h2 style='color:#2563eb; text-align:center;'>📋 Patient Card</h2>
            <div style='text-align:center; padding:20px; background:#e0f2fe; border-radius:20px; margin:20px 0;'>
                <h3 style='margin:5px; color:#1e40af;'>{patient_context.patient_id}</h3>
                <p style='margin:5px; font-size:18px;'><strong>Age:</strong> {patient_context.age} • <strong>Gender:</strong> {patient_context.gender}</p>
                <p style='margin:5px; color:#dc2626;'><strong>Date:</strong> {today}</p>
            </div>
            <strong style='color:#dc2626;'>Symptoms:</strong><br>
            <i style='font-size:16px; color:#374151;'>
                {', '.join(patient_context.current_symptoms) or 'No symptoms entered'}
            </i>
            <hr style='border:1px dashed #93c5fd; margin:25px 0;'>
            <p><strong>Allergies:</strong> {allergies or 'None'}</p>
            <p><strong>Current Meds:</strong> {current_meds or 'None'}</p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div style='background: linear-gradient(to bottom, #f0fdf4, #dcfce7); border: 6px solid #22c55e; border-radius: 30px; padding: 45px; box-shadow: 0 20px 50px rgba(34,197,94,0.25); min-height: 600px;'>
            <div style='text-align:center; margin-bottom:40px;'>
                <h1 style='color:#dc2626; font-weight:900; font-size:52px;'>AI DOCTOR</h1>
                <h2 style='color:#16a34a;'>Virtual Health Clinic</h2>
                <h3 style='color:#2563eb;'><strong>Rourkela, Odisha, India</strong></h3>
            </div>
            <h1 style='font-size:90px; color:#dc2626; text-align:center; font-weight:900; text-shadow: 5px 5px 15px rgba(220,38,38,0.4);'>Rx</h1>
        """, unsafe_allow_html=True)

        if st.session_state.current_prescription:
            output = st.session_state.current_prescription
            for i in range(len(output.medications)):
                st.markdown(f"""
                <div style='background: linear-gradient(to right, #f0fdf4, #bbf7d0); padding: 25px; border-radius: 20px; margin: 20px 0; border-left: 10px solid #16a34a; box-shadow: 0 8px 25px rgba(34,197,94,0.2);'>
                    <h3 style='color:#166534; margin:0 0 15px 0;'>{i+1}. {output.medications[i]}</h3>
                    <p style='margin:8px 0; font-size:18px;'><strong style='color:#2563eb;'>Take →</strong> <strong>{output.sig[i]}</strong></p>
                    <p style='margin:8px 0; font-size:17px;'><strong style='color:#dc2626;'>Dispense →</strong> {output.quantity[i]}</p>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown(f"<h3 style='text-align:center; color:#dc2626; margin:30px 0;'>Duration: <strong>{output.duration}</strong></h3>", unsafe_allow_html=True)
            st.markdown(f"<h3 style='text-align:center; color:#b91c1c;'>Refills: <strong>{output.refills}</strong></h3>", unsafe_allow_html=True)
            
            if output.additional_notes:
                st.info(f"**Important:** {output.additional_notes}")
        else:
            st.markdown("""
            <div style='text-align:center; padding:80px 20px; background:#f8fafc; border-radius:25px; border:4px dashed #94a3b8; margin-top:50px;'>
                <h3 style='color:#64748b;'>Your prescription will appear here</h3>
                <p style='color:#94a3b8; font-size:19px; margin:25px 0 0 0;'>
                    Chat with the doctor below to get your treatment
                </p>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)

    # Chat Section
    st.markdown("---")
    st.markdown("<h3 style='text-align:center; color:#1e3a8a; margin:40px 0 20px 0;'>💬 Chat with Your AI Doctor</h3>", unsafe_allow_html=True)

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"], unsafe_allow_html=True)

    if prompt := st.chat_input("🩺 Tell me how you're feeling or ask for medicine..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("🩺 Preparing your consultation and prescription..."):
                try:
                    result = asyncio.run(Runner.run(doctor_agent, prompt, context=patient_context))
                    output = result.final_output

                    if isinstance(output, Prescription):
                        st.session_state.current_prescription = output
                        st.success("✅ **Prescription Issued!**")
                        st.markdown("**Your prescription is now displayed above permanently ↑**")
                    elif isinstance(output, GeneralAdvice):
                        st.info("🩺 **Doctor's Advice**")
                        st.markdown(output.advice)
                        st.markdown(f"**Follow-up:** {output.follow_up}")

                    st.session_state.messages.append({"role": "assistant", "content": str(output)})
                    st.rerun()

                except InputGuardrailTripwireTriggered:
                    st.error("⚠️ Cannot prescribe this medicine — restricted or unsafe.")
                except Exception:
                    st.error("System error. Please try again.")
