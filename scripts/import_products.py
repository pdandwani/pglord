# import the products from hugging face - https://huggingface.co/datasets/Tvance100/items_full

import hashlib
import os

import psycopg
from dotenv import load_dotenv
from datasets import load_dataset

load_dotenv()

db_user = os.getenv("DB_USER")
db_pass = os.getenv("DB_PASS")
db_host = os.getenv("DB_HOST")
db_name = os.getenv("DB_NAME")
DATABASE_URL = f"postgresql://{db_user}:{db_pass}@{db_host}:5432/{db_name}"

LIMIT = 10_000
BATCH_SIZE = 500

INSERT_SQL = """
INSERT INTO products (
    external_id,
    title,
    category,
    price,
    weight,
    summary,
    search_vector
)
VALUES (
    %s, %s, %s, %s, %s, %s,
    to_tsvector(
        'english',
        coalesce(%s, '') || ' ' || coalesce(%s, '')
    )
)
ON CONFLICT (external_id) DO NOTHING
"""


def clean_text(value):
    if value is None:
        return None

    value = " ".join(str(value).split())
    return value or None


def clean_number(value):
    if value is None:
        return None

    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def make_external_id(title, category, price, summary):
    # The source dataset's displayed id field is null.
    # Use a deterministic fingerprint for this import.
    raw = "\x1f".join(str(value or "") for value in (title, category, price, summary))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def main():
    dataset = load_dataset(
        "Tvance100/items_full",
        split="train",
        streaming=True,
        token=os.getenv("HF_TOKEN"),
    )

    batch = []
    processed = 0
    skipped = 0
    inserted = 0

    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            for row in dataset:
                title = clean_text(row.get("title"))
                category = clean_text(row.get("category"))
                summary = clean_text(row.get("summary"))
                price = clean_number(row.get("price"))
                weight = clean_number(row.get("weight"))

                if not title or not summary:
                    skipped += 1
                    continue

                external_id = make_external_id(title, category, price, summary)

                batch.append(
                    (
                        external_id,
                        title,
                        category,
                        price,
                        weight,
                        summary,
                        title,
                        summary,
                    )
                )

                if len(batch) >= BATCH_SIZE:
                    cur.executemany(INSERT_SQL, batch)
                    inserted += cur.rowcount
                    conn.commit()

                    processed += len(batch)
                    print(
                        f"Processed: {processed}, "
                        f"inserted: {inserted}, skipped: {skipped}"
                    )
                    batch.clear()

                if processed + len(batch) >= LIMIT:
                    break

            if batch:
                cur.executemany(INSERT_SQL, batch)
                inserted += cur.rowcount
                conn.commit()
                processed += len(batch)

    print("\nImport complete")
    print(f"Processed: {processed}")
    print(f"Inserted: {inserted}")
    print(f"Skipped: {skipped}")


if __name__ == "__main__":
    main()
