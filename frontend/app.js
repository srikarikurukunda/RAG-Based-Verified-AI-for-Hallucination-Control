const API = 'http://localhost:5000';

// ── Scrape ────────────────────────────────────────────────────────────────────

async function scrapeUrl() {
  const url        = document.getElementById('urlInput').value.trim();
  const statusEl   = document.getElementById('scrapeStatus');
  const scrapeBtn  = document.getElementById('scrapeBtn');

  if (!url) {
    showScrapeStatus('Please enter a URL.', 'error');
    return;
  }

  scrapeBtn.disabled = true;
  scrapeBtn.textContent = 'Scraping...';
  showScrapeStatus('Fetching page content...', 'info');

  try {
    const res  = await fetch(`${API}/scrape`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url })
    });
    const data = await res.json();

    if (!res.ok) {
      showScrapeStatus('Error: ' + data.error, 'error');
    } else if (data.status === 'already_exists') {
      showScrapeStatus(data.message, 'info');
    } else {
      showScrapeStatus(
        `Scraped ${data.chars.toLocaleString()} characters. Index is rebuilding...`,
        'success'
      );
      document.getElementById('urlInput').value = '';
      // Poll until index rebuild is done
      pollRebuildStatus();
    }
  } catch (err) {
    showScrapeStatus('Could not connect to server. Is Flask running?', 'error');
  } finally {
    scrapeBtn.disabled = false;
    scrapeBtn.textContent = 'Scrape';
  }
}

function showScrapeStatus(msg, type) {
  const el = document.getElementById('scrapeStatus');
  el.textContent = msg;
  el.className = 'status-msg ' + type;
  el.classList.remove('hidden');
}

async function pollRebuildStatus() {
  const interval = setInterval(async () => {
    try {
      const res  = await fetch(`${API}/scrape/status`);
      const data = await res.json();
      if (!data.rebuilding) {
        clearInterval(interval);
        if (data.last_result === 'success') {
          showScrapeStatus('Knowledge base updated. You can now ask questions about this page.', 'success');
        } else {
          showScrapeStatus('Index rebuild finished with: ' + data.last_result, 'error');
        }
      }
    } catch {
      clearInterval(interval);
    }
  }, 2000);
}


// ── Ask ───────────────────────────────────────────────────────────────────────

async function askQuestion() {
  const question  = document.getElementById('questionInput').value.trim();
  const loading   = document.getElementById('loading');
  const result    = document.getElementById('result');
  const errorEl   = document.getElementById('error');
  const badge     = document.getElementById('badge');
  const answer    = document.getElementById('answer');
  const sourcesEl = document.getElementById('sources');

  // Reset
  result.classList.add('hidden');
  errorEl.classList.add('hidden');

  if (!question) {
    errorEl.textContent = 'Please enter a question.';
    errorEl.classList.remove('hidden');
    return;
  }

  loading.classList.remove('hidden');
  document.getElementById('askBtn').disabled = true;

  try {
    const res  = await fetch(`${API}/ask`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question })
    });
    const data = await res.json();
    loading.classList.add('hidden');
    document.getElementById('askBtn').disabled = false;

    if (!res.ok) {
      errorEl.textContent = 'Error: ' + (data.details?.join(', ') || data.error);
      errorEl.classList.remove('hidden');
      return;
    }

    // Badge
    if (data.source === 'cache') {
      badge.textContent = 'From cache';
      badge.className = 'badge badge-cache';
    } else {
      badge.textContent = 'RAG · Grounded answer';
      badge.className = 'badge badge-rag';
    }

    answer.textContent = data.answer;

    // Sources
    sourcesEl.innerHTML = '';
    if (data.sources && data.sources.length) {
      const label = document.createElement('span');
      label.textContent = 'Sources: ';
      sourcesEl.appendChild(label);
      data.sources.forEach((src, i) => {
        const a = document.createElement('a');
        a.href = src;
        a.target = '_blank';
        a.rel = 'noopener';
        a.textContent = src;
        sourcesEl.appendChild(a);
        if (i < data.sources.length - 1) {
          sourcesEl.appendChild(document.createTextNode(', '));
        }
      });
      sourcesEl.classList.remove('hidden');
    } else {
      sourcesEl.classList.add('hidden');
    }

    result.classList.remove('hidden');

  } catch (err) {
    loading.classList.add('hidden');
    document.getElementById('askBtn').disabled = false;
    errorEl.textContent = 'Could not connect to server. Is Flask running?';
    errorEl.classList.remove('hidden');
  }
}


// ── Keyboard shortcuts ────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('questionInput')
    .addEventListener('keypress', e => { if (e.key === 'Enter') askQuestion(); });

  document.getElementById('urlInput')
    .addEventListener('keypress', e => { if (e.key === 'Enter') scrapeUrl(); });
});
