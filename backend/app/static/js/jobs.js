// Universal job search screen logic

let hasActiveResume = false;
let activeResumeId = null;

document.addEventListener('DOMContentLoaded', async () => {
    const loading = document.getElementById('loading');
    const jobsContainer = document.getElementById('jobs-container');
    const emptyState = document.getElementById('empty-state');
    const searchForm = document.getElementById('search-form');
    const recommendedSection = document.getElementById('recommended-section');

    // Check for active resume (optional - doesn't block page)
    try {
        const activeResume = await checkActiveResume();
        if (activeResume) {
            hasActiveResume = true;
            activeResumeId = activeResume.id;
            setActiveResumeId(activeResume.id);

            // Show recommendations section if resume exists
            if (recommendedSection) {
                recommendedSection.classList.remove('hide');
            }
        }
    } catch (error) {
        // Resume check failed - that's OK, continue without it
        console.log('No active resume found - search-only mode enabled');
    }

    // Set up search form
    if (searchForm) {
        searchForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            await performSearch();
        });
    }

    // Load initial jobs (all jobs, no filters)
    await performSearch();
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

        // Display jobs
        jobsContainer.innerHTML = jobs.map(job => createJobCard(job, false)).join('');
        setupJobCardListeners();

    } catch (error) {
        loading.classList.add('hide');
        showAlert('Error loading jobs: ' + error.message, 'error');
    }
}

async function loadRecommendedJobs() {
    const recommendedContainer = document.getElementById('recommended-jobs-container');
    const recommendedLoading = document.getElementById('recommended-loading');

    if (!hasActiveResume) {
        return; // Can't load recommendations without resume
    }

    try {
        recommendedLoading?.classList.remove('hide');

        const jobs = await apiFetch('/jobs/recommended');

        recommendedLoading?.classList.add('hide');

        if (!jobs || jobs.length === 0) {
            if (recommendedContainer) {
                recommendedContainer.innerHTML = '<p>No AI-matched jobs found for your resume.</p>';
            }
            return;
        }

        // Display recommended jobs with match scores
        if (recommendedContainer) {
            recommendedContainer.innerHTML = jobs.slice(0, 5).map(job => createJobCard(job, true)).join('');
            setupJobCardListeners();
        }

    } catch (error) {
        recommendedLoading?.classList.add('hide');
        console.error('Error loading recommended jobs:', error);
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

function createJobCard(job, showMatchScore = false) {
    const missingSkills = job.missing_skills || [];
    const matchPercentage = job.match_percentage || 0;

    return `
        <div class="job-card">
            <div class="job-header">
                <div>
                    <h3 class="job-title">${job.title}</h3>
                    <p class="job-company">${job.company}</p>
                </div>
                ${showMatchScore ? `<span class="match-badge">${matchPercentage}%</span>` : ''}
            </div>

            <div class="job-meta">
                ${job.location ? `<p>📍 ${job.location}</p>` : ''}
                ${showMatchScore && job.match_reason ? `<p><strong>Why this match:</strong> ${job.match_reason}</p>` : ''}
            </div>

            ${showMatchScore && missingSkills.length > 0 ? `
                <details class="missing-skills">
                    <summary>Missing ${missingSkills.length} skill${missingSkills.length > 1 ? 's' : ''}</summary>
                    <div class="missing-skills-list">
                        ${missingSkills.map(skill => `<span class="missing-skill-tag">${skill}</span>`).join('')}
                    </div>
                </details>
            ` : ''}

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
