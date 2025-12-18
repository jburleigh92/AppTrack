// Resume upload screen logic

document.addEventListener('DOMContentLoaded', async () => {
    const form = document.getElementById('resume-upload-form');
    const fileInput = document.getElementById('resume-file');
    const uploadBtn = document.getElementById('upload-btn');
    const loading = document.getElementById('loading');
    const parsedData = document.getElementById('parsed-data');
    const continueBtn = document.getElementById('continue-btn');

    // Check if active resume already exists
    try {
        const activeResume = await checkActiveResume();
        if (activeResume && activeResume.extraction_complete) {
            displayParsedData(activeResume);
            continueBtn.disabled = false;
        }
    } catch (error) {
        console.log('No active resume found, showing upload form');
    }

    // Handle form submission
    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const file = fileInput.files[0];
        if (!file) {
            showAlert('Please select a file', 'error');
            return;
        }

        // Check file size (10MB)
        if (file.size > 10 * 1024 * 1024) {
            showAlert('File size must be less than 10MB', 'error');
            return;
        }

        // Show loading state
        uploadBtn.disabled = true;
        loading.classList.remove('hide');
        parsedData.classList.add('hide');

        try {
            // Create FormData
            const formData = new FormData();
            formData.append('file', file);

            // Upload resume
            const response = await fetch(`${API_BASE}/resume/upload`, {
                method: 'POST',
                body: formData,
            });

            if (!response.ok) {
                const error = await response.json().catch(() => ({}));
                throw new Error(error.detail || 'Upload failed');
            }

            const result = await response.json();

            // Hide loading
            loading.classList.add('hide');

            if (result.status === 'parsed') {
                showAlert('Resume uploaded and parsed successfully!', 'success');
                setActiveResumeId(result.resume_id);
                displayParsedData(result);

                // Enable continue button if extraction is complete
                if (result.extraction_complete) {
                    continueBtn.disabled = false;
                }
            } else {
                showAlert('Resume upload failed. Please try again.', 'error');
            }
        } catch (error) {
            loading.classList.add('hide');
            showAlert(error.message, 'error');
        } finally {
            uploadBtn.disabled = false;
        }
    });

    // Continue button click
    continueBtn.addEventListener('click', () => {
        window.location.href = '/jobs';
    });
});

function displayParsedData(data) {
    const parsedData = document.getElementById('parsed-data');
    parsedData.classList.remove('hide');

    // Contact info
    const contactInfo = document.getElementById('contact-info');
    const contactItems = [];
    if (data.email) contactItems.push(`<p><strong>Email:</strong> ${data.email}</p>`);
    if (data.phone) contactItems.push(`<p><strong>Phone:</strong> ${data.phone}</p>`);
    if (data.linkedin_url) contactItems.push(`<p><strong>LinkedIn:</strong> <a href="${data.linkedin_url}" target="_blank">${data.linkedin_url}</a></p>`);
    contactInfo.innerHTML = contactItems.join('') || '<p>No contact information found</p>';

    // Skills
    const skillsList = document.getElementById('skills-list');
    if (data.skills && data.skills.length > 0) {
        skillsList.innerHTML = data.skills.map(skill =>
            `<span class="skill-tag">${skill}</span>`
        ).join('');
    } else {
        skillsList.innerHTML = '<p>No skills found</p>';
    }

    // Experience
    const experienceList = document.getElementById('experience-list');
    if (data.experience && data.experience.length > 0) {
        experienceList.innerHTML = data.experience.map(exp => `
            <div class="experience-item">
                <strong>${exp.title || 'Unknown Title'}</strong> at ${exp.company || 'Unknown Company'}
                ${exp.duration ? `<br><small>${exp.duration}</small>` : ''}
                ${exp.description ? `<p>${exp.description}</p>` : ''}
            </div>
        `).join('');
    } else {
        experienceList.innerHTML = '<p>No experience found</p>';
    }

    // Education
    const educationList = document.getElementById('education-list');
    if (data.education && data.education.length > 0) {
        educationList.innerHTML = data.education.map(edu => `
            <div class="education-item">
                <strong>${edu.degree || 'Unknown Degree'}</strong>
                ${edu.institution ? `<br>${edu.institution}` : ''}
                ${edu.year ? `<br><small>${edu.year}</small>` : ''}
            </div>
        `).join('');
    } else {
        educationList.innerHTML = '<p>No education found</p>';
    }
}
