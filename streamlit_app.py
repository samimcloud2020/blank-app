# streamlit_app.py
import asyncio
import streamlit as st
from main import UserContext, Runner, fitness_agent, InputGuardrailTripwireTriggered, WorkoutPlan, MealPlan

# ===================================
# Page Setup - Modern & Colorful
# ===================================
st.set_page_config(
    page_title="💪 AI Fitness Coach Pro",
    page_icon="💪",
    layout="centered",
    initial_sidebar_state="expanded",
)

# Custom CSS for bold, colorful sidebar
st.markdown("""
<style>
    .css-1d391kg {padding-top: 1rem;}
    .sidebar .sidebar-content {
        background: linear-gradient(180deg, #1e1e2e, #2d1b69);
        color: white;
    }
    .stSelectbox > div > div {background-color: #3b2a8a !important; color: white;}
    .stTextInput > div > div > input {background-color: #4a3b9e; color: white;}
    h1, h2, h3 {color: #ff6b6b;}
    .stSuccess {background-color: #2ecc71; color: white;}
</style>
""", unsafe_allow_html=True)

st.title("💪 **Your Personal AI Fitness Coach**")
st.markdown("### Safe • Personalized • Science-Backed Fitness Guidance")

# ===================================
# Sidebar - Colorful & Bold
# ===================================
with st.sidebar:
    st.markdown("""
    <div style='text-align: center; padding: 10px;'>
        <h2 style='color:#ff6b6b; margin:0;'>👤 YOUR PROFILE</h2>
        <p style='color:#a29bfe;'>Customize your plan</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    name = st.text_input("**Your Name**", placeholder="e.g., Alex", value="")

    st.markdown("#### 🎯 **Fitness Level**")
    fitness_level = st.selectbox(
        "Choose your level",
        ["beginner", "intermediate", "advanced"],
        help="Be honest — better results come from accurate starting point!"
    )

    st.markdown("#### 🏆 **Main Goal**")
    fitness_goal = st.selectbox(
        "What are you working toward?",
        ["weight loss", "muscle gain", "general fitness", "strength", "endurance", "toning", "mobility/flexibility"]
    )

    st.markdown("#### 🍎 **Diet Preference**")
    dietary_preference = st.selectbox(
        "Any dietary needs?",
        ["no restrictions", "vegetarian", "vegan", "pescatarian", "keto", "gluten-free"]
    )

    st.markdown("#### 🏋️ **Equipment Available**")
    cols = st.columns(2)
    equipment = []
    options = ["dumbbells", "resistance bands", "barbell", "pull-up bar", "bench", "kettlebell", "gym access"]
    labels = ["Dumbbells", "Bands", "Barbell", "Pull-up Bar", "Bench", "Kettlebell", "Full Gym"]

    for i, (opt, label) in enumerate(zip(options, labels)):
        if cols[i % 2].checkbox(label, key=opt):
            equipment.append(opt)
    if not equipment:
        equipment = ["none / bodyweight only"]

    # Create context
    user_context = UserContext(
        user_id=name or "User",
        fitness_level=fitness_level,
        fitness_goal=fitness_goal,
        dietary_preference=dietary_preference,
        available_equipment=equipment
    )

    st.markdown("---")
    st.markdown(f"""
    <div style='text-align:center; background:#ff6b6b; padding:10px; border-radius:10px;'>
        <h3 style='color:white; margin:0;'>✅ READY TO TRAIN!</h3>
        <p style='color:white; margin:5px;'><strong>{fitness_goal.title()}</strong> mode activated</p>
    </div>
    """, unsafe_allow_html=True)

# ===================================
# Chat Interface
# ===================================
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("💬 Ask me for a workout, meal plan, tips, or motivation..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("🤖 Crafting your personalized plan..."):
            try:
                result = asyncio.run(Runner.run(fitness_agent, prompt, context=user_context))
                output = result.final_output

                if isinstance(output, WorkoutPlan):
                    st.success("💥 **Your Custom Workout Plan**")
                    for ex in output.exercises:
                        st.markdown(f"**• {ex}**")
                    st.info(f"**📋 Coach's Notes:** {output.notes}")

                elif isinstance(output, MealPlan):
                    st.success("🍱 **Your Custom Meal Plan**")
                    st.markdown(f"**🔥 Daily Calories:** {output.daily_calories}")
                    for meal in output.meal_suggestions:
                        st.markdown(f"**🍴 {meal}**")
                    st.info(f"**🥗 Nutrition Tips:** {output.notes}")

                else:
                    st.markdown(output)

                st.session_state.messages.append({"role": "assistant", "content": str(output)})

            except InputGuardrailTripwireTriggered as e:
                analysis = getattr(e, "guardrail_output", None)
                reason = getattr(analysis, "reasoning", "This involves potentially unsafe methods.")

                st.error(f"""
                🚨 **Safety Alert**

                I'm here to help you reach your goals **safely**.

                **⚠️ Issue Detected:** {reason}

                I cannot assist with steroids, dangerous drugs, or extreme crash diets.

                Let's build a **healthy, sustainable plan** that gets real results — safely and for the long term.

                Try asking:  
                • "Give me a beginner workout plan"  
                • "Safe meal plan for weight loss"  
                • "How can I build muscle naturally?"
                """)
                st.session_state.messages.append({"role": "assistant", "content": "Safety guardrail triggered: Dangerous request blocked."})

            except Exception as e:
                st.error("😕 Something went wrong. Please try again!")
