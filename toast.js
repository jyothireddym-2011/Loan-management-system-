/**
 * shared/js/toast.js
 *
 * Reusable toast notification. Every app previously reimplemented
 * this same ~10-line function against its own #toast element.
 * Now: include shared/css/components.css + this script (no markup
 * required — a container is created and managed automatically),
 * and call LendingToast.show("message") or LendingToast.error("message").
 *
 * Usage:
 *   LendingToast.show("Saved.");
 *   LendingToast.success("Payment submitted.");
 *   LendingToast.error("Could not reach the server.");
 *   const id = LendingToast.show("Uploading…", { duration: 0 }); // sticky
 *   LendingToast.dismiss(id);
 */
(function (window, document) {
  "use strict";

  // Guard against the script being included twice (e.g. once globally,
  // once in a page bundle) — keep the first instance as the source of truth.
  if (window.LendingToast) return;

  const MAX_VISIBLE = 4; // oldest toast is auto-dismissed if a 5th arrives
  let container = null;
  let seq = 0;

  function ensureContainer() {
    if (container && document.body.contains(container)) return container;

    container = document.getElementById("toast-region");
    if (!container) {
      container = document.createElement("div");
      container.id = "toast-region";
      document.body.appendChild(container);
    }
    container.className = "toast-region";
    // aria-live region: "polite" so toasts don't interrupt screen reader
    // users mid-sentence; errors get role="alert" per-toast (see below)
    // for a stronger, more immediate announcement.
    container.setAttribute("aria-live", "polite");
    container.setAttribute("aria-atomic", "false");
    return container;
  }

  function dismiss(id) {
    const el = document.getElementById(id);
    if (!el) return;
    el.classList.remove("toast--show");
    el.classList.add("toast--hide");
    // Remove after the CSS transition finishes (or immediately if the
    // browser/user prefers reduced motion, since the transition won't run).
    const prefersReducedMotion = window.matchMedia(
      "(prefers-reduced-motion: reduce)"
    ).matches;
    const removeNow = () => el.remove();
    if (prefersReducedMotion) {
      removeNow();
    } else {
      el.addEventListener("transitionend", removeNow, { once: true });
      // Fallback in case transitionend never fires (e.g. element hidden via display:none elsewhere)
      setTimeout(removeNow, 400);
    }
  }

  function show(message, options = {}) {
    const {
      variant = "info", // "info" | "success" | "error"
      duration = variant === "error" ? 4200 : 2600,
      dismissible = true,
    } = options;

    const region = ensureContainer();

    // Cap concurrent toasts: drop the oldest rather than let them pile up forever.
    const existing = region.querySelectorAll(".toast");
    if (existing.length >= MAX_VISIBLE) {
      dismiss(existing[0].id);
    }

    const id = `toast-${Date.now()}-${seq++}`;
    const el = document.createElement("div");
    el.id = id;
    el.className = `toast toast--${variant}`;
    // Errors interrupt more assertively; info/success stay polite.
    el.setAttribute("role", variant === "error" ? "alert" : "status");

    const text = document.createElement("span");
    text.className = "toast__message";
    text.textContent = message;
    el.appendChild(text);

    if (dismissible) {
      const closeBtn = document.createElement("button");
      closeBtn.type = "button";
      closeBtn.className = "toast__close";
      closeBtn.setAttribute("aria-label", "Dismiss notification");
      closeBtn.textContent = "×";
      closeBtn.addEventListener("click", () => dismiss(id));
      el.appendChild(closeBtn);
    }

    region.appendChild(el);
    // Force layout so the show transition actually runs (class added on
    // next frame rather than at creation).
    requestAnimationFrame(() => el.classList.add("toast--show"));

    if (duration > 0) {
      let remaining = duration;
      let timerStart = Date.now();
      let timer = setTimeout(() => dismiss(id), remaining);

      // Pause the auto-dismiss timer while hovered/focused, so a user
      // reading a message doesn't have it vanish mid-read.
      const pause = () => {
        clearTimeout(timer);
        remaining -= Date.now() - timerStart;
      };
      const resume = () => {
        if (remaining <= 0) {
          dismiss(id);
          return;
        }
        timerStart = Date.now();
        timer = setTimeout(() => dismiss(id), remaining);
      };
      el.addEventListener("mouseenter", pause);
      el.addEventListener("mouseleave", resume);
      el.addEventListener("focusin", pause);
      el.addEventListener("focusout", resume);
    }

    return id;
  }

  window.LendingToast = {
    show: (msg, opts) => show(msg, { ...opts, variant: "info" }),
    success: (msg, opts) => show(msg, { ...opts, variant: "success" }),
    error: (msg, opts) => show(msg, { ...opts, variant: "error" }),
    dismiss,
  };
})(window, document);