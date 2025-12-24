# streamlit_app.py
import asyncio
import streamlit as st
from datetime import date
from main import PatientContext, Runner, doctor_agent, InputGuardrailTripwireTriggered, Prescription, GeneralAdvice

st.set_page_config(page_title="🩺 Dr. AI - Virtual Clinic", page_icon="🩺", layout="centered")

# === BEAUTIFUL MODERN CSS ===
st.markdown("""
<style>
    .big-font {font-size: 52px !important; font-weight: bold; color: #1e3d59;}
    .header {color: #1167b1; font-weight: bold;}
    .rx-box {background: linear-gradient(135deg, #e3f2fd, #bbdefb); padding: 20px; border-radius: 15px; border-left: 8px solid #1976d2;}
    .sidebar .sidebar-content {background: linear-gradient(180deg, #03256c, #1167b1); color: white;}
    .stButton>button {background: #ff6b6b; color: white; font-weight: bold;}
    h1, h2, h3 {color: #03256c;}
    .patient-info {background: #f0f8ff; padding: 15px; border-radius: 10px; border: 2px dashed #1167b1;}
</style>
""", unsafe_allow_html=True)

st.markdown("<div class='big-font'>🩺 Dr. AI Clinic</div>", unsafe_allow_html=True)
st.markdown("### <span class='header'>Your Personal Virtual Doctor</span>", unsafe_allow_html=True)
st.caption("Professional • Safe • Always Here for You")

# === LEFT SIDEBAR - ATTRACTIVE PATIENT PROFILE ===
with st.sidebar:
    st.markdown("""
    <div style='text-align:center; padding:20px; background:#1167b1; border-radius:15px;'>
        <h2 style='color:white; margin:0;'>👤 Patient Card</h2>
        <p style='color:#a0d8f1;'>Fill your details</p>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("---")

    name = st.text_input("**Full Name**", value="Aisha Khan", placeholder="Enter name")
    age = st.number_input("**Age**", min_value=1, max_value=120, value=28)
    gender = st.selectbox("**Gender**", ["Female", "Male", "Other", "Prefer not to say"])

    st.markdown("#### 😷 Symptoms Today")
    symptoms = st.multiselect("Select symptoms", [
        "Headache", "Fever", "Sore Throat", "Cough", "Heartburn", "Allergies",
        "Body Pain", "Cold", "Nausea", "Rash", "Fatigue"
    ])
    other = st.text_input("Other symptoms")
    if other:
        symptoms.append(other)

    st.markdown("#### 🩹 Medical History")
    history = st.multiselect("Known conditions", ["None", "Hypertension", "Diabetes", "Asthma", "Migraines", "Allergies"])

    allergies = st.text_input("**Allergies**", placeholder="e.g., penicillin, nuts")
    meds = st.text_input("**Current Medications**", placeholder="e.g., metformin")

    # Build context
    patient_context = PatientContext(
        patient_id=name or "Patient",
        age=age,
        gender=gender.capitalize(),
        current_symptoms=symptoms,
        medical_history=history,
        allergies=[a.strip() for a in allergies.split(",") if a.strip()],
        current_medications=[m.strip() for m in meds.split(",") if m.strip()]
    )

    st.markdown("---")
    st.markdown(f"""
    <div style='text-align:center; background:#ff6b6b; padding:15px; border-radius:12px; color:white;'>
        <h3>✅ Ready for Consultation</h3>
        <p><strong>{name or "Patient"}</strong> • Age {age}</p>
    </div>
    """, unsafe_allow_html=True)

# === CHAT INTERFACE ===
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
        with st.spinner("🔬 Dr. AI is reviewing your case..."):
            try:
                result = asyncio.run(Runner.run(doctor_agent, prompt, context=patient_context))
                output = result.final_output

                today = date.today().strftime("%B %d, %Y")

                if isinstance(output, Prescription):
                    # === REALISTIC PRESCRIPTION DISPLAY ===
                    st.success("💊 **Prescription Issued**")

                    col1, col2 = st.columns([1, 3])

                    with col1:
                        st.markdown(f"""
                        <div class='patient-info'>
                            <h3 style='color:#1167b1; margin:0;'>Patient</h3>
                            <p><strong>{patient_context.patient_id}</strong><br>
                            Age: {patient_context.age} • {patient_context.gender}<br>
                            Date: <strong>{today}</strong><br><br>
                            <strong>Symptoms:</strong><br>
                            {', '.join(patient_context.current_symptoms) or 'Not specified'}
                            </p>
                        </div>
                        """, unsafe_allow_html=True)

                    with col2:
                        st.markdown("<div class='rx-box'>", unsafe_allow_html=True)
                        st.markdown("**Rx**")
                        for i, item in enumerate(output.rx_items):
                            st.markdown(f"**{i+1}. {item}**")
                            st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;Sig: {output.sig[i]}")
                            st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;Disp: {output.quantity[i]}")
                            st.markdown("<br>", unsafe_allow_html=True)
                        st.markdown(f"**Refills:** {output.refills}")
                        if output.notes:
                            st.info(f"**Note:** {output.notes}")
                        st.markdown("</div>", unsafe_allow_html=True)

                    st.warning("🩺 Take this prescription to your pharmacy. Follow instructions carefully.")

                elif isinstance(output, GeneralAdvice):
                    st.info("🩺 **Doctor's Advice**")
                    st.markdown(output.advice)
                    st.markdown(f"**Follow-up:** {output.follow_up}")

                st.session_state.messages.append({"role": "assistant", "content": str(output)})

            except InputGuardrailTripwireTriggered:
                st.error("""
                ⚠️ **Cannot Issue Prescription**
                
                This request involves restricted medication or requires in-person evaluation.
                
                For your safety, I can only prescribe common, safe medications.
                """)

            except Exception as e:
                st.error("System error. Please try again.")
