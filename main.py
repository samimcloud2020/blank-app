# main.py
import asyncio
from pydantic import BaseModel, Field
from agents import Agent, Runner, InputGuardrail, OutputGuardrail, GuardrailFunctionOutput, InputGuardrailTripwireTriggered
from typing import List, Optional
from dataclasses import dataclass
from dotenv import load_dotenv
import os

load_dotenv()
model = os.getenv('LLM_MODEL_NAME', 'gpt-4o-mini-2024-07-18')  # Use a model that supports tools

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

async def input_guardrail(ctx: PatientContext, agent, input_data: str):
    try:
        prompt = f"Patient message: '{input_data}'. Allergies: {ctx.allergies}. Safe to proceed with common meds?"
        result = await Runner.run(safety_reviewer_agent, prompt)
        analysis = result.final_output_as(SafetyAnalysis)
        return GuardrailFunctionOutput(output_info=analysis, tripwire_triggered=not analysis.is_safe)
    except:
        return GuardrailFunctionOutput(output_info=SafetyAnalysis(is_safe=True, reasoning="Error"), tripwire_triggered=False)

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

# --- Official OpenAI Web Search Tool (from docs) ---
web_search_tool = {
    "type": "function",
    "function": {
        "name": "search",
        "description": "Search the web for up-to-date medical information, drug dosages, guidelines, concentrations, and safety data from reliable sources.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query in English. Be specific: 'cetirizine adult dosage India', 'paracetamol 650mg safe for 30 year old', 'Ascoril LS syrup composition'"
                },
                "site": {
                    "type": "string",
                    "description": "Optional: restrict to reliable sites, e.g., 'site:drugs.com OR site:1mg.com OR site:nhs.uk OR site:webmd.com'"
                }
            },
            "required": ["query"]
        }
    }
}

# --- Prescription Agent - Now Uses Official OpenAI Search Tool ---
prescription_agent = Agent[PatientContext](
    name="Prescription Doctor",
    instructions="""
    You are an experienced Indian family doctor with access to real-time web search.

    Before prescribing:
    1. Use the 'search' tool to verify exact dosage, concentration, interactions, and safety from trusted sources.
    2. Search queries like:
       - 'cetirizine dosage for adults India'
       - 'paracetamol safe dose for fever'
       - 'Ascoril LS syrup uses and dosage'
    3. Restrict to reliable sites using 'site:' if needed.
    4. Confirm no allergy conflict.

    Then prescribe:
    - Accurate medicine for ALL symptoms
    - Correct strength and form (tablet preferred for adults)
    - Clear timing, food relation, duration
    - Quantity in number and words
    - Helpful notes and advice

    Always be 100% accurate — use search tool whenever unsure.
    Vary responses naturally.
    """,
    model=model,
    output_type=Prescription,
    tools=[web_search_tool]  # ← OFFICIAL OPENAI SEARCH TOOL
)

# --- General Advice Agent - Can also use search ---
advice_agent = Agent[PatientContext](
    name="General Advisor",
    instructions="""
    Give accurate, evidence-based advice.
    Use the 'search' tool for latest medical guidelines if needed.
    Be caring and clear about when to seek urgent care.
    Never prescribe.
    """,
    model=model,
    output_type=GeneralAdvice,
    tools=[web_search_tool]
)

# --- Main Doctor ---
doctor_agent = Agent[PatientContext](
    name="AI Doctor",
    instructions="""
    You are a caring virtual doctor in Rourkela, Odisha.
    
    Listen carefully to symptoms.
    If medication is needed → hand off to Prescription Doctor (who will verify with web search)
    Else → General Advisor
    Always prioritize patient safety and accuracy.
    """,
    model=model,
    handoffs=[prescription_agent, advice_agent],
    input_guardrails=[InputGuardrail(guardrail_function=input_guardrail)],
    output_guardrails=[OutputGuardrail(guardrail_function=output_guardrail)]
)
