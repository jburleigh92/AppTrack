// Universal job search screen logic
// SEARCH ONLY - no resume dependencies, no AI matching

document.addEventListener('DOMContentLoaded', async () => {
    const loading = document.getElementById('loading');
    const jobsContainer = document.getElementById('jobs-container');
    const emptyState = document.getElementById('empty-state');
    const searchForm = document.getElementById('search-form');

    // Hide loading, show initial empty state
    loading.classList.add('hide');
    emptyState.classList.remove('hide');

    // Set up search form - ONLY way to trigger search
    if (searchForm) {
        searchForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            await performSearch();
        });
    }
});

async function performSearch() {
    const loading = document.getElementById('loading');
    const jobsContainer = document.getElementById('jobs-container');
    const emptyState = document.getElementById('empty-state');

    // Get search parameters
    const keyword = document.getElementById('search-keyword')?.value || '';
    const location = document.getElementById('search-location')?.value || '';
    const company = document.getElementById('search-company')?.value || '';

    // Build query string
    const params = new URLSearchParams();
    if (keyword) params.append('keyword', keyword);
    if (location) params.append('location', location);
    if (company) params.append('company', company);

    const queryString = params.toString() ? `?${params.toString()}` : '';

    try {
        loading.classList.remove('hide');
        jobsContainer.innerHTML = '';
        emptyState.classList.add('hide');

        // ONLY call search endpoint - no AI, no matching, no resume
        const jobs = await apiFetch(`/jobs/search${queryString}`);

        loading.classList.add('hide');

        if (!jobs || jobs.length === 0) {
            emptyState.innerHTML = `
                <h3>No Jobs Found</h3>
                <p>No jobs match your search criteria.</p>
                <p>Try:</p>
                <ul style="text-align: left; max-width: 500px; margin: 1rem auto;">
                    <li>Using different keywords (e.g., "engineer", "developer", "backend")</li>
                    <li>Broadening your location search</li>
                    <li>Removing some filters</li>
                </ul>
                <p style="margin-top: 1rem;"><small>Searching across: Airbnb, Stripe, Shopify, Coinbase, Dropbox, Instacart, Robinhood, DoorDash, GitLab, Notion</small></p>
            `;
            emptyState.classList.remove('hide');
            return;
        }

        // Display jobs WITHOUT match scores
        jobsContainer.innerHTML = jobs.map(job => createJobCard(job)).join('');
        setupJobCardListeners();

    } catch (error) {
        loading.classList.add('hide');
        showAlert('Error loading jobs: ' + error.message, 'error');
    }
}

function setupJobCardListeners() {
    document.querySelectorAll('.apply-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const url = e.target.dataset.url;
            if (url) {
                window.open(url, '_blank');
            }
        });
    });

    document.querySelectorAll('.applied-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const company = e.target.dataset.company;
            const title = e.target.dataset.title;
            const url = e.target.dataset.url;

            // Navigate to applications page with pre-filled data
            const params = new URLSearchParams({
                company: company,
                title: title,
                url: url || '',
            });
            window.location.href = `/applications?${params.toString()}`;
        });
    });
}

function createJobCard(job) {
    // Simple job card - NO match scores, NO AI explanations
    return `
        <div class="job-card">
            <div class="job-header">
                <div>
                    <h3 class="job-title">${job.title}</h3>
                    <p class="job-company">${job.company}</p>
                </div>
            </div>

            <div class="job-meta">
                ${job.location ? `<p>📍 ${job.location}</p>` : ''}
            </div>

            <div class="job-actions">
                <button class="btn btn-primary apply-btn" data-url="${job.url || ''}">
                    Apply on Company Site
                </button>
                <button class="btn btn-secondary applied-btn"
                        data-company="${job.company}"
                        data-title="${job.title}"
                        data-url="${job.url || ''}">
                    I Applied
                </button>
            </div>
        </div>
    `;
}
