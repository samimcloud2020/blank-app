# streamlit_app.py
import streamlit as st
import nest_asyncio
import asyncio
from datetime import date
from main import PatientContext, Runner, doctor_agent, InputGuardrailTripwireTriggered, Prescription, GeneralAdvice

nest_asyncio.apply()

st.set_page_config(page_title="🩺 AI Doctor - Rourkela", page_icon="🩺", layout="centered")

# Design
st.markdown("""
<style>
    .big-title {font-size: 80px !important; font-weight: 900; background: linear-gradient(90deg, #ff1744, #00bcd4, #4caf50); -webkit-background-clip: text; -webkit-text-fill-color: transparent; text-align: center;}
    .header-box {background: linear-gradient(135deg, #1e3a8a, #3b82f6); padding: 35px; border-radius: 30px; color: white; text-align: center; box-shadow: 0 15px 40px rgba(59,130,246,0.4);}
    .rx-big {font-size: 120px !important; font-weight: 900; color: #dc2626; text-align: center; margin: 40px 0; text-shadow: 8px 8px 20px rgba(220,38,38,0.4); letter-spacing: 15px;}
    .rx-box {background: linear-gradient(to bottom, #f8fff8, #f0fdf4); border: 10px solid #16a34a; border-radius: 40px; padding: 60px; box-shadow: 0 30px 70px rgba(22,163,74,0.3);}
    .med-item {background: linear-gradient(to right, #f0fdfa, #ccfbf1); padding: 35px; border-radius: 30px; margin: 30px 0; border-left: 15px solid #14b8a6; box-shadow: 0 12px 35px rgba(20,184,166,0.2);}
    .patient-card {background: linear-gradient(to bottom, #dbeafe, #bfdbfe); border-left: 15px solid #2563eb; padding: 40px; border-radius: 30px; box-shadow: 0 15px 40px rgba(37,99,235,0.25);}
    .sidebar-title {background: linear-gradient(90deg, #d946ef, #f72585); padding: 30px; border-radius: 30px; text-align: center; color: white; font-size: 34px; font-weight: bold;}
    .sidebar-label {font-weight: bold; color: #fbbf24; font-size: 22px; background: #1e1b4b; padding: 15px; border-radius: 20px; text-align: center; margin: 25px 0 10px 0;}
    .sidebar .sidebar-content {background: linear-gradient(180deg, #0f172a, #1e293b); color: white; border-radius: 35px; padding: 30px;}
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("<div class='big-title'>🩺 AI DOCTOR</div>", unsafe_allow_html=True)
st.markdown("""
<div class='header-box'>
    <h1 style='margin:0; font-size:48px;'>VIRTUAL HEALTH CLINIC</h1>
    <h2 style='margin:15px 0; color:#fbbf24;'>Rourkela, Odisha, India</h2>
    <p style='font-size:24px;'>Personalized • Safe • Caring</p>
</div>
""", unsafe_allow_html=True)

# Session
if "messages" not in st.session_state:
    st.session_state.messages = []
if "current_prescription" not in st.session_state:
    st.session_state.current_prescription = None

# Sidebar - Patient Input
with st.sidebar:
    st.markdown("<div class='sidebar-title'>👤 Patient Profile</div>", unsafe_allow_html=True)

    st.markdown("<div class='sidebar-label'>📝 Full Name</div>", unsafe_allow_html=True)
    name = st.text_input("", value="Priya Singh", placeholder="Name", label_visibility="collapsed")

    st.markdown("<div class='sidebar-label'>🎂 Age</div>", unsafe_allow_html=True)
    age = st.number_input("", min_value=1, max_value=120, value=29, label_visibility="collapsed")

    st.markdown("<div class='sidebar-label'>⚧ Gender</div>", unsafe_allow_html=True)
    gender = st.selectbox("", ["Female", "Male", "Other"], label_visibility="collapsed")

    st.markdown("<div class='sidebar-label'>😷 Symptoms</div>", unsafe_allow_html=True)
    symptoms = st.multiselect("", ["Fever", "Headache", "Cough", "Sore Throat", "Body Pain", "Acidity", "Allergy", "Cold", "Runny Nose"], label_visibility="collapsed")
    other = st.text_input("Other?", label_visibility="collapsed")
    all_symptoms = symptoms + ([other] if other else [])

    st.markdown("<div class='sidebar-label'>⚠️ Allergies</div>", unsafe_allow_html=True)
    allergies = st.text_input("", placeholder="e.g., dust", label_visibility="collapsed")

    st.markdown("<div class='sidebar-label'>💊 Current Medicines</div>", unsafe_allow_html=True)
    current_meds = st.text_input("", placeholder="e.g., none", label_visibility="collapsed")

    patient_context = PatientContext(
        patient_id=name or "Patient",
        age=age,
        gender=gender,
        current_symptoms=all_symptoms,
        medical_history=[],
        allergies=[a.strip() for a in allergies.split(",") if a.strip()],
        current_medications=[m.strip() for m in current_meds.split(",") if m.strip()]
    )

# Main Layout
col1, col2 = st.columns([1.4, 2.6])
today = date.today().strftime("%d %B %Y")

with col1:
    st.markdown(f"""
    <div class='patient-card'>
        <h2 style='color:#2563eb; text-align:center;'>📋 Patient Card</h2>
        <div style='background:#e0f2fe; padding:30px; border-radius:25px; text-align:center;'>
            <h3 style='color:#1e40af;'>{patient_context.patient_id}</h3>
            <p style='font-size:19px;'><strong>Age:</strong> {patient_context.age} • <strong>Gender:</strong> {patient_context.gender}</p>
            <p style='color:#dc2626;'><strong>Date:</strong> {today}</p>
        </div>
        <strong style='color:#dc2626;'>Symptoms:</strong><br>
        <p style='font-size:17px; line-height:1.6;'>
            {', '.join(patient_context.current_symptoms) or 'None entered'}
        </p>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("<div class='rx-box'>", unsafe_allow_html=True)
    st.markdown("""
    <div style='text-align:center; margin-bottom:50px;'>
        <h1 style='color:#dc2626; font-weight:900; font-size:58px;'>AI DOCTOR</h1>
        <h2 style='color:#16a34a; font-size:34px;'>Virtual Health Clinic</h2>
        <h3 style='color:#2563eb; font-size:28px;'><strong>Rourkela, Odisha</strong></h3>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("<div class='rx-big'>Rx</div>", unsafe_allow_html=True)

    if st.session_state.current_prescription:
        output = st.session_state.current_prescription
        for i in range(len(output.medications)):
            st.markdown(f"""
            <div class='med-item'>
                <h3 style='color:#166534; font-size:28px; margin:0 0 20px 0;'>{i+1}. {output.medications[i]}</h3>
                <p style='font-size:21px; margin:15px 0;'><strong style='color:#2563eb;'>Take:</strong> {output.sig[i]}</p>
                <p style='font-size:20px; margin:15px 0; color:#dc2626;'><strong>Dispense:</strong> {output.quantity[i]}</p>
            </div>
            """, unsafe_allow_html=True)
        st.markdown(f"<h3 style='text-align:center; color:#dc2626; font-size:30px; margin:40px 0;'>Duration: <strong>{output.duration}</strong></h3>", unsafe_allow_html=True)
        st.markdown(f"<h3 style='text-align:center; color:#b91c1c; font-size:28px;'>Refills: <strong>{output.refills}</strong></h3>", unsafe_allow_html=True)
        if output.additional_notes:
            st.info(f"**Important:** {output.additional_notes}")
    else:
        st.markdown("""
        <div style='text-align:center; padding:120px; background:#f8fafc; border-radius:35px; border:6px dashed #94a3b8;'>
            <h3 style='color:#64748b; font-size:30px;'>Your personalized prescription will appear here</h3>
            <p style='color:#94a3b8; font-size:22px; margin:30px 0 0 0;'>Send a message below</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

# Chat
st.markdown("---")
st.markdown("<h3 style='text-align:center; color:#1e3a8a; margin:60px 0 20px 0; font-size:30px;'>💬 Chat with AI Doctor</h3>", unsafe_allow_html=True)

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"], unsafe_allow_html=True)

if prompt := st.chat_input("🩺 Tell me your symptoms or ask for treatment..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("🩺 Preparing your personalized prescription..."):
            try:
                result = asyncio.run(Runner.run(doctor_agent, prompt, context=patient_context))
                output = result.final_output

                if isinstance(output, Prescription):
                    st.session_state.current_prescription = output
                    st.success("✅ **Your Personalized Prescription is Ready!**")

                elif isinstance(output, GeneralAdvice):
                    st.info("🩺 **Doctor's Advice**")
                    st.markdown(output.advice)
                    st.markdown(f"**Follow-up:** {output.follow_up}")

                st.session_state.messages.append({"role": "assistant", "content": str(output)})

            except Exception as e:
                st.error(f"Error: {str(e)}")
