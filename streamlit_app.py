import streamlit as st
from agents import Agent, Runner, function_tool
from typing import List
import chromadb
from chromadb.utils import embedding_functions
from chromadb.config import Settings

# ------------------- In-Memory Vector Store (Persists in session_state) -------------------
@st.cache_resource
def get_collection():
    chroma_client = chromadb.Client(Settings(allow_reset=True))
    embedding_func = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )
    collection = chroma_client.create_collection(
        name="knowledge",
        embedding_function=embedding_func
    )
    return collection

collection = get_collection()

def add_chunks_to_db(chunks: List[str]):
    if not chunks:
        return
    ids = [f"chunk_{i}" for i in range(len(chunks))]
    collection.add(documents=chunks, ids=ids)

# ------------------- Tools -------------------
@function_tool
def extract_knowledge_chunks(text: str) -> List[str]:
    """Extract concise knowledge chunks from text."""
    import re
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    return [s.strip() for s in sentences if len(s) > 30]

@function_tool
def store_knowledge_chunks(chunks: List[str]) -> str:
    """Store chunks in vector DB."""
    add_chunks_to_db(chunks)
    return f"Stored {len(chunks)} chunks."

@function_tool
def retrieve_relevant_chunks(query: str, top_k: int = 5) -> List[str]:
    """Retrieve top relevant chunks."""
    if collection.count() == 0:
        return ["No knowledge ingested yet."]
    results = collection.query(query_texts=[query], n_results=top_k)
    return results["documents"][0]

# ------------------- Agents (Model from secrets) -------------------
model_name = st.secrets.get("MODEL_NAME", "gpt-4o-mini")

extraction_agent = Agent(
    name="Knowledge Extraction Agent",
    description="Extracts and stores knowledge",
    instructions="""
    1. Use extract_knowledge_chunks on the document.
    2. Use store_knowledge_chunks to save.
    Be concise.
    """,
    tools=[extract_knowledge_chunks, store_knowledge_chunks],
    model=model_name
)

query_agent = Agent(
    name="RAG Query Agent",
    description="Answers using retrieved knowledge",
    instructions="""
    1. Always call retrieve_relevant_chunks first.
    2. Answer ONLY from chunks. Cite key parts.
    3. If irrelevant/no chunks: "No knowledge available."
    """,
    tools=[retrieve_relevant_chunks],
    model=model_name
)

# ------------------- Streamlit UI -------------------
st.title("🧠 Agentic RAG Chatbot")
st.caption("💡 Upload .txt files → Ingest → Ask questions!")

# Sidebar: Ingestion
with st.sidebar:
    st.header("📤 Ingest Knowledge")
    uploaded_files = st.file_uploader("Upload .txt files", type=["txt"], accept_multiple_files=True)
    if st.button("🚀 Ingest Files") and uploaded_files:
        with st.spinner("Extracting & storing..."):
            full_text = ""
            for file in uploaded_files:
                full_text += file.getvalue().decode("utf-8") + "\n\n"
            # Reset DB for fresh ingest
            collection.delete_all()
            result = Runner.run_sync(extraction_agent, f"Process:\n\n{full_text}")
            st.success(result.final_output)
            st.info(f"💾 Knowledge ready! DB size: {collection.count()} chunks")

# Chat
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Ask about your knowledge..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Retrieving & answering..."):
            stream = Runner.run_streamed(query_agent, prompt)
            full_response = ""
            for item in stream:
                if item.type == "text":
                    st.write(item.content, end="")
                    full_response += item.content
            st.session_state.messages.append({"role": "assistant", "content": full_response})

st.info(f"🤖 Model: {model_name} | 💾 Chunks: {collection.count()}")
