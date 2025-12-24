# main.py
import asyncio
from pydantic import BaseModel, Field
from agents import Agent, Runner, InputGuardrail, OutputGuardrail, GuardrailFunctionOutput, InputGuardrailTripwireTriggered
from typing import List
from dataclasses import dataclass
from dotenv import load_dotenv
import os

load_dotenv()
model = os.getenv('LLM_MODEL_NAME', 'gpt-4o-mini')

# --- Output Models ---
class Prescription(BaseModel):
    """Prescription written by the doctor"""
    medication: str = Field(description="Name of the medication")
    dosage: str = Field(description="Dosage and frequency")
    duration: str = Field(description="How long to take it")
    instructions: str = Field(description="Additional patient instructions")
    refill: bool = Field(description="Whether refill is allowed")

class GeneralAdvice(BaseModel):
    """General medical advice or next steps"""
    advice: str = Field(description="Detailed medical advice or recommendations")
    follow_up: str = Field(description="Recommended follow-up or when to seek urgent care")

class SafetyAnalysis(BaseModel):
    """Analysis result for guardrails"""
    is_safe: bool = Field(description="Whether the content is medically safe and appropriate")
    reasoning: str = Field(description="Detailed explanation of the safety decision")

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

# --- Shared Safety Reviewer Agent (used for both input and output guardrails) ---
safety_reviewer_agent = Agent(
    name="Medical Safety Reviewer",
    instructions="""
    You are a strict medical ethics and patient safety expert.
    Your job is to evaluate content for:
    - Promotion or prescription of controlled substances (opioids, benzodiazepines, stimulants like Adderall)
    - Dangerous home remedies or unproven treatments
    - Encouraging delay of urgent care
    - Diagnosing serious conditions without recommending in-person evaluation
    - Drug-seeking enabling behavior
    - Ignoring allergies or contraindications
    - Overpromising cures or guarantees

    Only approve content that is conservative, evidence-based, and prioritizes patient safety.
    """,
    output_type=SafetyAnalysis,
    model=model
)

# --- INPUT GUARDRAIL: Check user request before processing ---
async def prescription_input_guardrail(ctx, agent, input_data):
    try:
        prompt = f"""
        Patient message: "{input_data}"
        
        Does this message contain a request for controlled substances, 
        self-diagnosis demanding specific drugs, or drug-seeking behavior?
        Evaluate strictly for safety.
        """
        result = await Runner.run(safety_reviewer_agent, prompt)
        analysis = result.final_output_as(SafetyAnalysis)
        return GuardrailFunctionOutput(
            output_info=analysis,
            tripwire_triggered=not analysis.is_safe  # Trigger if unsafe
        )
    except Exception as e:
        return GuardrailFunctionOutput(
            output_info=SafetyAnalysis(is_safe=True, reasoning=f"Guardrail error: {str(e)}"),
            tripwire_triggered=False
        )

# --- OUTPUT GUARDRAIL: Check agent's response after generation ---
async def medical_output_guardrail(ctx, agent, input_data, output_data):
    try:
        output_str = str(output_data)
        prompt = f"""
        Review this doctor response for medical safety:
        
        Patient context:
        - Age: {ctx.age}, Gender: {ctx.gender}
        - Symptoms: {', '.join(ctx.current_symptoms)}
        - Allergies: {', '.join(ctx.allergies)}
        - Current meds: {', '.join(ctx.current_medications)}
        
        Doctor's response:
        {output_str}
        
        Is this response medically safe, ethical, and responsible?
        Does it prescribe controlled drugs, give dangerous advice, or ignore red flags?
        """
        result = await Runner.run(safety_reviewer_agent, prompt)
        analysis = result.final_output_as(SafetyAnalysis)
        if not analysis.is_safe:
            # Replace unsafe output with safe fallback
            safe_fallback = GeneralAdvice(
                advice="""
                I'm sorry, but I cannot provide specific medical advice or prescriptions 
                that may be unsafe or require in-person evaluation. 
                Your health is my priority.
                
                Please consult a licensed physician in person for proper diagnosis and treatment.
                """,
                follow_up="Seek immediate care if symptoms worsen or include chest pain, difficulty breathing, severe bleeding, or confusion."
            )
            return GuardrailFunctionOutput(
                output_info=safe_fallback,
                tripwire_triggered=True,
                override_output=safe_fallback
            )
        return GuardrailFunctionOutput(
            output_info=analysis,
            tripwire_triggered=False
        )
    except Exception as e:
        # On error, default to safe response
        safe_fallback = GeneralAdvice(
            advice="Due to a system issue, I cannot provide detailed advice at this time. Please see a doctor in person.",
            follow_up="Contact a healthcare provider as soon as possible."
        )
        return GuardrailFunctionOutput(
            output_info=safe_fallback,
            tripwire_triggered=True,
            override_output=safe_fallback
        )

# --- Specialized Agents ---
prescription_agent = Agent[PatientContext](
    name="Prescription Specialist",
    handoff_description="Issues safe, common prescriptions only",
    instructions="""
    You are a cautious family physician.
    Only prescribe over-the-counter or common non-controlled medications 
    (e.g., ibuprofen, antihistamines, antibiotics for clear bacterial infections).
    Never prescribe opioids, benzodiazepines, stimulants, or weight loss drugs.
    Always check allergies and interactions.
    """,
    model=model,
    output_type=Prescription
)

advice_agent = Agent[PatientContext](
    name="General Medical Advisor",
    handoff_description="Provides safe general advice and symptom guidance",
    instructions="""
    You are an empathetic and responsible doctor.
    Offer evidence-based suggestions, home care tips, and clear red flags.
    Always recommend in-person care for serious or unclear symptoms.
    Never diagnose cancer, heart attack, stroke, or other emergencies online.
    """,
    model=model,
    output_type=GeneralAdvice
)

# --- Main Doctor Agent with BOTH Input and Output Guardrails ---
doctor_agent = Agent[PatientContext](
    name="Virtual Doctor",
    instructions="""
    You are a professional, ethical virtual doctor.
    
    - If the patient asks for medication or a prescription → hand off to Prescription Specialist
    - For symptoms, concerns, or general questions → hand off to General Medical Advisor
    
    Always prioritize safety, clarity, and responsibility.
    """,
    model=model,
    handoffs=[prescription_agent, advice_agent],
    input_guardrails=[InputGuardrail(guardrail_function=prescription_input_guardrail)],
    output_guardrails=[OutputGuardrail(guardrail_function=medical_output_guardrail)]
)

# --- Demo ---
async def demo():
    patient_context = PatientContext(
        patient_id="Jane Smith",
        age=42,
        gender="female",
        current_symptoms=["headache", "fever", "congestion"],
        medical_history=["migraines", "asthma"],
        allergies=["penicillin"],
        current_medications=["albuterol", "ibuprofen as needed"]
    )

    queries = [
        "I've had a headache and fever for 2 days. What can I take?",
        "Please prescribe me OxyContin for my pain",
        "Can I take ibuprofen with my albuterol?",
        "I think I have cancer, what should I do?"
    ]

    for query in queries:
        print("\n" + "="*70)
        print(f"PATIENT: {query}")
        print("="*70)

        try:
            result = await Runner.run(doctor_agent, query, context=patient_context)
            output = result.final_output

            if isinstance(output, Prescription):
                print("\n[💊 PRESCRIPTION ISSUED]")
                print(f"Medication: {output.medication}")
                print(f"Dosage: {output.dosage}")
                print(f"Duration: {output.duration}")
                print(f"Instructions: {output.instructions}")
            elif isinstance(output, GeneralAdvice):
                print("\n[🩺 DOCTOR'S ADVICE]")
                print(output.advice)
                print("\nFollow-up:", output.follow_up)
            else:
                print("\n[🩺 RESPONSE]")
                print(output)

        except InputGuardrailTripwireTriggered as e:
            analysis = getattr(e, "guardrail_output", None)
            reason = getattr(analysis, "reasoning", "Unsafe request detected.")
            print("\n[⚠️ INPUT GUARDRAIL BLOCKED]")
            print(f"Reason: {reason}")

        except Exception as e:
            print(f"\n[❌ ERROR]: {str(e)}")

if __name__ == "__main__":
    asyncio.run(demo())
