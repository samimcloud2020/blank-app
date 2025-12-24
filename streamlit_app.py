# streamlit_app.py
import asyncio
import streamlit as st
from datetime import date
from main import PatientContext, Runner, doctor_agent, InputGuardrailTripwireTriggered, Prescription, GeneralAdvice

st.set_page_config(page_title="🩺 AI Doctor - Rourkela", page_icon="🩺", layout="centered")

# === PROFESSIONAL & BEAUTIFUL DESIGN ===
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
    .rx-header {
        font-size: 100px !important; 
        font-weight: 900; 
        color: #dc2626; 
        text-align: center; 
        margin: 40px 0 30px 0;
        text-shadow: 6px 6px 20px rgba(220,38,38,0.3);
        letter-spacing: 10px;
    }
    .rx-box {
        background: linear-gradient(to bottom, #f8fff8, #f0fdf4); 
        border: 8px solid #16a34a; 
        border-radius: 35px; 
        padding: 50px; 
        box-shadow: 0 25px 60px rgba(22,163,74,0.3);
        min-height: 650px;
    }
    .med-item {
        background: linear-gradient(to right, #f0fdfa, #ccfbf1); 
        padding: 30px; 
        border-radius: 25px; 
        margin: 25px 0; 
        border-left: 12px solid #14b8a6;
        box-shadow: 0 10px 30px rgba(20,184,166,0.2);
    }
    .patient-card {
        background: linear-gradient(to bottom, #dbeafe, #bfdbfe); 
        border-left: 12px solid #2563eb; 
        padding: 35px; 
        border-radius: 25px;
        box-shadow: 0 15px 40px rgba(37,99,235,0.25);
        font-size: 18px;
        min-height: 550px;
    }
    .sidebar-title {
        background: linear-gradient(90deg, #ff7e5f, #feb47b); 
        padding: 25px; 
        border-radius: 25px; 
        text-align: center; 
        color: white; 
        font-size: 32px; 
        font-weight: bold;
        box-shadow: 0 12px 35px rgba(255,126,95,0.4);
        margin-bottom: 30px;
    }
    .label-bold {
        font-weight: bold; 
        color: #1e3a8a; 
        font-size: 20px; 
        margin: 15px 0 8px 0;
    }
    .sidebar .sidebar-content {
        background: linear-gradient(180deg, #e0e7ff, #c7d2fe); 
        border-radius: 30px; 
        padding: 30px;
        box-shadow: 0 15px 40px rgba(199,210,254,0.4);
    }
</style>
""", unsafe_allow_html=True)

# Session State
if "messages" not in st.session_state:
    st.session_state.messages = []
if "current_prescription" not in st.session_state:
    st.session_state.current_prescription = None
if "consultation_started" not in st.session_state:
    st.session_state.consultation_started = False

# Sidebar - Bold & Colorful Labels
with st.sidebar:
    st.markdown("<div class='sidebar-title'>👤 Patient Profile</div>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center; color:#4c1d95; font-size:17px; margin-bottom:30px;'>Fill details to get personalized care</p>", unsafe_allow_html=True)

    st.markdown("<div class='label-bold'>📝 Full Name</div>", unsafe_allow_html=True)
    name = st.text_input("", value="S K Patel", placeholder="Enter name", label_visibility="collapsed")

    st.markdown("<div class='label-bold'>🎂 Age</div>", unsafe_allow_html=True)
    age = st.number_input("", min_value=1, max_value=120, value=46, label_visibility="collapsed")

    st.markdown("<div class='label-bold'>⚧ Gender</div>", unsafe_allow_html=True)
    gender = st.selectbox("", ["Male", "Female", "Other"], label_visibility="collapsed")

    st.markdown("<div class='label-bold'>😷 Current Symptoms</div>", unsafe_allow_html=True)
    symptoms = st.multiselect("", [
        "Fever", "Headache", "Cold & Cough", "Sore Throat", "Body Pain", "Acidity", "Allergy"
    ], label_visibility="collapsed")
    other = st.text_input("Other symptoms?", label_visibility="collapsed")
    all_symptoms = symptoms + ([other] if other else [])

    st.markdown("<div class='label-bold'>⚠️ Allergies</div>", unsafe_allow_html=True)
    allergies = st.text_input("", value="dust", placeholder="e.g., penicillin", label_visibility="collapsed")

    st.markdown("<div class='label-bold'>💊 Current Medicines</div>", unsafe_allow_html=True)
    current_meds = st.text_input("", value="paracetamol", placeholder="List medicines", label_visibility="collapsed")

    patient_context = PatientContext(
        patient_id=name or "Patient",
        age=age,
        gender=gender,
        current_symptoms=all_symptoms,
        medical_history=[],
        allergies=[a.strip() for a in allergies.split(",") if a.strip()],
        current_medications=[m.strip() for m in current_meds.split(",") if m.strip()]
    )

# Initial Welcome Page
if not st.session_state.consultation_started and len(st.session_state.messages) == 0:
    st.markdown("<div class='big-title'>🩺 AI DOCTOR</div>", unsafe_allow_html=True)
    st.markdown("""
    <div class='welcome-box'>
        <h1 style='font-size:50px; margin:0;'>VIRTUAL HEALTH CLINIC</h1>
        <h2 style='font-size:38px; margin:20px 0 10px 0; color:#fbbf24;'>Rourkela, Odisha, India</h2>
        <p style='font-size:22px; margin:20px 0; color:#e0e7ff;'>
            Your Trusted AI Physician • Available 24/7 • Safe & Caring
        </p>
        <p style='font-size:19px; margin:30px 0 0 0; color:#c7d2fe;'>
            Enter your details on the left → Start chatting below to receive your prescription
        </p>
    </div>
    """, unsafe_allow_html=True)

    if prompt := st.chat_input("🩺 Describe your symptoms to begin consultation..."):
        st.session_state.consultation_started = True
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.rerun()

else:
    # Full Consultation View
    col1, col2 = st.columns([1.4, 2.6])
    today = date.today().strftime("%d %B %Y")

    with col1:
        st.markdown(f"""
        <div class='patient-card'>
            <h2 style='color:#2563eb; text-align:center; margin-bottom:20px;'>📋 Patient Card</h2>
            <div style='background:#e0f2fe; padding:25px; border-radius:20px; text-align:center; margin-bottom:25px;'>
                <h3 style='color:#1e40af; margin:5px 0;'>{patient_context.patient_id}</h3>
                <p style='margin:5px; font-size:19px;'><strong>Age:</strong> {patient_context.age} • <strong>Gender:</strong> {patient_context.gender}</p>
                <p style='margin:5px; color:#dc2626; font-size:18px;'><strong>Date:</strong> {today}</p>
            </div>
            <strong style='color:#dc2626; font-size:19px;'>Symptoms:</strong><br>
            <p style='color:#374151; font-size:17px; line-height:1.6;'>
                {', '.join(patient_context.current_symptoms) or 'Not specified'}
            </p>
            <hr style='border:2px dashed #93c5fd; margin:30px 0;'>
            <p><strong>Allergies:</strong> {allergies or 'None declared'}</p>
            <p><strong>Current Medicines:</strong> {current_meds or 'None'}</p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("<div class='rx-box'>", unsafe_allow_html=True)

        st.markdown("""
        <div style='text-align:center; margin-bottom:50px;'>
            <h1 style='color:#dc2626; font-weight:900; font-size:55px; text-shadow: 4px 4px 12px rgba(220,38,38,0.3);'>AI DOCTOR</h1>
            <h2 style='color:#16a34a; font-size:32px; margin:10px 0;'>Virtual Health Clinic</h2>
            <h3 style='color:#2563eb; font-size:26px; margin:0;'><strong>Rourkela, Odisha, India</strong></h3>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<div class='rx-header'>Rx</div>", unsafe_allow_html=True)

        if st.session_state.current_prescription:
            output = st.session_state.current_prescription
            for i in range(len(output.medications)):
                st.markdown(f"""
                <div class='med-item'>
                    <h3 style='color:#0f766e; font-size:24px; margin:0 0 20px 0; font-weight:bold;'>
                        {i+1}. {output.medications[i]}
                    </h3>
                    <p style='font-size:20px; margin:12px 0; line-height:1.8;'>
                        <strong style='color:#1d4ed8;'>Take:</strong> {output.sig[i]}
                    </p>
                    <p style='font-size:19px; margin:12px 0; color:#991b1b;'>
                        <strong>Dispense:</strong> {output.quantity[i]}
                    </p>
                </div>
                """, unsafe_allow_html=True)

            st.markdown(f"""
            <div style='text-align:center; margin:40px 0 20px 0;'>
                <h3 style='color:#dc2626; font-size:26px; margin:0;'>
                    Duration: <strong>{output.duration}</strong>
                </h3>
                <h3 style='color:#b91c1c; font-size:24px; margin:15px 0 0 0;'>
                    Refills: <strong>{output.refills}</strong>
                </h3>
            </div>
            """, unsafe_allow_html=True)

            if output.additional_notes:
                st.markdown(f"""
                <div style='background:#fff7ed; padding:25px; border-radius:20px; border-left:10px solid #f97316; margin-top:30px; box-shadow:0 8px 25px rgba(249,115,22,0.15);'>
                    <strong style='color:#c2410c; font-size:20px;'>⚠️ Important Note:</strong><br>
                    <p style='font-size:18px; margin:10px 0 0 0; color:#7c2d12; line-height:1.6;'>
                        {output.additional_notes}
                    </p>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style='text-align:center; padding:100px 20px; background:#fafafa; border-radius:30px; border:5px dashed #94a3b8; margin-top:60px;'>
                <h3 style='color:#64748b; font-size:26px; margin:0;'>Your prescription will appear here</h3>
                <p style='color:#94a3b8; font-size:20px; margin:30px 0 0 0;'>
                    Start chatting below to consult the doctor
                </p>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)

    # Chat Area
    st.markdown("---")
    st.markdown("<h3 style='text-align:center; color:#1e3a8a; margin:50px 0 20px 0; font-size:28px;'>💬 Chat with AI Doctor</h3>", unsafe_allow_html=True)

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"], unsafe_allow_html=True)

    if prompt := st.chat_input("🩺 Tell me your symptoms or ask for treatment..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("🩺 AI Doctor is preparing your prescription..."):
                try:
                    result = asyncio.run(Runner.run(doctor_agent, prompt, context=patient_context))
                    output = result.final_output

                    if isinstance(output, Prescription):
                        st.session_state.current_prescription = output
                        st.success("✅ **Prescription Issued Successfully!**")
                        st.markdown("**Check your beautiful prescription above ↑**")
                    elif isinstance(output, GeneralAdvice):
                        st.info("🩺 **Medical Advice**")
                        st.markdown(output.advice)
                        st.markdown(f"**Follow-up:** {output.follow_up}")

                    st.session_state.messages.append({"role": "assistant", "content": str(output)})
                    st.rerun()

                except InputGuardrailTripwireTriggered:
                    st.error("⚠️ Cannot prescribe — restricted medication or needs in-person exam.")
                except Exception:
                    st.error("System error. Please try again.")
