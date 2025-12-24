# streamlit_app.py
import asyncio
import streamlit as st
from main import PatientContext, Runner, doctor_agent, InputGuardrailTripwireTriggered, Prescription, GeneralAdvice

st.set_page_config(
    page_title="🩺 Virtual Doctor Consultation",
    page_icon="🩺",
    layout="centered",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .main {background-color: #f8f9fa;}
    .sidebar .sidebar-content {
        background: linear-gradient(180deg, #0f3b57, #1e5f87);
        color: white;
    }
    h1, h2, h3 {color: #0d6efd;}
    .stSuccess {background-color: #d4edda; color: #155724;}
    .stError {background-color: #f8d7da; color: #721c24;}
    .stInfo {background-color: #d1ecf1; color: #0c5460;}
</style>
""", unsafe_allow_html=True)

st.title("🩺 **Virtual Doctor Consultation**")
st.markdown("### Safe • Ethical • AI-Powered Medical Guidance")
st.caption("⚠️ This is not a substitute for real medical care. Always consult a licensed physician.")

# Sidebar - Patient Profile
with st.sidebar:
    st.markdown("""
    <div style='text-align: center; padding: 20px; background:#0d6efd; border-radius:10px; color:white;'>
        <h2>📋 Patient Profile</h2>
        <p>Accurate info = better guidance</p>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("---")

    name = st.text_input("**Full Name**", value="Jane Smith")
    age = st.number_input("**Age**", min_value=1, max_value=120, value=42)
    gender = st.selectbox("**Gender**", ["female", "male", "other", "prefer not to say"])

    st.markdown("#### 😷 **Current Symptoms**")
    symptoms = st.multiselect("Select common symptoms", [
        "fever", "cough", "sore throat", "headache", "fatigue", "nausea",
        "shortness of breath", "chest pain", "rash", "joint pain"
    ])
    custom_symptom = st.text_input("Other symptoms")
    if custom_symptom:
        symptoms.append(custom_symptom)

    st.markdown("#### 🩹 **Medical History**")
    history = st.multiselect("Known conditions", [
        "hypertension", "diabetes", "asthma", "migraines", "heart disease", "none"
    ])
    custom_history = st.text_input("Other conditions")
    if custom_history:
        history.append(custom_history)

    allergies = st.text_input("**Allergies** (e.g., penicillin, latex)", placeholder="none")
    meds = st.text_input("**Current Medications**", placeholder="e.g., albuterol, ibuprofen")

    patient_context = PatientContext(
        patient_id=name,
        age=age,
        gender=gender,
        current_symptoms=symptoms,
        medical_history=history,
        allergies=[a.strip() for a in allergies.split(",") if a.strip()],
        current_medications=[m.strip() for m in meds.split(",") if m.strip()]
    )

    st.markdown("---")
    st.markdown("<h3 style='text-align:center; color:white; background:#0d6efd; padding:10px; border-radius:10px;'>✅ Ready</h3>", unsafe_allow_html=True)

# Chat History
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("🩺 Describe your symptoms or ask a medical question..."):
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
                    st.markdown(f"**Instructions:** {output.instructions}")
                    st.markdown(f"**Refill:** {'Yes' if output.refill else 'No'}")

                elif isinstance(output, GeneralAdvice):
                    st.info("🩺 **Doctor's Recommendation**")
                    st.markdown(output.advice)
                    if "urgent" in output.follow_up.lower() or "emergency" in output.follow_up.lower():
                        st.warning(f"**⚠️ Important:** {output.follow_up}")
                    else:
                        st.markdown(f"**Next Steps:** {output.follow_up}")

                else:
                    st.markdown(output)

                st.session_state.messages.append({"role": "assistant", "content": str(output)})

            except InputGuardrailTripwireTriggered as e:
                reason = "This request appears to involve controlled substances or unsafe practices."
                st.error(f"""
                ⚠️ **Unable to Proceed**
                
                {reason}
                
                I cannot assist with requests for controlled medications or potentially harmful treatments.
                Please see a doctor in person for evaluation.
                """)
                st.session_state.messages.append({"role": "assistant", "content": "Input blocked by safety guardrail."})

            except Exception as e:
                st.error("😞 A system error occurred. Please try again later.")
                st.session_state.messages.append({"role": "assistant", "content": "Error occurred."})
