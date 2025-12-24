# streamlit_app.py
import asyncio
import os
import streamlit as st
from pydantic import BaseModel, Field
from typing import List

# ───────────────────────────────────────────────
#   Assuming your agent-related classes are in a separate file
#   (you can also keep them here if you prefer one-file solution)
# ───────────────────────────────────────────────

# We'll import your existing modules — adjust paths/names as needed
try:
    from main import (
        UserContext,
        fitness_agent,
        Runner,
        InputGuardrailTripwireTriggered,
        WorkoutPlan,
        MealPlan,
        # goal_analysis_agent, fitness_goal_guardrail, etc. if needed
    )
except ImportError:
    st.error("Could not import from main.py — please check file structure")
    st.stop()

# ───────────────────────────────────────────────
#   Page config
# ───────────────────────────────────────────────
st.set_page_config(
    page_title="Fitness Coach Agent",
    page_icon="🏋️",
    layout="wide"
)

st.title("🏋️ Fitness Coach Agent Demo")
st.markdown("Ask anything about workouts, nutrition, or general fitness!")

# ───────────────────────────────────────────────
#   Sidebar — User Profile
# ───────────────────────────────────────────────
with st.sidebar:
    st.header("Your Profile")
    
    user_id = st.text_input("User ID", value="user123")
    fitness_level = st.selectbox("Fitness Level", ["beginner", "intermediate", "advanced"], index=0)
    fitness_goal = st.selectbox("Main Goal", ["weight loss", "muscle gain", "general fitness", "strength", "endurance"])
    dietary_preference = st.selectbox("Dietary Preference", ["no restrictions", "vegetarian", "vegan", "keto"])
    
    st.subheader("Available Equipment")
    equipment_options = ["dumbbells", "resistance bands", "barbell", "pull-up bar", "bench", "none / bodyweight only"]
    available_equipment = st.multiselect("Select equipment you have", equipment_options, default=["dumbbells", "resistance bands"])
    
    user_context = UserContext(
        user_id=user_id,
        fitness_level=fitness_level,
        fitness_goal=fitness_goal,
        dietary_preference=dietary_preference,
        available_equipment=available_equipment
    )

# ───────────────────────────────────────────────
#   Chat interface
# ───────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    role = "user" if message["role"] == "user" else "assistant"
    avatar = "👤" if role == "user" else "🏋️"
    with st.chat_message(role, avatar=avatar):
        st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("Ask me anything about fitness..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    with st.chat_message("user", avatar="👤"):
        st.markdown(prompt)
    
    with st.chat_message("assistant", avatar="🏋️"):
        with st.spinner("Thinking..."):
            try:
                # Run the agent asynchronously
                result = asyncio.run(
                    Runner.run(fitness_agent, prompt, context=user_context)
                )
                
                final_output = result.final_output
                
                if isinstance(final_output, WorkoutPlan):
                    st.markdown("**🧘‍♂️ Workout Plan**")
                    st.write("**Exercises:**")
                    for ex in final_output.exercises:
                        st.markdown(f"- {ex}")
                    st.markdown(f"**Notes:** {final_output.notes}")
                
                elif isinstance(final_output, MealPlan):
                    st.markdown("**🍽️ Nutrition Plan**")
                    st.markdown(f"**Daily calories:** {final_output.daily_calories}")
                    st.write("**Meal suggestions:**")
                    for meal in final_output.meal_suggestions:
                        st.markdown(f"- {meal}")
                    st.markdown(f"**Notes:** {final_output.notes}")
                
                else:
                    # Generic response
                    st.markdown(final_output)
                
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": str(final_output)
                })
                
            except InputGuardrailTripwireTriggered as e:
                reason = getattr(e.guardrail_output, 'reasoning', "Unrealistic or unsafe goal detected.")
                msg = f"⚠️ **Safety guardrail triggered**\n\n{reason}"
                st.error(msg)
                st.session_state.messages.append({"role": "assistant", "content": msg})
                
            except Exception as e:
                error_msg = f"Error: {str(e)}"
                st.error(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": error_msg})
