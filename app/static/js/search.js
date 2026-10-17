document.addEventListener('DOMContentLoaded', () => {
  const searchInput = document.getElementById('search-input');
  const searchButton = document.getElementById('search-button');
  const resetButton = document.getElementById('reset-button');
  const loadingIndicator = document.getElementById('loading-indicator');
  const errorMessage = document.getElementById('error-message');
  const resultsStatusBar = document.getElementById('results-status-bar');
  const resultsTable = document.getElementById('search-results-table');
  const tbody = resultsTable.querySelector('tbody');

  let isSearching = false;

  const methodConfig = {
    fuzzy: { label: 'Similarity', field: 'similarity', cellClass: 'fuzzy-cell', digits: 2 },
    fts: { label: 'FTS rank', field: 'rank', cellClass: 'fts-cell', digits: 4 },
    vector: { label: 'Distance', field: 'distance', cellClass: 'vector-cell', digits: 4 },
    hybrid: { label: 'Hybrid score', field: 'hybrid_score', cellClass: 'hybrid-cell', digits: 4 }
  };

  function setStatus(message) {
    resultsStatusBar.replaceChildren();
    const paragraph = document.createElement('p');
    paragraph.textContent = message;
    resultsStatusBar.appendChild(paragraph);
  }

  function resetUI() {
    searchInput.value = '';
    tbody.replaceChildren();
    resultsStatusBar.style.borderBottom = '1px dashed var(--color-border)';
    setStatus('Enter a query to begin searching.');
    loadingIndicator.classList.add('loading-hidden');
    errorMessage.classList.add('hidden');
    errorMessage.textContent = '';
    searchButton.disabled = false;
    resetButton.disabled = true;
    resultsTable.classList.add('hidden');
    isSearching = false;
    searchInput.focus();
  }

  function displayError(message) {
    errorMessage.textContent = message;
    errorMessage.classList.remove('hidden');
    loadingIndicator.classList.add('loading-hidden');
    resultsTable.classList.add('hidden');
    setStatus('Search failed. Please try again.');
    searchButton.disabled = false;
    resetButton.disabled = searchInput.value.trim().length === 0;
  }

  function updateLoadingState(loading, query) {
    isSearching = loading;
    searchButton.disabled = loading;
    resetButton.disabled = loading || query.length === 0;
    loadingIndicator.classList.toggle('loading-hidden', !loading);
    if (loading) {
      errorMessage.classList.add('hidden');
      errorMessage.textContent = '';
      setStatus(`Searching for "${query}"...`);
    }
  }

  function formatScore(result, config) {
    const value = result[config.field];
    if (typeof value !== 'number' || !Number.isFinite(value)) return 'N/A';
    return value.toFixed(config.digits);
  }

  function createTextElement(tagName, className, text) {
    const element = document.createElement(tagName);
    element.className = className;
    element.textContent = text == null || text === '' ? '—' : String(text);
    return element;
  }

  function createResultCell(method, result) {
    const cell = document.createElement('td');
    cell.className = `method-cell ${methodConfig[method].cellClass}`;

    if (!result) {
      cell.classList.add('empty-result');
      cell.textContent = '—';
      cell.setAttribute('aria-label', 'No result at this rank');
      return cell;
    }

    const config = methodConfig[method];
    const record = document.createElement('div');
    record.className = 'result-record';

    record.appendChild(createTextElement('span', 'result-id', `ID: ${result.id ?? '—'}`));
    record.appendChild(createTextElement('div', 'result-title', result.title ?? 'Untitled'));
    record.appendChild(createTextElement('div', 'result-summary', result.summary ?? 'No summary available'));

    const scoreLabel =
      method === 'vector' ? `${config.label}: ${formatScore(result, config)} (lower is better)` : `${config.label}: ${formatScore(result, config)}`;
    record.appendChild(createTextElement('span', 'result-score', scoreLabel));
    cell.appendChild(record);
    return cell;
  }

  function renderSearchResults(results) {
    const methods = ['fuzzy', 'fts', 'vector', 'hybrid'];
    const normalizedResults = {};

    for (const method of methods) {
      if (!Array.isArray(results[method])) {
        throw new Error(`Invalid API response: "${method}" must be an array`);
      }
      normalizedResults[method] = results[method];
    }

    const maxRank = Math.max(0, ...methods.map(method => normalizedResults[method].length));
    tbody.replaceChildren();

    if (maxRank === 0) {
      resultsTable.classList.add('hidden');
      setStatus('No results found for this query.');
      return;
    }

    for (let rank = 0; rank < maxRank; rank += 1) {
      const row = document.createElement('tr');

      const rankCell = document.createElement('td');
      rankCell.className = 'rank-cell';
      rankCell.textContent = String(rank + 1);
      row.appendChild(rankCell);

      for (const method of methods) {
        row.appendChild(createResultCell(method, normalizedResults[method][rank]));
      }
      tbody.appendChild(row);
    }

    resultsTable.classList.remove('hidden');
    resultsStatusBar.style.borderBottom = '1px solid var(--color-border)';
    setStatus(`Showing results for "${searchInput.value.trim()}" — ${maxRank} rank${maxRank === 1 ? '' : 's'} across four search methods.`);
  }

  async function handleSearch(event) {
    event.preventDefault();
    if (isSearching) return;

    const query = searchInput.value.trim();
    if (!query) {
      searchInput.focus();
      return;
    }

    updateLoadingState(true, query);

    try {
      const response = await fetch(`/search?query=${encodeURIComponent(query)}`);
      if (!response.ok) {
        throw new Error(`Search request failed with status ${response.status}`);
      }

      const payload = await response.json();
      if (!payload || !payload.results) {
        throw new Error('Invalid API response');
      }

      renderSearchResults(payload.results);
      errorMessage.classList.add('hidden');
      errorMessage.textContent = '';
    } catch (error) {
      console.error('Search failed:', error);
      displayError('An error occurred while searching. Please try again.');
    } finally {
      updateLoadingState(false, query);
    }
  }

  searchButton.addEventListener('click', handleSearch);
  searchInput.addEventListener('keydown', event => {
    if (event.key === 'Enter') handleSearch(event);
  });
  resetButton.addEventListener('click', resetUI);
});
