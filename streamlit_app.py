import streamlit as st
from agents import Agent, Runner, function_tool
from typing import List
import chromadb
from chromadb.utils import embedding_functions
import os

# ------------------- Vector Store Setup -------------------
DB_PATH = "knowledge_db"

client = chromadb.PersistentClient(path=DB_PATH)
embedding_func = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)
collection = client.get_or_create_collection(
    name="knowledge",
    embedding_function=embedding_func
)

def add_chunks_to_db(chunks: List[str], metadatas: List[dict] | None = None):
    if not chunks:
        return
    ids = [f"chunk_{i}" for i in range(len(chunks))]
    collection.add(
        documents=chunks,
        ids=ids,
        metadatas=metadatas or [{} for _ in chunks]
    )

# ------------------- Tools with @function_tool -------------------
@function_tool
def extract_knowledge_chunks(text: str) -> List[str]:
    """Extract concise, self-contained knowledge chunks from raw text."""
    import re
    # Simple sentence splitting – replace with better logic or LLM chunking if needed
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    return [s.strip() for s in sentences if len(s) > 30]

@function_tool
def store_knowledge_chunks(chunks: List[str]) -> str:
    """Store extracted chunks into the vector database."""
    add_chunks_to_db(chunks)
    return f"Stored {len(chunks)} knowledge chunks successfully."

@function_tool
def retrieve_relevant_chunks(query: str, top_k: int = 5) -> List[str]:
    """Retrieve top_k most relevant knowledge chunks for the query."""
    results = collection.query(query_texts=[query], n_results=top_k)
    return results["documents"][0]

# ------------------- Agents -------------------
extraction_agent = Agent(
    name="Knowledge Extraction Agent",
    description="Extracts and stores knowledge from documents",
    instructions="""
    You are an expert at extracting clean, atomic facts from documents.
    1. Use extract_knowledge_chunks on the full document text.
    2. Then use store_knowledge_chunks to save them.
    Be concise and avoid duplicates.
    """,
    tools=[extract_knowledge_chunks, store_knowledge_chunks],
    model=st.secrets.get("MODEL_NAME", "gpt-4o-mini")  # Use secret or default
)

query_agent = Agent(
    name="RAG Query Agent",
    description="Answers questions using retrieved knowledge",
    instructions="""
    You are a helpful assistant that answers ONLY based on retrieved knowledge.
    1. Always call retrieve_relevant_chunks first.
    2. Synthesize a clear answer from the chunks.
    3. If no relevant info, say "I don't have knowledge about that."
    4. Cite sources by quoting key parts.
    """,
    tools=[retrieve_relevant_chunks],
    model=st.secrets.get("MODEL_NAME", "gpt-4o-mini")
)

# ------------------- Streamlit UI -------------------
st.title("🧠 Agentic RAG Chatbot")
st.caption("Upload documents to build knowledge, then ask questions!")

# Sidebar for file upload (ingestion)
with st.sidebar:
    st.header("Knowledge Ingestion")
    uploaded_files = st.file_uploader(
        "Upload text/PDF files (plain text only for now)",
        type=["txt"],
        accept_multiple_files=True
    )
    if st.button("Ingest Uploaded Files") and uploaded_files:
        with st.spinner("Extracting and storing knowledge..."):
            full_text = ""
            for file in uploaded_files:
                full_text += file.getvalue().decode("utf-8") + "\n\n"
            # Run extraction agent synchronously (simple case)
            result = Runner.run_sync(
                extraction_agent,
                f"Extract and store knowledge from this document:\n\n{full_text}"
            )
            st.success(result.final_output)

# Chat interface
if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Ask a question about your knowledge base..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            # Stream the response
            stream = Runner.run_streamed(query_agent, prompt)
            response = st.write_stream(item.content for item in stream if item.type == "text")
    
    st.session_state.messages.append({"role": "assistant", "content": response})

st.info(f"Using model: {st.secrets.get('MODEL_NAME', 'gpt-4o-mini')}")
