# DeDupify – Duplicate Detection with Elasticsearch and AI

Identify duplicate records (e.g. loan/insurance applications) using Elasticsearch phonetic search and an LLM. Based on the [Elasticsearch Labs blog](https://www.elastic.co/search-labs/blog/detect-duplicates-ai-elasticsearch).

## Flow

1. **Address variations** – LLM generates search keywords from user input (e.g. "123 Maple St., Syd" → Sydney, Street, Str, …)
2. **Elasticsearch search** – Phonetic name matching + address variations
3. **Duplicate analysis** – LLM scores match % and flags duplicates

## Project structure

```
deduplication/
├── similar_names_dataset.csv   # Dataset (kept at root for blog link)
├── src/
│   ├── app.py                 # Streamlit UI
│   ├── ingest_data.py         # Index CSV into Elasticsearch
│   └── validate.py            # Check ES connection
├── notebooks/
│   └── Deduplication_using_Search.ipynb
├── requirements.txt
├── run.py                     # Convenience: python run.py
└── .env.example
```

## Quick start

```bash
# 1. Clone and setup
git clone https://github.com/daya448/deduplication.git
cd deduplication
cp .env.example .env   # Edit with your credentials

# 2. Install
pip install -r requirements.txt

# 3. Validate (index must exist)
python -m src.validate

# 4. Run app
streamlit run src/app.py
# or: python run.py
```

## Configuration (.env)

| Variable | Description |
|----------|-------------|
| `ELASTIC_CLOUD_ID` | Elastic Cloud deployment ID |
| `ELASTIC_API_KEY` | Elasticsearch API key |
| `ELASTIC_INDEX_NAME` | Index name (default: `names-search`) |
| `AZURE_OPENAI_API_KEY` | Azure OpenAI API key |
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI endpoint URL |
| `AZURE_OPENAI_DEPLOYMENT_NAME` | Deployment name (e.g. `gpt-4o`) |

**Optional – local LLM:** Set `OLLAMA_BASE_URL=http://localhost:11434` to use Ollama instead of Azure.

## Indexing data

If the index is empty or missing:

```bash
python -m src.ingest_data
```

Uses `similar_names_dataset.csv` at repo root (blog link). Set `CSV_PATH` in `.env` to use another file.
