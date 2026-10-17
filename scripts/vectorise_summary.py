import json
import os

import psycopg
import requests
from dotenv import load_dotenv

load_dotenv()

db_user = os.getenv("DB_USER")
db_pass = os.getenv("DB_PASS")
db_host = os.getenv("DB_HOST")
db_name = os.getenv("DB_NAME")
DATABASE_URL = f"postgresql://{db_user}:{db_pass}@{db_host}:5432/{db_name}"
OLLAMA_HOST = os.getenv("OLLAMA_HOST")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL")
BATCH_SIZE = 100
EMBEDDING_DIMENSION = 768


def get_batch_summaries(last_id: int, limit: int, cur) -> list[tuple[int, str]]:
    """Keyset pagination: fetch the next rows with id > last_id that still need embeddings."""
    cur.execute(
        """
        SELECT id, summary FROM products
        WHERE description_embedding IS NULL
          AND id > %s
        ORDER BY id
        LIMIT %s;
        """,
        (last_id, limit),
    )
    results = cur.fetchall()
    print(f"--- Fetched batch after id {last_id} (size: {len(results)})")
    return results


def generate_embedding(summary: str) -> list[float] | None:
    if not summary:
        return None

    try:
        response = requests.post(
            f"{OLLAMA_HOST}/api/embeddings",
            json={"model": OLLAMA_MODEL, "prompt": summary},
            timeout=30,
        )
        response.raise_for_status()
        vector = response.json().get("embedding")

        if vector and len(vector) == EMBEDDING_DIMENSION:
            return vector

        print(
            f"Warning: bad embedding dimension ({len(vector) if vector else 'None'})."
        )
        return None

    except requests.exceptions.ConnectionError:
        print(f"Error: Could not connect to Ollama at {OLLAMA_HOST}.")
    except requests.exceptions.Timeout:
        print("Error: Ollama API request timed out.")
    except Exception as e:
        print(f"Unexpected error during embedding generation: {e}")
    return None


def process_batch(rows: list[tuple[int, str]]) -> list[tuple[int, list[float]]]:
    results = []
    for product_id, summary in rows:
        embedding = generate_embedding(summary)
        if embedding:
            results.append((product_id, embedding))
        else:
            print(f"Skipping product ID {product_id}: failed to generate embedding.")
    return results


def update_db_embeddings(cur, updates: list[tuple[int, list[float]]]):
    if not updates:
        return
    cur.executemany(
        "UPDATE products SET description_embedding = %s::vector WHERE id = %s;",
        [(json.dumps(emb), pid) for pid, emb in updates],
    )
    print(f"--- Updated {len(updates)} records.")


def main():
    print("Starting vectorization process...")
    try:
        with psycopg.connect(DATABASE_URL) as conn, conn.cursor() as cur:
            last_id = 0
            total = 0

            while True:
                rows = get_batch_summaries(last_id, BATCH_SIZE, cur)
                if not rows:
                    print("No more rows to process.")
                    break

                results = process_batch(rows)
                update_db_embeddings(cur, results)
                conn.commit()  # persist progress after every batch

                total += len(results)
                last_id = rows[-1][0]  # advance by id, not by offset

        print(f"\n--- Done. Embedded {total} records. ---")

    except psycopg.OperationalError as e:
        print(f"\nFATAL DATABASE CONNECTION ERROR: {e}")
    except Exception as e:
        print(f"\nFATAL UNEXPECTED ERROR: {e}")


if __name__ == "__main__":
    main()
