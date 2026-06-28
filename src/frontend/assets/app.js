// Zomato AI Culinary Concierge

document.addEventListener('DOMContentLoaded', () => {
    const API_BASE = window.location.origin;

    const statusIndicator = document.getElementById('api-status');
    const locationSelect = document.getElementById('location');
    const minRatingInput = document.getElementById('min_rating');
    const ratingValDisplay = document.getElementById('rating-val');
    const preferencesForm = document.getElementById('preferences-form');

    const welcomeState = document.getElementById('welcome-state');
    const loadingState = document.getElementById('loading-state');
    const resultsContent = document.getElementById('results-content');
    const emptyState = document.getElementById('empty-state');
    const errorState = document.getElementById('error-state');
    const currentSearch = document.getElementById('current-search');

    const loaderTitle = document.getElementById('loader-title');
    const loaderSubtitle = document.getElementById('loader-subtitle');

    const resultsSummary = document.getElementById('results-summary');
    const recommendationsGrid = document.getElementById('recommendations-grid');
    const metaCandidates = document.getElementById('meta-candidates');
    const metaRelaxed = document.getElementById('meta-relaxed');
    const metaMode = document.getElementById('meta-mode');
    const chipRelaxation = document.getElementById('chip-relaxation');
    const chipMode = document.getElementById('chip-mode');

    const summaryLocation = document.getElementById('summary-location');
    const summaryBudget = document.getElementById('summary-budget');
    const summaryCuisine = document.getElementById('summary-cuisine');
    const summaryRating = document.getElementById('summary-rating');

    const btnBroadenCta = document.getElementById('btn-broaden-cta');
    const btnRetry = document.getElementById('btn-retry');
    const btnNewSearch = document.getElementById('btn-new-search');

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

    const BUDGET_SIGNS = {
        low: '₹',
        medium: '₹₹',
        high: '₹₹₹',
    };

    let loaderInterval;
    const loaderMessages = [
        'Retrieving restaurants...',
        'Filtering candidates...',
        'Calling Groq LLM...',
        'Structuring response...',
    ];

    checkApiStatus();
    loadCities();

    minRatingInput.addEventListener('input', (e) => {
        ratingValDisplay.textContent = `${parseFloat(e.target.value).toFixed(1)}+`;
    });

    preferencesForm.addEventListener('submit', (e) => {
        e.preventDefault();
        triggerSearch();
    });

    btnBroadenCta.addEventListener('click', () => {
        minRatingInput.value = '3.0';
        ratingValDisplay.textContent = '3.0+';
        document.getElementById('cuisine').value = '';
        document.getElementById('additional_preferences').value = '';
        document.querySelector('input[name="budget"][value="medium"]').checked = true;
        triggerSearch();
    });

    btnRetry.addEventListener('click', triggerSearch);

    btnNewSearch.addEventListener('click', () => {
        currentSearch.classList.add('hidden');
        showPanelState('welcome');
        window.scrollTo({ top: 0, behavior: 'smooth' });
    });

    async function checkApiStatus() {
        try {
            const res = await fetch(`${API_BASE}/health`);
            if (res.ok) {
                const data = await res.json();
                if (data.ready) {
                    setApiStatus('online', `Online · ${data.llm_provider}`);
                } else {
                    setApiStatus('loading', 'Loading dataset...');
                    setTimeout(checkApiStatus, 5000);
                }
            } else {
                setApiStatus('offline', 'Unavailable');
                setTimeout(checkApiStatus, 5000);
            }
        } catch {
            setApiStatus('offline', 'Connection error');
            setTimeout(checkApiStatus, 5000);
        }
    }

    function setApiStatus(status, text) {
        const dot = statusIndicator.querySelector('.status-dot');
        const txt = statusIndicator.querySelector('.status-text');
        dot.className = 'status-dot';
        dot.classList.add(`status-${status}`);
        txt.textContent = text;
    }

    async function loadCities() {
        try {
            const res = await fetch(`${API_BASE}/api/v1/cities`);
            if (!res.ok) return;
            const data = await res.json();
            locationSelect.innerHTML = '<option value="" disabled selected>Select a city...</option>';
            data.cities.forEach((city) => {
                const option = document.createElement('option');
                option.value = city;
                option.textContent = city;
                locationSelect.appendChild(option);
            });
        } catch (err) {
            console.error('Failed to load cities:', err);
        }
    }

    function triggerSearch() {
        const formData = new FormData(preferencesForm);
        const requestData = {
            location: formData.get('location'),
            budget: formData.get('budget'),
            cuisine: formData.get('cuisine') || null,
            min_rating: parseFloat(formData.get('min_rating')),
            additional_preferences: formData.get('additional_preferences') || null,
        };

        if (!requestData.location) {
            alert('Please select a neighborhood / city.');
            return;
        }

        updateSearchSummary(requestData);
        performRecommendationRequest(requestData);
    }

    function updateSearchSummary(payload) {
        summaryLocation.textContent = payload.location;
        summaryBudget.textContent = BUDGET_LABELS[payload.budget] || payload.budget;
        summaryCuisine.textContent = payload.cuisine ? `${payload.cuisine} Cuisine` : 'Any Cuisine';
        summaryRating.textContent = `${payload.min_rating.toFixed(1)}+ Rating`;
        currentSearch.classList.remove('hidden');
    }

    async function performRecommendationRequest(payload) {
        showPanelState('loading');
        startLoaderCycle();

        try {
            const response = await fetch(`${API_BASE}/api/v1/recommendations`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });

            clearInterval(loaderInterval);

            if (response.ok) {
                renderResults(await response.json());
            } else {
                const errorData = await response.json().catch(() => ({}));
                const msg = errorData?.detail?.message || errorData?.detail || 'An unexpected error occurred.';
                showError(typeof msg === 'string' ? msg : JSON.stringify(msg));
            }
        } catch {
            clearInterval(loaderInterval);
            showError('Network connection failed. Make sure the server is running.');
        }
    }

    function renderResults(data) {
        if (!data.recommendations || data.recommendations.length === 0) {
            const msg = data.meta?.empty_reason || 'Try broadening your cuisine or lowering the minimum rating.';
            document.getElementById('empty-message').textContent = msg;
            showPanelState('empty');
            return;
        }

        const summaryText = data.summary || 'Here are your recommended restaurant selections.';
        resultsSummary.textContent = `"${summaryText}"`;

        metaCandidates.textContent = data.meta.candidates_considered;
        metaRelaxed.textContent = data.meta.filters_relaxed ? 'Yes' : 'No';
        chipRelaxation.className = data.meta.filters_relaxed
            ? 'meta-chip meta-chip-relaxed-yes'
            : 'meta-chip';

        if (data.meta.degraded_mode) {
            metaMode.textContent = 'Degraded';
            chipMode.className = 'meta-chip meta-chip-mode-degraded';
        } else {
            metaMode.textContent = 'Groq LLM';
            chipMode.className = 'meta-chip';
        }

        recommendationsGrid.innerHTML = '';

        data.recommendations.forEach((rec, index) => {
            const card = document.createElement('article');
            const isFeatured = rec.rank === 1;
            card.className = isFeatured ? 'result-card featured' : 'result-card';

            const rating = parseFloat(rec.rating);
            let ratingClass = 'rating-high';
            if (rating < 3.5) ratingClass = 'rating-low';
            else if (rating < 4.2) ratingClass = 'rating-mid';

            const cuisines = rec.cuisine ? rec.cuisine.split(',').map((c) => c.trim()).slice(0, 2) : [];
            const primaryCuisine = cuisines[0] || 'Multi-cuisine';
            const budgetSign = estimateBudgetSign(rec.estimated_cost);
            const imageUrl = CARD_IMAGES[index % CARD_IMAGES.length];

            const rankBadge = isFeatured
                ? `<div class="pick-badge"><span class="material-symbols-outlined filled">trophy</span> #1 Pick</div>`
                : `<div class="rank-badge-sm">#${rec.rank}</div>`;

            card.innerHTML = `
                <div class="card-image-wrap">
                    <div class="card-image" style="background-image:url('${imageUrl}')"></div>
                    <div class="card-image-gradient"></div>
                    <div class="card-badges-top">
                        ${rankBadge}
                        <div class="rating-badge ${ratingClass}">
                            ${rating.toFixed(1)}
                            <span class="material-symbols-outlined filled" style="font-size:14px">star</span>
                        </div>
                    </div>
                </div>
                <div class="card-body">
                    <h3>${escapeHtml(rec.name)}</h3>
                    <p class="card-location">${escapeHtml(data.meta?.resolved_city || '')}</p>
                    ${isFeatured
                        ? `<p class="card-explanation">${escapeHtml(rec.explanation)}</p>`
                        : `<div class="concierge-notes">${escapeHtml(rec.explanation)}</div>`
                    }
                    <div class="card-footer">
                        <div class="card-tags">
                            <span class="card-tag">${escapeHtml(rec.estimated_cost || budgetSign)}</span>
                            <span class="card-tag">${escapeHtml(primaryCuisine)}</span>
                        </div>
                        ${isFeatured
                            ? `<button type="button" class="btn-primary btn-details" style="padding:10px 16px">View Details <span class="material-symbols-outlined">arrow_forward</span></button>`
                            : `<button type="button" class="btn-details">Details</button>`
                        }
                    </div>
                </div>
            `;

            recommendationsGrid.appendChild(card);
        });

        showPanelState('results');
    }

    function estimateBudgetSign(costStr) {
        if (!costStr) return '₹₹';
        const match = costStr.match(/[\d,]+/);
        if (!match) return '₹₹';
        const amount = parseInt(match[0].replace(/,/g, ''), 10);
        if (amount < 400) return '₹';
        if (amount < 800) return '₹₹';
        if (amount < 1200) return '₹₹₹';
        return '₹₹₹₹';
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    function showPanelState(state) {
        welcomeState.classList.add('hidden');
        loadingState.classList.add('hidden');
        resultsContent.classList.add('hidden');
        emptyState.classList.add('hidden');
        errorState.classList.add('hidden');

        if (state === 'welcome') welcomeState.classList.remove('hidden');
        else if (state === 'loading') loadingState.classList.remove('hidden');
        else if (state === 'results') resultsContent.classList.remove('hidden');
        else if (state === 'empty') emptyState.classList.remove('hidden');
        else if (state === 'error') errorState.classList.remove('hidden');
    }

    function startLoaderCycle() {
        let msgIndex = 0;
        loaderTitle.textContent = loaderMessages[0];
        loaderTitle.style.opacity = '1';

        if (loaderInterval) clearInterval(loaderInterval);

        loaderInterval = setInterval(() => {
            msgIndex = (msgIndex + 1) % loaderMessages.length;
            loaderTitle.style.opacity = '0.3';
            setTimeout(() => {
                loaderTitle.textContent = loaderMessages[msgIndex];
                loaderTitle.style.opacity = '1';
            }, 300);
        }, 3000);
    }

    function showError(message) {
        document.getElementById('error-message').textContent = message;
        showPanelState('error');
    }
});





