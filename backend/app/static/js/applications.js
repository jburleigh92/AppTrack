// Applications dashboard screen logic

let applications = [];

document.addEventListener('DOMContentLoaded', async () => {
    const form = document.getElementById('capture-form');
    const loading = document.getElementById('loading');
    const container = document.getElementById('applications-container');
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
    }

    // Check for pre-filled data from URL params
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.has('company')) {
        document.getElementById('company').value = urlParams.get('company');
    }
    if (urlParams.has('title')) {
        document.getElementById('job-title').value = urlParams.get('title');
    }
    if (urlParams.has('url')) {
        document.getElementById('job-url').value = urlParams.get('url');
    }

    // Handle form submission
    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const formData = {
            company_name: document.getElementById('company').value,
            job_title: document.getElementById('job-title').value,
            job_posting_url: document.getElementById('job-url').value || undefined,
            notes: document.getElementById('notes').value || undefined,
        };

        try {
            await apiFetch('/applications/capture', {
                method: 'POST',
                body: JSON.stringify(formData),
            });

            showAlert('Application captured successfully!', 'success');
            form.reset();

            // Reload applications
            await loadApplications();
        } catch (error) {
            showAlert('Error capturing application: ' + error.message, 'error');
        }
    });

    // Load initial applications
    await loadApplications();

    async function loadApplications() {
        try {
            applications = await apiFetch('/applications');

            loading.classList.add('hide');

            if (!applications || applications.length === 0) {
                container.classList.add('hide');
                emptyState.classList.remove('hide');
                return;
            }

            container.classList.remove('hide');
            emptyState.classList.add('hide');

            renderApplications();
        } catch (error) {
            loading.classList.add('hide');
            showAlert('Error loading applications: ' + error.message, 'error');
        }
    }

    function renderApplications() {
        const tbody = document.getElementById('applications-list');
        tbody.innerHTML = applications.map(app => createApplicationRow(app)).join('');

        // Add event listeners for rows
        document.querySelectorAll('.app-row').forEach(row => {
            row.addEventListener('click', (e) => {
                // Don't toggle if clicking on status select
                if (e.target.tagName === 'SELECT') {
                    return;
                }

                const appId = row.dataset.appId;
                const detailsRow = document.getElementById(`details-${appId}`);

                if (detailsRow) {
                    const detailsCell = detailsRow.querySelector('.app-details');
                    detailsCell.classList.toggle('visible');

                    // Load timeline and analysis if not already loaded
                    if (detailsCell.classList.contains('visible') && !detailsCell.dataset.loaded) {
                        loadApplicationDetails(appId);
                        detailsCell.dataset.loaded = 'true';
                    }
                }
            });
        });

        // Add event listeners for status selects
        document.querySelectorAll('.status-select').forEach(select => {
            select.addEventListener('change', async (e) => {
                e.stopPropagation();
                const appId = select.dataset.appId;
                const newStatus = select.value;

                try {
                    await apiFetch(`/applications/${appId}`, {
                        method: 'PATCH',
                        body: JSON.stringify({ status: newStatus }),
                    });

                    showAlert('Status updated successfully!', 'success');

                    // Reload applications to get updated data
                    await loadApplications();
                } catch (error) {
                    showAlert('Error updating status: ' + error.message, 'error');
                    // Reload to revert the select
                    await loadApplications();
                }
            });
        });

        // Add event listeners for delete buttons
        document.querySelectorAll('.delete-btn').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                e.stopPropagation();
                const appId = btn.dataset.appId;

                // Find the application to get company name
                const app = applications.find(a => a.id === appId);
                const company = app ? app.company_name : 'this application';

                // Confirm deletion
                if (!confirm(`Are you sure you want to delete ${company}?`)) {
                    return;
                }

                try {
                    btn.disabled = true;
                    btn.textContent = 'Deleting...';

                    await apiFetch(`/applications/${appId}`, {
                        method: 'DELETE',
                    });

                    showAlert('Application deleted successfully!', 'success');

                    // Reload applications
                    await loadApplications();
                } catch (error) {
                    showAlert('Error deleting application: ' + error.message, 'error');
                    btn.disabled = false;
                    btn.textContent = 'Delete';
                }
            });
        });
    }

    async function loadApplicationDetails(appId) {
        const detailsCell = document.getElementById(`details-${appId}`).querySelector('.app-details');

        try {
            // Load timeline
            const timeline = await apiFetch(`/applications/${appId}/timeline`);
            renderTimeline(detailsCell, timeline.events || []);

            // Try to load analysis
            try {
                const analysis = await apiFetch(`/analysis/${appId}/analysis`);
                renderAnalysis(detailsCell, analysis, appId);
            } catch (error) {
                // Analysis not found, show run button
                renderAnalysisButton(detailsCell, appId);
            }
        } catch (error) {
            detailsCell.innerHTML += `<p class="alert alert-error">Error loading details: ${error.message}</p>`;
        }
    }

    function renderTimeline(container, events) {
        const timelineSection = document.createElement('div');
        timelineSection.className = 'detail-section';
        timelineSection.innerHTML = '<h4>Timeline</h4>';

        if (events.length === 0) {
            timelineSection.innerHTML += '<p>No timeline events</p>';
        } else {
            const timelineHtml = events.map(event => `
                <div class="timeline-event">
                    <div class="timeline-event-type">${formatEventType(event.event_type)}</div>
                    <div class="timeline-event-time">${formatDate(event.occurred_at)}</div>
                    ${event.event_data ? `<div class="timeline-event-data">${formatEventData(event.event_data)}</div>` : ''}
                </div>
            `).join('');
            timelineSection.innerHTML += timelineHtml;
        }

        container.appendChild(timelineSection);
    }

    function renderAnalysis(container, analysis, appId) {
        const analysisSection = document.createElement('div');
        analysisSection.className = 'detail-section';
        analysisSection.innerHTML = `
            <h4>Analysis</h4>
            <div class="analysis-section">
                <div class="match-score">${analysis.match_score}% Match</div>

                ${analysis.qualifications_met && analysis.qualifications_met.length > 0 ? `
                    <div class="qualifications">
                        <h5>✅ Qualifications Met (${analysis.qualifications_met.length})</h5>
                        <ul>
                            ${analysis.qualifications_met.map(q => `<li>${q}</li>`).join('')}
                        </ul>
                    </div>
                ` : ''}

                ${analysis.qualifications_missing && analysis.qualifications_missing.length > 0 ? `
                    <div class="qualifications">
                        <h5>❌ Qualifications Missing (${analysis.qualifications_missing.length})</h5>
                        <ul>
                            ${analysis.qualifications_missing.map(q => `<li>${q}</li>`).join('')}
                        </ul>
                    </div>
                ` : ''}

                ${analysis.suggestions && analysis.suggestions.length > 0 ? `
                    <div class="qualifications">
                        <h5>💡 Suggestions</h5>
                        <ul>
                            ${analysis.suggestions.map(s => `<li>${s}</li>`).join('')}
                        </ul>
                    </div>
                ` : ''}
            </div>
        `;

        container.appendChild(analysisSection);
    }

    function renderAnalysisButton(container, appId) {
        const analysisSection = document.createElement('div');
        analysisSection.className = 'detail-section';
        analysisSection.id = `analysis-section-${appId}`;
        analysisSection.innerHTML = `
            <h4>Analysis</h4>
            <p>No analysis run yet.</p>
            <button class="btn btn-primary btn-small run-analysis-btn" data-app-id="${appId}">
                Run Analysis
            </button>
        `;

        container.appendChild(analysisSection);

        // Add event listener for run analysis button
        const runBtn = analysisSection.querySelector('.run-analysis-btn');
        runBtn.addEventListener('click', async (e) => {
            e.stopPropagation();
            const appId = runBtn.dataset.appId;

            try {
                runBtn.disabled = true;
                runBtn.textContent = 'Running Analysis...';

                await apiFetch(`/analysis/${appId}/analysis/run`, {
                    method: 'POST',
                });

                showAlert('Analysis started! Refresh the page in a few seconds to see results.', 'info');

                // Update button text
                runBtn.textContent = 'Analysis In Progress...';
            } catch (error) {
                showAlert('Error running analysis: ' + error.message, 'error');
                runBtn.disabled = false;
                runBtn.textContent = 'Run Analysis';
            }
        });
    }

    function formatEventType(type) {
        const typeMap = {
            'application_captured': 'Application Captured',
            'status_changed': 'Status Changed',
            'note_added': 'Note Added',
            'email_received': 'Email Received',
        };
        return typeMap[type] || type;
    }

    function formatEventData(data) {
        if (typeof data === 'string') {
            return data;
        }
        if (typeof data === 'object') {
            return Object.entries(data)
                .map(([key, value]) => `<strong>${key}:</strong> ${value}`)
                .join('<br>');
        }
        return JSON.stringify(data);
    }
});

function createApplicationRow(app) {
    return `
        <tr class="app-row" data-app-id="${app.id}">
            <td>${app.company_name}</td>
            <td>${app.job_title}</td>
            <td>
                <select class="status-select" data-app-id="${app.id}" onclick="event.stopPropagation()">
                    <option value="applied" ${app.status === 'applied' ? 'selected' : ''}>Applied</option>
                    <option value="screening" ${app.status === 'screening' ? 'selected' : ''}>Screening</option>
                    <option value="interview" ${app.status === 'interview' ? 'selected' : ''}>Interview</option>
                    <option value="offer" ${app.status === 'offer' ? 'selected' : ''}>Offer</option>
                    <option value="rejected" ${app.status === 'rejected' ? 'selected' : ''}>Rejected</option>
                    <option value="withdrawn" ${app.status === 'withdrawn' ? 'selected' : ''}>Withdrawn</option>
                </select>
            </td>
            <td>${formatDate(app.created_at)}</td>
            <td>
                <button class="btn btn-danger btn-small delete-btn" data-app-id="${app.id}" onclick="event.stopPropagation()">
                    Delete
                </button>
            </td>
        </tr>
        <tr id="details-${app.id}">
            <td colspan="5">
                <div class="app-details"></div>
            </td>
        </tr>
    `;
}
