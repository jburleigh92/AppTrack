// Shared utilities for AppTrack UI

const API_BASE = '/api/v1';

// Fetch wrapper with error handling
async function apiFetch(endpoint, options = {}) {
    try {
        const response = await fetch(`${API_BASE}${endpoint}`, {
            ...options,
            headers: {
                'Content-Type': 'application/json',
                ...options.headers,
            },
        });

        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.detail || `HTTP ${response.status}: ${response.statusText}`);
        }

        // Handle 204 No Content
        if (response.status === 204) {
            return null;
        }

        return await response.json();
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
}

// Check if active resume exists
async function checkActiveResume() {
    try {
        const resume = await apiFetch('/resume/active');
        return resume;
    } catch (error) {
        if (error.message.includes('404')) {
            return null;
        }
        throw error;
    }
}

// Format date
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
    });
}

// Show alert message
function showAlert(message, type = 'info') {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type}`;
    alertDiv.textContent = message;

    const container = document.querySelector('.container');
    container.insertBefore(alertDiv, container.firstChild);

    setTimeout(() => {
        alertDiv.remove();
    }, 5000);
}

// Store resume ID in session
function setActiveResumeId(resumeId) {
    sessionStorage.setItem('activeResumeId', resumeId);
}

function getActiveResumeId() {
    return sessionStorage.getItem('activeResumeId');
}
