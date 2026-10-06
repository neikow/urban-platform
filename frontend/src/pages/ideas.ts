import { requestJson } from "../lib/api";
import { maybeById, onReady } from "../lib/dom";
import { ParticipationPanel } from "../lib/participation";

interface Idea {
  description: string;
  anonymize: boolean;
}

interface IdeaState {
  has_submitted: boolean;
  user_idea: Idea | null;
}

onReady(() => {
  const root = maybeById("ideas-component");
  if (!root || root.dataset.canParticipate !== "true") return;

  const { projectId, csrfToken = "" } = root.dataset;
  const msg = root.dataset;
  const url = `/api/projects/${projectId}/idea/`;

  const panel = new ParticipationPanel(
    {
      loading: "ideas-loading",
      form: "ideas-form-container",
      result: "ideas-result-container",
      error: "ideas-error",
      errorText: "ideas-error-text",
    },
    msg.msgGenericError ?? "",
  );
  const form = maybeById<HTMLFormElement>("ideas-form");
  const description = maybeById<HTMLTextAreaElement>("ideas-description");
  const anonymous = maybeById<HTMLInputElement>("ideas-anonymous");
  const resultText = maybeById("ideas-result-text");

  function displayIdea(idea: Idea): void {
    if (resultText) resultText.textContent = idea.description;
    if (description) description.value = idea.description;
    if (anonymous) anonymous.checked = idea.anonymize;
    panel.showResult();
  }

  form?.addEventListener("submit", (event) => {
    event.preventDefault();
    const text = description?.value.trim() ?? "";
    if (!text) {
      panel.showError(msg.msgEmpty ?? "");
      return;
    }
    void panel.run(msg.msgSubmitError ?? "", async () => {
      const data = await requestJson<{ idea: Idea }>(url, {
        method: "POST",
        csrfToken,
        body: { description: text, anonymize: anonymous?.checked ?? false },
      });
      if (data.success) {
        displayIdea(data.idea);
      } else {
        panel.handleFailure(data);
        panel.showForm();
      }
    });
  });

  maybeById("ideas-change-btn")?.addEventListener("click", () => panel.showForm());

  maybeById("ideas-remove-btn")?.addEventListener("click", () => {
    if (!window.confirm(msg.msgConfirmRemove ?? "")) return;
    void panel.run(msg.msgRemoveError ?? "", async () => {
      const data = await requestJson<object>(url, { method: "DELETE", csrfToken });
      if (data.success) {
        form?.reset();
        panel.showForm();
      } else {
        panel.handleFailure(data);
      }
    });
  });

  void panel.run(msg.msgLoadError ?? "", async () => {
    const data = await requestJson<IdeaState>(`${url}mine/`);
    if (!data.success) {
      panel.handleFailure(data);
    } else if (data.has_submitted && data.user_idea) {
      displayIdea(data.user_idea);
    } else {
      panel.showForm();
    }
  });
});
