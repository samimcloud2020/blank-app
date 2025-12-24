# streamlit_app.py
import streamlit as st
from datetime import date
from main import PatientContext, Runner, doctor_agent, InputGuardrailTripwireTriggered, Prescription, GeneralAdvice

st.set_page_config(page_title="🩺 AI Doctor - Rourkela", page_icon="🩺", layout="centered")

# === YOUR BEAUTIFUL DESIGN (keep exactly as you had) ===
st.markdown("""
<style>
    .big-title {
        font-size: 78px !important;
        font-weight: 900;
        background: linear-gradient(90deg, #ff1744, #00bcd4, #4caf50);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin: 20px 0 10px 0;
        letter-spacing: 4px;
    }
    .header-box {
        background: linear-gradient(135deg, #1e3a8a, #3b82f6, #60a5fa);
        padding: 35px;
        border-radius: 30px;
        color: white;
        text-align: center;
        box-shadow: 0 15px 40px rgba(59,130,246,0.4);
        margin-bottom: 40px;
        border: 4px solid #93c5fd;
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
    }
    .sidebar-title {
        background: linear-gradient(90deg, #d946ef, #f72585);
        padding: 25px;
        border-radius: 25px;
        text-align: center;
        color: white;
        font-size: 32px;
        font-weight: bold;
        box-shadow: 0 12px 35px rgba(249,38,133,0.5);
        margin-bottom: 30px;
    }
    .sidebar-label {
        font-weight: bold !important;
        color: #fbbf24 !important;
        font-size: 20px !important;
        background: #1e1b4b;
        padding: 12px;
        border-radius: 15px;
        text-align: center;
        margin: 20px 0 10px 0;
        box-shadow: 0 6px 15px rgba(0,0,0,0.3);
    }
    .sidebar .sidebar-content {
        background: linear-gradient(180deg, #0f172a, #1e293b);
        color: white;
        border-radius: 30px;
        padding: 20px;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("<div class='big-title'>🩺 AI DOCTOR</div>", unsafe_allow_html=True)
st.markdown("""
<div class='header-box'>
    <h1 style='margin:0; font-size:45px; color:white;'>VIRTUAL HEALTH CLINIC</h1>
    <h2 style='margin:15px 0 10px 0; color:#fbbf24;'>Rourkela, Odisha, India</h2>
    <p style='font-size:22px; margin:0; color:#e0e7ff;'>
        Your Trusted AI Physician • Safe • Caring • 24/7 Available
    </p>
</div>
""", unsafe_allow_html=True)

# Session state
if "messages" not in st.session_state:
    st.session_state.messages = []

# Sidebar - Bold & Colorful
with st.sidebar:
    st.markdown("<div class='sidebar-title'>👤 Patient Profile</div>", unsafe_allow_html=True)

    st.markdown("<div class='sidebar-label'>📝 Full Name</div>", unsafe_allow_html=True)
    name = st.text_input("", value="Priya Singh", placeholder="Enter name", label_visibility="collapsed")

    st.markdown("<div class='sidebar-label'>🎂 Age</div>", unsafe_allow_html=True)
    age = st.number_input("", min_value=1, max_value=120, value=29, label_visibility="collapsed")

    st.markdown("<div class='sidebar-label'>⚧ Gender</div>", unsafe_allow_html=True)
    gender = st.selectbox("", ["Female", "Male", "Other"], label_visibility="collapsed")

    st.markdown("<div class='sidebar-label'>😷 Current Symptoms</div>", unsafe_allow_html=True)
    symptoms = st.multiselect("", [
        "Fever", "Headache", "Cold & Cough", "Sore Throat", "Body Pain", "Acidity",
        "Allergy", "Stomach Upset", "Loose Motion", "Vomiting", "Weakness"
    ], label_visibility="collapsed")
    other = st.text_input("Other symptoms?", placeholder="Not listed?", label_visibility="collapsed")
    all_symptoms = symptoms + ([other] if other else [])

    st.markdown("<div class='sidebar-label'>⚠️ Allergies</div>", unsafe_allow_html=True)
    allergies = st.text_input("", placeholder="e.g., penicillin", label_visibility="collapsed")

    st.markdown("<div class='sidebar-label'>💊 Current Medicines</div>", unsafe_allow_html=True)
    current_meds = st.text_input("", placeholder="List medicines", label_visibility="collapsed")

    patient_context = PatientContext(
        patient_id=name or "Patient",
        age=age,
        gender=gender,
        current_symptoms=all_symptoms,
        medical_history=[],
        allergies=[a.strip() for a in allergies.split(",") if a.strip()],
        current_medications=[m.strip() for m in current_meds.split(",") if m.strip()]
    )

# Chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"], unsafe_allow_html=True)

# Chat input
if prompt := st.chat_input("🩺 Describe your symptoms or ask for medicine..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("🩺 AI Doctor is preparing your prescription..."):
            try:
                # CORRECT WAY: Use await instead of asyncio.run()
                result = await Runner.run(doctor_agent, prompt, context=patient_context)
                output = result.final_output
                today = date.today().strftime("%d %B %Y")

                if isinstance(output, Prescription):
                    st.success("✅ **Prescription Ready!**")

                    col1, col2 = st.columns([1.3, 2.7])

                    with col1:
                        st.markdown(f"""
                        <div class='patient-card'>
                            <h3 style='color:#0277bd; text-align:center;'>📋 Patient Details</h3>
                            <p style='text-align:center; background:#e0f2fe; padding:20px; border-radius:15px;'>
                                <strong style='font-size:20px;'>{patient_context.patient_id}</strong><br>
                                Age: <strong>{patient_context.age}</strong> • Gender: <strong>{patient_context.gender}</strong><br>
                                Date: <strong>{today}</strong>
                            </p>
                            <strong style='color:#d32f2f;'>Symptoms:</strong><br>
                            <i>{', '.join(patient_context.current_symptoms) or 'General'}</i>
                        </div>
                        """, unsafe_allow_html=True)

                    with col2:
                        st.markdown("<div class='rx-box'>", unsafe_allow_html=True)
                        st.markdown("""
                        <div style='text-align:center; margin-bottom:40px;'>
                            <h1 style='color:#dc2626; font-weight:900; font-size:52px;'>AI DOCTOR</h1>
                            <h2 style='color:#16a34a;'>Virtual Health Clinic</h2>
                            <h3 style='color:#2563eb;'><strong>Rourkela, Odisha, India</strong></h3>
                        </div>
                        """, unsafe_allow_html=True)
                        st.markdown("<div class='rx-header'>Rx</div>", unsafe_allow_html=True)

                        for i in range(len(output.medications)):
                            st.markdown(f"""
                            <div class='med-item'>
                                <h3 style='color:#166534; font-size:26px;'>{i+1}. {output.medications[i]}</h3>
                                <p style='font-size:20px;'><strong style='color:#2563eb;'>Take:</strong> {output.sig[i]}</p>
                                <p style='font-size:19px; color:#dc2626;'><strong>Dispense:</strong> {output.quantity[i]}</p>
                            </div>
                            """, unsafe_allow_html=True)

                        st.markdown(f"<h3 style='text-align:center; color:#dc2626;'>Duration: <strong>{output.duration}</strong></h3>", unsafe_allow_html=True)
                        st.markdown(f"<h3 style='text-align:center; color:#b91c1c;'>Refills: <strong>{output.refills}</strong></h3>", unsafe_allow_html=True)

                        if output.additional_notes:
                            st.info(f"**Note:** {output.additional_notes}")

                        st.markdown("</div>", unsafe_allow_html=True)

                elif isinstance(output, GeneralAdvice):
                    st.info("🩺 **Doctor's Advice**")
                    st.markdown(output.advice)
                    st.markdown(f"**Follow-up:** {output.follow_up}")

                st.session_state.messages.append({"role": "assistant", "content": str(output)})

            except InputGuardrailTripwireTriggered:
                st.error("⚠️ Cannot prescribe — restricted or unsafe medication.")
            except Exception as e:
                st.error(f"😞 Error: {str(e)}")  # This will show the real error if any
