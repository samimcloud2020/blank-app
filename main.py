# main.py
import asyncio
from pydantic import BaseModel, Field
from agents import Agent, Runner, InputGuardrail, OutputGuardrail, GuardrailFunctionOutput, InputGuardrailTripwireTriggered
from typing import List, Optional
from dataclasses import dataclass
from dotenv import load_dotenv
import os
from datetime import date

load_dotenv()
model = os.getenv('LLM_MODEL_NAME', 'gpt-4o-mini')

# --- Realistic Prescription Model ---
class Prescription(BaseModel):
    """Real-life style prescription"""
    rx_items: List[str] = Field(description="List of medications in Rx format (e.g., 'Tab. Ibuprofen 400mg')")
    sig: List[str] = Field(description="Directions for each drug (e.g., '1 tab three times daily after food')")
    quantity: List[str] = Field(description="Dispense quantity (e.g., '#30 (thirty)')")
    refills: str = Field(default="No refills", description="Refills allowed")
    notes: Optional[str] = Field(default=None, description="Additional doctor notes or warnings")

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
    name="Medical Safety Reviewer",
    instructions="""
    APPROVE only safe, common medications:
    - Ibuprofen, Acetaminophen, Amoxicillin, Cetirizine, Omeprazole, Azithromycin, etc.
    
    BLOCK:
    - Opioids, Benzodiazepines, Stimulants, Sleeping pills, Weight loss drugs
    - Drug-seeking or demanding specific controlled meds
    - Ignoring allergies
    """,
    output_type=SafetyAnalysis,
    model=model
)

async def input_guardrail(ctx: PatientContext, agent, input_data: str):
    try:
        prompt = f"Patient asks: '{input_data}'. Allergies: {ctx.allergies}. Is this safe to proceed (no controlled drugs)? Yes/No and reason."
        result = await Runner.run(safety_reviewer_agent, prompt)
        analysis = result.final_output_as(SafetyAnalysis)
        return GuardrailFunctionOutput(output_info=analysis, tripwire_triggered=not analysis.is_safe)
    except:
        return GuardrailFunctionOutput(output_info=SafetyAnalysis(is_safe=True, reasoning="Error"), tripwire_triggered=False)

async def output_guardrail(ctx: PatientContext, agent, input_data: str, output_data):
    try:
        output_str = str(output_data)
        prompt = f"Review response:\n{output_str}\nPatient allergies: {ctx.allergies}\nSafe? Only common meds allowed."
        result = await Runner.run(safety_reviewer_agent, prompt)
        analysis = result.final_output_as(SafetyAnalysis)
        if not analysis.is_safe:
            safe = GeneralAdvice(
                advice="I cannot prescribe that medication as it is restricted or unsafe without in-person evaluation.",
                follow_up="Please consult a doctor in person."
            )
            return GuardrailFunctionOutput(output_info=safe, tripwire_triggered=True, override_output=safe)
        return GuardrailFunctionOutput(output_info=analysis, tripwire_triggered=False)
    except:
        fallback = GeneralAdvice(advice="Safety check failed.", follow_up="See a doctor.")
        return GuardrailFunctionOutput(output_info=fallback, tripwire_triggered=True, override_output=fallback)

# --- Prescription Agent (Writes in Real Doctor Format) ---
prescription_agent = Agent[PatientContext](
    name="Prescription Doctor",
    instructions="""
    You are a professional doctor writing a real prescription.
    
    Format exactly like real life:
    
    Rx
    1. Tab. [Medication] [Strength]
       Sig: [dosage instructions in full sentences]
       Disp: #[number] ([written in words])
    
    2. Next drug...
    
    Refills: No refills (or number)
    
    Use proper medical abbreviations and formal tone.
    Always check allergies before prescribing.
    """,
    model=model,
    output_type=Prescription
)

advice_agent = Agent[PatientContext](
    name="General Advisor",
    instructions="Give caring, evidence-based advice with clear red flags.",
    model=model,
    output_type=GeneralAdvice
)

# --- Main Doctor ---
doctor_agent = Agent[PatientContext](
    name="Dr. AI - Virtual Physician",
    instructions="""
    You are a compassionate, board-certified virtual doctor.
    If patient needs medication → hand off to Prescription Doctor.
    Otherwise → General Advisor.
    """,
    model=model,
    handoffs=[prescription_agent, advice_agent],
    input_guardrails=[InputGuardrail(guardrail_function=input_guardrail)],
    output_guardrails=[OutputGuardrail(guardrail_function=output_guardrail)]
)
