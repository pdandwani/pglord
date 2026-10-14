import os
from typing import Any

import psycopg
import requests
from dotenv import load_dotenv

# --- Configuration ---
# Load environment variables
load_dotenv()

db_user = os.getenv("DB_USER")
db_pass = os.getenv("DB_PASS")
db_host = os.getenv("DB_HOST")
db_name = os.getenv("DB_NAME")
DATABASE_URL = f"postgresql://{db_user}:{db_pass}@{db_host}:5432/{db_name}"


# --- Helper Functions ---
def get_db_connection() -> psycopg.Connection:
    """
    Establishes and returns a connection to the PostgreSQL database using the full URL.
    Raises psycopg.OperationalError if connection fails.
    """

    if not DATABASE_URL:
        raise psycopg.OperationalError("DATABASE_URL environment variable is not set.")
    try:
        # Use the pre-configured connection string
        conn = psycopg.connect(DATABASE_URL)
        return conn
    except psycopg.OperationalError as e:
        print(f"Database connection failed: {e}")
        raise psycopg.OperationalError(f"Database connection failed: {e}")


def generate_embedding(query_text: str) -> list[float] | None:
    """
    Calls the local Ollama API to generate a vector embedding for the given text.
    This function replicates the logic from scripts/vectorise_summary.py.
    """
    if not os.getenv("OLLAMA_HOST") or not os.getenv("OLLAMA_MODEL"):
        print("Error: OLLAMA_HOST or OLLAMA_MODEL environment variables are not set.")
        return None

    api_url = f"{os.getenv('OLLAMA_HOST')}/api/embeddings"
    payload = {
        "model": os.getenv("OLLAMA_MODEL"),
        "prompt": query_text,
        "options": {"preferred_model_output_format": "json"},
    }

    try:
        response = requests.post(api_url, json=payload, timeout=30)
        response.raise_for_status()
        result = response.json()
        vector = result.get("embedding")

        if vector:
            return vector
        else:
            print("Warning: Ollama response did not contain an 'embedding' field.")
            return None

    except requests.exceptions.ConnectionError:
        print(f"Error: Could not connect to Ollama at {os.getenv('OLLAMA_HOST')}.")
        return None
    except requests.exceptions.Timeout:
        print("Error: Ollama API request timed out.")
        return None
    except Exception as e:
        print(f"An unexpected error occurred during embedding generation: {e}")
        return None


# --- Search Methods ---


def fuzzy_search(query: str, limit: int = 5) -> list[dict[str, Any]]:
    """
    Searches product titles using PostgreSQL pg_trgm similarity.

    The query is treated as a phrase for comparison.
    """
    conn = None
    results = []

    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            sql = f"""
            SELECT
                id,
                title,
                summary,
                similarity(title, %s) AS similarity
            FROM products
            WHERE title %% %s
            ORDER BY similarity DESC
            LIMIT {limit};
            """
            # Pass the term twice: once for the similarity function and once for the % operator.
            cur.execute(sql, (query, query))

            for row in cur.fetchall():
                product_id, title, summary, similarity = row
                results.append(
                    {
                        "id": product_id,
                        "title": title,
                        "summary": summary,
                        "similarity": similarity,
                    }
                )
        return results

    except psycopg.OperationalError as e:
        print(f"Fuzzy Search DB Error: {e}")
        return []
    finally:
        if conn:
            conn.close()


def fts_search(query: str, limit: int = 5) -> list[dict[str, Any]]:
    """
    Performs a full-text search on the 'search_vector' tsvector column.

    Uses ts_rank to order results by relevance.
    """
    conn = None
    results = []

    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            sql = f"""
            SELECT
                id,
                title,
                summary,
                ts_rank(search_vector, websearch_to_tsquery('english', %s)) AS rank
            FROM products
            WHERE search_vector @@ websearch_to_tsquery('english', %s)
            ORDER BY rank DESC
            LIMIT {limit};
            """
            cur.execute(sql, (query, query))

            for row in cur.fetchall():
                product_id, title, summary, rank = row
                results.append(
                    {"id": product_id, "title": title, "summary": summary, "rank": rank}
                )
        return results

    except psycopg.OperationalError as e:
        print(f"FTS Search DB Error: {e}")
        return []
    finally:
        if conn:
            conn.close()


def vector_search(query: str, limit: int = 5) -> list[dict[str, Any]]:
    """
    Generates a vector embedding for the query and performs similarity search
    using the desc_embedding column and pgvector distance operators.
    """
    # 1. Generate embedding
    query_embedding = generate_embedding(query)

    vector_str = "[" + ",".join(str(value) for value in query_embedding) + "]"

    if query_embedding is None:
        print("Vector Search failed: Could not generate embedding.")
        return []

    conn = None
    results = []
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # 2. Execute vector similarity search
            sql = """
            SELECT
                id,
                title,
                summary,
                description_embedding <=> %s::vector AS distance
            FROM products
            ORDER BY distance ASC NULLS LAST
            LIMIT %s;
            """
            # We pass the generated vector as a parameter
            cur.execute(sql, (vector_str, limit))

            for row in cur.fetchall():
                product_id, title, summary, distance = row
                results.append(
                    {
                        "id": product_id,
                        "title": title,
                        "summary": summary,
                        "distance": distance,
                    }
                )

        return results

    except psycopg.OperationalError as e:
        print(f"Vector Search DB Error: {e}")
        return []
    finally:
        if conn:
            conn.close()
