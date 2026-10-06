import { type ApiFailure, redirectIfRequired } from "./api";
import { hide, maybeById, show } from "./dom";

/**
 * The vote and idea cards switch between a loading state, a form and the
 * user's submitted answer, with an error banner on top.
 */
export class ParticipationPanel {
  private readonly loading: HTMLElement | null;
  private readonly form: HTMLElement | null;
  private readonly result: HTMLElement | null;
  private readonly error: HTMLElement | null;
  private readonly errorText: HTMLElement | null;

  constructor(
    ids: { loading: string; form: string; result: string; error: string; errorText: string },
    private readonly genericError: string,
  ) {
    this.loading = maybeById(ids.loading);
    this.form = maybeById(ids.form);
    this.result = maybeById(ids.result);
    this.error = maybeById(ids.error);
    this.errorText = maybeById(ids.errorText);
  }

  showForm(): void {
    show(this.form);
    hide(this.result);
  }

  showResult(): void {
    hide(this.form);
    show(this.result);
  }

  setLoading(loading: boolean): void {
    if (loading) {
      show(this.loading);
      hide(this.form, this.result);
    } else {
      hide(this.loading);
    }
  }

  showError(message: string): void {
    if (this.errorText) this.errorText.textContent = message;
    show(this.error);
  }

  hideError(): void {
    hide(this.error);
  }

  handleFailure(failure: ApiFailure): void {
    if (!redirectIfRequired(failure)) this.showError(failure.error ?? this.genericError);
  }

  /** Run an API call with the loading state, reporting network errors as `fallbackError`. */
  async run(fallbackError: string, action: () => Promise<void>): Promise<void> {
    this.setLoading(true);
    this.hideError();
    try {
      await action();
    } catch (error) {
      console.error(error);
      this.showError(fallbackError);
    } finally {
      this.setLoading(false);
    }
  }
}
