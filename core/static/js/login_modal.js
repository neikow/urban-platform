document.addEventListener('DOMContentLoaded', function() {
    const loginForm = document.getElementById('login-form');
    const errorDiv = document.getElementById('login-error');
    const errorText = document.getElementById('login-error-text');

    loginForm.addEventListener('submit', async function(e) {
        e.preventDefault();

        errorDiv.classList.add('hidden');

        const formData = new FormData(loginForm);

        try {
            const response = await fetch(loginForm.action, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });

            const data = await response.json();

            if (data.success) {
                window.location.href = data.redirect;
            } else {
                // Display errors
                let errorMessage;
                if (data.errors) {
                    if (data.errors.__all__) {
                        errorMessage = data.errors.__all__.join(' ');
                    }
                    else {
                        const firstError = Object.values(data.errors)[0];
                        errorMessage = Array.isArray(firstError) ? firstError.join(' ') : String(firstError);
                    }
                } else {
                    errorMessage = 'Une erreur est survenue. Veuillez vérifier vos informations.';
                }
                errorText.textContent = errorMessage;
                errorDiv.classList.remove('hidden');
            }
        } catch (error) {
            errorText.textContent = 'Une erreur est survenue. Veuillez réessayer.';
            errorDiv.classList.remove('hidden');
        }
    });
});
