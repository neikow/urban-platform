interface LoginResponse {
  success: boolean;
  redirect?: string;
  errors?: Record<string, string[] | string>;
}

/** Submit the login modal form over fetch and show the first error inline. */
export function installLoginModal(): void {
  const form = document.getElementById("login-form");
  const errorBox = document.getElementById("login-error");
  const errorText = document.getElementById("login-error-text");
  if (!(form instanceof HTMLFormElement) || !errorBox || !errorText) return;

  const fallback = form.dataset.msgError ?? "";

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    errorBox.classList.add("hidden");

    let message = fallback;
    try {
      const response = await fetch(form.action, {
        method: "POST",
        body: new FormData(form),
        headers: { "X-Requested-With": "XMLHttpRequest" },
        credentials: "same-origin",
      });
      const data = (await response.json()) as LoginResponse;
      if (data.success && data.redirect) {
        window.location.href = data.redirect;
        return;
      }
      const errors = data.errors ?? {};
      const first = errors["__all__"] ?? Object.values(errors)[0];
      if (first) message = Array.isArray(first) ? first.join(" ") : first;
    } catch (error) {
      console.error(error);
    }
    errorText.textContent = message;
    errorBox.classList.remove("hidden");
  });
}
