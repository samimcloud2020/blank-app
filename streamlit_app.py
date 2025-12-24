# streamlit_app.py
import asyncio
import streamlit as st
from main import PatientContext, Runner, doctor_agent, InputGuardrailTripwireTriggered, Prescription, GeneralAdvice

# Page Config
st.set_page_config(
    page_title="🩺 Virtual Doctor - AI Consultation",
    page_icon="🩺",
    layout="centered",
    initial_sidebar_state="expanded"
)

# Styling
st.markdown("""
<style>
    .main {background-color: #f8f9fa;}
    .sidebar .sidebar-content {background: linear-gradient(180deg, #0d47a1, #1976d2); color: white;}
    h1, h2, h3 {color: #0d47a1;}
    .stSuccess {background-color: #e8f5e8; color: #2e7d32;}
    .stError {background-color: #ffebee; color: #c62828;}
    .stInfo {background-color: #e3f2fd; color: #1565c0;}
</style>
""", unsafe_allow_html=True)

st.title("🩺 **Virtual Doctor Consultation**")
st.markdown("### Safe • Responsible • AI-Powered Medical Guidance")
st.caption("⚠️ This is not a substitute for real medical care. For emergencies, call your local emergency services.")

# Sidebar - Patient Profile Input
with st.sidebar:
    st.markdown("<h2 style='color:white;'>📋 Patient Information</h2>", unsafe_allow_html=True)
    st.markdown("---")

    name = st.text_input("**Full Name**", value="Alex Rivera")
    age = st.number_input("**Age**", min_value=1, max_value=120, value=30)
    gender = st.selectbox("**Gender**", ["male", "female", "other", "prefer not to say"])

    st.markdown("#### 😷 **Current Symptoms**")
    symptoms = st.multiselect(
        "Select or add your symptoms",
        ["fever", "headache", "sore throat", "cough", "runny nose", "heartburn", "allergy symptoms",
         "nausea", "rash", "joint pain", "fatigue", "shortness of breath"]
    )
    custom_symptom = st.text_input("Other symptom")
    if custom_symptom:
        symptoms.append(custom_symptom)

    st.markdown("#### 🩹 **Medical History**")
    history = st.multiselect("Known conditions", ["hypertension", "diabetes", "asthma", "migraines", "none"])
    other_history = st.text_input("Other conditions")
    if other_history:
        history.append(other_history)

    allergies = st.text_input("**Allergies** (e.g., penicillin, nuts)", placeholder="none")
    current_meds = st.text_input("**Current Medications**", placeholder="e.g., ibuprofen, metformin")

    # Build Patient Context from Web Input
    patient_context = PatientContext(
        patient_id=name or "Patient",
        age=age,
        gender=gender,
        current_symptoms=symptoms,
        medical_history=history,
        allergies=[a.strip() for a in allergies.split(",") if a.strip()],
        current_medications=[m.strip() for m in current_meds.split(",") if m.strip()]
    )

    st.markdown("---")
    st.markdown("<h3 style='text-align:center; color:white; background:#0d47a1; padding:10px; border-radius:10px;'>✅ Ready for Consultation</h3>", unsafe_allow_html=True)

# Chat Interface
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("🩺 Tell me your symptoms or ask a medical question..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("🩺 Your doctor is reviewing your case..."):
            try:
                result = asyncio.run(Runner.run(doctor_agent, prompt, context=patient_context))
                output = result.final_output

                if isinstance(output, Prescription):
                    st.success("💊 **Prescription Issued**")
                    st.markdown(f"**Medication:** {output.medication}")
                    st.markdown(f"**Dosage:** {output.dosage}")
                    st.markdown(f"**Duration:** {output.duration}")
                    st.markdown(f"**Quantity:** {output.quantity}")
                    st.markdown(f"**Instructions:** {output.instructions}")
                    if output.notes:
                        st.info(f"**Note from Doctor:** {output.notes}")
                    st.markdown(f"**Refill Allowed:** {'Yes' if output.refill else 'No'}")
                    st.warning("Take this prescription to your pharmacy.")

                elif isinstance(output, GeneralAdvice):
                    st.info("🩺 **Doctor's Recommendation**")
                    st.markdown(output.advice)
                    st.markdown(f"**Follow-up:** {output.follow_up}")

                else:
                    st.markdown(output)

                st.session_state.messages.append({"role": "assistant", "content": str(output)})

            except InputGuardrailTripwireTriggered:
                st.error("""
                ⚠️ **Cannot Proceed with Request**
                
                This involves a controlled or restricted medication.
                I can only prescribe safe, common medications for routine conditions.
                
                Please see a doctor in person.
                """)

            except Exception as e:
                st.error("😞 A system error occurred. Please try again.")
