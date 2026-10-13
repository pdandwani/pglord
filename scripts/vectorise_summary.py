import os
import requests
import psycopg
import json
from dotenv import load_dotenv
from typing import List, Tuple, Dict

# Load environment variables from .env file
load_dotenv()

# Configuration
db_user = os.getenv("DB_USER")
db_pass = os.getenv("DB_PASS")
db_host = os.getenv("DB_HOST")
db_name = os.getenv("DB_NAME")
DATABASE_URL = f"postgresql://{db_user}:{db_pass}@{db_host}:5432/{db_name}"
OLLAMA_HOST = os.getenv("OLLAMA_HOST")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL")
BATCH_SIZE = 100
EMBEDDING_DIMENSION = 768


def get_batch_summaries(
    offset: int, limit: int, db_cursor: psycopg.cursor
) -> List[Tuple[int, str]]:
    """
    Fetches product IDs and summaries in a paginated manner.
    Returns a list of (product_id, summary_text).
    """
    query = """
    SELECT id, summary FROM products
    ORDER BY id
    LIMIT %s OFFSET %s;
    """
    db_cursor.execute(query, (limit, offset))
    results = db_cursor.fetchall()

    print(f"--- Fetched batch starting at offset {offset} (size: {len(results)})")
    return results


def generate_embedding(summary: str) -> List[float] | None:
    """
    Calls the local Ollama API to generate a vector embedding for the given text.
    """
    if not summary:
        return None

    api_url = f"{OLLAMA_HOST}/api/embeddings"
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": summary,
        "options": {"preferred_model_output_format": "json"},
    }

    try:
        response = requests.post(api_url, json=payload, timeout=30)
        response.raise_for_status()

        result = response.json()
        vector = result.get("embedding")

        if vector and len(vector) == EMBEDDING_DIMENSION:
            return vector
        else:
            print(
                f"Warning: Received vector of incorrect dimension ({len(vector)}) for a summary."
            )
            return None

    except requests.exceptions.ConnectionError:
        print(
            f"Error: Could not connect to Ollama at {OLLAMA_HOST}. Check server status."
        )
        return None
    except requests.exceptions.Timeout:
        print("Error: Ollama API request timed out.")
        return None
    except Exception as e:
        print(f"An unexpected error occurred during embedding generation: {e}")
        return None


def process_batch(
    summaries_and_ids: List[Tuple[int, str]],
) -> List[Tuple[int, List[float]]]:
    """
    Generates embeddings for a batch of summaries.
    Returns a list of (product_id, embedding_vector).
    """
    results = []
    for product_id, summary in summaries_and_ids:
        embedding = generate_embedding(summary)
        if embedding:
            results.append((product_id, embedding))
        else:
            print(f"Skipping product ID {product_id}: Failed to generate embedding.")
    return results


def update_db_embeddings(
    db_conn: psycopg.Connection,
    db_cursor: psycopg.cursor,
    updates: List[Tuple[int, List[float]]],
):
    """
    Updates the 'description_embedding' column for a batch of products.
    NOTE: This assumes the database supports vector storage compatible with JSON encoding for demonstration.
    """
    print(f"--- Starting database update for {len(updates)} records.")

    for product_id, embedding in updates:
        # We are using JSON encoding as a placeholder for the vector type due to the limitations
        # of a generic SQL interface. In a real application, the psycopg client would handle
        # the native vector type (e.g., using a UDT or specific library function).
        embedding_json = json.dumps(embedding)

        sql = """
        UPDATE products
        SET description_embedding = %s
        WHERE id = %s;
        """
        db_cursor.execute(sql, (embedding_json, product_id))

    print(f"--- Finished database update for batch.")


def main():
    """
    Main function to orchestrate the vectorization process.
    """
    print("Starting vectorization process...")

    try:
        # 1. Establish DB Connection
        # We must assume DATABASE_URL is correctly set by .env
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                offset = 0

                while True:
                    # 2. Fetch summaries
                    summaries_and_ids = get_batch_summaries(offset, BATCH_SIZE, cur)

                    if not summaries_and_ids:
                        print("Reached the end of the products table.")
                        break

                    # 3. Generate embeddings
                    vectorized_results = process_batch(summaries_and_ids)

                    # 4. Update database
                    update_db_embeddings(conn, cur, vectorized_results)

                    # Update offset for the next page
                    offset += len(summaries_and_ids)

        print("\n--- Vectorization process completed successfully. ---")

    except psycopg.OperationalError as e:
        print(f"\nFATAL DATABASE CONNECTION ERROR: {e}")
        print(
            "Please ensure the database is running and the DATABASE_URL in your .env file is correct."
        )
    except Exception as e:
        print(f"\nFATAL UNEXPECTED ERROR during main execution: {e}")


if __name__ == "__main__":
    main()
