// Job recommendations screen logic

document.addEventListener('DOMContentLoaded', async () => {
    const loading = document.getElementById('loading');
    const jobsContainer = document.getElementById('jobs-container');
    const emptyState = document.getElementById('empty-state');

    // Check for active resume
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

    // Load jobs
    try {
        const jobs = await apiFetch('/jobs/discover');

        loading.classList.add('hide');

        if (!jobs || jobs.length === 0) {
            // Update empty state for Greenhouse-based discovery
            emptyState.innerHTML = `
                <h3>No Job Recommendations</h3>
                <p>Checked job boards from 10 tech companies, found 0 matching your skills.</p>
                <p>This means either:</p>
                <ul style="text-align: left; max-width: 500px; margin: 1rem auto;">
                    <li>No open positions match your resume skills</li>
                    <li>Your resume may need more skills listed</li>
                    <li>Try uploading a resume with more technical skills</li>
                </ul>
                <p style="margin-top: 1rem;"><small>Companies checked: Airbnb, Stripe, Shopify, Coinbase, Dropbox, Instacart, Robinhood, DoorDash, GitLab, Notion</small></p>
            `;

            emptyState.classList.remove('hide');
            return;
        }

        // Display jobs
        jobsContainer.innerHTML = jobs.map(job => createJobCard(job)).join('');

        // Add event listeners
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

    } catch (error) {
        loading.classList.add('hide');
        showAlert('Error loading jobs: ' + error.message, 'error');
    }
});

function createJobCard(job) {
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
