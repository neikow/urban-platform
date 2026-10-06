/**
 * Declarative behaviours wired with data attributes instead of inline
 * `on*=` handlers, so templates carry no JavaScript:
 *
 * - `data-dialog-open="<dialog id>"`: open a <dialog> as a modal
 * - `data-dialog-close`: close the enclosing <dialog>
 * - `data-dismiss`: remove the closest `[data-dismissible]` element
 * - `data-autosubmit` (on a form control): submit its form on change
 * - `data-password-toggle="<input id>"`: show or hide a password field
 */
export function installBehaviors(root: Document = document): void {
  root.addEventListener("click", (event) => {
    const target = event.target;
    if (!(target instanceof Element)) return;

    const opener = target.closest<HTMLElement>("[data-dialog-open]");
    if (opener) {
      const dialog = root.getElementById(opener.dataset.dialogOpen ?? "");
      if (dialog instanceof HTMLDialogElement) {
        event.preventDefault();
        dialog.showModal();
      }
      return;
    }

    if (target.closest("[data-dialog-close]")) {
      target.closest("dialog")?.close();
      return;
    }

    if (target.closest("[data-dismiss]")) {
      target.closest("[data-dismissible]")?.remove();
      return;
    }

    const toggle = target.closest<HTMLElement>("[data-password-toggle]");
    if (toggle) togglePassword(toggle, toggle.dataset.passwordToggle ?? "");
  });

  root.addEventListener("change", (event) => {
    const target = event.target;
    if (target instanceof HTMLElement && target.matches("[data-autosubmit]")) {
      (target as HTMLInputElement).form?.requestSubmit();
    }
  });
}

function togglePassword(button: HTMLElement, fieldId: string): void {
  const input = document.getElementById(fieldId);
  if (!(input instanceof HTMLInputElement)) return;

  const reveal = input.type === "password";
  input.type = reveal ? "text" : "password";
  button.setAttribute("aria-pressed", String(reveal));
  document.getElementById(`eye-open-${fieldId}`)?.classList.toggle("hidden", reveal);
  document.getElementById(`eye-closed-${fieldId}`)?.classList.toggle("hidden", !reveal);
}
