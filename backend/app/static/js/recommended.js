// AI-powered job recommendations page
// REQUIRES RESUME - uses intent analysis and skill matching
// USER MUST CLICK BUTTON TO RUN - no auto-execution

document.addEventListener('DOMContentLoaded', async () => {
    const runButton = document.getElementById('run-recommendations-btn');
    const loading = document.getElementById('loading');
    const jobsContainer = document.getElementById('jobs-container');
    const emptyState = document.getElementById('empty-state');
    const initialState = document.getElementById('initial-state');

    // Check for active resume (REQUIRED for this page)
    let hasResume = false;
    try {
        const activeResume = await checkActiveResume();
        if (!activeResume) {
            showAlert('No active resume found. Please upload a resume first.', 'error');
            setTimeout(() => {
                window.location.href = '/';
            }, 2000);
            return;
        }

        hasResume = true;
        setActiveResumeId(activeResume.id);

        // Show initial state with button
        if (initialState) {
            initialState.classList.remove('hide');
        }
    } catch (error) {
        showAlert('Error checking resume: ' + error.message, 'error');
        setTimeout(() => {
            window.location.href = '/';
        }, 2000);
        return;
    }

    // Wire button click handler - ONLY way to trigger AI
    if (runButton && hasResume) {
        runButton.addEventListener('click', async () => {
            await runRecommendations();
        });
    }
});

async function runRecommendations() {
    const runButton = document.getElementById('run-recommendations-btn');
    const loading = document.getElementById('loading');
    const jobsContainer = document.getElementById('jobs-container');
    const emptyState = document.getElementById('empty-state');
    const initialState = document.getElementById('initial-state');

    try {
        // Hide initial state, show loading
        if (initialState) {
            initialState.classList.add('hide');
        }
        loading.classList.remove('hide');

        // Disable button during execution
        if (runButton) {
            runButton.disabled = true;
            runButton.textContent = 'Analyzing Resume...';
        }

        // ONLY NOW call the AI endpoint - user explicitly clicked
        const jobs = await apiFetch('/jobs/recommended');

        loading.classList.add('hide');

        if (!jobs || jobs.length === 0) {
            emptyState.classList.remove('hide');
            if (runButton) {
                runButton.disabled = false;
                runButton.textContent = 'Run AI Recommendations';
            }
            return;
        }

        // Display jobs WITH match scores and explanations
        jobsContainer.innerHTML = jobs.map(job => createRecommendedJobCard(job)).join('');
        setupJobCardListeners();

        // Update button
        if (runButton) {
            runButton.disabled = false;
            runButton.textContent = 'Refresh Recommendations';
        }

    } catch (error) {
        loading.classList.add('hide');
        showAlert('Error loading recommendations: ' + error.message, 'error');

        // Re-enable button on error
        if (runButton) {
            runButton.disabled = false;
            runButton.textContent = 'Run AI Recommendations';
        }

        // Show initial state again
        if (initialState) {
            initialState.classList.remove('hide');
        }
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

function createRecommendedJobCard(job) {
    // AI-powered job card - SHOWS match scores and explanations
    const missingSkills = job.missing_skills || [];
    const matchPercentage = job.match_percentage || 0;

    return `
        <div class="job-card">
            <div class="job-header">
                <div>
                    <h3 class="job-title">${job.title}</h3>
                    <p class="job-company">${job.company}</p>
                </div>
                <span class="match-badge">${matchPercentage}%</span>
            </div>

            <div class="job-meta">
                ${job.location ? `<p>📍 ${job.location}</p>` : ''}
                ${job.match_reason ? `<p><strong>Why this match:</strong> ${job.match_reason}</p>` : ''}
            </div>

            ${missingSkills.length > 0 ? `
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
