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

# --- Output Models ---
class Prescription(BaseModel):
    """Prescription issued by the virtual doctor"""
    medication: str = Field(description="Name of the medication (generic preferred)")
    dosage: str = Field(description="Strength and frequency")
    duration: str = Field(description="How long to take it")
    quantity: str = Field(description="Total number of tablets/capsules etc.")
    instructions: str = Field(description="Clear patient instructions")
    refill: bool = Field(default=False, description="Allow refills?")
    notes: Optional[str] = Field(default=None, description="Additional doctor notes")

class GeneralAdvice(BaseModel):
    """General medical guidance without prescription"""
    advice: str = Field(description="Detailed, empathetic medical advice")
    follow_up: str = Field(description="When to seek in-person care or next steps")

class SafetyAnalysis(BaseModel):
    is_safe: bool
    reasoning: str

# --- Patient Context (Filled from web form) ---
@dataclass
class PatientContext:
    patient_id: str
    age: int
    gender: str
    current_symptoms: List[str]
    medical_history: List[str]
    allergies: List[str]
    current_medications: List[str]

# --- Safety Reviewer (Shared for Input & Output Guardrails) ---
safety_reviewer_agent = Agent(
    name="Medical Safety Reviewer",
    instructions="""
    You are a strict medical ethics and safety officer.

    APPROVE prescriptions only for common, non-controlled medications such as:
    • Pain/Fever: ibuprofen, acetaminophen
    • Allergies: cetirizine, loratadine
    • Acid reflux: omeprazole, famotidine
    • Bacterial infections: amoxicillin, azithromycin (if clearly indicated)
    • Cough/Cold: dextromethorphan, guaifenesin
    • Topical: hydrocortisone cream

    REJECT and flag as unsafe:
    • Opioids (oxycodone, hydrocodone, etc.)
    • Benzodiazepines (Xanax, Valium)
    • Stimulants (Adderall, Ritalin)
    • Sleeping pills (Ambien)
    • Weight loss drugs
    • Requests demanding specific controlled drugs
    • Ignoring allergies or dangerous interactions

    Prioritize patient safety above all.
    """,
    output_type=SafetyAnalysis,
    model=model
)

# --- INPUT GUARDRAIL ---
async def input_safety_guardrail(ctx: PatientContext, agent, input_data: str):
    try:
        prompt = f"""
        Patient message: "{input_data}"
        Patient age: {ctx.age}, Allergies: {ctx.allergies}, Current meds: {ctx.current_medications}

        Does this message request or demand controlled substances, show drug-seeking behavior,
        or involve unsafe self-diagnosis demanding restricted drugs?
        Is it safe to proceed?
        """
        result = await Runner.run(safety_reviewer_agent, prompt)
        analysis = result.final_output_as(SafetyAnalysis)
        return GuardrailFunctionOutput(
            output_info=analysis,
            tripwire_triggered=not analysis.is_safe
        )
    except Exception:
        return GuardrailFunctionOutput(
            output_info=SafetyAnalysis(is_safe=True, reasoning="Safety check failed"),
            tripwire_triggered=False
        )

# --- OUTPUT GUARDRAIL ---
async def output_safety_guardrail(ctx: PatientContext, agent, input_data: str, output_data):
    try:
        output_str = str(output_data)
        prompt = f"""
        Review this doctor's response for safety:

        Patient: Age {ctx.age}, Symptoms: {ctx.current_symptoms}
        Allergies: {ctx.allergies}, Current meds: {ctx.current_medications}

        Doctor's response:
        {output_str}

        Does it prescribe only allowed safe medications?
        Does it avoid controlled drugs and dangerous advice?
        """
        result = await Runner.run(safety_reviewer_agent, prompt)
        analysis = result.final_output_as(SafetyAnalysis)

        if not analysis.is_safe:
            safe_fallback = GeneralAdvice(
                advice="""
                I'm sorry, but I cannot prescribe or recommend the requested treatment 
                as it may be unsafe or require in-person medical evaluation.

                Your safety is my top priority.
                """,
                follow_up="Please visit a doctor or urgent care for proper assessment and treatment."
            )
            return GuardrailFunctionOutput(
                output_info=safe_fallback,
                tripwire_triggered=True,
                override_output=safe_fallback
            )
        return GuardrailFunctionOutput(output_info=analysis, tripwire_triggered=False)
    except Exception:
        fallback = GeneralAdvice(
            advice="A safety review error occurred. I cannot provide this advice at this time.",
            follow_up="Please consult a healthcare professional in person."
        )
        return GuardrailFunctionOutput(
            output_info=fallback,
            tripwire_triggered=True,
            override_output=fallback
        )

# --- Prescription Specialist (Can and WILL prescribe safe meds) ---
prescription_agent = Agent[PatientContext](
    name="Prescription Doctor",
    handoff_description="Issues prescriptions for common, safe medications",
    instructions="""
    You are a licensed, responsible family doctor.
    When symptoms clearly suggest a common condition (e.g., headache, allergy, acid reflux, likely bacterial infection),
    prescribe appropriate safe medication.

    Always include:
    - Generic name
    - Dosage, duration, quantity
    - Clear instructions
    - Check for allergies/interactions
    - Advise when to seek help if no improvement
    """,
    model=model,
    output_type=Prescription
)

# --- General Medical Advisor ---
advice_agent = Agent[PatientContext](
    name="General Medical Advisor",
    handoff_description="Provides advice, home remedies, and red flags",
    instructions="""
    You are a caring doctor giving safe, evidence-based guidance.
    Suggest rest, hydration, OTC options, and always include red flags for urgent care.
    """,
    model=model,
    output_type=GeneralAdvice
)

# --- Main Virtual Doctor Agent ---
doctor_agent = Agent[PatientContext](
    name="Virtual Doctor",
    instructions="""
    You are a professional, empathetic virtual doctor conducting a consultation.

    • If the patient describes symptoms and asks for treatment/medication → hand off to Prescription Doctor
    • For general questions, prevention, or unclear cases → hand off to General Medical Advisor

    Always be safe, responsible, and clear.
    """,
    model=model,
    handoffs=[prescription_agent, advice_agent],
    input_guardrails=[InputGuardrail(guardrail_function=input_safety_guardrail)],
    output_guardrails=[OutputGuardrail(guardrail_function=output_safety_guardrail)]
)

# No demo() function anymore — all input comes from Streamlit
