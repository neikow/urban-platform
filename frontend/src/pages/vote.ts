import { requestJson } from "../lib/api";
import { maybeById, onReady } from "../lib/dom";
import { ParticipationPanel } from "../lib/participation";

const CHOICES = ["FAVORABLE", "RATHER_FAVORABLE", "RATHER_UNFAVORABLE", "UNFAVORABLE"] as const;
type Choice = (typeof CHOICES)[number];

const CHOICE_COLORS: Record<Choice, string> = {
  FAVORABLE: "bg-success",
  RATHER_FAVORABLE: "bg-info",
  RATHER_UNFAVORABLE: "bg-warning",
  UNFAVORABLE: "bg-error",
};

interface Vote {
  choice: Choice;
  comment: string;
  anonymize: boolean;
}

interface Results {
  total_votes: number;
  choices: Record<Choice, { count: number; percentage: number; label?: string }>;
}

interface VoteState {
  has_voted: boolean;
  user_vote: Vote | null;
  results: Results | null;
}

function el<K extends keyof HTMLElementTagNameMap>(
  tag: K,
  className: string,
  text?: string,
): HTMLElementTagNameMap[K] {
  const element = document.createElement(tag);
  element.className = className;
  if (text !== undefined) element.textContent = text;
  return element;
}

onReady(() => {
  const root = maybeById("vote-component");
  if (!root || root.dataset.canParticipate !== "true") return;

  const { projectId, csrfToken = "" } = root.dataset;
  const msg = root.dataset;
  const url = `/api/projects/${projectId}/vote/`;
  const plural = new Intl.PluralRules(document.documentElement.lang || "fr");

  const panel = new ParticipationPanel(
    {
      loading: "vote-loading",
      form: "vote-form-container",
      result: "vote-results-container",
      error: "vote-error",
      errorText: "vote-error-text",
    },
    msg.msgGenericError ?? "",
  );
  const form = maybeById<HTMLFormElement>("vote-form");
  const submitButton = maybeById<HTMLButtonElement>("vote-submit-btn");
  const comment = maybeById<HTMLTextAreaElement>("vote-comment");
  const anonymous = maybeById<HTMLInputElement>("vote-anonymous");
  const resultsList = maybeById("vote-results");
  const userChoice = maybeById("user-vote-choice");
  const userComment = maybeById("user-vote-comment");
  const userCommentContainer = maybeById("user-vote-comment-container");
  const choiceInputs = () => document.querySelectorAll<HTMLInputElement>('input[name="vote_choice"]');
  const labels: Partial<Record<Choice, string>> = {};

  function selectedChoice(): Choice | undefined {
    return document.querySelector<HTMLInputElement>('input[name="vote_choice"]:checked')?.value as
      | Choice
      | undefined;
  }

  function totalLabel(count: number): string {
    const template = plural.select(count) === "one" ? msg.msgTotalOne : msg.msgTotalOther;
    return (template ?? "{count}").replace("{count}", String(count));
  }

  function renderResults(results: Results, vote: Vote): void {
    for (const choice of CHOICES) {
      const label = results.choices[choice]?.label;
      if (label) labels[choice] = label;
    }

    if (resultsList) {
      const rows = CHOICES.map((choice) => {
        const data = results.choices[choice];
        const mine = vote.choice === choice;
        const row = el("div", mine ? "mb-2 font-semibold" : "mb-2");
        const header = el("div", "flex justify-between text-sm mb-1");
        header.append(
          el("span", "", `${labels[choice] ?? choice}${mine ? " ✓" : ""}`),
          el("span", "", `${data.percentage}%`),
        );
        const track = el("div", "w-full bg-base-300 rounded-full h-3");
        const bar = el("div", `${CHOICE_COLORS[choice]} h-3 rounded-full transition-all duration-500`);
        bar.style.width = `${data.percentage}%`;
        track.append(bar);
        row.append(header, track);
        return row;
      });
      resultsList.replaceChildren(el("div", "text-sm text-base-content/70 mb-3", totalLabel(results.total_votes)), ...rows);
    }

    if (userChoice) userChoice.textContent = labels[vote.choice] ?? vote.choice;
    if (userComment) userComment.textContent = vote.comment;
    userCommentContainer?.classList.toggle("hidden", !vote.comment);

    // Pre-fill the form for "change my vote".
    for (const input of choiceInputs()) input.checked = input.value === vote.choice;
    if (submitButton) submitButton.disabled = false;
    if (comment) comment.value = vote.comment;
    if (anonymous) anonymous.checked = vote.anonymize;

    panel.showResult();
  }

  // Clicking the selected choice again clears it.
  for (const label of document.querySelectorAll<HTMLLabelElement>(".vote-choice-btn")) {
    const input = label.querySelector<HTMLInputElement>('input[name="vote_choice"]');
    if (!input) continue;
    let wasChecked = false;
    label.addEventListener("pointerdown", () => {
      wasChecked = input.checked;
    });
    label.addEventListener("click", (event) => {
      if (wasChecked) {
        event.preventDefault();
        input.checked = false;
      }
      wasChecked = false;
      if (submitButton) submitButton.disabled = !input.checked && !selectedChoice();
    });
  }
  for (const input of choiceInputs()) {
    input.addEventListener("change", () => {
      if (submitButton) submitButton.disabled = !selectedChoice();
    });
  }

  form?.addEventListener("submit", (event) => {
    event.preventDefault();
    const choice = selectedChoice();
    if (!choice) {
      panel.showError(msg.msgSelectOption ?? "");
      return;
    }
    void panel.run(msg.msgSubmitError ?? "", async () => {
      const data = await requestJson<{ vote: Vote; results: Results }>(url, {
        method: "POST",
        csrfToken,
        body: {
          choice,
          comment: comment?.value.trim() ?? "",
          anonymize: anonymous?.checked ?? false,
        },
      });
      if (data.success) {
        renderResults(data.results, data.vote);
      } else {
        panel.handleFailure(data);
        panel.showForm();
      }
    });
  });

  maybeById("change-vote-btn")?.addEventListener("click", () => panel.showForm());

  maybeById("remove-vote-btn")?.addEventListener("click", () => {
    if (!window.confirm(msg.msgConfirmRemove ?? "")) return;
    void panel.run(msg.msgRemoveError ?? "", async () => {
      const data = await requestJson<object>(url, { method: "DELETE", csrfToken });
      if (data.success) {
        form?.reset();
        if (submitButton) submitButton.disabled = true;
        panel.showForm();
      } else {
        panel.handleFailure(data);
      }
    });
  });

  void panel.run(msg.msgLoadError ?? "", async () => {
    const data = await requestJson<VoteState>(`${url}results/`);
    if (!data.success) {
      panel.handleFailure(data);
    } else if (data.has_voted && data.user_vote && data.results) {
      renderResults(data.results, data.user_vote);
    } else {
      panel.showForm();
    }
  });
});
