/**
 * shared/js/apiClient.js
 *
 * Centralized API layer for all lending-frontend apps.
 * Replaces the pattern of each app hard-coding its own
 * `fetch(`${API_BASE}/...`)` calls with duplicated try/catch blocks.
 *
 * Usage:
 *   const data = await LendingAPI.get('/api/lending/123456789012');
 *   const data = await LendingAPI.post('/api/lending/create', payload);
 *
 *   // Cancellable request (e.g. a debounced lookup superseded by a newer one):
 *   const ctrl = new AbortController();
 *   LendingAPI.get('/api/lending/search', { signal: ctrl.signal });
 *   ctrl.abort(); // cancels in flight, caller's catch sees code "ABORTED"
 *
 *   // Retry a transient failure (network/timeout/5xx) up to N times:
 *   const data = await LendingAPI.get('/api/lending/123', { retries: 2 });
 *
 * All methods throw a normalized ApiError on failure, so callers
 * only need one catch block instead of re-implementing
 * "is it JSON? is it a network error? did the backend say success:false?"
 * in every page.
 */
(function (window) {
  "use strict";

  const BASE_URL = window.LENDING_API_BASE || "http://localhost:5001";
  const DEFAULT_TIMEOUT_MS = 10000;

  class ApiError extends Error {
    constructor(message, { status = null, code = "UNKNOWN", cause = null, data = null } = {}) {
      super(message);
      this.name = "ApiError";
      this.status = status;
      this.code = code; // 'NETWORK' | 'TIMEOUT' | 'ABORTED' | 'HTTP' | 'BACKEND' | 'PARSE'
      this.cause = cause;
      this.data = data; // raw response body, when available (e.g. { duplicate: {...} })
      if (data && typeof data === "object") {
        // Surface known structured fields (e.g. `duplicate`) directly on
        // the error too, so callers can do `err.duplicate` without
        // reaching into `err.data`.
        for (const key of Object.keys(data)) {
          if (!(key in this)) this[key] = data[key];
        }
      }
    }
  }

  function friendlyMessage(err) {
    switch (err.code) {
      case "NETWORK":
        return "Can't reach the server. Check your connection and try again.";
      case "TIMEOUT":
        return "The server took too long to respond. Please try again.";
      case "ABORTED":
        return "The request was cancelled.";
      case "HTTP":
        if (err.status === 401 || err.status === 403) return "Your session has expired. Please log in again.";
        if (err.status === 404) return "The requested record could not be found.";
        if (err.status >= 500) return "Something went wrong on our end. Please try again shortly.";
        return "The request could not be completed.";
      case "BACKEND":
        return err.message || "The server rejected the request.";
      case "PARSE":
        return "The server sent back a response we couldn't understand. Please try again.";
      default:
        return "Something unexpected happened. Please try again.";
    }
  }

  function isRetryable(err) {
    // Only retry failures that are plausibly transient. Never retry ABORTED
    // (the caller explicitly cancelled) or 4xx HTTP/BACKEND errors (retrying
    // a bad request or a rejected password won't succeed on attempt 2).
    if (err.code === "NETWORK" || err.code === "TIMEOUT") return true;
    if (err.code === "HTTP" && err.status >= 500) return true;
    return false;
  }

  function delay(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  async function requestOnce(path, { method, body, headers, timeoutMs, signal }) {
    // Combine the caller's own AbortSignal (if any) with our internal
    // timeout-driven one, so either can cancel the fetch.
    const timeoutController = new AbortController();
    const timer = setTimeout(() => timeoutController.abort(), timeoutMs);

    const onCallerAbort = () => timeoutController.abort();
    if (signal) {
      if (signal.aborted) timeoutController.abort();
      else signal.addEventListener("abort", onCallerAbort, { once: true });
    }

    let response;
    try {
      response = await fetch(`${BASE_URL}${path}`, {
        method,
        headers: {
          ...(body ? { "Content-Type": "application/json" } : {}),
          ...headers,
        },
        body: body ? JSON.stringify(body) : undefined,
        signal: timeoutController.signal,
      });
    } catch (err) {
      clearTimeout(timer);
      if (signal) signal.removeEventListener("abort", onCallerAbort);

      if (err.name === "AbortError") {
        // Distinguish "caller cancelled on purpose" from "we timed out
        // waiting" so friendlyMessage() can say the right thing.
        if (signal && signal.aborted) {
          throw new ApiError("Request was cancelled", { code: "ABORTED", cause: err });
        }
        throw new ApiError("Request timed out", { code: "TIMEOUT", cause: err });
      }
      throw new ApiError("Network request failed", { code: "NETWORK", cause: err });
    }
    clearTimeout(timer);
    if (signal) signal.removeEventListener("abort", onCallerAbort);

    // Read the raw text first so we can tell "genuinely empty body"
    // (safe — common for 204 No Content, e.g. a successful DELETE) apart
    // from "non-empty but not valid JSON" (a real problem worth surfacing
    // distinctly, rather than silently returning null as if it succeeded).
    const rawText = await response.text().catch(() => "");
    let data = null;
    if (rawText.length > 0) {
      try {
        data = JSON.parse(rawText);
      } catch (err) {
        if (response.ok) {
          throw new ApiError("The server sent back an unreadable response", {
            status: response.status,
            code: "PARSE",
            cause: err,
          });
        }
        // For non-ok responses with an unparseable body, fall through with
        // data = null; the generic HTTP error message below still applies.
      }
    }

    if (!response.ok) {
      throw new ApiError(
        (data && (data.message || data.error)) || `Request failed with status ${response.status}`,
        { status: response.status, code: "HTTP", data }
      );
    }

    if (data && data.success === false) {
      throw new ApiError(data.error || data.message || "The server rejected the request.", { code: "BACKEND", data });
    }

    // Explicitly normalize "ok, empty body" (e.g. 204 from a DELETE) to an
    // empty object rather than null, so callers can safely do `result.foo`
    // without an extra null-check for the common "delete succeeded" case.
    return data === null ? {} : data;
  }

  async function request(path, options = {}) {
    const {
      method = "GET",
      body,
      headers = {},
      timeoutMs = DEFAULT_TIMEOUT_MS,
      signal,
      retries = 0,
      retryDelayMs = 400,
    } = options;

    let attempt = 0;
    // eslint-disable-next-line no-constant-condition
    while (true) {
      try {
        return await requestOnce(path, { method, body, headers, timeoutMs, signal });
      } catch (err) {
        const canRetry = attempt < retries && isRetryable(err);
        if (!canRetry) throw err;
        attempt += 1;
        // Simple linear backoff; sufficient for a low-traffic internal tool.
        await delay(retryDelayMs * attempt);
      }
    }
  }

  window.LendingAPI = {
    get: (path, opts) => request(path, { ...opts, method: "GET" }),
    post: (path, body, opts) => request(path, { ...opts, method: "POST", body }),
    put: (path, body, opts) => request(path, { ...opts, method: "PUT", body }),
    delete: (path, body, opts) => request(path, { ...opts, method: "DELETE", body }),
    ApiError,
    friendlyMessage,
  };
})(window);