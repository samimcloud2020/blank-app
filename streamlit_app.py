# streamlit_app.py
import asyncio
import os
import streamlit as st

from main import (
    UserContext,
    Runner,
    fitness_agent,
    InputGuardrailTripwireTriggered,
    WorkoutPlan,
    MealPlan,
)

# ───────────────────────────────────────────────
# Page Config
# ───────────────────────────────────────────────
st.set_page_config(
    page_title="AI Fitness Coach",
    page_icon="🏋️",
    layout="centered",
    initial_sidebar_state="expanded",
)

st.title("🏋️‍♂️ Your Personal AI Fitness Coach")
st.markdown("Get personalized workout and nutrition advice based on your goals and setup!")

# ───────────────────────────────────────────────
# Sidebar: User Context (Profile)
# ───────────────────────────────────────────────
with st.sidebar:
    st.header("👤 Your Fitness Profile")

    # --- Basic Info ---
    st.subheader("Personal Info")
    user_id = st.text_input("Name or ID (optional)", value="User", placeholder="e.g., Alex")

    # --- Fitness Level ---
    st.subheader("Current Level")
    fitness_level = st.selectbox(
        "How would you describe your fitness level?",
        options=["beginner", "intermediate", "advanced"],
        index=0,
        help="Beginner: New to exercise | Intermediate: Regular but not advanced | Advanced: Training consistently for years"
    )

    # --- Goal ---
    st.subheader("Main Goal")
    fitness_goal = st.selectbox(
        "What is your primary fitness goal?",
        options=[
            "weight loss",
            "muscle gain",
            "general fitness",
            "strength",
            "endurance",
            "toning",
            "improved mobility"
        ],
        index=0
    )

    # --- Diet ---
    st.subheader("Dietary Preferences")
    dietary_preference = st.selectbox(
        "Do you follow any specific diet?",
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

    # --- Equipment ---
    st.subheader("Available Equipment")
    st.caption("Select everything you have access to")

    equipment_options = {
        "none / bodyweight only": "None",
        "dumbbells": "Dumbbells",
        "resistance bands": "Resistance Bands",
        "barbell": "Barbell & Plates",
        "pull-up bar": "Pull-up Bar",
        "bench": "Workout Bench",
        "kettlebell": "Kettlebell",
        "yoga mat": "Yoga Mat",
        "gym access": "Full Gym Access"
    }

    selected_equipment = []
    for key, label in equipment_options.items():
        if st.checkbox(label, key=f"eq_{key}"):
            selected_equipment.append(key)

    if not selected_equipment:
        selected_equipment = ["none / bodyweight only"]

    # --- Create UserContext ---
    user_context = UserContext(
        user_id=user_id or "anonymous",
        fitness_level=fitness_level,
        fitness_goal=fitness_goal,
        dietary_preference=dietary_preference,
        available_equipment=selected_equipment
    )

    st.divider()
    st.success("✅ Profile ready!")
    st.caption(f"Goal: {fitness_goal.title()} | Level: {fitness_level.title()}")

# ───────────────────────────────────────────────
# Main Chat Interface
# ───────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("Ask about workouts, diet, tips, or motivation..."):
    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Assistant response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                result = asyncio.run(
                    Runner.run(fitness_agent, prompt, context=user_context)
                )

                final_output = result.final_output

                response_text = ""
                if isinstance(final_output, WorkoutPlan):
                    st.success("💪 Personalized Workout Plan")
                    st.write("**Recommended Exercises:**")
                    for ex in final_output.exercises:
                        st.markdown(f"• {ex}")
                    st.info(f"📝 **Notes:** {final_output.notes}")
                    response_text = f"**Workout Plan**\nExercises: {', '.join(final_output.exercises)}\nNotes: {final_output.notes}"

                elif isinstance(final_output, MealPlan):
                    st.success("🍎 Personalized Meal Plan")
                    st.write(f"**Target Daily Calories:** {final_output.daily_calories}")
                    st.write("**Meal Ideas:**")
                    for meal in final_output.meal_suggestions:
                        st.markdown(f"• {meal}")
                    st.info(f"📝 **Advice:** {final_output.notes}")
                    response_text = f"**Meal Plan**\nCalories: {final_output.daily_calories}\nMeals: {', '.join(final_output.meal_suggestions)}\nNotes: {final_output.notes}"

                else:
                    # Plain text response
                    st.markdown(final_output)
                    response_text = str(final_output)

                # Save to history
                st.session_state.messages.append({"role": "assistant", "content": response_text})

            except InputGuardrailTripwireTriggered as e:
                reason = getattr(e.guardrail_output, "reasoning", "Unrealistic or unsafe goal detected.")
                warning_msg = f"⚠️ **Safety Alert**\n\nYour goal appears unsafe or unrealistic.\n\n**Reason:** {reason}\n\nPlease aim for sustainable progress (e.g., 0.5–2 lbs per week for weight loss)."
                st.error(warning_msg)
                st.session_state.messages.append({"role": "assistant", "content": warning_msg})

            except Exception as e:
                error_msg = f"😕 Sorry, something went wrong: {str(e)}"
                st.error(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": error_msg})
