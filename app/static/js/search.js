/**
 * @fileoverview Frontend search interaction logic for pglord.
 *
 * This script handles user input, makes concurrent API requests to the FastAPI backend,
 * displays loading states, handles errors, and dynamically renders the search results
 * using vanilla DOM APIs, ensuring responsive behavior and data safety.
 */

document.addEventListener('DOMContentLoaded', () => {
  const searchInput = document.getElementById('search-input');
  const searchButton = document.getElementById('search-button');
  const resetButton = document.getElementById('reset-button');
  const resultsContainer = document.getElementById('search-results-grid');
  const loadingIndicator = document.getElementById('loading-indicator');
  const errorMessage = document.getElementById('error-message');
  const resultsStatusBar = document.getElementById('results-status-bar');

  let isSearching = false;
  let currentQuery = '';

  /**
   * Resets the UI state to its initial state.
   */
  function resetUI() {
    searchInput.value = '';
    resultsContainer.innerHTML = '';
    resultsStatusBar.innerHTML = '<p>Enter a query to begin searching.</p>';
    loadingIndicator.classList.add('loading-hidden');
    errorMessage.classList.add('hidden');
    searchButton.disabled = false;
    resetButton.disabled = true;
    resultsStatusBar.style.borderBottom = '2px dashed var(--color-border)';
    resultsStatusBar.innerHTML = '<p>Enter a query to begin searching.</p>';
    currentQuery = '';
  }

  /**
   * Displays a custom error message to the user.
   * @param {string} message - The message to display.
   */
  function displayError(message) {
    errorMessage.textContent = message;
    errorMessage.classList.remove('hidden');
    loadingIndicator.classList.add('loading-hidden');
    searchButton.disabled = false;
    resultsStatusBar.innerHTML = `<p class="error-text" style="display:block;">Error: ${message}</p>`;
  }

  /**
   * Updates the UI for the search state (loading/disabled).
   * @param {boolean} loading - True if a search is in progress.
   * @param {string} query - The query being searched.
   */
  function updateLoadingState(loading, query) {
    isSearching = loading;
    if (isSearching) {
      searchButton.disabled = true;
      resetButton.disabled = true;
      loadingIndicator.classList.remove('loading-hidden');
      errorMessage.classList.add('hidden');
      // resultsStatusBar.textContent = `Searching for "${query}"...`;
    } else {
      searchButton.disabled = false;
      loadingIndicator.classList.add('loading-hidden');
      if (query.length > 0) {
        resetButton.disabled = false;
      }
    }
  }

  /**
   * Renders the entire set of results into the respective panels.
   * @param {object} searchResults - The response data from the /search endpoint.
   * @param {string} query - The original query.
   */
  function renderSearchResults(searchResults, query) {
    const { fuzzy, fts, vector, hybrid } = searchResults.results;
    const fuzzyCount = fuzzy?.length || 0;
    const ftsCount = fts?.length || 0;
    const vectorCount = vector?.length || 0;
    const hybridCount = hybrid?.length || 0;

    // Process results for each panel and build the entire panel HTML string
    const buildPanelHtml = (panelName, results) => {
      let resultsListHtml = '';
      if (results.length === 0) {
        resultsListHtml =
          '<p class="result-card" style="text-align: center; padding: 20px; color: #666;">No products found matching this query.</p>';
      } else {
        results.forEach((result) => {
          // Determine score detail HTML based on the search method
          let scoreDetailHtml = '';
          let scoreValue = null;

          if (panelName === 'fuzzy' && typeof result.similarity === 'number') {
            scoreValue = result.similarity;
            scoreDetailHtml = `Fuzzy Similarity: ${(scoreValue * 100).toFixed(2)}%`;
          } else if (panelName === 'fts' && typeof result.rank === 'number') {
            scoreValue = result.rank;
            scoreDetailHtml = `FTS Rank: ${scoreValue.toFixed(4)}`;
          } else if (panelName === 'vector' && typeof result.distance === 'number') {
            scoreValue = result.distance;
            scoreDetailHtml = `Vector Distance: ${scoreValue.toFixed(4)}`;
          } else if (panelName === 'hybrid' && typeof result.hybrid_score === 'number') {
            scoreValue = result.hybrid_score;
            scoreDetailHtml = `RRF Score: ${scoreValue.toFixed(4)}`;
          } else {
            scoreDetailHtml = 'Metric N/A';
          }

          const resultCardHtml = `
                        <div class="result-card">
                            <div class="result-card-title">${result.title}</div>
                            <div class="result-card-summary">${result.summary}</div>
                            <div class="score-detail">${scoreDetailHtml}</div>
                            <div class="results-meta">
                                <span class="result-id">ID: ${result.id}</span>
                            </div>
                        </div>
                    `;
          resultsListHtml += resultCardHtml;
        });
      }

      return `
                <div class="result-panel ${panelName}">
                    <div class="panel-header">
                        <h2>${panelName === 'fuzzy' ? 'pg_trgm' : panelName === 'fts' ? 'PostgreSQL FTS' : panelName === 'vector' ? 'pgvector' : 'Hybrid Search'}</h2>
                        <div class="score-display">${panelName.toUpperCase()}</div>
                    </div>
                    <div class="results-list">${resultsListHtml}</div>
                    <div class="results-meta" style="border-top: none;">
                        <span class="total-count">${results.length} Results</span>
                    </div>
                </div>
            `;
    };

    const fuzzyHtml = buildPanelHtml('fuzzy', fuzzy);
    const ftsHtml = buildPanelHtml('fts', fts);
    const vectorHtml = buildPanelHtml('vector', vector);
    const hybridHtml = buildPanelHtml('hybrid', hybrid);

    // Assemble the final grid HTML
    resultsContainer.innerHTML = `
            <div class="result-panel fuzzy">${fuzzyHtml}</div>
            <div class="result-panel fts">${ftsHtml}</div>
            <div class="result-panel vector">${vectorHtml}</div>
            ${hybrid ? `<div class="result-panel hybrid">${hybridHtml}</div>` : ''}
        `;

    const totalCount = fuzzyCount + ftsCount + vectorCount + hybridCount;
    resultsStatusBar.innerHTML = `<p>Successfully searched for "${query}". Results rendered in ${totalCount} total items.</p>`;
  }

  /**
   * Primary search submission handler.
   * @param {Event} event - The DOM event.
   */
  async function handleSearch(event) {
    const query = searchInput.value.trim();

    if (query.length === 0) {
      event.preventDefault();
      return;
    }

    // Prevent consecutive requests (though the UI handles disabling)
    if (isSearching) {
      console.warn('Search already in progress.');
      return;
    }

    // 1. Update UI for loading state
    updateLoadingState(true, query);
    // resultsStatusBar.textContent = "Sending requests to backend...";

    try {
      // 2. Execute the search logic
      // NOTE: The /search endpoint uses query parameters, so no body is sent.
      const response = await fetch('/search?query=' + encodeURIComponent(query));

      if (!response.ok) {
        const errorBody = await response.text();
        // Try to parse JSON error message if available
        try {
          const errorJson = JSON.parse(errorBody);
          throw new Error(errorJson.detail || `HTTP error! Status: ${response.status}`);
        } catch (e) {
          throw new Error(
            `HTTP error! Status: ${response.status}. Body: ${errorBody.substring(0, 100)}`,
          );
        }
      }

      const data = await response.json();

      // 3. Render the results
      renderSearchResults(data, query);
    } catch (error) {
      console.error('Search failed:', error);
      displayError(error.message);
    } finally {
      // 4. Reset UI state
      updateLoadingState(false, query);
      currentQuery = query;
    }
  }

  // --- Event Listeners ---

  // Search on button click
  searchButton.addEventListener('click', handleSearch);

  // Search on Enter keypress in input field
  searchInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleSearch(e);
    }
  });

  // Reset button handler
  resetButton.addEventListener('click', () => {
    resetUI();
  });

  // Initialize on load
  resetUI();
});
