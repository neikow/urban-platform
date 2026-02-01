document.addEventListener('DOMContentLoaded', function() {
    const voteComponent = document.getElementById('vote-component');
    if (!voteComponent) return;

    const projectId = voteComponent.dataset.projectId;
    const isAuthenticated = voteComponent.dataset.isAuthenticated === 'true';
    const csrfToken = voteComponent.dataset.csrfToken;

    const messages = {
        selectOption: voteComponent.dataset.msgSelectOption || 'Please select an option',
        genericError: voteComponent.dataset.msgGenericError || 'An error occurred',
        loadError: voteComponent.dataset.msgLoadError || 'An error occurred while loading',
        submitError: voteComponent.dataset.msgSubmitError || 'An error occurred while submitting the vote',
        removeError: voteComponent.dataset.msgRemoveError || 'An error occurred while removing the vote',
        confirmRemove: voteComponent.dataset.msgConfirmRemove || 'Are you sure you want to remove your vote?',
    };

    const voteForm = document.getElementById('vote-form');
    const voteFormContainer = document.getElementById('vote-form-container');
    const voteResultsContainer = document.getElementById('vote-results-container');
    const voteResults = document.getElementById('vote-results');
    const voteLoading = document.getElementById('vote-loading');
    const voteError = document.getElementById('vote-error');
    const voteErrorText = document.getElementById('vote-error-text');
    const voteSubmitBtn = document.getElementById('vote-submit-btn');
    const changeVoteBtn = document.getElementById('change-vote-btn');
    const removeVoteBtn = document.getElementById('remove-vote-btn');
    const userVoteChoice = document.getElementById('user-vote-choice');
    const userVoteComment = document.getElementById('user-vote-comment');
    const userVoteCommentContainer = document.getElementById('user-vote-comment-container');
    const voteChoices = document.querySelectorAll('input[name="vote_choice"]');
    const commentTextarea = document.getElementById('vote-comment');
    const anonymousCheckbox = document.getElementById('vote-anonymous');

    let choiceLabels = {};

    const choiceColors = {
        'UNFAVORABLE': 'bg-error',
        'RATHER_UNFAVORABLE': 'bg-warning',
        'RATHER_FAVORABLE': 'bg-info',
        'FAVORABLE': 'bg-success'
    };

    if (!isAuthenticated) return;

    loadVoteState();

    voteChoices.forEach(choice => {
        choice.addEventListener('change', function() {
            if (voteSubmitBtn) voteSubmitBtn.disabled = false;
        });
    });

    if (voteForm) {
        voteForm.addEventListener('submit', async function(e) {
            e.preventDefault();

            const selectedChoice = document.querySelector('input[name="vote_choice"]:checked');
            if (!selectedChoice) {
                showError(messages.selectOption);
                return;
            }

            const comment = commentTextarea ? commentTextarea.value.trim() : '';
            const isAnonymous = anonymousCheckbox ? anonymousCheckbox.checked : false;

            await submitVote(selectedChoice.value, comment, isAnonymous);
        });
    }

    if (changeVoteBtn) {
        changeVoteBtn.addEventListener('click', function() {
            showVoteForm();
        });
    }

    if (removeVoteBtn) {
        removeVoteBtn.addEventListener('click', async function() {
            if (confirm(messages.confirmRemove)) {
                await removeVote();
            }
        });
    }

    async function loadVoteState() {
        showLoading(true);
        hideError();

        try {
            const response = await fetch(`/api/projects/${projectId}/vote/results`, {
                method: 'GET',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });

            const data = await response.json();

            if (data.success) {
                // Extract labels from API response if available
                if (data.results && data.results.choices) {
                    for (const [key, value] of Object.entries(data.results.choices)) {
                        if (value.label) {
                            choiceLabels[key] = value.label;
                        }
                    }
                }

                if (data.has_voted && data.user_vote) {
                    displayResults(data.results, data.user_vote);
                } else {
                    showVoteForm();
                }
            } else {
                showError(data.error || messages.genericError);
            }
        } catch (error) {
            console.error('Error loading vote state:', error);
            showError(messages.loadError);
        } finally {
            showLoading(false);
        }
    }

    async function submitVote(choice, comment, isAnonymous) {
        showLoading(true);
        hideError();

        try {
            const response = await fetch(`/api/projects/${projectId}/vote`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken,
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: JSON.stringify({
                    choice: choice,
                    comment: comment,
                    anonymize: isAnonymous
                })
            });

            const data = await response.json();

            if (data.success) {
                if (data.results && data.results.choices) {
                    for (const [key, value] of Object.entries(data.results.choices)) {
                        if (value.label) {
                            choiceLabels[key] = value.label;
                        }
                    }
                }
                displayResults(data.results, data.vote);
            } else {
                showError(data.error || messages.genericError);
                showVoteForm();
            }
        } catch (error) {
            console.error('Error submitting vote:', error);
            showError(messages.submitError);
            showVoteForm();
        } finally {
            showLoading(false);
        }
    }

    async function removeVote() {
        showLoading(true);
        hideError();

        try {
            const response = await fetch(`/api/projects/${projectId}/vote`, {
                method: 'DELETE',
                headers: {
                    'X-CSRFToken': csrfToken,
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });

            const data = await response.json();

            if (data.success) {
                if (voteForm) voteForm.reset();
                if (commentTextarea) commentTextarea.value = '';
                if (anonymousCheckbox) anonymousCheckbox.checked = false;
                voteSubmitBtn.disabled = true;
                showVoteForm();
            } else {
                showError(data.error || messages.genericError);
            }
        } catch (error) {
            console.error('Error removing vote:', error);
            showError(messages.removeError);
        } finally {
            showLoading(false);
        }
    }

    /**
     * Display vote results
     */
    function displayResults(results, userVote) {
        if (!results || !voteResults) return;

        let html = `
            <div class="text-sm text-base-content/70 mb-3">
                ${results.total_votes} vote${results.total_votes > 1 ? 's' : ''} au total
            </div>
        `;

        const orderedChoices = ['FAVORABLE', 'RATHER_FAVORABLE', 'RATHER_UNFAVORABLE', 'UNFAVORABLE'];

        orderedChoices.forEach(choiceKey => {
            const choiceData = results.choices[choiceKey];
            if (choiceData) {
                const isUserChoice = userVote && userVote.choice === choiceKey;
                const label = choiceData.label || choiceLabels[choiceKey] || choiceKey;
                html += `
                    <div class="mb-2 ${isUserChoice ? 'font-semibold' : ''}">
                        <div class="flex justify-between text-sm mb-1">
                            <span>${label}${isUserChoice ? ' ✓' : ''}</span>
                            <span>${choiceData.percentage}%</span>
                        </div>
                        <div class="w-full bg-base-300 rounded-full h-3">
                            <div class="${choiceColors[choiceKey]} h-3 rounded-full transition-all duration-500"
                                 style="width: ${choiceData.percentage}%"></div>
                        </div>
                    </div>
                `;
            }
        });

        voteResults.innerHTML = html;

        if (userVote && userVoteChoice) {
            const userLabel = (results.choices[userVote.choice] && results.choices[userVote.choice].label)
                || choiceLabels[userVote.choice]
                || userVote.choice;
            userVoteChoice.textContent = userLabel;

            if (userVote.comment && userVoteComment && userVoteCommentContainer) {
                userVoteComment.textContent = userVote.comment;
                userVoteCommentContainer.classList.remove('hidden');
            } else if (userVoteCommentContainer) {
                userVoteCommentContainer.classList.add('hidden');
            }
        }

        if (userVote) {
            const choiceInput = document.querySelector(`input[name="vote_choice"][value="${userVote.choice}"]`);
            if (choiceInput) {
                choiceInput.checked = true;
                voteSubmitBtn.disabled = false;
            }
            if (commentTextarea && userVote.comment) {
                commentTextarea.value = userVote.comment;
            }
            if (anonymousCheckbox) {
                anonymousCheckbox.checked = userVote.anonymize || false;
            }
        }

        showResults();
    }

    function showVoteForm() {
        if (voteFormContainer) voteFormContainer.classList.remove('hidden');
        if (voteResultsContainer) voteResultsContainer.classList.add('hidden');
    }

    function showResults() {
        if (voteFormContainer) voteFormContainer.classList.add('hidden');
        if (voteResultsContainer) voteResultsContainer.classList.remove('hidden');
    }

    function showLoading(show) {
        if (voteLoading) {
            if (show) {
                voteLoading.classList.remove('hidden');
                if (voteFormContainer) voteFormContainer.classList.add('hidden');
                if (voteResultsContainer) voteResultsContainer.classList.add('hidden');
            } else {
                voteLoading.classList.add('hidden');
            }
        }
    }

    function showError(message) {
        if (voteError && voteErrorText) {
            voteErrorText.textContent = message;
            voteError.classList.remove('hidden');
        }
    }

    function hideError() {
        if (voteError) {
            voteError.classList.add('hidden');
        }
    }
});
