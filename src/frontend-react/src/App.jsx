import { useState, useEffect, useRef } from 'react';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '';

const CARD_IMAGES = [
  'https://lh3.googleusercontent.com/aida-public/AB6AXuDoXWyruGowERNl6OiGwuR5z1tZtsYlQy1Tnyq0wMh04wSRI2i71nuiWnqsCSjcIihypN2p8KpaVC5ETcs-M-1HRLiR_O0OjX2ZQ4TRiSJukeg5j_8UaxFeupixq56bx4oETKBQwH9ZPSf0nr6f8hTGsjR3PYjUtPybFdYYOkMQ30-L7qjNcWDXa9bzKBbHXZGw1xfVVW29lxnlYoBSxgriSPc0Ko_QpTMY-9vPs7dbKrL7QA36M5V2LYRWOYFQxGU3_x0Sc1DCq_TY',
  'https://lh3.googleusercontent.com/aida-public/AB6AXuCMFGdkV1RdnOphscmQj-L1AbIlSxm6DnHbDJwJzgnXk9az7YXntHfrlctSYmJ2B-zMrb6IH74SD7EH1pyc-0BVUXzDAaDIsMgLne44q4o3buSzGobIFdZ9TuoCG2T0_eGIWjOdphAwo8Vl95Ln56tEgZ4KoZyvkao-4aE3OVIaa-uYUUYpUFI315zzN56TzFuu9PAHhQi5eux_xiqzgkQ1seLhM0dWVE7B7gLT3dnB2pG0AfNjncfUGsbuoy3bF44_rpCPqQ-4bH_R',
  'https://lh3.googleusercontent.com/aida-public/AB6AXuDiWf2N_ouQISsgZyGKd7_S0ivrbLepAN4FQhGZT8SgSsbqFaJe88gYP8ybaoUd__JrXqx1UXL1UwcEwJmQk_cGyGPXLcAXJVqvjaI7XpIgfdN0_nsJBv1qFFgC-76181sD0YKLnkIGIXZ8oKETxP3KDtt46MIUGR5EwmbAwAUlslIRQmYgUTXuq2EdccB4B4z5J75FANUVympo3K_g4OLKlg4q8wF-AfJUSjrX-TlF_cjpforMw8Aa-aGa8x8O4uWhW5f0gZNL4NYp',
  'https://lh3.googleusercontent.com/aida-public/AB6AXuD0AxPxB63PfD2OHkM10d_E1wkg1_abURetBUL4rKNFXz-c5vjgxmvfY-qcVZiQ9ueIx8TOWwwIfR2k_zN07YEzULx8Auxqw07QZgsDqmYBn2XyTgn6h1EsYoYPIOL8Vmob9g-yQw_gLDixdzKPk5zI1lxYbZapQESVlclcUa_25nJISP4yHKggJKo0et_vT1PTlRZxZBpEfPFu1-PxKpZlNqFOg0dyYWzMUzh5DX06AAhw5epMGxSQfgoDCjWcdG7kgyp2sam56rZX',
  'https://lh3.googleusercontent.com/aida-public/AB6AXuCO1nOr5Ktv12qquKP334T4QSZ92x3oB6DcNkT3Gr5iJk7TccIl50YRxjkVr__RlSNA-0-1WXCFflawj39-8lSZ9VKznFtZaYvpcoOKFw3j4CrP6vTOccAoiPMcWYDOBrY-GMUCVtBJs3uaxrxqCzQcQcEo5hBPZQ5Ao1eWzUUL1FpbxtvgH8J2SNLWGRdU8hbtTxuN5pJhbrJahRIArSjOgJob2qmOk-gsqVbnPX-k5GNO9AM0c2UGb7l_n6NUi_bRHX5tgoBhW9E2',
];

const BUDGET_LABELS = {
  low: 'Low Budget',
  medium: 'Medium Budget',
  high: 'High Budget',
};

const loaderMessages = [
  'Retrieving restaurants...',
  'Filtering candidates...',
  'Calling Groq LLM...',
  'Structuring response...',
];

function App() {
  const [apiStatus, setApiStatus] = useState({ status: 'loading', text: 'Connecting...' });
  const [cities, setCities] = useState([]);
  const [panelState, setPanelState] = useState('welcome'); // welcome, loading, results, empty, error
  const [errorMessage, setErrorMessage] = useState('');
  const [emptyMessage, setEmptyMessage] = useState('');

  // Form States
  const [cuisine, setCuisine] = useState('');
  const [location, setLocation] = useState('');
  const [budget, setBudget] = useState('medium');
  const [minRating, setMinRating] = useState(4.0);
  const [additional, setAdditional] = useState('');

  // Search Results States
  const [summary, setSummary] = useState('');
  const [meta, setMeta] = useState({ candidatesConsidered: 0, filtersRelaxed: false, degradedMode: false });
  const [recommendations, setRecommendations] = useState([]);
  const [resolvedCity, setResolvedCity] = useState('');

  // Loader dynamic message
  const [loaderMessage, setLoaderMessage] = useState(loaderMessages[0]);
  const loaderIntervalRef = useRef(null);

  useEffect(() => {
    checkApiStatus();
    loadCities();
    return () => {
      if (loaderIntervalRef.current) clearInterval(loaderIntervalRef.current);
    };
  }, []);

  const checkApiStatus = async () => {
    try {
      const res = await fetch(`${API_BASE}/health`);
      if (res.ok) {
        const data = await res.json();
        if (data.ready) {
          setApiStatus({ status: 'online', text: `Online · ${data.llm_provider}` });
        } else {
          setApiStatus({ status: 'loading', text: 'Loading dataset...' });
          setTimeout(checkApiStatus, 5000);
        }
      } else {
        setApiStatus({ status: 'offline', text: 'Unavailable' });
        setTimeout(checkApiStatus, 5000);
      }
    } catch {
      setApiStatus({ status: 'offline', text: 'Connection error' });
      setTimeout(checkApiStatus, 5000);
    }
  };

  const loadCities = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/cities`);
      if (res.ok) {
        const data = await res.json();
        setCities(data.cities || []);
      }
    } catch (err) {
      console.error('Failed to load cities:', err);
    }
  };

  const startLoaderCycle = () => {
    if (loaderIntervalRef.current) clearInterval(loaderIntervalRef.current);
    let msgIndex = 0;
    setLoaderMessage(loaderMessages[0]);

    loaderIntervalRef.current = setInterval(() => {
      msgIndex = (msgIndex + 1) % loaderMessages.length;
      setLoaderMessage(loaderMessages[msgIndex]);
    }, 3000);
  };

  const handleSubmit = async (e) => {
    if (e) e.preventDefault();
    if (!location) {
      alert('Please select a neighborhood / city.');
      return;
    }

    setPanelState('loading');
    startLoaderCycle();

    try {
      const response = await fetch(`${API_BASE}/api/v1/recommendations`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          location,
          budget,
          cuisine: cuisine || null,
          min_rating: parseFloat(minRating),
          additional_preferences: additional || null,
        }),
      });

      if (loaderIntervalRef.current) clearInterval(loaderIntervalRef.current);

      if (response.ok) {
        const data = await response.json();
        renderResults(data);
      } else {
        const errorData = await response.json().catch(() => ({}));
        const msg = errorData?.detail?.message || errorData?.detail || 'An unexpected error occurred.';
        setErrorMessage(typeof msg === 'string' ? msg : JSON.stringify(msg));
        setPanelState('error');
      }
    } catch (err) {
      if (loaderIntervalRef.current) clearInterval(loaderIntervalRef.current);
      setErrorMessage('Network connection failed. Make sure the server is running.');
      setPanelState('error');
    }
  };

  const renderResults = (data) => {
    if (!data.recommendations || data.recommendations.length === 0) {
      const msg = data.meta?.empty_reason || 'Try broadening your cuisine or lowering the minimum rating.';
      setEmptyMessage(msg);
      setPanelState('empty');
      return;
    }

    setSummary(data.summary || 'Here are your recommended restaurant selections.');
    setResolvedCity(data.meta?.resolved_city || '');
    setMeta({
      candidatesConsidered: data.meta.candidates_considered,
      filtersRelaxed: data.meta.filters_relaxed,
      degradedMode: data.meta.degraded_mode,
    });
    setRecommendations(data.recommendations);
    setPanelState('results');
  };

  const handleRelaxFilters = () => {
    setMinRating(3.0);
    setCuisine('');
    setAdditional('');
    setBudget('medium');
    // We cannot immediately submit because state updates are asynchronous,
    // so we set the values and let the user trigger it or run it inside useEffect or custom triggers.
    // To make it instant, we can call the submit function using the new values directly:
    setPanelState('loading');
    startLoaderCycle();

    fetch(`${API_BASE}/api/v1/recommendations`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        location,
        budget: 'medium',
        cuisine: null,
        min_rating: 3.0,
        additional_preferences: null,
      }),
    })
      .then((res) => res.json())
      .then((data) => {
        if (loaderIntervalRef.current) clearInterval(loaderIntervalRef.current);
        renderResults(data);
      })
      .catch(() => {
        if (loaderIntervalRef.current) clearInterval(loaderIntervalRef.current);
        setErrorMessage('Network connection failed. Make sure the server is running.');
        setPanelState('error');
      });
  };

  const handleNewSearch = () => {
    setPanelState('welcome');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const estimateBudgetSign = (costStr) => {
    if (!costStr) return '₹₹';
    const match = costStr.match(/[\d,]+/);
    if (!match) return '₹₹';
    const amount = parseInt(match[0].replace(/,/g, ''), 10);
    if (amount < 400) return '₹';
    if (amount < 800) return '₹₹';
    if (amount < 1200) return '₹₹₹';
    return '₹₹₹₹';
  };

  return (
    <>
      <div className="glow-ambient"></div>
      <div className="glow-ambient-blue"></div>

      <header className="top-header">
        <div className="top-header-brand">Zomato AI</div>
        <nav className="top-header-nav">
          <a href="#" className="nav-link"><span className="material-symbols-outlined">explore</span> Discover</a>
          <a href="#" className="nav-link"><span className="material-symbols-outlined">history</span> History</a>
          <a href="#" className="nav-link nav-link-active" onClick={handleNewSearch}><span className="material-symbols-outlined filled">add_circle</span> New Search</a>
        </nav>
        <div className="top-header-actions">
          <div className="status-indicator" id="api-status">
            <span className={`status-dot status-${apiStatus.status}`}></span>
            <span className="status-text">{apiStatus.text}</span>
          </div>
        </div>
      </header>

      <aside className="sidebar">
        <div className="sidebar-inner">
          <div className="sidebar-brand">
            <div className="brand-icon"><span className="material-symbols-outlined filled">restaurant_menu</span></div>
            <div>
              <h2>Concierge</h2>
              <p>AI Culinary Planner</p>
            </div>
          </div>

          {(panelState === 'results' || panelState === 'loading') && (
            <div className="current-search" id="current-search">
              <h3>Current Search</h3>
              <ul id="search-summary-list">
                <li><span className="material-symbols-outlined filled">location_on</span><span>{location || '—'}</span></li>
                <li><span className="material-symbols-outlined">payments</span><span>{BUDGET_LABELS[budget] || '—'}</span></li>
                <li><span className="material-symbols-outlined">restaurant</span><span>{cuisine ? `${cuisine} Cuisine` : 'Any Cuisine'}</span></li>
                <li><span className="material-symbols-outlined filled">star</span><span>{minRating.toFixed(1)}+ Rating</span></li>
              </ul>
            </div>
          )}

          <nav className="sidebar-nav">
            <a href="#" className="sidebar-nav-item"><span className="material-symbols-outlined">home</span> Home</a>
            <a href="#" className="sidebar-nav-item active"><span className="material-symbols-outlined filled">explore</span> Discover</a>
            <a href="#" className="sidebar-nav-item"><span className="material-symbols-outlined">favorite</span> Favorites</a>
            <a href="#" className="sidebar-nav-item"><span className="material-symbols-outlined">history</span> History</a>
          </nav>

          <div className="sidebar-footer">
            <button type="button" className="btn-primary btn-block" id="btn-new-search" onClick={handleNewSearch}>
              <span className="material-symbols-outlined">add</span> New Search
            </button>
          </div>
        </div>
      </aside>

      <main className="main-canvas">
        {panelState === 'welcome' && (
          <section className="view-panel" id="welcome-state">
            <div className="welcome-grid">
              <div className="welcome-form-col">
                <div className="welcome-heading">
                  <h1>Your Personal<br /><span className="gradient-text">AI Culinary Assistant</span></h1>
                  <p><span className="material-symbols-outlined">auto_awesome</span> Tell me what you're craving.</p>
                </div>

                <form id="preferences-form" className="glass-card preference-form" onSubmit={handleSubmit}>
                  <div className="form-field">
                    <label htmlFor="cuisine">Craving / Vibe</label>
                    <div class="input-wrap">
                      <span className="material-symbols-outlined">search</span>
                      <input
                        type="text"
                        id="cuisine"
                        name="cuisine"
                        placeholder="e.g. Cozy Italian spot for a date night..."
                        autoComplete="off"
                        value={cuisine}
                        onChange={(e) => setCuisine(e.target.value)}
                      />
                    </div>
                  </div>

                  <div className="form-field">
                    <label htmlFor="location">Neighborhood</label>
                    <div className="input-wrap">
                      <span className="material-symbols-outlined">location_on</span>
                      <select
                        id="location"
                        name="location"
                        required
                        value={location}
                        onChange={(e) => setLocation(e.target.value)}
                      >
                        <option value="" disabled>Select a city...</option>
                        {cities.map((city) => (
                          <option key={city} value={city}>{city}</option>
                        ))}
                      </select>
                    </div>
                  </div>

                  <div className="form-row">
                    <div className="form-field">
                      <label>Budget</label>
                      <div className="budget-segment" id="budget-segment">
                        <label className="budget-option">
                          <input
                            type="radio"
                            name="budget"
                            value="low"
                            checked={budget === 'low'}
                            onChange={(e) => setBudget(e.target.value)}
                          />
                          <span>₹</span>
                        </label>
                        <label className="budget-option">
                          <input
                            type="radio"
                            name="budget"
                            value="medium"
                            checked={budget === 'medium'}
                            onChange={(e) => setBudget(e.target.value)}
                          />
                          <span>₹₹</span>
                        </label>
                        <label className="budget-option">
                          <input
                            type="radio"
                            name="budget"
                            value="high"
                            checked={budget === 'high'}
                            onChange={(e) => setBudget(e.target.value)}
                          />
                          <span>₹₹₹</span>
                        </label>
                      </div>
                    </div>
                    <div className="form-field">
                      <label htmlFor="min_rating">Min Rating</label>
                      <div className="rating-field">
                        <span id="rating-val" className="rating-pill">{minRating.toFixed(1)}+</span>
                        <input
                          type="range"
                          id="min_rating"
                          name="min_rating"
                          min="2.0"
                          max="5.0"
                          step="0.1"
                          value={minRating}
                          onChange={(e) => setMinRating(parseFloat(e.target.value))}
                        />
                      </div>
                    </div>
                  </div>

                  <div className="form-field">
                    <label htmlFor="additional_preferences">Special Instructions</label>
                    <div className="input-wrap textarea-wrap">
                      <textarea
                        id="additional_preferences"
                        name="additional_preferences"
                        rows="2"
                        placeholder="Dietary restrictions, seating preferences, etc."
                        value={additional}
                        onChange={(e) => setAdditional(e.target.value)}
                      ></textarea>
                    </div>
                  </div>

                  <button type="submit" className="btn-primary btn-block" id="btn-submit">
                    <span className="material-symbols-outlined filled">auto_awesome</span>
                    Find Recommendations
                  </button>
                </form>

                <p className="form-footnote">
                  <span className="material-symbols-outlined">info</span>
                  AI filters candidates → returns ranked picks with reasoning
                </p>
              </div>

              <div className="welcome-hero-col">
                <div className="hero-card">
                  <div className="hero-image"></div>
                  <div className="hero-overlay"></div>
                  <div className="hero-badge hero-badge-bottom">
                    <span className="material-symbols-outlined">verified</span>
                    TOP RATED MATCHES
                  </div>
                  <div className="hero-badge hero-badge-float">
                    <span className="material-symbols-outlined filled">restaurant</span>
                  </div>
                </div>
              </div>
            </div>
          </section>
        )}

        {panelState === 'loading' && (
          <section className="view-panel" id="loading-state">
            <div className="loading-center">
              <div className="orbit-loader">
                <div className="orbit-ring orbit-ring-1"></div>
                <div className="orbit-ring orbit-ring-2"></div>
                <div className="orbit-core">
                  <span className="material-symbols-outlined filled">restaurant_menu</span>
                </div>
              </div>
              <h2>Curating your experience</h2>
              <p className="loading-cycle" id="loader-title" style={{ opacity: 1 }}>{loaderMessage}</p>
              <p className="loading-sub" id="loader-subtitle">Our AI concierge is analyzing availability and assembling your culinary itinerary.</p>
              <div className="skeleton-preview">
                <div className="skeleton-card"><div className="skeleton-thumb"></div><div className="skeleton-lines"><div></div><div></div></div></div>
                <div className="skeleton-card"><div className="skeleton-thumb"></div><div className="skeleton-lines"><div></div><div></div></div></div>
              </div>
            </div>
          </section>
        )}

        {panelState === 'results' && (
          <section className="view-panel" id="results-content">
            <header className="results-header">
              <div className="results-title">
                <span className="material-symbols-outlined filled">auto_awesome</span>
                <h2>Curated for You</h2>
              </div>
              <div className="ai-explanation-block">
                <p id="results-summary">"{summary}"</p>
              </div>
              <div className="meta-chips">
                <div className="meta-chip"><span className="material-symbols-outlined">radar</span><span>Scanned: <strong>{meta.candidatesConsidered}</strong></span></div>
                <div className={`meta-chip ${meta.filtersRelaxed ? 'meta-chip-relaxed-yes' : ''}`} id="chip-relaxation">
                  <span className="material-symbols-outlined">tune</span><span>Relaxation: <strong>{meta.filtersRelaxed ? 'Yes' : 'No'}</strong></span>
                </div>
                <div className={`meta-chip ${meta.degradedMode ? 'meta-chip-mode-degraded' : ''}`} id="chip-mode">
                  <span className="material-symbols-outlined">memory</span><span>Mode: <strong>{meta.degradedMode ? 'Degraded' : 'Groq LLM'}</strong></span>
                </div>
              </div>
            </header>
            <div className="results-bento" id="recommendations-grid">
              {recommendations.map((rec, index) => {
                const isFeatured = rec.rank === 1;
                const rating = parseFloat(rec.rating);
                let ratingClass = 'rating-high';
                if (rating < 3.5) ratingClass = 'rating-low';
                else if (rating < 4.2) ratingClass = 'rating-mid';

                const cuisines = rec.cuisine ? rec.cuisine.split(',').map((c) => c.trim()).slice(0, 2) : [];
                const primaryCuisine = cuisines[0] || 'Multi-cuisine';
                const budgetSign = estimateBudgetSign(rec.estimated_cost);
                const imageUrl = CARD_IMAGES[index % CARD_IMAGES.length];

                return (
                  <article key={rec.id || index} className={isFeatured ? 'result-card featured' : 'result-card'}>
                    <div className="card-image-wrap">
                      <div className="card-image" style={{ backgroundImage: `url('${imageUrl}')` }}></div>
                      <div className="card-image-gradient"></div>
                      <div className="card-badges-top">
                        {isFeatured ? (
                          <div className="pick-badge"><span className="material-symbols-outlined filled">trophy</span> #1 Pick</div>
                        ) : (
                          <div className="rank-badge-sm">#{rec.rank}</div>
                        )}
                        <div className={`rating-badge ${ratingClass}`}>
                          {rating.toFixed(1)}
                          <span className="material-symbols-outlined filled" style={{ fontSize: '14px' }}>star</span>
                        </div>
                      </div>
                    </div>
                    <div className="card-body">
                      <h3>{rec.name}</h3>
                      <p className="card-location">{resolvedCity}</p>
                      {isFeatured ? (
                        <p className="card-explanation">{rec.explanation}</p>
                      ) : (
                        <div className="concierge-notes">{rec.explanation}</div>
                      )}
                      <div className="card-footer">
                        <div className="card-tags">
                          <span className="card-tag">{rec.estimated_cost || budgetSign}</span>
                          <span className="card-tag">{primaryCuisine}</span>
                        </div>
                        {isFeatured ? (
                          <button type="button" className="btn-primary btn-details" style={{ padding: '10px 16px' }}>
                            View Details <span className="material-symbols-outlined">arrow_forward</span>
                          </button>
                        ) : (
                          <button type="button" className="btn-details">Details</button>
                        )}
                      </div>
                    </div>
                  </article>
                );
              })}
            </div>
          </section>
        )}

        {panelState === 'empty' && (
          <section className="view-panel" id="empty-state">
            <div className="state-card">
              <div className="state-icon state-icon-empty"><span className="material-symbols-outlined filled">search</span></div>
              <h3>No Restaurants Found</h3>
              <div className="concierge-note">
                <p id="empty-message">{emptyMessage}</p>
              </div>
              <button type="button" className="btn-primary" id="btn-broaden-cta" onClick={handleRelaxFilters}>
                <span className="material-symbols-outlined">tune</span> Relax Filters
              </button>
            </div>
          </section>
        )}

        {panelState === 'error' && (
          <section className="view-panel" id="error-state">
            <div className="state-card state-card-error">
              <div className="state-icon state-icon-error"><span className="material-symbols-outlined filled">warning</span></div>
              <h3>Something went wrong</h3>
              <div className="concierge-note concierge-note-error">
                <p id="error-message">{errorMessage}</p>
              </div>
              <button type="button" className="btn-secondary" id="btn-retry" onClick={() => handleSubmit()}>
                <span className="material-symbols-outlined">refresh</span> Retry Search
              </button>
            </div>
          </section>
        )}
      </main>
    </>
  );
}

export default App;
