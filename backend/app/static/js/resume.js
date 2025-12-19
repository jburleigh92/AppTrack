// Resume upload screen logic

document.addEventListener('DOMContentLoaded', async () => {
    const form = document.getElementById('resume-upload-form');
    const fileInput = document.getElementById('resume-file');
    const uploadBtn = document.getElementById('upload-btn');
    const loading = document.getElementById('loading');
    const parsedData = document.getElementById('parsed-data');
    const continueBtn = document.getElementById('continue-btn');
    const reparseBtn = document.getElementById('reparse-btn');

    // Check if active resume already exists
    try {
        const activeResume = await checkActiveResume();
        if (activeResume && activeResume.extraction_complete) {
            displayParsedData(activeResume);
            continueBtn.disabled = false;
            reparseBtn.classList.remove('hide');
        }
    } catch (error) {
        console.log('No active resume found, showing upload form');
    }

    // Handle re-parse button click
    reparseBtn.addEventListener('click', async () => {
        reparseBtn.disabled = true;
        reparseBtn.textContent = 'Re-Parsing...';
        loading.classList.remove('hide');

        try {
            const response = await apiFetch('/resume/active/reparse', {
                method: 'POST'
            });

            showAlert('Resume re-parsed successfully!', 'success');

            // Reload active resume data
            const activeResume = await checkActiveResume();
            displayParsedData(activeResume);
            continueBtn.disabled = false;

        } catch (error) {
            showAlert('Re-parse failed: ' + error.message, 'error');
        } finally {
            loading.classList.add('hide');
            reparseBtn.disabled = false;
            reparseBtn.textContent = 'Re-Parse Resume';
        }
    });

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

            if (result.status === 'parsed' && result.resume_data) {
                showAlert('Resume uploaded and parsed successfully!', 'success');
                setActiveResumeId(result.resume_id);
                displayParsedData(result.resume_data);

                // Enable continue button if extraction is complete
                if (result.resume_data.extraction_complete) {
                    continueBtn.disabled = false;
                }

                // Show re-parse button
                reparseBtn.classList.remove('hide');
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
        experienceList.innerHTML = data.experience.map(exp => {
            const title = exp.title || 'Position';
            const company = exp.company || '';
            const duration = exp.duration || '';
            const description = exp.description || '';

            return `
                <div class="experience-item">
                    <strong>${title}</strong>${company ? ` at ${company}` : ''}
                    ${duration ? `<br><small>${duration}</small>` : ''}
                    ${description ? `<p style="margin-top: 0.5rem;">${description}</p>` : ''}
                </div>
            `;
        }).join('');
    } else {
        experienceList.innerHTML = '<p>No experience found</p>';
    }

    // Education
    const educationList = document.getElementById('education-list');
    if (data.education && data.education.length > 0) {
        educationList.innerHTML = data.education.map(edu => {
            const degree = edu.degree || 'Degree';
            const institution = edu.institution || '';
            const year = edu.year || '';

            return `
                <div class="education-item">
                    <strong>${degree}</strong>
                    ${institution ? `<br>${institution}` : ''}
                    ${year ? `<br><small>${year}</small>` : ''}
                </div>
            `;
        }).join('');
    } else {
        educationList.innerHTML = '<p>No education found</p>';
    }
}
