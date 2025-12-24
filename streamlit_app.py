# streamlit_app.py
import asyncio
import os
import streamlit as st

# Import from your main.py
from main import (
    UserContext,
    Runner,
    fitness_agent,
    InputGuardrailTripwireTriggered,
    WorkoutPlan,
    MealPlan,
)

# ==============================================
# Page Configuration
# ==============================================
st.set_page_config(
    page_title="AI Fitness Coach",
    page_icon="🏋️",
    layout="centered",
    initial_sidebar_state="expanded",
)

st.title("🏋️‍♂️ Your Personal AI Fitness Coach")
st.markdown("Get safe, personalized workout and nutrition advice powered by AI.")

# ==============================================
# Sidebar: User Profile (UserContext)
# ==============================================
with st.sidebar:
    st.header("👤 Your Profile")

    user_id = st.text_input("Name/ID (optional)", value="User", placeholder="e.g., Alex")

    st.subheader("Fitness Level")
    fitness_level = st.selectbox(
        "Your current fitness level",
        options=["beginner", "intermediate", "advanced"],
        index=0,
        help="Beginner: little/no experience | Intermediate: regular training | Advanced: years of consistent training"
    )

    st.subheader("Primary Goal")
    fitness_goal = st.selectbox(
        "What do you want to achieve?",
        options=[
            "weight loss",
            "muscle gain",
            "general fitness",
            "strength",
            "endurance",
            "toning",
            "mobility/flexibility"
        ],
        index=0
    )

    st.subheader("Dietary Preferences")
    dietary_preference = st.selectbox(
        "Any dietary restrictions?",
        options=[
            "no restrictions",
            "vegetarian",
            "vegan",
            "pescatarian",
            "keto",
            "paleo",
            "gluten-free"
        ],
        index=0
    )

    st.subheader("Available Equipment")
    st.caption("Check all that you have access to")

    equipment_mapping = {
        "none / bodyweight only": "None",
        "dumbbells": "Dumbbells",
        "resistance bands": "Resistance Bands",
        "barbell": "Barbell & Plates",
        "pull-up bar": "Pull-up Bar",
        "bench": "Workout Bench",
        "kettlebell": "Kettlebell",
        "yoga mat": "Yoga Mat",
        "gym access": "Full Gym Access",
    }

    selected_equipment = []
    for key, label in equipment_mapping.items():
        if st.checkbox(label, key=f"eq_{key}"):
            selected_equipment.append(key)

    if not selected_equipment:
        selected_equipment = ["none / bodyweight only"]

    # Create UserContext
    user_context = UserContext(
        user_id=user_id or "anonymous",
        fitness_level=fitness_level,
        fitness_goal=fitness_goal,
        dietary_preference=dietary_preference,
        available_equipment=selected_equipment,
    )

    st.divider()
    st.success("✅ Profile Ready!")
    st.caption(f"Goal: **{fitness_goal.title()}** • Level: **{fitness_level.title()}**")

# ==============================================
# Chat History & Interface
# ==============================================
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display previous messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# User input
if prompt := st.chat_input("Ask about workouts, diet, motivation, or anything fitness-related..."):
    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Generate assistant response
    with st.chat_message("assistant"):
        with st.spinner("Creating your personalized plan..."):
            try:
                # Run the agent
                result = asyncio.run(Runner.run(fitness_agent, prompt, context=user_context))
                final_output = result.final_output

                response_text = ""

                # Handle WorkoutPlan
                if isinstance(final_output, WorkoutPlan):
                    st.success("💪 Your Custom Workout Plan")
                    st.write("**Exercises:**")
                    for exercise in final_output.exercises:
                        st.markdown(f"• {exercise}")
                    st.info(f"📝 **Tips & Notes:** {final_output.notes}")
                    response_text = f"**Workout Plan**\n\nExercises:\n" + "\n".join(f"- {e}" for e in final_output.exercises) + f"\n\nNotes: {final_output.notes}"

                # Handle MealPlan
                elif isinstance(final_output, MealPlan):
                    st.success("🍎 Your Custom Meal Plan")
                    st.markdown(f"**Target Daily Calories:** `{final_output.daily_calories}`")
                    st.write("**Meal Ideas:**")
                    for meal in final_output.meal_suggestions:
                        st.markdown(f"• {meal}")
                    st.info(f"📝 **Nutrition Advice:** {final_output.notes}")
                    response_text = f"**Meal Plan**\n\nDaily Calories: {final_output.daily_calories}\n\nMeals:\n" + "\n".join(f"- {m}" for m in final_output.meal_suggestions) + f"\n\nNotes: {final_output.notes}"

                # Fallback: plain text
                else:
                    st.markdown(final_output)
                    response_text = str(final_output)

                # Save to session
                st.session_state.messages.append({"role": "assistant", "content": response_text})

            except InputGuardrailTripwireTriggered as e:
                # Fixed: correctly access guardrail_output.reasoning
                analysis = getattr(e, "guardrail_output", None)
                reason = getattr(analysis, "reasoning", "Unrealistic or unsafe goal detected.") if analysis else "Unsafe goal detected."

                warning_msg = f"""
                ⚠️ **Safety Guardrail Activated**

                Your request involves a goal that may be **unsafe or unrealistic**.

                **Reason:** {reason}

                💡 **Healthy Reminder:**  
                Safe, sustainable weight loss is 0.5–2 pounds per week. Extreme rapid changes can harm your health.

                Let me help you create a **safe and effective** long-term plan instead!
                """
                st.error(warning_msg)
                st.session_state.messages.append({"role": "assistant", "content": warning_msg})

            except Exception as e:
                error_msg = "😕 Sorry, something went wrong. Please try again."
                st.error(error_msg + f" (Details: {str(e)})")
                st.session_state.messages.append({"role": "assistant", "content": error_msg})
