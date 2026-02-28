"""
Index CSV data into Elasticsearch for duplicate detection.
Run from project root: python -m src.ingest_data
Uses similar_names_dataset.csv at repo root (blog link).
"""
import os
from pathlib import Path

import pandas as pd
from elasticsearch import Elasticsearch, helpers
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

INDEX_NAME = os.environ.get("ELASTIC_INDEX_NAME", "names-search")
# Keep at repo root - blog link: .../deduplication/.../main/similar_names_dataset.csv
CSV_PATH = os.environ.get("CSV_PATH", "similar_names_dataset.csv")


def main():
    cloud_id = os.environ.get("ELASTIC_CLOUD_ID")
    api_key = os.environ.get("ELASTIC_API_KEY")
    if not cloud_id or not api_key:
        raise SystemExit("Set ELASTIC_CLOUD_ID and ELASTIC_API_KEY in .env")

    es = Elasticsearch(cloud_id=cloud_id, api_key=api_key)

    # Resolve CSV path from project root
    root = Path(__file__).resolve().parent.parent
    csv_path = root / CSV_PATH if not os.path.isabs(CSV_PATH) else Path(CSV_PATH)
    if not csv_path.exists():
        raise SystemExit(f"CSV not found: {csv_path}")

    df = pd.read_csv(csv_path)
    # Normalize column names to lowercase (index expects name, address, dob)
    df.columns = [c.lower() for c in df.columns]
    if "dob" in df.columns and df["dob"].dtype == object:
        df["dob"] = pd.to_datetime(df["dob"], errors="coerce").dt.strftime("%Y-%m-%d")

    def gen():
        for _, row in df.iterrows():
            yield {"_index": INDEX_NAME, "_source": row.to_dict()}

    if es.indices.exists(index=INDEX_NAME):
        print(f"Deleting existing index {INDEX_NAME}...")
        es.indices.delete(index=INDEX_NAME)

    success, failed = helpers.bulk(es, gen(), raise_on_error=False, return_details=True)
    if failed:
        print("Some docs failed:", failed)
    print(f"Indexed {success} documents into {INDEX_NAME}")


if __name__ == "__main__":
    main()
