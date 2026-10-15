import asyncio
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Request, status
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .search_service import fts_search, fuzzy_search, vector_search

# --- Setup ---
# Initialize the FastAPI application
app = FastAPI(
    title="PGLord API",
    description="A minimal API service built to interface with existing data processing pipelines.",
    version="0.1.0",
)

BASE_DIR = Path(__file__).resolve().parent

# Mount static files (CSS and JS)
# Assumes the structure app/static/ is correct
app.mount(
    "/static",
    StaticFiles(directory=BASE_DIR / "static"),
    name="static",
)

# Initialize Jinja2 templates
# Assumes the template directory app/templates/ is correct
templates = Jinja2Templates(directory=BASE_DIR / "templates")


@app.get("/health", tags=["System"])
def health_check():
    """
    Health check endpoint.
    Used to confirm the FastAPI service is running correctly.
    """
    return {"status": "ok", "service": "FastAPI", "version": "0.1.0"}


@app.get("/", tags=["UI"])
async def read_root(request: Request):
    return templates.TemplateResponse(request=request, name="index.html", context={})


@app.get("/search", tags=["Search"])
async def search_products(
    query: str = Query(
        ..., description="The search term used for all three search methods."
    )
):
    """
    Executes parallel fuzzy, full-text, and vector searches on products.

    Args:
        query: The search term used for all three search methods.

    Returns:
        A dictionary containing the original query and the results from all methods.

    Raises:
        HTTPException: If the search query is missing or blank.
    """

    if not query or not query.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Query must not be blank.",
        )

    print(f"Received search query: {query}. Initiating concurrent search.")

    # Run the searches concurrently in separate threads to prevent blocking the event loop
    # as the underlying search functions use blocking psycopg calls.
    fuzzy_task = asyncio.to_thread(fuzzy_search, query)
    fts_task = asyncio.to_thread(fts_search, query)
    vector_task = asyncio.to_thread(vector_search, query)

    fuzzy_results, fts_results, vector_results = await asyncio.gather(
        fuzzy_task, fts_task, vector_task
    )

    # Consolidate results into the required structure
    return {
        "query": query,
        "results": {
            "fuzzy": fuzzy_results,
            "fts": fts_results,
            "vector": vector_results,
        },
    }
