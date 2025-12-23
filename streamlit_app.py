# app.py - Secure PDF RAG Chatbot (Beautiful & Clean Chat Experience)
import os
import streamlit as st
from openai import OpenAI
from agents import Agent, Runner, FileSearchTool
from dotenv import load_dotenv  # Optional: only for local testing

# ----------------------------- Load Secrets Safely -----------------------------
load_dotenv(override=False)

if "OPENAI_API_KEY" not in st.secrets:
    st.error("❌ OPENAI_API_KEY not found in Streamlit Secrets!")
    st.stop()

OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]

if "PASSWORD" not in st.secrets:
    st.error("❌ PASSWORD not found in Streamlit Secrets!")
    st.stop()

PASSWORD = st.secrets["PASSWORD"]

MODEL_NAME = st.secrets.get("MODEL_NAME", "gpt-4o")

# ----------------------------- Stunning & Colorful Theme -----------------------------
st.set_page_config(page_title="Secure PDF RAG", layout="wide")

st.markdown("""
<style>
    .main {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 50%, #f093fb 100%);
        background-attachment: fixed;
        color: white;
        padding: 2rem;
    }
    [data-testid="stSidebar"] {
        background: linear-gradient(to bottom, #5e42a6, #764ba2);
        padding-top: 1rem;
        border-right: 3px solid rgba(255,255,255,0.2);
    }
    h1 {
        color: #ffffff !important;
        font-size: 3.5rem !important;
        font-weight: 800 !important;
        text-align: center;
        text-shadow: 0 4px 10px rgba(0,0,0,0.3);
        margin-bottom: 1rem;
    }
    .big-bold {
        font-size: 1.8rem !important;
        font-weight: bold !important;
        color: #e0e0ff !important;
        text-align: center;
        margin: 2rem 0;
    }
    .status-box {
        padding: 2rem;
        border-radius: 20px;
        background: rgba(255,255,255,0.15);
        backdrop-filter: blur(10px);
        margin: 2rem auto;
        max-width: 900px;
        text-align: center;
        font-size: 1.4rem;
        font-weight: bold;
        border: 2px solid rgba(255,255,255,0.3);
        box-shadow: 0 8px 32px rgba(0,0,0,0.2);
    }
    .stChatInput > div > div > input {
        background: rgba(255,255,255,0.95) !important;
        color: #333 !important;
        border-radius: 30px !important;
        font-size: 1.3rem !important;
        padding: 1.3rem 1.8rem !important;
        box-shadow: 0 6px 20px rgba(0,0,0,0.2);
        border: none;
    }
    .stChatMessage {
        background: rgba(255,255,255,0.1);
        border-radius: 18px;
        padding: 1rem;
        margin: 1rem 0;
        backdrop-filter: blur(5px);
    }
    .footer {
        text-align: center;
        color: #d0d0ff;
        margin-top: 8rem;
        font-size: 1.1rem;
        font-weight: bold;
        text-shadow: 0 2px 5px rgba(0,0,0,0.3);
    }
</style>
""", unsafe_allow_html=True)

# ----------------------------- OpenAI Client -----------------------------
client = OpenAI(api_key=OPENAI_API_KEY)

# ----------------------------- Sidebar: Login & Upload -----------------------------
with st.sidebar:
    st.markdown("### 🔐 **Access Control**")

    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if not st.session_state.authenticated:
        st.markdown("**Enter your access password**")
        password_input = st.text_input("Password", type="password", label_visibility="collapsed")
        if st.button("🔓 Login"):
            if password_input == PASSWORD:
                st.session_state.authenticated = True
                st.success("✅ Access granted!")
                st.rerun()
            else:
                st.error("❌ Incorrect password")
        st.stop()

    st.success("✅ **Authenticated**")
    st.markdown("---")
    st.markdown("### 📤 **Upload PDF Documents**")
    st.markdown("**Drag & drop your PDFs below**")

    uploaded_files = st.file_uploader(
        "Upload PDFs",
        type=["pdf"],
        accept_multiple_files=True,
        label_visibility="collapsed"
    )

    if uploaded_files:
        st.markdown("### 🔄 Processing your PDFs... Please wait")

        progress_bar = st.progress(0)
        status_text = st.empty()

        total = len(uploaded_files)
        file_ids = []

        for i, file in enumerate(uploaded_files):
            status_text.text(f"Uploading: {file.name} ({i+1}/{total})")
            temp_path = f"/tmp/{file.name}"
            with open(temp_path, "wb") as f:
                f.write(file.getbuffer())
            uploaded = client.files.create(file=open(temp_path, "rb"), purpose="assistants")
            file_ids.append(uploaded.id)
            os.remove(temp_path)
            progress_bar.progress((i + 1) / total * 0.7)

        status_text.text("Setting up knowledge base...")
        stores = client.vector_stores.list(limit=20)
        vector_store = next((vs for vs in stores.data if vs.name == "Secure_PDF_RAG_Store"), None)
        if not vector_store:
            vector_store = client.vector_stores.create(name="Secure_PDF_RAG_Store")

        status_text.text("Indexing documents... Final step!")
        client.vector_stores.file_batches.create_and_poll(
            vector_store_id=vector_store.id,
            file_ids=file_ids
        )

        progress_bar.progress(1.0)
        status_text.empty()

        st.session_state.vector_store = vector_store
        st.session_state.pdfs_ready = True

        st.success(f"✅ {total} PDF(s) fully processed and ready!")
        st.balloons()

# ----------------------------- Main Area -----------------------------
st.markdown("<h1>📄 Secure PDF Intelligence Assistant</h1>", unsafe_allow_html=True)
st.markdown("<div class='big-bold'>Ask any question about your uploaded PDFs</div>", unsafe_allow_html=True)

# Only show "Ready" box if no messages yet (i.e., user hasn't asked anything)
if "pdfs_ready" not in st.session_state or not st.session_state.pdfs_ready:
    st.markdown("""
        <div class='status-box'>
            <h3>⏳ Waiting for PDF upload...</h3>
            <p>Upload your documents in the sidebar to begin.</p>
        </div>
    """, unsafe_allow_html=True)
elif not st.session_state.get("messages"):  # No questions asked yet
    st.markdown("""
        <div class='status-box'>
            <h2>✅ Your documents are ready!</h2>
            <p><strong>Type your first question below 👇</strong></p>
        </div>
    """, unsafe_allow_html=True)
# Otherwise: no box — clean chat view

# RAG Agent Setup
file_search_tool = FileSearchTool(vector_store_ids=[st.session_state.vector_store.id])

agent = Agent(
    name="Secure PDF Expert",
    instructions="""
You are a highly accurate and professional assistant analyzing confidential PDF documents.
- Always search and retrieve exact information from the uploaded PDFs.
- Provide clear, detailed, and concise answers.
- If information is not found, respond: "I could not find that information in the uploaded documents."
- Be helpful and professional.
""",
    model=MODEL_NAME,
    tools=[file_search_tool],
)

# Chat History
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(f"**{msg['content']}**")

# User Input
if prompt := st.chat_input("🔍 Ask your question here..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(f"**{prompt}**")

    with st.chat_message("assistant"):
        with st.spinner("🔍 Searching your documents..."):
            result = Runner.run_sync(agent, prompt)
            response = result.final_output

            st.markdown(f"**{response}**")
            st.session_state.messages.append({"role": "assistant", "content": response})

# Footer
st.markdown("<div class='footer'>🔒 Secure • Private • Powered by OpenAI</div>", unsafe_allow_html=True)
