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
    medications: List[str] = Field(description="e.g., 'Tab. Cetirizine 10mg'")
    sig: List[str] = Field(description="Accurate instructions")
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
    instructions="""
    You are a strict medical safety and accuracy expert.
    Check dosage, concentration, allergies, interactions.
    Approve only safe, correct prescriptions.
    Block any inaccuracy or unsafe advice.
    """,
    output_type=SafetyAnalysis,
    model=model
)

# --- INPUT GUARDRAIL ---
async def input_guardrail(ctx: PatientContext, agent, input_data: str):
    try:
        prompt = f"Patient message: '{input_data}'. Allergies: {ctx.allergies}. Safe to proceed?"
        result = await Runner.run(safety_reviewer_agent, prompt)
        analysis = result.final_output_as(SafetyAnalysis)
        return GuardrailFunctionOutput(output_info=analysis, tripwire_triggered=not analysis.is_safe)
    except:
        return GuardrailFunctionOutput(output_info=SafetyAnalysis(is_safe=True, reasoning="Error"), tripwire_triggered=False)

# --- OUTPUT GUARDRAIL - FIXED SIGNATURE ---
async def output_guardrail(ctx: PatientContext, agent, input_data: str, output_data):
    try:
        prompt = f"""
        Review this response for safety and accuracy:
        {str(output_data)}
        
        Patient allergies: {ctx.allergies}
        Current meds: {ctx.current_medications}
        
        Is dosage, concentration, and advice 100% correct and safe?
        """
        result = await Runner.run(safety_reviewer_agent, prompt)
        analysis = result.final_output_as(SafetyAnalysis)
        if not analysis.is_safe:
            safe = GeneralAdvice(
                advice="I cannot provide this prescription as it may be inaccurate or unsafe without in-person evaluation.",
                follow_up="Please consult a licensed doctor."
            )
            return GuardrailFunctionOutput(output_info=safe, tripwire_triggered=True, override_output=safe)
        return GuardrailFunctionOutput(output_info=analysis, tripwire_triggered=False)
    except:
        fallback = GeneralAdvice(advice="Safety review error.", follow_up="See a doctor.")
        return GuardrailFunctionOutput(output_info=fallback, tripwire_triggered=True, override_output=fallback)

# --- Prescription Agent - Accurate Dosages ---
prescription_agent = Agent[PatientContext](
    name="Prescription Doctor",
    instructions="""
    You are an experienced Indian family doctor.
    

    
    Think step-by-step:
    1. Check age, symptoms, allergies
    2. Choose correct medicine and form (prefer tablet for adults)
    3. Calculate exact dose accurately
    4. Write clear instructions with timing and food relation
    
    Be natural, vary responses, but always accurate.
    """,
    model=model,
    output_type=Prescription
)

# --- General Advice Agent ---
advice_agent = Agent[PatientContext](
    name="General Advisor",
    instructions="""
    Give accurate, evidence-based advice.
    Be caring and clear about red flags.
    Never prescribe.
    """,
    model=model,
    output_type=GeneralAdvice
)

# --- Main Doctor ---
doctor_agent = Agent[PatientContext](
    name="AI Doctor",
    instructions="""
    You are a caring virtual doctor.
    If medicine is needed → hand off to Prescription Doctor
    Else → General Advisor
    Always prioritize accuracy and safety.
    """,
    model=model,
    handoffs=[prescription_agent, advice_agent],
    input_guardrails=[InputGuardrail(guardrail_function=input_guardrail)],
    output_guardrails=[OutputGuardrail(guardrail_function=output_guardrail)]
)
