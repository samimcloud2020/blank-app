# streamlit_app.py
import streamlit as st
from agents import Agent, Runner, function_tool
from typing import List
import chromadb
from chromadb.utils import embedding_functions

# ------------------- In-memory Vector Store (Session-persistent on Streamlit Cloud) -------------------
if "collection" not in st.session_state:
    client = chromadb.EphemeralClient()  # Pure in-memory, no disk
    embedding_func = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )
   
    # Safely get or create collection
    st.session_state.collection = client.get_or_create_collection(
        name="knowledge",
        embedding_function=embedding_func
    )

collection = st.session_state.collection

def add_chunks(chunks: List[str]):
    if not chunks:
        return
    ids = [f"chunk_{i}" for i in range(len(chunks))]
    collection.add(documents=chunks, ids=ids)

# ------------------- Tools -------------------
@function_tool
def extract_knowledge_chunks(text: str) -> List[str]:
    """Extract clean, factual sentences from raw text."""
    import re
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    return [s.strip() for s in sentences if len(s.strip()) > 25]

@function_tool
def store_knowledge_chunks(chunks: List[str]) -> str:
    """Save chunks to vector database."""
    add_chunks(chunks)
    return f"Successfully stored {len(chunks)} chunks."

@function_tool
def retrieve_relevant_chunks(query: str, top_k: int = 6) -> List[str]:
    """Retrieve most relevant chunks for the query."""
    results = collection.query(query_texts=[query], n_results=top_k)
    return results["documents"][0]

# ------------------- Agents -------------------
model = st.secrets.get("MODEL_NAME", "gpt-4o-mini")

extraction_agent = Agent(
    name="Knowledge Extraction Agent",
    instructions="""
    You are an expert at extracting clean facts from documents.
    1. Call extract_knowledge_chunks with the full text.
    2. Then call store_knowledge_chunks with the result.
    Be concise, remove fluff and duplicates.
    """,
    tools=[extract_knowledge_chunks, store_knowledge_chunks],
    model=model
)

query_agent = Agent(
    name="RAG Assistant",
    instructions="""
    You are a helpful assistant that answers questions using only the retrieved knowledge.
    - Always call retrieve_relevant_chunks first.
    - Base your answer only on the returned chunks.
    - If nothing relevant is found, say: "I don't have information about that in my knowledge base."
    - Quote or paraphrase the chunks naturally.
    """,
    tools=[retrieve_relevant_chunks],
    model=model
)

# ------------------- Streamlit UI -------------------
st.title("🧠 Agentic RAG Chatbot")
st.caption("Upload .txt files → ask questions → powered by OpenAI Agents SDK")

# Sidebar - Upload & Ingest
with st.sidebar:
    st.header("Upload Knowledge")
    uploaded_files = st.file_uploader(
        "Upload text files",
        type=["txt"],
        accept_multiple_files=True
    )
    if st.button("Ingest Files") and uploaded_files:
        with st.spinner("Processing..."):
            full_text = ""
            for f in uploaded_files:
                full_text += f.getvalue().decode("utf-8") + "\n\n"
            result = Runner.run_sync(extraction_agent, f"Extract and store:\n\n{full_text}")
            st.success(result.final_output or "Knowledge ingested successfully!")

# Chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Chat input
if prompt := st.chat_input("Ask anything about your uploaded documents..."):
    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Assistant response with streaming
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            # Run synchronously but stream token-by-token
            result = Runner.run_sync(query_agent, prompt)
            
            placeholder = st.empty()
            full_response = ""
            
            # Stream deltas as they come
            for event in result.stream_events():
                if event.type == "raw_response_event" and hasattr(event.data, "delta"):
                    delta = event.data.delta
                    full_response += delta
                    placeholder.markdown(full_response + "▌")  # Cursor effect
            
            # Final render without cursor
            placeholder.markdown(full_response)
    
    # Save assistant message
    st.session_state.messages.append({"role": "assistant", "content": full_response})

# Footer info
st.info(f"Model: `{model}` • Knowledge persists during your session (resets on reload)")
