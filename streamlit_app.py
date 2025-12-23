# app.py - Secure PDF Intelligence Assistant (PDF First Priority + Web Fallback)
import os
import streamlit as st
from openai import OpenAI
from agents import Agent, Runner, FileSearchTool, WebSearchTool
from dotenv import load_dotenv

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

# ----------------------------- Stylish Yellow & Gold Theme -----------------------------
st.set_page_config(page_title="Secure PDF Intelligence Assistant", layout="wide")

st.markdown("""
<style>
    .main {
        background: linear-gradient(135deg, #FFD700 0%, #FFA500 30%, #FF8C00 70%, #FF6347 100%);
        background-attachment: fixed;
        color: #1a1a1a;
        padding: 2rem;
    }
    [data-testid="stSidebar"] {
        background: linear-gradient(to bottom, #FFB300, #FF8F00);
        padding-top: 1rem;
        border-right: 4px solid #FFD700;
        box-shadow: 5px 0 15px rgba(0,0,0,0.2);
    }
    h1 {
        color: #8B4513 !important;
        font-size: 3.8rem !important;
        font-weight: 900 !important;
        text-align: center;
        text-shadow: 0 4px 8px rgba(0,0,0,0.3);
        margin-bottom: 1rem;
        font-family: 'Georgia', serif;
    }
    .big-bold {
        font-size: 2rem !important;
        font-weight: bold !important;
        color: #8B4513 !important;
        text-align: center;
        margin: 2rem 0;
        text-shadow: 0 2px 4px rgba(0,0,0,0.2);
    }
    .status-box {
        padding: 2.5rem;
        border-radius: 25px;
        background: rgba(255, 255, 255, 0.85);
        backdrop-filter: blur(12px);
        margin: 2rem auto;
        max-width: 900px;
        text-align: center;
        font-size: 1.5rem;
        font-weight: bold;
        color: #8B4513;
        border: 4px solid #FFD700;
        box-shadow: 0 10px 30px rgba(0,0,0,0.3);
    }
    .stChatInput > div > div > input {
        background: white !important;
        color: #333 !important;
        border-radius: 35px !important;
        font-size: 1.4rem !important;
        padding: 1.4rem 2rem !important;
        box-shadow: 0 8px 25px rgba(0,0,0,0.3);
        border: 3px solid #FFD700;
    }
    .stChatMessage {
        background: rgba(255, 255, 255, 0.9);
        border-radius: 20px;
        padding: 1.2rem;
        margin: 1rem 0;
        backdrop-filter: blur(8px);
        border: 1px solid #FFD700;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    .footer {
        text-align: center;
        color: #8B4513;
        margin-top: 8rem;
        font-size: 1.2rem;
        font-weight: bold;
        text-shadow: 0 2px 5px rgba(0,0,0,0.2);
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
    st.markdown("**Drag & drop your PDFs below (optional)**")

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

        st.success(f"✅ {total} PDF(s) fully processed!")
        st.balloons()

# ----------------------------- Main Area -----------------------------
st.markdown("<h1>📄 Secure PDF Intelligence Assistant</h1>", unsafe_allow_html=True)
st.markdown("<div class='big-bold'>Ask anything — I'll check your PDFs first, then the web if needed</div>", unsafe_allow_html=True)

# Status message
if "pdfs_ready" not in st.session_state or not st.session_state.pdfs_ready:
    st.markdown("""
        <div class='status-box'>
            <h3>🌐 Web search ready</h3>
            <p>You can ask questions now. Upload PDFs for document-specific answers.</p>
        </div>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
        <div class='status-box'>
            <h2>✅ PDFs loaded</h2>
            <p><strong>I will always search your documents first for the most accurate answer.</strong></p>
        </div>
    """, unsafe_allow_html=True)

# ----------------------------- Tools & Agent (PDF = Top Priority) -----------------------------
tools = [WebSearchTool()]  # Web search always available

if st.session_state.get("pdfs_ready") and "vector_store" in st.session_state:
    file_search_tool = FileSearchTool(vector_store_ids=[st.session_state.vector_store.id])
    tools = [file_search_tool, WebSearchTool()]  # File search FIRST in list → higher priority

agent = Agent(
    name="PDF-First Intelligence Expert",
    instructions="""
You are a highly intelligent assistant with strict priority:

1. TOP PRIORITY: Always search the uploaded PDF documents FIRST using file search.
   - If the question is about content in the PDFs (e.g., ownership, revenue, dates, numbers, statements), use file search.
   - Trust PDF content as the primary and most authoritative source.

2. FALLBACK: Only use web search if:
   - No relevant information is found in the PDFs
   - The question is about current year (2025 or later), recent events, or general knowledge not in documents

3. You may use both tools when comparing PDF data with current info.

Rules:
- Be accurate and professional.
- If PDF has the info → use it and say "According to the uploaded document..."
- If not in PDF → use web search and cite source.
- If not found anywhere → say: "I could not find that information in the documents or on the web."
""",
    model=MODEL_NAME,
    tools=tools,
)

# ----------------------------- Chat History (Shows query immediately) -----------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(f"**{msg['content']}**")

# User Input — Query appears instantly
if prompt := st.chat_input("🔍 Ask anything — I'll search your PDFs first"):
    # Show user question immediately
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(f"**{prompt}**")
    st.rerun()  # Force immediate display of user message

    # Now process the answer
    with st.chat_message("assistant"):
        with st.spinner("🔍 Searching your documents first..."):
            result = Runner.run_sync(agent, prompt)
            response = result.final_output

            st.markdown(f"**{response}**")
            st.session_state.messages.append({"role": "assistant", "content": response})

    st.rerun()  # Refresh to show full conversation

# ----------------------------- Footer -----------------------------
st.markdown("<div class='footer'>🔒 Secure • Intelligent • PDF Priority + Web Fallback • Powered by OpenAI</div>", unsafe_allow_html=True)
