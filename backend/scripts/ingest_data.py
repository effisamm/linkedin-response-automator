import csv
import json
import logging
import argparse
import chromadb
from sentence_transformers import SentenceTransformer
import sys
from pathlib import Path

# Add the project root to the Python path to allow importing 'app'
sys.path.append(str(Path(__file__).parent.parent))
from app.core.config import settings
from app.core.logging_config import setup_logging

# Setup JSON logging
setup_logging()
logger = logging.getLogger(__name__)

def process_csv_in_batches(csv_path: Path, batch_size: int = 100):
    """
    Generator that reads CSV and yields batches of conversations.
    Groups messages by conversation_id.
    """
    conversations = {}
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            conv_id = row['conversation_id']
            if conv_id not in conversations:
                conversations[conv_id] = []
            conversations[conv_id].append({
                'sender': row['sender'],
                'text': row['text']
            })
    
    # Yield conversations in batches
    conv_list = list(conversations.values())
    for i in range(0, len(conv_list), batch_size):
        yield conv_list[i:i + batch_size]

def ingest_data(client_id: str):
    """
    Main function to ingest data from CSV for a specific client.
    """
    logger.info("Starting data ingestion", extra={"client_id": client_id})

    # 1. Load client configurations
    with open(settings.CLIENT_CONFIG_PATH, 'r') as f:
        client_configs = json.load(f)
    
    client_config = client_configs.get(client_id)
    if not client_config:
        logger.error("Client ID not found", extra={"client_id": client_id})
        return

    collection_name = client_config['collection_name']

    # 2. Initialize ChromaDB client and collection
    settings.CHROMADB_PATH.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(settings.CHROMADB_PATH))
    collection = client.get_or_create_collection(name=collection_name)
    logger.info(
        "Connected to ChromaDB",
        extra={
            "client_id": client_id,
            "collection_name": collection_name
        }
    )

    # 3. Initialize the embedding model
    logger.info(
        "Loading embedding model",
        extra={
            "client_id": client_id,
            "model_name": settings.EMBEDDING_MODEL_NAME
        }
    )
    model = SentenceTransformer(settings.EMBEDDING_MODEL_NAME)
    logger.info("Embedding model loaded", extra={"client_id": client_id})

    # 4. Process CSV in batches
    batch_generator = process_csv_in_batches(settings.CSV_DATA_PATH)
    total_docs_processed = 0
    total_docs_added = 0

    for i, batch in enumerate(batch_generator):
        logger.info(
            "Processing batch",
            extra={
                "client_id": client_id,
                "batch_number": i + 1
            }
        )
        documents = [" ".join([msg['text'] for msg in convo]) for convo in batch]

        if not documents:
            continue

        ids = [f"convo_{total_docs_processed + j}" for j in range(len(documents))]
        total_docs_processed += len(documents)

        existing_ids = set(collection.get(ids=ids)['ids'])
        logger.info(
            "Found existing documents in batch",
            extra={
                "client_id": client_id,
                "batch_number": i + 1,
                "existing_count": len(existing_ids)
            }
        )

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
            logger.info(
                "Added new documents in batch",
                extra={
                    "client_id": client_id,
                    "batch_number": i + 1,
                    "new_docs_count": len(new_docs_to_add)
                }
            )
        
    logger.info(
        "Data ingestion complete",
        extra={
            "client_id": client_id,
            "total_processed": total_docs_processed,
            "total_added": total_docs_added,
            "collection_count": collection.count()
        }
    )

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest conversation data for a specific client.")
    parser.add_argument("--client-id", type=str, required=True, help="The ID of the client to ingest data for.")
    args = parser.parse_args()

    if not settings.CSV_DATA_PATH.exists():
        logger.error("CSV data file not found", extra={"csv_path": str(settings.CSV_DATA_PATH)})
    else:
        ingest_data(args.client_id)
