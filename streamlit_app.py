# streamlit_app.py
import asyncio
import streamlit as st
from datetime import date
from main import PatientContext, Runner, doctor_agent, InputGuardrailTripwireTriggered, Prescription, GeneralAdvice

st.set_page_config(page_title="🩺 AI Doctor - Rourkela", page_icon="🩺", layout="centered")

# === PRODUCTION-READY STUNNING DESIGN ===
st.markdown("""
<style>
    .big-title {
        font-size: 72px !important; 
        font-weight: 900; 
        background: linear-gradient(90deg, #ff1744, #00bcd4, #4caf50); 
        -webkit-background-clip: text; 
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin: 0;
        letter-spacing: 3px;
    }
    .header-box {
        background: linear-gradient(135deg, #1e3a8a, #3b82f6, #60a5fa); 
        padding: 30px; 
        border-radius: 25px; 
        color: white; 
        text-align: center;
        box-shadow: 0 12px 40px rgba(59,130,246,0.4);
        margin-bottom: 30px;
        border: 3px solid #93c5fd;
    }
    .rx-header {
        font-size: 90px !important; 
        font-weight: 900; 
        color: #dc2626; 
        text-align: center; 
        margin: 40px 0 30px 0;
        text-shadow: 5px 5px 15px rgba(220,38,38,0.4);
        letter-spacing: 8px;
    }
    .rx-box {
        background: linear-gradient(to bottom, #f0fdf4, #dcfce7); 
        border: 6px solid #22c55e; 
        border-radius: 30px; 
        padding: 45px; 
        box-shadow: 0 20px 50px rgba(34,197,94,0.25);
        margin: 30px 0;
        min-height: 500px;
    }
    .med-item {
        background: linear-gradient(to right, #f0fdf4, #bbf7d0); 
        padding: 25px; 
        border-radius: 20px; 
        margin: 20px 0; 
        border-left: 10px solid #16a34a;
        box-shadow: 0 8px 25px rgba(34,197,94,0.2);
        transition: transform 0.3s;
    }
    .patient-card {
        background: linear-gradient(to bottom, #dbeafe, #bfdbfe, #93c5fd); 
        border-left: 12px solid #2563eb; 
        padding: 30px; 
        border-radius: 20px;
        box-shadow: 0 12px 35px rgba(37,99,235,0.2);
        font-size: 17px;
        min-height: 400px;
    }
    .sidebar .sidebar-content {
        background: linear-gradient(180deg, #7c3aed, #a855f7, #c084fc); 
        color: white;
        border-radius: 20px;
    }
    .stTextInput > div > div > input, .stSelectbox > div > div > select {
        background-color: rgba(255,255,255,0.9) !important;
        color: #1e293b !important;
        font-weight: bold;
    }
    .stButton>button {
        background: linear-gradient(90deg, #ec4899, #f43f5e); 
        color: white; 
        font-weight: bold; 
        border-radius: 15px; 
        height: 60px; 
        font-size: 20px;
        border: none;
        box-shadow: 0 8px 20px rgba(236,72,153,0.4);
    }
    h1, h2, h3, h4 {color: #1e293b;}
</style>
""", unsafe_allow_html=True)

# Main Header
st.markdown("<div class='big-title'>🩺 AI DOCTOR</div>", unsafe_allow_html=True)
st.markdown("""
<div class='header-box'>
    <h1 style='margin:0; font-size:42px; color:white;'>VIRTUAL HEALTH CLINIC</h1>
    <h2 style='margin:10px 0 5px 0; color:#fbbf24;'>Rourkela, Odisha, India</h2>
    <p style='font-size:20px; margin:0; color:#fecaca;'>Your Trusted AI Physician • Available 24/7 • Safe & Caring</p>
</div>
""", unsafe_allow_html=True)

# === LEFT SIDEBAR - SUPER COLORFUL & ATTRACTIVE ===
with st.sidebar:
    st.markdown("""
    <div style='text-align:center; padding:25px; background:linear-gradient(135deg,#a855f7,#e879f9); border-radius:20px; box-shadow:0 10px 30px rgba(168,85,247,0.4);'>
        <h2 style='color:white; margin:0; font-size:32px;'>👤 Patient Profile</h2>
        <p style='color:#f3e8ff; font-size:18px; margin:10px 0 0 0;'>Enter your details below</p>
    </div>
    """, unsafe_allow_html=True)

    name = st.text_input("**Full Name**", value="S K Patel", placeholder="Your full name", key="name")
    age = st.number_input("**Age**", min_value=1, max_value=120, value=46, key="age")
    gender = st.selectbox("**Gender**", ["Male", "Female", "Other"], key="gender")

    st.markdown("#### 😷 Current Symptoms")
    symptoms = st.multiselect("Select all that apply", [
        "Fever", "Headache", "Cold & Cough", "Sore Throat", "Body Pain", "Acidity",
        "Allergy", "Stomach Upset", "Loose Motion", "Vomiting", "Weakness", "Breathing Difficulty"
    ], key="symptoms")
    other = st.text_input("Any other symptoms?", key="other_symptom")
    if other:
        symptoms.append(other)

    allergies = st.text_input("**Known Allergies**", placeholder="e.g., dust, penicillin", value="dust", key="allergies")
    current_meds = st.text_input("**Current Medicines**", placeholder="e.g., paracetamol", value="paracetamol", key="meds")

    # Build context
    all_symptoms = symptoms + ([other] if other else [])
    patient_context = PatientContext(
        patient_id=name or "Patient",
        age=age,
        gender=gender,
        current_symptoms=all_symptoms,
        medical_history=[],
        allergies=[a.strip() for a in allergies.split(",") if a.strip()],
        current_medications=[m.strip() for m in current_meds.split(",") if m.strip()]
    )

    st.markdown("---")
    st.markdown(f"""
    <div style='text-align:center; background:linear-gradient(90deg,#ec4899,#f43f5e); padding:20px; border-radius:20px; color:white; box-shadow:0 10px 30px rgba(236,72,153,0.5);'>
        <h2 style='margin:0;'>✅ Ready for Consultation</h2>
        <h3 style='margin:10px 0 0 0;'>{name or "Patient"} • {age} yrs</h3>
    </div>
    """, unsafe_allow_html=True)

# === MAIN AREA - ALWAYS SHOW PATIENT CARD & PRESCRIPTION BOX ===
st.markdown("<h2 style='text-align:center; color:#1e293b;'>Your Personalized Consultation</h2>", unsafe_allow_html=True)

col1, col2 = st.columns([1.4, 2.6])

today = date.today().strftime("%d %B %Y")

with col1:
    st.markdown(f"""
    <div class='patient-card'>
        <h2 style='color:#2563eb; text-align:center; margin-top:0;'>📋 Patient Card</h2>
        <div style='text-align:center; padding:15px; background:#e0f2fe; border-radius:15px; margin:15px 0;'>
            <h3 style='margin:5px; color:#1e40af;'>{patient_context.patient_id}</h3>
            <p style='margin:5px; font-size:18px;'><strong>Age:</strong> {patient_context.age} • <strong>Gender:</strong> {patient_context.gender}</p>
            <p style='margin:5px; color:#dc2626;'><strong>Date:</strong> {today}</p>
        </div>
        <strong style='color:#dc2626;'>Chief Complaints:</strong><br>
        <i style='color:#374151; font-size:16px;'>
            {', '.join(patient_context.current_symptoms) or 'No symptoms entered yet'}
        </i>
        <hr style='border:1px dashed #93c5fd; margin:20px 0;'>
        <p><strong>Allergies:</strong> {allergies or 'None declared'}</p>
        <p><strong>Current Meds:</strong> {current_meds or 'None'}</p>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("<div class='rx-box'>", unsafe_allow_html=True)

    # Always show clinic header
    st.markdown("""
    <div style='text-align:center; margin-bottom:40px;'>
        <h1 style='color:#dc2626; font-weight:900; margin:0; font-size:52px; text-shadow: 3px 3px 10px rgba(220,38,38,0.3);'>AI DOCTOR</h1>
        <h2 style='color:#16a34a; margin:10px 0 5px 0; font-weight:bold;'>Virtual Health Clinic</h2>
        <h3 style='color:#2563eb; margin:0;'><strong>Rourkela, Odisha, India</strong></h3>
    </div>
    """, unsafe_allow_html=True)

    # Big Rx
    st.markdown("<div class='rx-header'>Rx</div>", unsafe_allow_html=True)

    # Placeholder if no prescription yet
    if "last_prescription" not in st.session_state:
        st.markdown("""
        <div style='text-align:center; padding:60px; background:#f3f4f6; border-radius:20px; border:3px dashed #94a3b8;'>
            <h3 style='color:#64748b; margin:0;'>Your prescription will appear here</h3>
            <p style='color:#94a3b8; font-size:18px; margin:20px 0 0 0;'>Describe your symptoms in the chat below 👇</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("</div>", unsafe_allow_html=True)

# Chat History
if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.last_prescription = None

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"], unsafe_allow_html=True)

# User Input
if prompt := st.chat_input("🩺 Describe your symptoms or ask for treatment..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("🩺 AI Doctor is preparing your prescription..."):
            try:
                result = asyncio.run(Runner.run(doctor_agent, prompt, context=patient_context))
                output = result.final_output

                if isinstance(output, Prescription):
                    # Update prescription display
                    st.rerun()  # To refresh the static prescription box

                    st.success("✅ **Prescription Issued Successfully!**")

                    # Display in chat
                    prescription_html = "<div class='rx-box'>"
                    prescription_html += """
                    <div style='text-align:center; margin-bottom:40px;'>
                        <h1 style='color:#dc2626; font-weight:900;'>AI DOCTOR</h1>
                        <h3 style='color:#16a34a;'>Virtual Health Clinic • Rourkela, Odisha</h3>
                    </div>
                    <div class='rx-header'>Rx</div>
                    """
                    for i in range(len(output.medications)):
                        prescription_html += f"""
                        <div class='med-item'>
                            <h3 style='color:#166534;'>{i+1}. {output.medications[i]}</h3>
                            <p><strong style='color:#2563eb;'>Take →</strong> <strong>{output.sig[i]}</strong></p>
                            <p><strong style='color:#dc2626;'>Dispense →</strong> {output.quantity[i]}</p>
                        </div>
                        """
                    prescription_html += f"<h3 style='text-align:center; color:#dc2626; margin-top:30px;'>Duration: {output.duration}</h3>"
                    prescription_html += f"<h3 style='text-align:center; color:#b91c1c;'>Refills: {output.refills}</h3>"
                    if output.additional_notes:
                        prescription_html += f"<div style='background:#fff7ed; padding:20px; border-radius:15px; border-left:8px solid #f97316; margin-top:25px;'><strong style='color:#c2410c;'>⚠️ Note:</strong> {output.additional_notes}</div>"
                    prescription_html += "</div>"

                    st.markdown(prescription_html, unsafe_allow_html=True)
                    st.session_state.last_prescription = output

                    st.warning("💊 Take this prescription to any pharmacy • Follow instructions carefully")

                elif isinstance(output, GeneralAdvice):
                    st.info("🩺 **Doctor's Advice**")
                    st.markdown(f"<div style='font-size:18px; line-height:1.8;'>{output.advice}</div>", unsafe_allow_html=True)
                    st.markdown(f"**Follow-up:** {output.follow_up}")

                st.session_state.messages.append({"role": "assistant", "content": str(output)})

            except InputGuardrailTripwireTriggered:
                st.error("⚠️ **Cannot prescribe this medication**\n\nRestricted or requires in-person examination.")
            except Exception as e:
                st.error("System error. Please try again.")

# Update static prescription box on rerun
if st.session_state.get("last_prescription"):
    with col2:
        st.markdown("<div class='rx-box'>", unsafe_allow_html=True)
        st.markdown("""
        <div style='text-align:center; margin-bottom:40px;'>
            <h1 style='color:#dc2626; font-weight:900;'>AI DOCTOR</h1>
            <h3 style='color:#16a34a;'>Virtual Health Clinic • Rourkela, Odisha</h3>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("<div class='rx-header'>Rx</div>", unsafe_allow_html=True)
        
        output = st.session_state.last_prescription
        for i in range(len(output.medications)):
            st.markdown(f"""
            <div class='med-item'>
                <h3 style='color:#166534;'>{i+1}. {output.medications[i]}</h3>
                <p><strong style='color:#2563eb;'>Take →</strong> <strong>{output.sig[i]}</strong></p>
                <p><strong style='color:#dc2626;'>Dispense →</strong> {output.quantity[i]}</p>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown(f"<h3 style='text-align:center; color:#dc2626; margin-top:30px;'>Duration: {output.duration}</h3>", unsafe_allow_html=True)
        st.markdown(f"<h3 style='text-align:center; color:#b91c1c;'>Refills: {output.refills}</h3>", unsafe_allow_html=True)
        if output.additional_notes:
            st.info(f"**Important:** {output.additional_notes}")
        
        st.markdown("</div>", unsafe_allow_html=True)
