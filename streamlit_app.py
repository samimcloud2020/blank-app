# streamlit_app.py
import asyncio
import streamlit as st
from datetime import date
from main import PatientContext, Runner, doctor_agent, InputGuardrailTripwireTriggered, Prescription, GeneralAdvice

st.set_page_config(page_title="🩺 AI Doctor - Rourkela", page_icon="🩺", layout="centered")

# === GORGEOUS COLORFUL DESIGN ===
st.markdown("""
<style>
    .big-title {font-size: 60px !important; font-weight: bold; background: linear-gradient(90deg, #ff6b6b, #4ecdc4); -webkit-background-clip: text; -webkit-text-fill-color: transparent;}
    .header-box {background: linear-gradient(135deg, #667eea, #764ba2); padding: 20px; border-radius: 15px; color: white; text-align: center;}
    .rx-header {font-size: 50px; font-weight: bold; color: #d32f2f; text-align: center; margin: 20px 0;}
    .rx-box {background: #f8fff8; border: 3px solid #4caf50; border-radius: 20px; padding: 30px; box-shadow: 0 10px 30px rgba(0,0,0,0.1);}
    .patient-card {background: #e3f2fd; border-left: 8px solid #2196f3; padding: 20px; border-radius: 10px;}
    .sidebar .sidebar-content {background: linear-gradient(180deg, #0d47a1, #1976d2); color: white;}
    h1, h2, h3 {color: #1e3d59;}
    .stButton>button {background: #ff5252; color: white; font-weight: bold; border-radius: 10px;}
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("<div class='big-title'>🩺 AI DOCTOR</div>", unsafe_allow_html=True)
st.markdown("""
<div class='header-box'>
    <h2>Virtual Clinic • Rourkela, Odisha</h2>
    <p>Your Trusted AI Physician | Safe • Fast • Caring</p>
</div>
""", unsafe_allow_html=True)

# Sidebar - Beautiful Patient Form
with st.sidebar:
    st.markdown("""
    <div style='text-align:center; padding:20px; background:#1976d2; border-radius:15px;'>
        <h2 style='color:white;'>👤 Patient Details</h2>
        <p style='color:#bbdefb;'>Please fill accurately</p>
    </div>
    """, unsafe_allow_html=True)

    name = st.text_input("**Full Name**", value="Rahul Sharma", placeholder="Enter your name")
    age = st.number_input("**Age**", min_value=1, max_value=120, value=32)
    gender = st.selectbox("**Gender**", ["Male", "Female", "Other"])

    st.markdown("#### 😷 Today's Symptoms")
    symptoms = st.multiselect("Select your symptoms", [
        "Fever", "Headache", "Cold & Cough", "Sore Throat", "Body Pain", "Acidity",
        "Allergy", "Stomach Upset", "Loose Motion", "Vomiting"
    ])
    other = st.text_input("Other symptoms?")
    if other:
        symptoms.append(other)

    allergies = st.text_input("**Allergies** (if any)", placeholder="e.g., penicillin")
    current_meds = st.text_input("**Current Medicines**", placeholder="e.g., none")

    patient_context = PatientContext(
        patient_id=name or "Patient",
        age=age,
        gender=gender,
        current_symptoms=symptoms,
        medical_history=[],
        allergies=[a.strip() for a in allergies.split(",") if a.strip()],
        current_medications=[m.strip() for m in current_meds.split(",") if m.strip()]
    )

    st.markdown("---")
    st.markdown(f"""
    <div style='text-align:center; background:#ff5252; padding:15px; border-radius:12px; color:white;'>
        <h3>✅ Consultation Ready</h3>
        <p><strong>{name}</strong> • {age} years</p>
    </div>
    """, unsafe_allow_html=True)

# Chat History
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"], unsafe_allow_html=True)

# User Input
if prompt := st.chat_input("🩺 Tell me how you're feeling or ask for medicine..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("🩺 AI Doctor is writing your prescription..."):
            try:
                result = asyncio.run(Runner.run(doctor_agent, prompt, context=patient_context))
                output = result.final_output
                today = date.today().strftime("%d %B %Y")

                if isinstance(output, Prescription):
                    st.success("✅ **Prescription Ready**")

                    # Two columns: Left = Patient Info, Right = Prescription
                    col1, col2 = st.columns([1.2, 2.5])

                    with col1:
                        st.markdown(f"""
                        <div class='patient-card'>
                            <h3 style='color:#1976d2;'>Patient</h3>
                            <p>
                            <strong>{patient_context.patient_id}</strong><br>
                            Age: {patient_context.age} • {patient_context.gender}<br>
                            Date: <strong>{today}</strong><br><br>
                            <strong>Symptoms:</strong><br>
                            {', '.join(patient_context.current_symptoms) or 'General consultation'}
                            </p>
                        </div>
                        """, unsafe_allow_html=True)

                    with col2:
                        st.markdown("<div class='rx-box'>", unsafe_allow_html=True)

                        # Doctor Header
                        st.markdown("""
                        <div style='text-align:center; margin-bottom:20px;'>
                            <h2 style='color:#d32f2f; font-weight:bold;'>AI DOCTOR</h2>
                            <h4>Virtual Clinic<br><strong>Rourkela, Odisha, India</strong></h4>
                        </div>
                        """, unsafe_allow_html=True)

                        # Big Bold Rx
                        st.markdown("<div class='rx-header'>Rx</div>", unsafe_allow_html=True)

                        # Medications with full instructions
                        for i in range(len(output.medications)):
                            st.markdown(f"**{i+1}. {output.medications[i]}**")
                            st.markdown(f"<strong>↳ Take:</strong> {output.sig[i]}", unsafe_allow_html=True)
                            st.markdown(f"<strong>↳ Dispense:</strong> {output.quantity[i]}", unsafe_allow_html=True)
                            st.markdown("<br>", unsafe_allow_html=True)

                        st.markdown(f"**Duration:** {output.duration}")
                        st.markdown(f"**Refills:** {output.refills}")

                        if output.additional_notes:
                            st.info(f"**Important Note:** {output.additional_notes}")

                        st.markdown("</div>", unsafe_allow_html=True)

                    st.warning("💊 Take this prescription to your pharmacy. Follow timing exactly. Contact doctor if no improvement in 3 days.")

                elif isinstance(output, GeneralAdvice):
                    st.info("🩺 **Doctor's Advice**")
                    st.markdown(output.advice)
                    st.markdown(f"**Follow-up:** {output.follow_up}")  # ← FIXED LINE

                # Save response to chat history
                st.session_state.messages.append({"role": "assistant", "content": str(output)})

            except InputGuardrailTripwireTriggered:
                error_msg = """
                ⚠️ **Cannot Issue This Prescription**
                
                This medicine is restricted or unsafe without physical examination.
                For your safety, I can only prescribe common, non-controlled medications.
                
                Please visit a doctor in person.
                """
                st.error(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": error_msg})

            except Exception as e:
                st.error("😞 System error occurred. Please try again.")
                st.session_state.messages.append({"role": "assistant", "content": "Error occurred."})
