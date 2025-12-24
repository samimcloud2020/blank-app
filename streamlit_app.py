# streamlit_app.py
import asyncio
import streamlit as st
from datetime import date
from main import PatientContext, Runner, doctor_agent, InputGuardrailTripwireTriggered, Prescription, GeneralAdvice

st.set_page_config(page_title="🩺 AI Doctor - Rourkela", page_icon="🩺", layout="centered")

# === SUPER ATTRACTIVE & BOLD DESIGN ===
st.markdown("""
<style>
    .big-title {
        font-size: 68px !important; 
        font-weight: 900; 
        background: linear-gradient(90deg, #ff1744, #00e5ff); 
        -webkit-background-clip: text; 
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 10px;
    }
    .header-box {
        background: linear-gradient(135deg, #311b92, #512da8, #7e57c2); 
        padding: 25px; 
        border-radius: 20px; 
        color: white; 
        text-align: center;
        box-shadow: 0 8px 25px rgba(0,0,0,0.3);
        margin-bottom: 30px;
    }
    .rx-header {
        font-size: 80px !important; 
        font-weight: 900; 
        color: #c62828; 
        text-align: center; 
        margin: 30px 0 20px 0;
        text-shadow: 3px 3px 8px rgba(0,0,0,0.3);
        letter-spacing: 5px;
    }
    .rx-box {
        background: linear-gradient(to bottom, #ffffff, #f1f8e9); 
        border: 5px solid #2e7d32; 
        border-radius: 25px; 
        padding: 40px; 
        box-shadow: 0 15px 40px rgba(46,125,50,0.2);
        margin: 20px 0;
    }
    .med-item {
        background: #e8f5e8; 
        padding: 18px; 
        border-radius: 15px; 
        margin: 15px 0; 
        border-left: 6px solid #43a047;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    .patient-card {
        background: linear-gradient(to bottom, #e1f5fe, #bbdefb); 
        border-left: 10px solid #0277bd; 
        padding: 25px; 
        border-radius: 15px;
        box-shadow: 0 8px 25px rgba(2,119,189,0.15);
        font-size: 16px;
    }
    .sidebar .sidebar-content {
        background: linear-gradient(180deg, #1a237e, #303f9f); 
        color: white;
    }
    .stButton>button {
        background: #d500f9; 
        color: white; 
        font-weight: bold; 
        border-radius: 12px; 
        height: 50px; 
        font-size: 18px;
    }
    h1, h2, h3 {color: #1a237e;}
</style>
""", unsafe_allow_html=True)

# Main Header
st.markdown("<div class='big-title'>🩺 AI DOCTOR</div>", unsafe_allow_html=True)
st.markdown("""
<div class='header-box'>
    <h2 style='margin:0; font-size:36px;'>VIRTUAL HEALTH CLINIC</h2>
    <h3 style='margin:5px 0;'>Rourkela, Odisha, India</h3>
    <p style='font-size:18px; margin:10px 0 0 0;'>Advanced AI-Powered Medical Care • Available 24/7</p>
</div>
""", unsafe_allow_html=True)

# Sidebar (same as before - kept clean)
with st.sidebar:
    st.markdown("""
    <div style='text-align:center; padding:20px; background:#303f9f; border-radius:15px;'>
        <h2 style='color:white;'>👤 Patient Details</h2>
        <p style='color:#c5cae9;'>Enter accurate information</p>
    </div>
    """, unsafe_allow_html=True)

    name = st.text_input("**Full Name**", value="Priya Singh", placeholder="Your name")
    age = st.number_input("**Age**", min_value=1, max_value=120, value=29)
    gender = st.selectbox("**Gender**", ["Female", "Male", "Other"])

    st.markdown("#### 😷 Current Symptoms")
    symptoms = st.multiselect("Select symptoms", [
        "Fever", "Headache", "Cold & Cough", "Sore Throat", "Body Pain", "Acidity",
        "Allergy", "Stomach Upset", "Loose Motion", "Vomiting", "Weakness"
    ])
    other = st.text_input("Any other symptoms?")
    if other:
        symptoms.append(other)

    allergies = st.text_input("**Allergies**", placeholder="e.g., penicillin, dust")
    current_meds = st.text_input("**Current Medicines**", placeholder="none")

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
    <div style='text-align:center; background:#d500f9; padding:15px; border-radius:15px; color:white;'>
        <h3>✅ Ready for Consultation</h3>
        <p style='margin:5px;'><strong>{name}</strong> • {age} yrs</p>
    </div>
    """, unsafe_allow_html=True)

# Chat Interface
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"], unsafe_allow_html=True)

if prompt := st.chat_input("🩺 Describe your symptoms or ask for treatment..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("🩺 AI Doctor is preparing your prescription..."):
            try:
                result = asyncio.run(Runner.run(doctor_agent, prompt, context=patient_context))
                output = result.final_output
                today = date.today().strftime("%d %B %Y")

                if isinstance(output, Prescription):
                    st.success("✅ **Your Prescription is Ready!**")

                    col1, col2 = st.columns([1.3, 2.7])

                    with col1:
                        st.markdown(f"""
                        <div class='patient-card'>
                            <h3 style='color:#0277bd; margin-top:0;'>📋 Patient Information</h3>
                            <p>
                            <strong style='font-size:18px;'>{patient_context.patient_id}</strong><br>
                            Age: <strong>{patient_context.age}</strong> • Gender: <strong>{patient_context.gender}</strong><br>
                            Date: <strong>{today}</strong><br><br>
                            <strong style='color:#d32f2f;'>Chief Complaints:</strong><br>
                            <i>{', '.join(patient_context.current_symptoms) or 'Routine check-up'}</i>
                            </p>
                        </div>
                        """, unsafe_allow_html=True)

                    with col2:
                        st.markdown("<div class='rx-box'>", unsafe_allow_html=True)

                        # Clinic Header
                        st.markdown("""
                        <div style='text-align:center; margin-bottom:30px;'>
                            <h1 style='color:#c62828; font-weight:900; margin:0; font-size:48px;'>AI DOCTOR</h1>
                            <h3 style='color:#2e7d32; margin:5px 0;'>Virtual Health Clinic</h3>
                            <h4 style='color:#1976d2; margin:0;'><strong>Rourkela, Odisha, India</strong></h4>
                        </div>
                        """, unsafe_allow_html=True)

                        # SUPER BOLD Rx
                        st.markdown("<div class='rx-header'>Rx</div>", unsafe_allow_html=True)

                        # Each Medicine in Bold Attractive Box
                        for i in range(len(output.medications)):
                            st.markdown(f"""
                            <div class='med-item'>
                                <h3 style='color:#2e7d32; margin:0 0 10px 0; font-weight:bold;'>
                                    {i+1}. {output.medications[i]}
                                </h3>
                                <p style='margin:8px 0; font-size:17px;'>
                                    <strong style='color:#1976d2;'>Take →</strong> <strong>{output.sig[i]}</strong>
                                </p>
                                <p style='margin:8px 0; font-size:16px;'>
                                    <strong style='color:#d32f2f;'>Dispense →</strong> {output.quantity[i]}
                                </p>
                            </div>
                            """, unsafe_allow_html=True)

                        st.markdown(f"<h4 style='color:#d32f2f; text-align:center; margin-top:25px;'>Duration: <strong>{output.duration}</strong></h4>", unsafe_allow_html=True)
                        st.markdown(f"<h4 style='text-align:center; color:#c62828;'>Refills: <strong>{output.refills}</strong></h4>", unsafe_allow_html=True)

                        if output.additional_notes:
                            st.markdown(f"""
                            <div style='background:#fff3e0; padding:15px; border-radius:12px; border-left:6px solid #ff8f00; margin-top:20px;'>
                                <strong style='color:#e65100;'>⚠️ Important Instructions:</strong><br>
                                {output.additional_notes}
                            </div>
                            """, unsafe_allow_html=True)

                        st.markdown("</div>", unsafe_allow_html=True)

                    st.markdown("""
                    <div style='text-align:center; margin-top:30px; padding:20px; background:#e8f5e8; border-radius:15px; border:2px dashed #4caf50;'>
                        <h3 style='color:#2e7d32; margin:0;'>💊 Show this prescription at any pharmacy</h3>
                        <p style='color:#1b5e20; margin:10px 0 0 0;'>Follow dosage strictly • Contact doctor if symptoms worsen</p>
                    </div>
                    """, unsafe_allow_html=True)

                elif isinstance(output, GeneralAdvice):
                    st.info("🩺 **Doctor's Advice**")
                    st.markdown(f"<div style='font-size:18px; line-height:1.6;'>{output.advice}</div>", unsafe_allow_html=True)
                    st.markdown(f"**Follow-up:** {output.follow_up}")

                st.session_state.messages.append({"role": "assistant", "content": str(output)})

            except InputGuardrailTripwireTriggered:
                st.error("⚠️ **Prescription Denied**\n\nThis medication is restricted or unsafe without in-person examination. Please visit a local doctor.")

            except Exception as e:
                st.error("😞 Something went wrong. Please try again.")
