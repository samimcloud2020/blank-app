# main.py
import asyncio
from pydantic import BaseModel, Field
from agents import Agent, Runner, InputGuardrail, OutputGuardrail, GuardrailFunctionOutput, InputGuardrailTripwireTriggered
from typing import List, Optional
from dataclasses import dataclass
from dotenv import load_dotenv
import os

load_dotenv()
model = os.getenv('LLM_MODEL_NAME', 'gpt-4o-mini')

# --- Models ---
class Prescription(BaseModel):
    medications: List[str] = Field(description="Medication with correct strength, e.g., 'Tab. Cetirizine 10mg' or 'Syrup Cetirizine 5mg/5ml'")
    sig: List[str] = Field(description="Accurate instructions, e.g., 'One tablet once daily in the evening' or '10 ml once daily in the evening for 10mg dose'")
    duration: str = Field(description="Correct duration, e.g., 'for 7 days'")
    quantity: List[str] = Field(description="Accurate dispense, e.g., '#10 (Ten tablets)' or '#100 ml (One hundred ml)'")
    refills: str = Field(default="No refills")
    additional_notes: Optional[str] = Field(default=None, description="Important accurate warnings")

class GeneralAdvice(BaseModel):
    advice: str
    follow_up: str

class SafetyAnalysis(BaseModel):
    is_safe: bool
    reasoning: str

# --- Patient Context ---
@dataclass
class PatientContext:
    patient_id: str
    age: int
    gender: str
    current_symptoms: List[str]
    medical_history: List[str]
    allergies: List[str]
    current_medications: List[str]

# --- Safety Reviewer - Strict Accuracy Check ---
safety_reviewer_agent = Agent(
    name="Safety Reviewer",
    instructions="""
    You are a strict medical accuracy and safety expert.
    
    Check for:
    - Correct medication concentrations (e.g., Cetirizine syrup is 5mg/5ml, dose 10ml for 10mg)
    - Accurate dosages based on age (10mg for adults, 5mg for children 6-12)
    - No wrong calculations or unsafe advice
    - Prefer tablets for adults (Tab. Cetirizine 10mg)
    - Block if any error in dosage, concentration, or safety
    
    Only approve if 100% accurate and safe.
    """,
    output_type=SafetyAnalysis,
    model=model
)

async def input_guardrail(ctx, agent, input_data):
    try:
        prompt = f"Patient says: '{input_data}'. Allergies: {ctx.allergies}. Is this safe and accurate for common meds?"
        result = await Runner.run(safety_reviewer_agent, prompt)
        analysis = result.final_output_as(SafetyAnalysis)
        return GuardrailFunctionOutput(output_info=analysis, tripwire_triggered=not analysis.is_safe)
    except:
        return GuardrailFunctionOutput(output_info=SafetyAnalysis(is_safe=True, reasoning="Error"), tripwire_triggered=False)

async def output_guardrail(ctx, agent, input_data, output_data):
    try:
        prompt = f"Review response: {str(output_data)}. Allergies: {ctx.allergies}. Is dosage/concentration accurate and safe?"
        result = await Runner.run(safety_reviewer_agent, prompt)
        analysis = result.final_output_as(SafetyAnalysis)
        if not analysis.is_safe:
            safe = GeneralAdvice(advice="Cannot provide — potential inaccuracy or unsafe. See doctor in person.", follow_up="Consult a physician.")
            return GuardrailFunctionOutput(output_info=safe, tripwire_triggered=True, override_output=safe)
        return GuardrailFunctionOutput(output_info=analysis, tripwire_triggered=False)
    except:
        fallback = GeneralAdvice(advice="Safety error.", follow_up="See doctor.")
        return GuardrailFunctionOutput(output_info=fallback, tripwire_triggered=True, override_output=fallback)

# --- Prescription Agent - Accurate & Varied ---
prescription_agent = Agent[PatientContext](
    name="Prescription Doctor",
    instructions="""
    You are a careful, accurate family doctor in India.
    
    Step-by-step thinking:
    1. Analyze symptoms, age, gender, allergies.
    2. Choose correct medication with accurate strength (e.g., Cetirizine syrup is 5mg/5ml, tablet is 10mg).
    3. Calculate exact dose: For adults, Cetirizine = 10mg daily (tablet 10mg or syrup 10ml of 5mg/5ml).
    4. Vary naturally based on patient (lower dose for elderly).
    5. Instructions must be precise: 'One tablet once daily in the evening' or '10 ml once daily in the evening before bed'.
    6. Double-check for accuracy — no errors in concentration or volume.
    7. Be empathetic, add notes like 'Avoid driving if drowsy'.
    
    Always be correct — never write wrong dosage or concentration.
    """,
    model=model,
    output_type=Prescription
)

# --- General Advisor - Accurate Advice ---
advice_agent = Agent[PatientContext](
    name="General Advisor",
    instructions="""
    You are a caring doctor giving accurate, evidence-based advice.
    
    - Be precise with facts (e.g., 'Cetirizine dose is 10mg daily for adults').
    - Suggest home care, diet, rest.
    - Clearly list red flags for urgent care.
    - Never prescribe — only advise.
    - Double-check for accuracy in every response.
    """,
    model=model,
    output_type=GeneralAdvice
)

# --- Main Doctor - Ensures Accuracy ---
doctor_agent = Agent[PatientContext](
    name="AI Doctor",
    instructions="""
    You are a responsible virtual doctor in Rourkela.
    
    - Understand the patient's exact complaint.
    - If medicine needed → hand off to Prescription Doctor (ensure accurate).
    - Else → General Advisor (ensure accurate).
    - Be empathetic, natural, and double-check for correctness.
    """,
    model=model,
    handoffs=[prescription_agent, advice_agent],
    input_guardrails=[InputGuardrail(guardrail_function=input_guardrail)],
    output_guardrails=[OutputGuardrail(guardrail_function=output_guardrail)]
)
