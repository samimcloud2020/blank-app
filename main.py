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
    medications: List[str] = Field(description="Medication with strength, e.g., 'Tab. Paracetamol 650mg'")
    sig: List[str] = Field(description="Full patient instructions: dosage, timing, food relation, e.g., 'One tablet twice daily after food'")
    duration: str = Field(description="How long to take, e.g., 'for 5 days' or 'until symptoms improve'")
    quantity: List[str] = Field(description="Dispense quantity in number and words, e.g., '#30 (Thirty)'")
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
    You are a strict medical safety expert.
    
    APPROVE only safe, common, non-controlled medications:
    - Paracetamol, Ibuprofen, Cetirizine, Loratadine, Omeprazole, Amoxicillin, Azithromycin
    - Cough syrups (Ascoril LS, Benadryl), antacids, antihistamines, etc.
    
    BLOCK immediately:
    - Opioids, benzodiazepines, stimulants, sleeping pills, steroids, weight loss drugs
    - Any controlled substance
    - Ignoring known allergies
    - Overdosing or dangerous combinations
    
    Always prioritize patient safety.
    """,
    output_type=SafetyAnalysis,
    model=model
)

async def input_guardrail(ctx: PatientContext, agent, input_data: str):
    try:
        prompt = f"""
        Patient message: "{input_data}"
        Known allergies: {ctx.allergies}
        Current medications: {ctx.current_medications}
        
        Does this request involve controlled substances, drug-seeking, or unsafe demands?
        Is it safe to evaluate for common medication?
        """
        result = await Runner.run(safety_reviewer_agent, prompt)
        analysis = result.final_output_as(SafetyAnalysis)
        return GuardrailFunctionOutput(output_info=analysis, tripwire_triggered=not analysis.is_safe)
    except:
        return GuardrailFunctionOutput(output_info=SafetyAnalysis(is_safe=True, reasoning="Error"), tripwire_triggered=False)

async def output_guardrail(ctx: PatientContext, agent, input_data: str, output_data):
    try:
        output_str = str(output_data)
        prompt = f"""
        Review this response for safety:
        {output_str}
        
        Patient allergies: {ctx.allergies}
        Current meds: {ctx.current_medications}
        
        Does it prescribe only allowed safe medications?
        Does it avoid controlled drugs and dangerous advice?
        """
        result = await Runner.run(safety_reviewer_agent, prompt)
        analysis = result.final_output_as(SafetyAnalysis)
        if not analysis.is_safe:
            safe = GeneralAdvice(
                advice="I cannot prescribe or recommend that medication as it may be unsafe or restricted without in-person evaluation.",
                follow_up="Please consult a licensed doctor in person."
            )
            return GuardrailFunctionOutput(output_info=safe, tripwire_triggered=True, override_output=safe)
        return GuardrailFunctionOutput(output_info=analysis, tripwire_triggered=False)
    except:
        fallback = GeneralAdvice(advice="Safety check error.", follow_up="See a doctor.")
        return GuardrailFunctionOutput(output_info=fallback, tripwire_triggered=True, override_output=fallback)

# --- Prescription Agent - NOW GIVES VARIED, PERSONALIZED PRESCRIPTIONS ---
prescription_agent = Agent[PatientContext](
    name="Prescription Doctor",
    instructions="""
    You are a compassionate, experienced family doctor in India writing a real prescription.

    Think step-by-step:
    1. Carefully read the patient's current symptoms, age, gender, allergies, and current medications.
    2. Diagnose the most likely common condition (cold, fever, allergy, acidity, cough, etc.).
    3. Choose appropriate, safe medications from common ones only.
    4. Vary dosage and timing based on age and severity (e.g., lower dose for elderly).
    5. Always include relation to food (before/after) and specific times (morning/night).
    6. Use realistic Indian pharmacy names and formats.

    Write in professional format:
    - Medication name with strength
    - Full instructions: "One tablet twice daily after food in morning and night"
    - Duration: "for 3 days" or "5 days" or "until symptoms resolve"
    - Quantity: number and words
    - Add helpful notes (e.g., drink water, rest, when to seek help)

    Be natural and vary your prescriptions — do not repeat the same one.
    Always check allergies before prescribing.
    """,
    model=model,
    output_type=Prescription
)

# --- General Advisor ---
advice_agent = Agent[PatientContext](
    name="General Medical Advisor",
    instructions="""
    You are a caring doctor giving safe, evidence-based advice.
    
    Suggest home remedies, rest, hydration, diet tips.
    Clearly mention red flags: when to go to hospital.
    Be empathetic and detailed.
    Never prescribe — only advise.
    """,
    model=model,
    output_type=GeneralAdvice
)

# --- Main Virtual Doctor ---
doctor_agent = Agent[PatientContext](
    name="AI Doctor",
    instructions="""
    You are a kind, professional virtual doctor in Rourkela, Odisha.
    
    Listen carefully to the patient's complaint.
    
    - If they describe symptoms and need medicine → hand off to Prescription Doctor
    - If they ask for advice, prevention, or general health → hand off to General Medical Advisor
    
    Always be empathetic, clear, and responsible.
    Respond in a natural, conversational way.
    """,
    model=model,
    handoffs=[prescription_agent, advice_agent],
    input_guardrails=[InputGuardrail(guardrail_function=input_guardrail)],
    output_guardrails=[OutputGuardrail(guardrail_function=output_guardrail)]
)
