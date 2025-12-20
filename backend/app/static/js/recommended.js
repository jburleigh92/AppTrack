// AI-powered job recommendations page
// REQUIRES RESUME - uses intent analysis and skill matching

document.addEventListener('DOMContentLoaded', async () => {
    const loading = document.getElementById('loading');
    const jobsContainer = document.getElementById('jobs-container');
    const emptyState = document.getElementById('empty-state');

    // Check for active resume (REQUIRED for this page)
    try {
        const activeResume = await checkActiveResume();
        if (!activeResume) {
            showAlert('No active resume found. Please upload a resume first.', 'error');
            setTimeout(() => {
                window.location.href = '/';
            }, 2000);
            return;
        }

        setActiveResumeId(activeResume.id);
    } catch (error) {
        showAlert('Error checking resume: ' + error.message, 'error');
        setTimeout(() => {
            window.location.href = '/';
        }, 2000);
        return;
    }

    // Load AI-powered recommendations
    try {
        // ONLY call the recommended endpoint - AI matching with scoring
        const jobs = await apiFetch('/jobs/recommended');

        loading.classList.add('hide');

        if (!jobs || jobs.length === 0) {
            emptyState.classList.remove('hide');
            return;
        }

        // Display jobs WITH match scores and explanations
        jobsContainer.innerHTML = jobs.map(job => createRecommendedJobCard(job)).join('');
        setupJobCardListeners();

    } catch (error) {
        loading.classList.add('hide');
        showAlert('Error loading recommendations: ' + error.message, 'error');
    }
});

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
