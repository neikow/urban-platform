function togglePasswordVisibility(fieldId) {
    const passwordInput = document.getElementById(fieldId);
    if (!passwordInput) {
        return;
    }

    const eyeOpenIcon = document.getElementById(`eye-open-${fieldId}`);
    const eyeClosedIcon = document.getElementById(`eye-closed-${fieldId}`);

    if (!eyeOpenIcon || !eyeClosedIcon) {
        return;
    }

    const isPasswordVisible = passwordInput.type === "text";

    if (isPasswordVisible) {
        passwordInput.type = "password";
        eyeOpenIcon.classList.remove("hidden");
        eyeClosedIcon.classList.add("hidden");
    } else {
        passwordInput.type = "text";
        eyeOpenIcon.classList.add("hidden");
        eyeClosedIcon.classList.remove("hidden");
    }
}
