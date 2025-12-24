# streamlit_app.py
import streamlit as st
import nest_asyncio
import asyncio
from datetime import date
from main import PatientContext, Runner, doctor_agent, InputGuardrailTripwireTriggered, Prescription, GeneralAdvice

# Fix for asyncio in Streamlit
nest_asyncio.apply()

st.set_page_config(page_title="🩺 AI Doctor - Rourkela", page_icon="🩺", layout="centered")

# === BEAUTIFUL & PROFESSIONAL DESIGN ===
st.markdown("""
<style>
    .big-title {font-size: 78px !important; font-weight: 900; background: linear-gradient(90deg, #ff1744, #00bcd4, #4caf50); -webkit-background-clip: text; -webkit-text-fill-color: transparent; text-align: center; margin: 20px 0;}
    .header-box {background: linear-gradient(135deg, #1e3a8a, #3b82f6); padding: 35px; border-radius: 30px; color: white; text-align: center; box-shadow: 0 15px 40px rgba(59,130,246,0.4);}
    .rx-header {font-size: 100px !important; font-weight: 900; color: #dc2626; text-align: center; margin: 40px 0 30px 0; text-shadow: 6px 6px 20px rgba(220,38,38,0.3);}
    .rx-box {background: linear-gradient(to bottom, #f8fff8, #f0fdf4); border: 8px solid #16a34a; border-radius: 35px; padding: 50px; box-shadow: 0 25px 60px rgba(22,163,74,0.3);}
    .med-item {background: linear-gradient(to right, #f0fdfa, #ccfbf1); padding: 30px; border-radius: 25px; margin: 25px 0; border-left: 12px solid #14b8a6; box-shadow: 0 10px 30px rgba(20,184,166,0.2);}
    .patient-card {background: linear-gradient(to bottom, #dbeafe, #bfdbfe); border-left: 12px solid #2563eb; padding: 35px; border-radius: 25px; box-shadow: 0 15px 40px rgba(37,99,235,0.25);}
    .sidebar-title {background: linear-gradient(90deg, #d946ef, #f72585); padding: 25px; border-radius: 25px; text-align: center; color: white; font-size: 32px; font-weight: bold;}
    .sidebar-label {font-weight: bold; color: #fbbf24; font-size: 20px; background: #1e1b4b; padding: 12px; border-radius: 15px; text-align: center; margin: 20px 0 10px 0;}
    .sidebar .sidebar-content {background: linear-gradient(180deg, #0f172a, #1e293b); color: white; border-radius: 30px; padding: 20px;}
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("<div class='big-title'>🩺 AI DOCTOR</div>", unsafe_allow_html=True)
st.markdown("""
<div class='header-box'>
    <h1 style='margin:0; font-size:45px;'>VIRTUAL HEALTH CLINIC</h1>
    <h2 style='margin:15px 0; color:#fbbf24;'>Rourkela, Odisha, India</h2>
    <p style='font-size:22px;'>Safe • Caring • 24/7 Available</p>
</div>
""", unsafe_allow_html=True)

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# === LEFT SIDEBAR - PATIENT INPUT (Used for Personalized Prescription) ===
with st.sidebar:
    st.markdown("<div class='sidebar-title'>👤 Patient Profile</div>", unsafe_allow_html=True)

    st.markdown("<div class='sidebar-label'>📝 Full Name</div>", unsafe_allow_html=True)
    name = st.text_input("name_input", value="Priya Singh", placeholder="Your full name", label_visibility="collapsed")

    st.markdown("<div class='sidebar-label'>🎂 Age</div>", unsafe_allow_html=True)
    age = st.number_input("age_input", min_value=1, max_value=120, value=29, label_visibility="collapsed")

    st.markdown("<div class='sidebar-label'>⚧ Gender</div>", unsafe_allow_html=True)
    gender = st.selectbox("gender_input", ["Female", "Male", "Other"], label_visibility="collapsed")

    st.markdown("<div class='sidebar-label'>😷 Current Symptoms</div>", unsafe_allow_html=True)
    symptoms = st.multiselect("symptoms_input", [
        "Fever", "Headache", "Cough", "Sore Throat", "Body Pain", "Acidity",
        "Allergy", "Cold", "Runny Nose", "Weakness", "Nausea"
    ], label_visibility="collapsed")
    other_symptom = st.text_input("other_symptom", placeholder="Any other symptom?", label_visibility="collapsed")
    all_symptoms = symptoms + ([other_symptom] if other_symptom else [])

    st.markdown("<div class='sidebar-label'>⚠️ Allergies</div>", unsafe_allow_html=True)
    allergies_input = st.text_input("allergies_input", placeholder="e.g., penicillin, dust", label_visibility="collapsed")

    st.markdown("<div class='sidebar-label'>💊 Current Medicines</div>", unsafe_allow_html=True)
    current_meds_input = st.text_input("current_meds_input", placeholder="e.g., paracetamol", label_visibility="collapsed")

    # Create PatientContext from sidebar input
    patient_context = PatientContext(
        patient_id=name or "Patient",
        age=age,
        gender=gender,
        current_symptoms=all_symptoms,
        medical_history=[],
        allergies=[a.strip() for a in allergies_input.split(",") if a.strip()],
        current_medications=[m.strip() for m in current_meds_input.split(",") if m.strip()]
    )

    st.markdown("---")
    st.markdown(f"""
    <div style='text-align:center; background:linear-gradient(90deg,#ec4899,#f43f5e); padding:20px; border-radius:20px; color:white; box-shadow:0 10px 30px rgba(236,72,153,0.5);'>
        <h2 style='margin:0;'>✅ Consultation Ready</h2>
        <h3 style='margin:10px 0 0 0;'>{name} • {age} yrs</h3>
    </div>
    """, unsafe_allow_html=True)

# Main Layout - Patient Card + Prescription Box
col1, col2 = st.columns([1.4, 2.6])
today = date.today().strftime("%d %B %Y")

with col1:
    st.markdown(f"""
    <div class='patient-card'>
        <h2 style='color:#2563eb; text-align:center; margin-bottom:20px;'>📋 Patient Card</h2>
        <div style='background:#e0f2fe; padding:25px; border-radius:20px; text-align:center;'>
            <h3 style='color:#1e40af; margin:5px 0;'>{patient_context.patient_id}</h3>
            <p style='margin:5px; font-size:18px;'><strong>Age:</strong> {patient_context.age} • <strong>Gender:</strong> {patient_context.gender}</p>
            <p style='margin:5px; color:#dc2626;'><strong>Date:</strong> {today}</p>
        </div>
        <strong style='color:#dc2626; font-size:19px;'>Symptoms:</strong><br>
        <p style='color:#374151; font-size:17px; line-height:1.6;'>
            {', '.join(patient_context.current_symptoms) or 'No symptoms entered'}
        </p>
        <hr style='border:2px dashed #93c5fd; margin:30px 0;'>
        <p><strong>Allergies:</strong> {allergies_input or 'None'}</p>
        <p><strong>Current Medicines:</strong> {current_meds_input or 'None'}</p>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("<div class='rx-box'>", unsafe_allow_html=True)
    st.markdown("""
    <div style='text-align:center; margin-bottom:40px;'>
        <h1 style='color:#dc2626; font-weight:900; font-size:55px;'>AI DOCTOR</h1>
        <h2 style='color:#16a34a; font-size:32px;'>Virtual Health Clinic</h2>
        <h3 style='color:#2563eb; font-size:26px;'><strong>Rourkela, Odisha, India</strong></h3>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("<div class='rx-header'>Rx</div>", unsafe_allow_html=True)

    # Show placeholder until prescription is generated
    if "current_prescription" not in st.session_state or st.session_state.current_prescription is None:
        st.markdown("""
        <div style='text-align:center; padding:100px 20px; background:#fafafa; border-radius:30px; border:5px dashed #94a3b8; margin-top:60px;'>
            <h3 style='color:#64748b; font-size:26px;'>Your prescription will appear here</h3>
            <p style='color:#94a3b8; font-size:20px; margin:30px 0 0 0;'>
                Send a message below to get your personalized treatment
            </p>
        </div>
        """, unsafe_allow_html=True)
    else:
        output = st.session_state.current_prescription
        for i in range(len(output.medications)):
            st.markdown(f"""
            <div class='med-item'>
                <h3 style='color:#166534; font-size:26px; margin:0 0 15px 0;'>{i+1}. {output.medications[i]}</h3>
                <p style='font-size:20px; margin:12px 0;'><strong style='color:#2563eb;'>Take:</strong> {output.sig[i]}</p>
                <p style='font-size:19px; margin:12px 0; color:#dc2626;'><strong>Dispense:</strong> {output.quantity[i]}</p>
            </div>
            """, unsafe_allow_html=True)
        st.markdown(f"<h3 style='text-align:center; color:#dc2626; margin:30px 0;'>Duration: <strong>{output.duration}</strong></h3>", unsafe_allow_html=True)
        st.markdown(f"<h3 style='text-align:center; color:#b91c1c;'>Refills: <strong>{output.refills}</strong></h3>", unsafe_allow_html=True)
        if output.additional_notes:
            st.info(f"**Important Note:** {output.additional_notes}")

    st.markdown("</div>", unsafe_allow_html=True)

# Chat Area
st.markdown("---")
st.markdown("<h3 style='text-align:center; color:#1e3a8a; margin:50px 0 20px 0; font-size:28px;'>💬 Chat with AI Doctor</h3>", unsafe_allow_html=True)

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"], unsafe_allow_html=True)

# User Input
if prompt := st.chat_input("🩺 Describe your symptoms or ask for treatment..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("🩺 AI Doctor is analyzing your symptoms and preparing prescription..."):
            try:
                # Use the patient_context from sidebar
                result = asyncio.run(Runner.run(doctor_agent, prompt, context=patient_context))
                output = result.final_output

                if isinstance(output, Prescription):
                    st.session_state.current_prescription = output  # Save for permanent display
                    st.success("✅ **Your Personalized Prescription is Ready!**")
                    st.markdown("**See your prescription above ↑**")

                    # Also show in chat
                    chat_rx = f"**Prescription for {patient_context.patient_id} ({patient_context.age} yrs, {patient_context.gender})**\n\n"
                    for i in range(len(output.medications)):
                        chat_rx += f"**{i+1}. {output.medications[i]}**\n"
                        chat_rx += f"**Take:** {output.sig[i]}\n"
                        chat_rx += f"**Dispense:** {output.quantity[i]}\n\n"
                    chat_rx += f"**Duration:** {output.duration}\n"
                    chat_rx += f"**Refills:** {output.refills}\n"
                    if output.additional_notes:
                        chat_rx += f"**Note:** {output.additional_notes}"
                    st.markdown(chat_rx)

                elif isinstance(output, GeneralAdvice):
                    st.info("🩺 **Doctor's Advice**")
                    st.markdown(output.advice)
                    st.markdown(f"**Follow-up:** {output.follow_up}")

                st.session_state.messages.append({"role": "assistant", "content": str(output)})

            except InputGuardrailTripwireTriggered:
                st.error("⚠️ Cannot prescribe — restricted medication.")
            except Exception as e:
                st.error(f"Error: {str(e)}")
