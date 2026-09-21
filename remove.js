/**
 * remove-app/remove.js — refactored
 *
 * Same behavior as the original, rebuilt on the shared layer:
 *   - shared/js/apiClient.js    (no more raw fetch + duplicated try/catch)
 *   - shared/js/lendingService.js (no endpoint URLs live in this file anymore)
 *   - shared/js/validators.js   (Aadhaar/password rules shared with every other form)
 *   - shared/js/toast.js        (was a copy-pasted 10-line function)
 *   - shared/js/confirmDialog.js (the "confirm before permanently deleting" step —
 *     the single most important line in this file, since this is the one
 *     irreversible action in the whole app)
 */
(function () {
  "use strict";

  const V = window.LendingValidators;

  const aadharInput = document.getElementById("aadhar");
  aadharInput.addEventListener("input", () => {
    aadharInput.value = V.formatAadhaar(aadharInput.value);
  });

  // Password visibility toggle (both fields)
  document.querySelectorAll(".password-toggle").forEach((btn) => {
    btn.addEventListener("click", () => {
      const input = document.getElementById(btn.dataset.target);
      const showing = input.type === "text";
      input.type = showing ? "password" : "text";
      btn.setAttribute("aria-pressed", String(!showing));
      btn.querySelector('[aria-hidden="true"]').textContent = showing ? "Show" : "Hide";
      btn.querySelector(".visually-hidden").textContent = showing ? "Show password" : "Hide password";
    });
  });

  function setError(id, msg) {
    const el = document.getElementById("err-" + id);
    if (el) el.textContent = msg || "";
  }

  function clearAllErrors() {
    ["bname", "aadhar", "password", "confirmPassword"].forEach((id) => setError(id, ""));
  }

  function clearPasswordFields() {
    document.getElementById("password").value = "";
    document.getElementById("confirmPassword").value = "";
  }

  const form = document.getElementById("removeForm");
  const submitBtn = document.getElementById("submitBtn");
  const resultCard = document.getElementById("resultCard");
  const resultHeading = document.getElementById("resultHeading");
  const resultMessage = document.getElementById("resultMessage");

  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const name = document.getElementById("bname").value.trim();
    const aadharDigits = aadharInput.value.replace(/\D/g, "");
    // Passwords are intentionally NOT trimmed — see login.js for why.
    const password = document.getElementById("password").value;
    const confirmPassword = document.getElementById("confirmPassword").value;

    clearAllErrors();

    const { valid, errors } = V.validateForm({
      bname: { value: name, rules: [{ test: V.isNonEmpty, message: "Borrower name is required." }] },
      aadhar: { value: aadharDigits, rules: [{ test: V.isValidAadhaar, message: "Enter a valid 12-digit Aadhar number." }] },
      password: { value: password, rules: [{ test: (v) => v.length >= 6, message: "Password must be at least 6 characters." }] },
      confirmPassword: {
        value: confirmPassword,
        rules: [{ test: (v) => V.passwordsMatch(password, v), message: "Passwords do not match." }],
      },
    });

    const fieldOrder = ["bname", "aadhar", "password", "confirmPassword"];
    fieldOrder.forEach((id) => setError(id, errors[id]));

    if (!valid) {
      window.LendingToast.error("Please fix the highlighted fields");
      // Move focus to the first invalid field — especially important on a
      // delete form, where a keyboard/screen reader user should be routed
      // straight to what's stopping the action.
      const firstInvalidId = fieldOrder.find((id) => errors[id]);
      if (firstInvalidId) {
        const el = document.getElementById(firstInvalidId);
        if (el) el.focus();
      }
      clearPasswordFields();
      return;
    }

    const confirmed = await window.LendingConfirm.ask(
      `This will permanently remove the lending record for ${name}. This can't be undone.`,
      { confirmLabel: "Remove record" }
    );
    if (!confirmed) return;

    // Guard against a second click/Enter firing another delete request
    // while the first is still in flight — this call is not idempotent.
    submitBtn.disabled = true;
    const originalLabel = submitBtn.textContent;
    submitBtn.textContent = "Removing…";

    let result;
    try {
      result = await window.LendingService.removeLoan({
        borrower_name: name,
        aadhaar_number: aadharDigits,
        password,
        confirm_password: confirmPassword,
      });
    } catch (err) {
      window.LendingToast.error(window.LendingAPI.friendlyMessage(err));
      clearPasswordFields();
      submitBtn.disabled = false;
      submitBtn.textContent = originalLabel;
      return;
    }

    resultMessage.textContent = result.message;
    resultCard.classList.remove("hidden");
    form.reset();
    window.LendingToast.success("Lending record removed");
    resultCard.scrollIntoView({ behavior: "smooth", block: "start" });
    // Move focus to the confirmation heading so screen reader/keyboard
    // users immediately hear/see that the deletion completed.
    resultHeading.focus();

    // Re-enable in case the user navigates back to this form via history
    // rather than the back-link, without a full page reload.
    submitBtn.disabled = false;
    submitBtn.textContent = originalLabel;
  });
})();