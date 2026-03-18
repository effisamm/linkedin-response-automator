import csv
import json
import argparse
import chromadb
from sentence_transformers import SentenceTransformer
import sys
from pathlib import Path

# Add the project root to the Python path to allow importing 'app'
sys.path.append(str(Path(__file__).parent.parent))
from app.core.config import settings

def process_csv_in_batches(csv_path: Path, batch_size: int = 100):
    # ... (implementation remains the same)
    pass

def ingest_data(client_id: str):
    """
    Main function to ingest data from CSV for a specific client.
    """
    print(f"--- Starting Data Ingestion for client: {client_id} ---")

    # 1. Load client configurations
    with open(settings.CLIENT_CONFIG_PATH, 'r') as f:
        client_configs = json.load(f)
    
    client_config = client_configs.get(client_id)
    if not client_config:
        print(f"Error: Client ID '{client_id}' not found in client_configs.json")
        return

    collection_name = client_config['collection_name']

    # 2. Initialize ChromaDB client and collection
    settings.CHROMADB_PATH.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(settings.CHROMADB_PATH))
    collection = client.get_or_create_collection(name=collection_name)
    print(f"Connected to ChromaDB. Collection: '{collection_name}'")

    # 3. Initialize the embedding model
    print(f"Loading embedding model: '{settings.EMBEDDING_MODEL_NAME}'...")
    model = SentenceTransformer(settings.EMBEDDING_MODEL_NAME)
    print("Model loaded.")

    # 4. Process CSV in batches
    batch_generator = process_csv_in_batches(settings.CSV_DATA_PATH)
    total_docs_processed = 0
    total_docs_added = 0

    for i, batch in enumerate(batch_generator):
        print(f"Processing batch {i + 1}...")
        documents = [" ".join([msg['text'] for msg in convo]) for convo in batch]

        if not documents:
            continue

        ids = [f"convo_{total_docs_processed + j}" for j in range(len(documents))]
        total_docs_processed += len(documents)

        existing_ids = set(collection.get(ids=ids)['ids'])
        print(f"Found {len(existing_ids)} existing documents in this batch. Skipping them.")

        new_docs_to_add = []
        new_ids_to_add = []
        new_embeddings_to_add = []

        if len(documents) > len(existing_ids):
            embeddings = model.encode(documents)
            for j, doc_id in enumerate(ids):
                if doc_id not in existing_ids:
                    new_ids_to_add.append(doc_id)
                    new_docs_to_add.append(documents[j])
                    new_embeddings_to_add.append(embeddings[j])

        if new_docs_to_add:
            collection.add(
                embeddings=new_embeddings_to_add,
                documents=new_docs_to_add,
                ids=new_ids_to_add
            )
            total_docs_added += len(new_docs_to_add)
            print(f"Added {len(new_docs_to_add)} new documents in batch {i + 1}.")
        
    print("\n--- Data Ingestion Complete ---")
    print(f"Total documents processed: {total_docs_processed}")
    print(f"Total new documents added: {total_docs_added}")
    print(f"Collection '{collection_name}' now contains {collection.count()} documents.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest conversation data for a specific client.")
    parser.add_argument("--client-id", type=str, required=True, help="The ID of the client to ingest data for.")
    args = parser.parse_args()

    if not settings.CSV_DATA_PATH.exists():
        print(f"Error: CSV data file not found at {settings.CSV_DATA_PATH}")
    else:
        ingest_data(args.client_id)
