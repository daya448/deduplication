"""
DeDupify - Duplicate detection with Elasticsearch and AI
Based on: https://www.elastic.co/search-labs/blog/detect-duplicates-ai-elasticsearch
"""
import os
import json
from pathlib import Path

import streamlit as st
from elasticsearch import Elasticsearch
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from dotenv import load_dotenv

# Load .env from project root (works when run from src/ or notebooks/)
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# Elasticsearch connection
CLOUD_ID = os.environ.get("ELASTIC_CLOUD_ID")
API_KEY = os.environ.get("ELASTIC_API_KEY")
INDEX_NAME = os.environ.get("ELASTIC_INDEX_NAME", "names-search")

# Initialize LLM - support both Ollama (local) and Azure OpenAI
def get_llm():
    if os.environ.get("OLLAMA_BASE_URL"):
        from langchain_community.llms import Ollama
        return Ollama(
            base_url=os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"),
            model=os.environ.get("OLLAMA_MODEL", "llama3.2:3b")
        )
    # Azure OpenAI (or OpenAI-compatible)
    api_key = os.environ.get("AZURE_OPENAI_API_KEY")
    endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT", "").rstrip("/")
    if not api_key or not endpoint:
        raise ValueError("Set AZURE_OPENAI_API_KEY and AZURE_OPENAI_ENDPOINT in .env (or OLLAMA_BASE_URL for local LLM)")
    try:
        from langchain_openai import AzureChatOpenAI
    except ImportError:
        from langchain_community.chat_models import AzureChatOpenAI
    return AzureChatOpenAI(
        azure_endpoint=endpoint,
        openai_api_key=api_key,
        deployment_name=os.environ.get("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o"),
        openai_api_version=os.environ.get("AZURE_OPENAI_API_VERSION", "2024-08-01-preview"),
    )


def get_es_client():
    return Elasticsearch(cloud_id=CLOUD_ID, api_key=API_KEY)


# Step 4: Generate address variations via LLM
def generate_address_variations(llm, input_address: str) -> list[str]:
    """Generate address variations to improve search recall."""
    prompt = PromptTemplate(
        template="""Given this address: "{address}"
Generate a JSON array of 5-8 search keywords/variations that could match the same location.
Include: full form, abbreviations (St/Street, Ave/Avenue, Rd/Road), city abbreviations (Syd/Sydney, Melb/Melbourne).
Example: ["123 Maple St., Sydney", "Street", "Str", "Syd", "Sydney"]
Return ONLY a JSON array, no other text.""",
        input_variables=["address"],
    )
    chain = LLMChain(llm=llm, prompt=prompt)
    result = chain.run(address=input_address)
    try:
        # Extract JSON array from response (handle markdown code blocks)
        text = result.strip()
        if "```" in text:
            text = text.split("```")[1].replace("json", "").strip()
        variations = json.loads(text)
        return [input_address] + [str(v) for v in variations if v][:7]
    except (json.JSONDecodeError, TypeError):
        return [input_address]


# Step 5: Build search query with name + address variations
def query_elasticsearch(es, index: str, input_name: str, address_variations: list[str], size: int = 10):
    """Search using phonetic name matching and address variations."""
    # Bool query: name (match for phonetic) + address (should match any variation)
    address_should = [{"match": {"address": term}} for term in address_variations[:5]]
    body = {
        "query": {
            "bool": {
                "must": [{"match": {"name": input_name}}],
                "should": address_should,
                "minimum_should_match": 1,
            }
        },
        "size": size,
    }
    response = es.search(index=index, body=body)
    return response["hits"]["hits"]


# Step 6: Check duplicates via LLM
def check_duplicates(llm, search_name: str, input_address: str, es_hits: list) -> str:
    """Pass ES results to LLM for duplicate probability analysis."""
    if not es_hits:
        return "No potential matches found."
    # Format context: one record per line
    records = []
    for hit in es_hits:
        src = hit.get("_source", {})
        records.append(f"- {src.get('name', '')} | {src.get('address', '')} | DOB: {src.get('dob', 'N/A')}")
    response_names = "\n".join(records)
    prompt = PromptTemplate(
        template="""Compare the Input Name and Address against each record below. For each, provide:
1. Match percentage (0-100)
2. Duplicate status (Yes/No - Yes if match > 80%)
3. Brief explanation

Input Name: {search_name}
Input Address: {input_address}

Records from search:
{response_names}

Format as a table with columns: Name, Address, Match %, Duplicate?, Explanation.
Sort by Match % descending. No preamble.""",
        input_variables=["search_name", "input_address", "response_names"],
    )
    chain = LLMChain(llm=llm, prompt=prompt)
    return chain.run(
        search_name=search_name,
        input_address=input_address,
        response_names=response_names,
    )


def main():
    st.set_page_config(page_title="DeDupify - Duplicate Detection", layout="centered")
    st.markdown("""
        <style>
            .stTextInput input { background-color: #f0f8ff; padding: 10px; border-radius: 5px; }
            .stButton button { background-color: #4CAF50; color: white; border-radius: 5px; }
            .stButton button:hover { background-color: #45a049; }
        </style>
    """, unsafe_allow_html=True)

    st.title("🔍 DeDupify - Duplicate Detection")
    st.write("Enter name and address to find potential duplicates. Uses Elasticsearch phonetic search + AI.")

    input_name = st.text_input("Search Name", placeholder="e.g. John Smith")
    input_address = st.text_input("Enter Address", placeholder="e.g. 123 Maple St., Sydney")

    if st.button("Search 🔍"):
        if not input_name or not input_address:
            st.warning("Please enter both name and address.")
            return
        if not CLOUD_ID or not API_KEY:
            st.error("Missing ELASTIC_CLOUD_ID or ELASTIC_API_KEY in .env")
            return

        with st.spinner("Searching and analyzing..."):
            try:
                es = get_es_client()
                llm = get_llm()

                # Step 4: Generate address variations
                with st.expander("Address variations (LLM-generated)", expanded=False):
                    variations = generate_address_variations(llm, input_address)
                    st.write(variations)

                # Step 5: Search Elasticsearch
                hits = query_elasticsearch(es, INDEX_NAME, input_name, variations)

                if not hits:
                    st.info("No potential duplicates found.")
                    return

                # Step 6: LLM duplicate check
                result = check_duplicates(llm, input_name, input_address, hits)

                st.write("### Results")
                st.markdown(result)
            except Exception as e:
                st.error(f"Error: {e}")
                raise


if __name__ == "__main__":
    main()
