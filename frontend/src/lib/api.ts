/** Shape returned by the participation endpoints on failure. */
export interface ApiFailure {
  success: false;
  error?: string;
  code?: string;
  action_url?: string;
}

export type ApiResponse<T> = (T & { success: true }) | ApiFailure;

export async function requestJson<T>(
  url: string,
  init: { method?: "GET" | "POST" | "DELETE"; body?: unknown; csrfToken?: string } = {},
): Promise<ApiResponse<T>> {
  const headers: Record<string, string> = { "X-Requested-With": "XMLHttpRequest" };
  if (init.body !== undefined) headers["Content-Type"] = "application/json";
  if (init.csrfToken) headers["X-CSRFToken"] = init.csrfToken;

  const response = await fetch(url, {
    method: init.method ?? "GET",
    headers,
    credentials: "same-origin",
    ...(init.body !== undefined ? { body: JSON.stringify(init.body) } : {}),
  });
  return (await response.json()) as ApiResponse<T>;
}

/**
 * Handle a failure that needs navigation rather than a message.
 * Returns true when the page is being redirected.
 */
export function redirectIfRequired(failure: ApiFailure): boolean {
  // The server asks for consent to the latest code of conduct first; the
  // consent page sends the user back here afterwards.
  if (failure.code === "code_of_conduct_required" && failure.action_url) {
    window.location.href = failure.action_url;
    return true;
  }
  return false;
}
