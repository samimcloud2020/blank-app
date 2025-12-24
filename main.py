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
    medications: List[str] = Field(description="e.g., 'Tab. Paracetamol 650mg'")
    sig: List[str] = Field(description="Full instructions, e.g., 'One tablet three times daily after food'")
    duration: str = Field(description="e.g., 'for 5 days'")
    quantity: List[str] = Field(description="e.g., '#15 (Fifteen)'")
    refills: str = Field(default="No refills")
    additional_notes: Optional[str] = Field(default=None)

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
    instructions="""
    Approve only safe common medications: Paracetamol, Ibuprofen, Cetirizine, Amoxicillin, Omeprazole, cough syrups, etc.
    Block opioids, benzodiazepines, stimulants, steroids, weight loss drugs.
    Check allergies and interactions.
    """,
    output_type=SafetyAnalysis,
    model=model
)

async def input_guardrail(ctx, agent, input_data):
    try:
        prompt = f"Patient says: '{input_data}'. Allergies: {ctx.allergies}. Safe to proceed with common meds?"
        result = await Runner.run(safety_reviewer_agent, prompt)
        analysis = result.final_output_as(SafetyAnalysis)
        return GuardrailFunctionOutput(output_info=analysis, tripwire_triggered=not analysis.is_safe)
    except:
        return GuardrailFunctionOutput(output_info=SafetyAnalysis(is_safe=True, reasoning="Error"), tripwire_triggered=False)

async def output_guardrail(ctx, agent, input_data, output_data):
    try:
        prompt = f"Review response: {str(output_data)}. Allergies: {ctx.allergies}. Only safe meds allowed?"
        result = await Runner.run(safety_reviewer_agent, prompt)
        analysis = result.final_output_as(SafetyAnalysis)
        if not analysis.is_safe:
            safe = GeneralAdvice(advice="Cannot prescribe — unsafe or restricted.", follow_up="See doctor in person.")
            return GuardrailFunctionOutput(output_info=safe, tripwire_triggered=True, override_output=safe)
        return GuardrailFunctionOutput(output_info=analysis, tripwire_triggered=False)
    except:
        fallback = GeneralAdvice(advice="Safety error.", follow_up="Consult doctor.")
        return GuardrailFunctionOutput(output_info=fallback, tripwire_triggered=True, override_output=fallback)

# --- Prescription Doctor - Varied & Natural ---
prescription_agent = Agent[PatientContext](
    name="Prescription Doctor",
    instructions="""
    You are an experienced Indian family doctor.
    Analyze symptoms, age, allergies carefully.
    Prescribe only safe common medicines.
    Vary dosage, timing, duration naturally.
    Use realistic format with food relation and specific times.
    Be empathetic and add useful notes.
    """,
    model=model,
    output_type=Prescription
)

advice_agent = Agent[PatientContext](
    name="General Advisor",
    instructions="Give caring, detailed advice with home care and red flags.",
    model=model,
    output_type=GeneralAdvice
)

# --- Main Doctor ---
doctor_agent = Agent[PatientContext](
    name="AI Doctor",
    instructions="""
    You are a kind virtual doctor.
    If patient needs medicine → hand off to Prescription Doctor
    Else → General Advisor
    Be natural and caring.
    """,
    model=model,
    handoffs=[prescription_agent, advice_agent],
    input_guardrails=[InputGuardrail(guardrail_function=input_guardrail)],
    output_guardrails=[OutputGuardrail(guardrail_function=output_guardrail)]
)
