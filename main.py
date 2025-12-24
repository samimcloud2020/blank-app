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
    medications: List[str] = Field(description="Medicine with strength, e.g., 'Tab. Cetirizine 10mg'")
    sig: List[str] = Field(description="Real doctor style: 'One tablet once daily at night after food'")
    duration: str = Field(description="e.g., 'for 5 days'")
    quantity: List[str] = Field(description="e.g., '#10 (Ten tablets)'")
    refills: str = "No refills"
    additional_notes: Optional[str] = None

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

# --- Safety Reviewer ---
safety_reviewer_agent = Agent(
    name="Safety Reviewer",
    instructions="Strictly check for correct dosage, concentration, allergies, interactions. Block unsafe or wrong prescriptions.",
    output_type=SafetyAnalysis,
    model=model
)

async def input_guardrail(ctx: PatientContext, agent, input_data: str):
    try:
        prompt = f"Patient: {ctx.patient_id}, Age: {ctx.age}, Symptoms: {ctx.current_symptoms}, Allergies: {ctx.allergies}. Message: '{input_data}'. Safe?"
        result = await Runner.run(safety_reviewer_agent, prompt)
        analysis = result.final_output_as(SafetyAnalysis)
        return GuardrailFunctionOutput(output_info=analysis, tripwire_triggered=not analysis.is_safe)
    except:
        return GuardrailFunctionOutput(output_info=SafetyAnalysis(is_safe=True, reasoning="Error"), tripwire_triggered=False)

async def output_guardrail(ctx: PatientContext, agent, input_data: str, output_data):
    try:
        prompt = f"Review: {str(output_data)}\nPatient: {ctx.patient_id}, Allergies: {ctx.allergies}, Current meds: {ctx.current_medications}. Is it safe and accurate?"
        result = await Runner.run(safety_reviewer_agent, prompt)
        analysis = result.final_output_as(SafetyAnalysis)
        if not analysis.is_safe:
            safe = GeneralAdvice(advice="Cannot prescribe — unsafe or inaccurate.", follow_up="See doctor in person.")
            return GuardrailFunctionOutput(output_info=safe, tripwire_triggered=True, override_output=safe)
        return GuardrailFunctionOutput(output_info=analysis, tripwire_triggered=False)
    except:
        fallback = GeneralAdvice(advice="Safety error.", follow_up="See doctor.")
        return GuardrailFunctionOutput(output_info=fallback, tripwire_triggered=True, override_output=fallback)

# --- Real-World Prescription Doctor ---
prescription_agent = Agent[PatientContext](
    name="Prescription Doctor",
    instructions="""
    You are a senior family physician in Rourkela, Odisha writing real prescriptions.

    Patient:
    Name: {ctx.patient_id}
    Age: {ctx.age}
    Gender: {ctx.gender}
    Symptoms: {ctx.current_symptoms}
    Allergies: {ctx.allergies}
    Current medicines: {ctx.current_medications}

    You MUST prescribe medicine for the symptoms.
    Write exactly like real doctors but its a example of style doctor prescribe:
    - Use Tab., Cap., Syrup., etc.
    - Correct strength (e.g., Tab. Paracetamol 650mg, Syrup Cetirizine 5mg/5ml)
    - Real instructions: "One tablet three times daily after food", "10 ml once daily at night"
    - Duration: "for 3 days", "for 5 days"
    - Quantity: "#15 (Fifteen)", "#100 ml (One hundred ml)"
    - Add notes: "Take with water", "Avoid alcohol", "If no improvement in 3 days, consult doctor"

    Be natural, caring, and professional.
    Vary wording but always accurate.
    """,
    model=model,
    output_type=Prescription
)

# --- Main Doctor - Always Prescribes ---
doctor_agent = Agent[PatientContext](
    name="AI Doctor",
    instructions="""
    You are a caring doctor.
    The patient has entered symptoms and profile.
    Always hand off to Prescription Doctor to write a real Rx prescription.
    Do not give only advice — prescribe medicine.
    """,
    model=model,
    handoffs=[prescription_agent],
    input_guardrails=[InputGuardrail(guardrail_function=input_guardrail)],
    output_guardrails=[OutputGuardrail(guardrail_function=output_guardrail)]
)
