document.addEventListener('DOMContentLoaded', function() {
    const ideasComponent = document.getElementById('ideas-component');
    if (!ideasComponent) return;

    const projectId = ideasComponent.dataset.projectId;
    const isAuthenticated = ideasComponent.dataset.isAuthenticated === 'true';
    const csrfToken = ideasComponent.dataset.csrfToken;

    const messages = {
        empty: ideasComponent.dataset.msgEmpty || 'Please describe your idea',
        genericError: ideasComponent.dataset.msgGenericError || 'An error occurred',
        loadError: ideasComponent.dataset.msgLoadError || 'An error occurred while loading',
        submitError: ideasComponent.dataset.msgSubmitError || 'An error occurred while submitting your idea',
        removeError: ideasComponent.dataset.msgRemoveError || 'An error occurred while removing your idea',
        confirmRemove: ideasComponent.dataset.msgConfirmRemove || 'Are you sure you want to remove your idea?',
    };

    const ideasForm = document.getElementById('ideas-form');
    const ideasFormContainer = document.getElementById('ideas-form-container');
    const ideasResultContainer = document.getElementById('ideas-result-container');
    const ideasResultText = document.getElementById('ideas-result-text');
    const ideasLoading = document.getElementById('ideas-loading');
    const ideasError = document.getElementById('ideas-error');
    const ideasErrorText = document.getElementById('ideas-error-text');
    const changeBtn = document.getElementById('ideas-change-btn');
    const removeBtn = document.getElementById('ideas-remove-btn');
    const descriptionTextarea = document.getElementById('ideas-description');
    const anonymousCheckbox = document.getElementById('ideas-anonymous');

    if (!isAuthenticated) return;

    loadIdeaState();

    if (ideasForm) {
        ideasForm.addEventListener('submit', async function(e) {
            e.preventDefault();

            const description = descriptionTextarea ? descriptionTextarea.value.trim() : '';
            if (!description) {
                showError(messages.empty);
                return;
            }

            const isAnonymous = anonymousCheckbox ? anonymousCheckbox.checked : false;
            await submitIdea(description, isAnonymous);
        });
    }

    if (changeBtn) {
        changeBtn.addEventListener('click', function() {
            showForm();
        });
    }

    if (removeBtn) {
        removeBtn.addEventListener('click', async function() {
            if (confirm(messages.confirmRemove)) {
                await removeIdea();
            }
        });
    }

    async function loadIdeaState() {
        showLoading(true);
        hideError();

        try {
            const response = await fetch(`/api/projects/${projectId}/idea/mine/`, {
                method: 'GET',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });

            const data = await response.json();

            if (data.success) {
                if (data.has_submitted && data.user_idea) {
                    displayIdea(data.user_idea);
                } else {
                    showForm();
                }
            } else {
                showError(data.error || messages.genericError);
            }
        } catch (error) {
            console.error('Error loading idea state:', error);
            showError(messages.loadError);
        } finally {
            showLoading(false);
        }
    }

    async function submitIdea(description, isAnonymous) {
        showLoading(true);
        hideError();

        try {
            const response = await fetch(`/api/projects/${projectId}/idea/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken,
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: JSON.stringify({
                    description: description,
                    anonymize: isAnonymous
                })
            });

            const data = await response.json();

            if (data.success) {
                displayIdea(data.idea);
            } else {
                showError(data.error || messages.genericError);
                showForm();
            }
        } catch (error) {
            console.error('Error submitting idea:', error);
            showError(messages.submitError);
            showForm();
        } finally {
            showLoading(false);
        }
    }

    async function removeIdea() {
        showLoading(true);
        hideError();

        try {
            const response = await fetch(`/api/projects/${projectId}/idea/`, {
                method: 'DELETE',
                headers: {
                    'X-CSRFToken': csrfToken,
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });

            const data = await response.json();

            if (data.success) {
                if (ideasForm) ideasForm.reset();
                if (descriptionTextarea) descriptionTextarea.value = '';
                if (anonymousCheckbox) anonymousCheckbox.checked = false;
                showForm();
            } else {
                showError(data.error || messages.genericError);
            }
        } catch (error) {
            console.error('Error removing idea:', error);
            showError(messages.removeError);
        } finally {
            showLoading(false);
        }
    }

    function displayIdea(idea) {
        if (!idea) return;

        if (ideasResultText) {
            ideasResultText.textContent = idea.description || '';
        }
        if (descriptionTextarea) {
            descriptionTextarea.value = idea.description || '';
        }
        if (anonymousCheckbox) {
            anonymousCheckbox.checked = idea.anonymize || false;
        }

        showResult();
    }

    function showForm() {
        if (ideasFormContainer) ideasFormContainer.classList.remove('hidden');
        if (ideasResultContainer) ideasResultContainer.classList.add('hidden');
    }

    function showResult() {
        if (ideasFormContainer) ideasFormContainer.classList.add('hidden');
        if (ideasResultContainer) ideasResultContainer.classList.remove('hidden');
    }

    function showLoading(show) {
        if (ideasLoading) {
            if (show) {
                ideasLoading.classList.remove('hidden');
                if (ideasFormContainer) ideasFormContainer.classList.add('hidden');
                if (ideasResultContainer) ideasResultContainer.classList.add('hidden');
            } else {
                ideasLoading.classList.add('hidden');
            }
        }
    }

    function showError(message) {
        if (ideasError && ideasErrorText) {
            ideasErrorText.textContent = message;
            ideasError.classList.remove('hidden');
        }
    }

    function hideError() {
        if (ideasError) {
            ideasError.classList.add('hidden');
        }
    }
});
