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
    medications: List[str]
    sig: List[str]
    duration: str
    quantity: List[str]
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
    instructions="Strictly check dosage, concentration, allergies. Block unsafe or wrong prescriptions.",
    output_type=SafetyAnalysis,
    model=model
)

async def input_guardrail(ctx: PatientContext, agent, input_data: str):
    try:
        prompt = f"Patient: {ctx.patient_id}, Age: {ctx.age}, Symptoms: {ctx.current_symptoms}, Allergies: {ctx.allergies}. Message: '{input_data}'. Safe to proceed?"
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
            safe = GeneralAdvice(advice="Cannot prescribe — unsafe or inaccurate.", follow_up="See doctor.")
            return GuardrailFunctionOutput(output_info=safe, tripwire_triggered=True, override_output=safe)
        return GuardrailFunctionOutput(output_info=analysis, tripwire_triggered=False)
    except:
        fallback = GeneralAdvice(advice="Safety error.", follow_up="See doctor.")
        return GuardrailFunctionOutput(output_info=fallback, tripwire_triggered=True, override_output=fallback)

# --- Prescription Doctor - Personalized & Varied ---
prescription_agent = Agent[PatientContext](
    name="Prescription Doctor",
    instructions="""
    You are a caring family doctor in Rourkela.

    Patient details:
    Name: {ctx.patient_id}
    Age: {ctx.age}
    Gender: {ctx.gender}
    Symptoms: {ctx.current_symptoms}
    Allergies: {ctx.allergies}
    Current medicines: {ctx.current_medications}

    Prescribe accurate medicine for ALL symptoms.
    Use correct dosage based on age.
    Prefer tablets for adults.
    Write full instructions: timing, food, duration.
    Add caring advice.
    Vary wording naturally — never repeat same prescription.
    """,
    model=model,
    output_type=Prescription
)

advice_agent = Agent[PatientContext](
    name="General Advisor",
    instructions="""
    Give caring, accurate advice based on patient symptoms, age, and profile.
    Include home care and red flags.
    Never prescribe.
    """,
    model=model,
    output_type=GeneralAdvice
)

doctor_agent = Agent[PatientContext](
    name="AI Doctor",
    instructions="""
    You are a compassionate doctor.
    Use full patient profile for personalized response.
    If medicine needed → hand off to Prescription Doctor
    Else → General Advisor
    Be natural and caring.
    """,
    model=model,
    handoffs=[prescription_agent, advice_agent],
    input_guardrails=[InputGuardrail(guardrail_function=input_guardrail)],
    output_guardrails=[OutputGuardrail(guardrail_function=output_guardrail)]
)
