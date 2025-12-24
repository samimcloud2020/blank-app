# main.py
import asyncio
from pydantic import BaseModel, Field
from agents import Agent, Runner, InputGuardrail, OutputGuardrail, GuardrailFunctionOutput, InputGuardrailTripwireTriggered, WebSearchTool  # ← IMPORT WebSearchTool
from typing import List, Optional
from dataclasses import dataclass
from dotenv import load_dotenv
import os

load_dotenv()
model = os.getenv('LLM_MODEL_NAME', 'gpt-4o-mini')  # Model that supports tool calling

# --- Models ---
class Prescription(BaseModel):
    medications: List[str] = Field(description="e.g., 'Tab. Paracetamol 650mg'")
    sig: List[str] = Field(description="Real instructions: 'One tablet three times daily after food'")
    duration: str = Field(description="e.g., 'for 5 days'")
    quantity: List[str] = Field(description="e.g., '#15 (Fifteen tablets)'")
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
    You are a strict medical safety expert.
    Review prescription for:
    - Correct dosage and concentration
    - No allergy conflicts
    - No dangerous interactions with current medications
    - Age-appropriate dosing
    Block if any inaccuracy or risk.
    """,
    output_type=SafetyAnalysis,
    model=model
)

async def input_guardrail(ctx: PatientContext, agent, input_data: str):
    try:
        prompt = f"Patient: {ctx.patient_id}, Age: {ctx.age}, Symptoms: {ctx.current_symptoms}, Allergies: {ctx.allergies}, Current meds: {ctx.current_medications}. User message: '{input_data}'. Is it safe to prescribe common medicine?"
        result = await Runner.run(safety_reviewer_agent, prompt)
        analysis = result.final_output_as(SafetyAnalysis)
        return GuardrailFunctionOutput(output_info=analysis, tripwire_triggered=not analysis.is_safe)
    except:
        return GuardrailFunctionOutput(output_info=SafetyAnalysis(is_safe=True, reasoning="Guardrail error"), tripwire_triggered=False)

async def output_guardrail(ctx: PatientContext, agent, input_data: str, output_data):
    try:
        prompt = f"""
        Review this prescription:
        {str(output_data)}
        
        Patient profile:
        Name: {ctx.patient_id}
        Age: {ctx.age}
        Allergies: {ctx.allergies}
        Current medications: {ctx.current_medications}
        
        Is the dosage, concentration, and medication choice 100% safe and accurate?
        """
        result = await Runner.run(safety_reviewer_agent, prompt)
        analysis = result.final_output_as(SafetyAnalysis)
        if not analysis.is_safe:
            safe = GeneralAdvice(
                advice="I cannot provide this prescription as it may be unsafe or inaccurate. Please consult a doctor in person.",
                follow_up="Visit a nearby clinic for proper evaluation."
            )
            return GuardrailFunctionOutput(output_info=safe, tripwire_triggered=True, override_output=safe)
        return GuardrailFunctionOutput(output_info=analysis, tripwire_triggered=False)
    except:
        fallback = GeneralAdvice(advice="Safety system error.", follow_up="Consult a doctor.")
        return GuardrailFunctionOutput(output_info=fallback, tripwire_triggered=True, override_output=fallback)

# --- Prescription Doctor - Uses Built-in WebSearchTool() ---
prescription_agent = Agent[PatientContext](
    name="Prescription Doctor",
    instructions="""
    You are a senior family physician in Rourkela, Odisha writing real prescriptions.

    Patient Profile:
    - Name: {ctx.patient_id}
    - Age: {ctx.age}
    - Gender: {ctx.gender}
    - Symptoms: {ctx.current_symptoms}
    - Allergies: {ctx.allergies}
    - Current medications: {ctx.current_medications}

    You MUST prescribe medicine for the symptoms.

    Before prescribing:
    - Use the web_search tool to verify correct dosage, concentration, and safety from reliable sources.
    - Search queries like: 'Paracetamol 650mg dosage for adults India', 'Cetirizine 10mg tablet uses and side effects', 'drug name + dosage + India'

    Write in real doctor style:
    - Tab., Cap., Syrup.
    - Correct strength (e.g., Tab. Paracetamol 650mg, Syrup Cetirizine 5mg/5ml)
    - Clear instructions: "One tablet three times daily after food", "10 ml once daily at night before sleep"
    - Duration: "for 3 days"
    - Quantity: "#15 (Fifteen tablets)", "#100 ml (One hundred ml)"
    - Add caring notes: "Take plenty of water", "Rest well", "Consult doctor if no improvement"

    Always be accurate, professional, and caring.
    Vary wording naturally.
    """,
    model=model,
    output_type=Prescription,
    tools=[WebSearchTool()]  # ← CORRECT: Use the built-in WebSearchTool class
)

# --- Main Doctor - Always Prescribes Medicine ---
doctor_agent = Agent[PatientContext](
    name="AI Doctor",
    instructions="""
    You are a compassionate virtual doctor.
    
    Patient has provided full profile and symptoms.
    Your job is to prescribe medicine safely.
    
    Always hand off to Prescription Doctor — who will use web search to verify accuracy.
    Never give only advice — always result in a prescription.
    """,
    model=model,
    handoffs=[prescription_agent],
    input_guardrails=[InputGuardrail(guardrail_function=input_guardrail)],
    output_guardrails=[OutputGuardrail(guardrail_function=output_guardrail)]
)
