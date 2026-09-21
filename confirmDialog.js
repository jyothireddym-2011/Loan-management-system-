/**
 * shared/js/confirmDialog.js
 *
 * Reusable confirmation dialog for destructive or high-stakes actions
 * (delete a loan record, submit a payment, confirm an upload) —
 * addresses the "confirmation dialogs" gap noted in the UI/UX review.
 *
 * Usage:
 *   const ok = await LendingConfirm.ask("Remove this loan record? This can't be undone.");
 *   if (!ok) return;
 *
 *   // Advanced usage:
 *   const ok = await LendingConfirm.ask("Delete 12 records permanently?", {
 *     title: "Confirm bulk delete",
 *     confirmLabel: "Delete",
 *     cancelLabel: "Keep them",
 *     tone: "danger",       // "danger" | "default"
 *     confirmDelayMs: 0     // require a short pause before Confirm is clickable
 *   });
 */
(function (window, document) {
  "use strict";

  // Stack of currently-open dialogs, topmost last. Enables correct
  // Escape/Tab handling when dialogs are opened on top of one another.
  const stack = [];

  const FOCUSABLE_SELECTOR = [
    "a[href]",
    "button:not([disabled])",
    "textarea:not([disabled])",
    "input:not([disabled])",
    "select:not([disabled])",
    '[tabindex]:not([tabindex="-1"])',
  ].join(",");

  function getFocusable(container) {
    return Array.from(container.querySelectorAll(FOCUSABLE_SELECTOR)).filter(
      (el) => el.offsetParent !== null // skip hidden elements
    );
  }

  function lockBodyScroll() {
    if (stack.length === 0) {
      document.body.dataset.confirmPrevOverflow = document.body.style.overflow || "";
      document.body.style.overflow = "hidden";
    }
  }

  function unlockBodyScrollIfEmpty() {
    if (stack.length === 0) {
      document.body.style.overflow = document.body.dataset.confirmPrevOverflow || "";
      delete document.body.dataset.confirmPrevOverflow;
    }
  }

  function ask(message, options = {}) {
    const {
      title = null,
      confirmLabel = "Confirm",
      cancelLabel = "Cancel",
      tone = "danger", // "danger" | "default" — controls confirm button styling
      confirmDelayMs = 0, // if >0, confirm button is disabled for this long on open
      closeOnOverlayClick = true,
    } = options;

    return new Promise((resolve) => {
      const previouslyFocused = document.activeElement;

      const overlay = document.createElement("div");
      overlay.className = "confirm-overlay";

      overlay.innerHTML = `
        <div class="confirm-dialog" role="alertdialog" aria-modal="true"
             ${title ? 'aria-labelledby="confirmTitle"' : ""}
             aria-describedby="confirmMsg">
          ${title ? `<h2 id="confirmTitle" class="confirm-title"></h2>` : ""}
          <p id="confirmMsg" class="confirm-message"></p>
          <div class="confirm-actions">
            <button type="button" class="btn secondary" data-action="cancel"></button>
            <button type="button" class="btn ${tone === "danger" ? "danger" : "primary"}" data-action="confirm"></button>
          </div>
        </div>`;

      const dialog = overlay.querySelector(".confirm-dialog");
      const cancelBtn = overlay.querySelector('[data-action="cancel"]');
      const confirmBtn = overlay.querySelector('[data-action="confirm"]');
      const titleEl = overlay.querySelector(".confirm-title");

      overlay.querySelector(".confirm-message").textContent = message;
      cancelBtn.textContent = cancelLabel;
      confirmBtn.textContent = confirmLabel;
      if (titleEl) titleEl.textContent = title;

      document.body.appendChild(overlay);
      lockBodyScroll();

      // Optional: briefly disable Confirm to prevent reflexive double-Enter
      // on destructive actions (e.g. rapid repeated deletes).
      if (confirmDelayMs > 0) {
        confirmBtn.disabled = true;
        setTimeout(() => {
          confirmBtn.disabled = false;
        }, confirmDelayMs);
      }

      const entry = { overlay, cancelBtn, confirmBtn, dialog };
      stack.push(entry);

      const isTopmost = () => stack[stack.length - 1] === entry;

      const cleanup = (result) => {
        const idx = stack.indexOf(entry);
        if (idx !== -1) stack.splice(idx, 1);

        overlay.remove();
        document.removeEventListener("keydown", onKey, true);
        unlockBodyScrollIfEmpty();

        if (previouslyFocused && typeof previouslyFocused.focus === "function") {
          previouslyFocused.focus();
        }
        resolve(result);
      };

      const onKey = (e) => {
        // Only the topmost dialog responds to keyboard input.
        if (!isTopmost()) return;

        if (e.key === "Escape") {
          e.stopPropagation();
          cleanup(false);
          return;
        }

        if (e.key === "Tab") {
          const focusable = getFocusable(dialog);
          if (focusable.length === 0) return;
          const first = focusable[0];
          const last = focusable[focusable.length - 1];

          if (e.shiftKey && document.activeElement === first) {
            e.preventDefault();
            last.focus();
          } else if (!e.shiftKey && document.activeElement === last) {
            e.preventDefault();
            first.focus();
          } else if (!focusable.includes(document.activeElement)) {
            // Focus somehow escaped the dialog — pull it back in.
            e.preventDefault();
            first.focus();
          }
        }
      };
      // Capture phase so a topmost dialog can intercept before page handlers.
      document.addEventListener("keydown", onKey, true);

      cancelBtn.addEventListener("click", () => cleanup(false));
      confirmBtn.addEventListener("click", () => {
        if (confirmBtn.disabled) return;
        cleanup(true);
      });

      if (closeOnOverlayClick) {
        overlay.addEventListener("click", (e) => {
          if (e.target === overlay) cleanup(false);
        });
      }

      cancelBtn.focus();
    });
  }

  /** Force-close all open dialogs (e.g. on route change/logout), resolving each as false. */
  function closeAll() {
    // Iterate over a copy since cleanup mutates `stack`.
    [...stack].reverse().forEach((entry) => entry.cancelBtn.click());
  }

  window.LendingConfirm = { ask, closeAll };
})(window, document);