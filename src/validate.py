"""
Validate Elasticsearch connection and names-search index.
Run from project root: python -m src.validate
"""
import os
from pathlib import Path

from elasticsearch import Elasticsearch
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

INDEX = os.environ.get("ELASTIC_INDEX_NAME", "names-search")


def main():
    cloud_id = os.environ.get("ELASTIC_CLOUD_ID")
    api_key = os.environ.get("ELASTIC_API_KEY")
    if not cloud_id or not api_key:
        print("FAIL: Set ELASTIC_CLOUD_ID and ELASTIC_API_KEY in .env")
        return False

    try:
        es = Elasticsearch(cloud_id=cloud_id, api_key=api_key)
        info = es.info()
        print(f"OK: Connected to Elasticsearch {info['version']['number']}")

        if es.indices.exists(index=INDEX):
            count = es.count(index=INDEX)["count"]
            print(f"OK: Index '{INDEX}' exists with {count} documents")
        else:
            print(f"WARN: Index '{INDEX}' not found. Run: python -m src.ingest_data")
        return True
    except Exception as e:
        print(f"FAIL: {e}")
        return False


if __name__ == "__main__":
    main()
