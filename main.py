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

# --- Realistic Prescription Model ---
class Prescription(BaseModel):
    """Professional real-life prescription format"""
    medications: List[str] = Field(description="Medication name with strength, e.g., 'Tab. Paracetamol 500mg'")
    sig: List[str] = Field(description="Full instructions: dosage, timing, relation to food, e.g., 'One tablet three times daily after food'")
    duration: str = Field(description="How many days, e.g., 'for 5 days'")
    quantity: List[str] = Field(description="Dispense amount, e.g., '#15 (Fifteen)'")
    refills: str = Field(default="No refills")
    additional_notes: Optional[str] = Field(default=None, description="Warnings, side effects, when to stop, etc.")

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
    APPROVE only safe, common medications.
    ALLOW: Paracetamol, Ibuprofen, Cetirizine, Amoxicillin, Omeprazole, Azithromycin, Syrups like cough syrup, etc.
    BLOCK: Opioids, Benzodiazepines, Steroids, Sleeping pills, Adderall, etc.
    Check allergies carefully.
    """,
    output_type=SafetyAnalysis,
    model=model
)

async def input_guardrail(ctx: PatientContext, agent, input_data: str):
    try:
        prompt = f"Patient: '{input_data}' | Allergies: {ctx.allergies} | Safe to prescribe common medicine? No controlled drugs."
        result = await Runner.run(safety_reviewer_agent, prompt)
        analysis = result.final_output_as(SafetyAnalysis)
        return GuardrailFunctionOutput(output_info=analysis, tripwire_triggered=not analysis.is_safe)
    except:
        return GuardrailFunctionOutput(output_info=SafetyAnalysis(is_safe=True, reasoning="Error"), tripwire_triggered=False)

async def output_guardrail(ctx: PatientContext, agent, input_data: str, output_data):
    try:
        output_str = str(output_data)
        prompt = f"Review prescription:\n{output_str}\nAllergies: {ctx.allergies}\nOnly common safe drugs allowed?"
        result = await Runner.run(safety_reviewer_agent, prompt)
        analysis = result.final_output_as(SafetyAnalysis)
        if not analysis.is_safe:
            safe = GeneralAdvice(
                advice="I cannot prescribe this medication as it is restricted or unsafe without physical examination.",
                follow_up="Please visit a nearby doctor immediately."
            )
            return GuardrailFunctionOutput(output_info=safe, tripwire_triggered=True, override_output=safe)
        return GuardrailFunctionOutput(output_info=analysis, tripwire_triggered=False)
    except:
        fallback = GeneralAdvice(advice="Safety error.", follow_up="See a doctor.")
        return GuardrailFunctionOutput(output_info=fallback, tripwire_triggered=True, override_output=fallback)

# --- Prescription Doctor Agent (Writes Full Detailed Instructions) ---
prescription_agent = Agent[PatientContext](
    name="Prescription Doctor",
    instructions="""
    You are a senior doctor writing a professional prescription in India.

    Write clearly with full instructions:
    - How many tablets/syrup (e.g., One tablet, 10 ml)
    - How many times a day (morning, afternoon, night)
    - Before or after food
    - Duration (for 3 days, 5 days, etc.)
    - Quantity in numbers and words

    Example:
    Tab. Paracetamol 650mg
    → One tablet three times daily after food for 3 days

    Syrup. Ascoril LS
    → 10 ml three times daily after food for 5 days

    Always check allergies.
    Use proper medical format.
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

# --- Main Virtual Doctor ---
doctor_agent = Agent[PatientContext](
    name="AI Doctor",
    instructions="""
    You are a kind, experienced virtual doctor.
    If patient needs medicine → hand off to Prescription Doctor.
    Otherwise → give advice via General Advisor.
    """,
    model=model,
    handoffs=[prescription_agent, advice_agent],
    input_guardrails=[InputGuardrail(guardrail_function=input_guardrail)],
    output_guardrails=[OutputGuardrail(guardrail_function=output_guardrail)]
)
