# 🐘 pglord

**The Lord of the Queries.**

A PostgreSQL search playground exploring fuzzy matching, full-text search, vector search, and hybrid retrieval. The goal is to understand how different search techniques find and rank relevant results, and how their performance and relevance compare.

## 🚧 Project Status

Early development.

- [x] Import product data from Hugging Face
- [x] Store product records in PostgreSQL
- [x] Generate local text embeddings
- [ ] Implement trigram similarity using `pg_trgm`
- [ ] Implement PostgreSQL full-text search (FTS)
- [ ] Implement semantic search using `pgvector`
- [ ] Implement hybrid search
- [ ] Build a UI to compare the top 5 results from each search method
- [ ] Benchmark relevance and performance
- [ ] Dockerize the application

## 🎯 Goals

- Understand the differences between lexical, fuzzy, and semantic search.
- Explore PostgreSQL extensions for modern search workloads.
- Compare search relevance and query performance on a shared dataset.
- Experiment with PostgreSQL indexing and query optimization.
- Evaluate hybrid retrieval strategies combining keyword and vector search.

## 🛠️ Tech Stack

- **Database:** PostgreSQL
- **Fuzzy search:** `pg_trgm`
- **Full-text search:** PostgreSQL FTS (`tsvector` / `tsquery`)
- **Vector search:** `pgvector`
- **Embedding generation:** Ollama with a local embedding model (nomic-embed-text)
- **Data ingestion:** Python
- **Environment:** Python virtual environment (`.venv`)

## 📦 Dataset

pglord uses the [`Tvance100/items_full`](https://huggingface.co/datasets/Tvance100/items_full) dataset from Hugging Face.

The dataset contains product metadata and descriptive text, including:

| Field | Description |
|---|---|
| `title` | Product title |
| `category` | Product category |
| `price` | Product price |
| `weight` | Product weight |
| `summary` | Product summary and descriptive text |
| `full` | Additional source field |
| `prompt` | Additional source field |
| `id` | Source dataset identifier |

The product summaries are used as the initial input for generating vector embeddings.

See the dataset card for its provenance, licensing, and usage conditions before redistributing the data.

## 📁 Project Structure

```text
pglord/
├── scripts/
│   ├── import_products.py
│   └── vectorise_summary.py
├── .gitignore
├── README.md
└── requirements.txt
```

The structure will evolve as search implementations, benchmarking tools, and the UI are added.

## ⚙️ Prerequisites

- Python 3
- PostgreSQL with `pg_trgm` and `pgvector` available
- Ollama
- A compatible local embedding model

## 🚀 Getting Started

### 1. Clone the repository

```bash
git clone <repository-url>
cd pglord
```

### 2. Create a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

On Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure PostgreSQL

Create a database for pglord and enable the required extensions:

```sql
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS vector;
```

Create the `products` table using the project's database schema.

### 5. Configure database connectivity

Provide the database connection details expected by the scripts through environment variables or a local, untracked `.env` file.

Example connection string:

```text
postgresql://<user>:<password>@localhost:5432/pglord
```

Update the database name and credentials to match your environment.

### 6. Import product data

```bash
python scripts/import_products.py
```

This script imports the selected product records from Hugging Face into PostgreSQL.

### 7. Generate vector embeddings

Ensure Ollama is running and your configured embedding model is available locally.

```bash
python scripts/vectorise_summary.py
```

This script generates embeddings from product summaries and stores them in PostgreSQL for subsequent vector search experiments.

Refer to each script for its current configuration requirements.

## 🔍 Planned Search Experiments

pglord will compare several approaches using the same dataset and user queries.

| Search method | Purpose |
|---|---|
| Exact matching | Establish a baseline |
| Trigram similarity | Handle misspellings and similar strings |
| Full-text search | Match and rank relevant keywords |
| Vector search | Retrieve semantically similar descriptions |
| Hybrid search | Combine lexical and semantic rankings |

The planned UI will accept a search query and display the top 5 results from each implemented search method.

## 📊 Evaluation

The benchmark will explore:

- Query latency, including p50 and p95.
- Precision@5 and Recall@5.
- Index size and index creation time.
- Query plans using `EXPLAIN (ANALYZE, BUFFERS)`.
- Trade-offs between relevance, latency, and storage.
- Exact versus approximate nearest-neighbor search.

A manually judged set of representative queries will be used to evaluate relevance. The objective is to understand which search approach works best for different query types rather than assume one method is universally superior.

## 🗺️ Roadmap

1. Complete data ingestion and embedding generation.
2. Implement and test each search strategy independently.
3. Add hybrid search and ranking comparisons.
4. Build the search comparison UI.
5. Benchmark performance at different dataset sizes.
6. Containerize the application with Docker Compose.

## 📜 License

NA