/**
 * pay-app/pay.js — refactored
 *
 * Same behavior as the original, rebuilt on the shared layer:
 *   - shared/js/apiClient.js    (no more raw fetch + duplicated try/catch)
 *   - shared/js/lendingService.js (no endpoint URLs live in this file anymore)
 *   - shared/js/validators.js   (Aadhaar/amount/password rules shared with every other form)
 *   - shared/js/toast.js        (was a copy-pasted 10-line function)
 *   - shared/js/confirmDialog.js (adds the "confirm before submitting a payment" step from the UI/UX review)
 */
(function () {
  "use strict";

  const V = window.LendingValidators;

  const aadharInput = document.getElementById("aadhar");
  const payingAmountInput = document.getElementById("payingAmount");
  const balancePanel = document.getElementById("balancePanel");
  const oldAmountEl = document.getElementById("oldAmount");
  const payingPreviewEl = document.getElementById("payingPreview");
  const newAmountEl = document.getElementById("newAmount");

  let currentRecord = null;
  let lookupTimer = null;

  aadharInput.addEventListener("input", () => {
    aadharInput.value = V.formatAadhaar(aadharInput.value);
    scheduleLookup();
  });

  function resetBalancePreview() {
    currentRecord = null;
    balancePanel.classList.add("hidden");
  }

  function updateBalancePreview() {
    if (!currentRecord) {
      balancePanel.classList.add("hidden");
      return;
    }
    const paying = Number(payingAmountInput.value.replace(/,/g, "") || 0);
    const newAmt = currentRecord.amount - paying;
    oldAmountEl.textContent = currentRecord.amount;
    payingPreviewEl.textContent = paying || 0;
    newAmountEl.textContent = newAmt >= 0 ? newAmt : "Exceeds balance";
    balancePanel.classList.remove("hidden");
  }

  async function lookupRecord() {
    const digits = aadharInput.value.replace(/\D/g, "");
    if (!V.isValidAadhaar(digits)) {
      resetBalancePreview();
      return;
    }
    try {
      const data = await window.LendingService.lookupBorrower(digits);
      currentRecord = data.record;
      updateBalancePreview();
    } catch (err) {
      // Live preview is best-effort — a failed lookup here shouldn't
      // interrupt typing. Errors surface for real on actual submit.
      resetBalancePreview();
    }
  }

  function scheduleLookup() {
    clearTimeout(lookupTimer);
    lookupTimer = setTimeout(lookupRecord, 350);
  }

  payingAmountInput.addEventListener("input", updateBalancePreview);

  const agreementFile = document.getElementById("agreementFile");
  const agreementFileName = document.getElementById("agreementFileName");
  agreementFile.addEventListener("change", () => {
    agreementFileName.textContent = agreementFile.files[0] ? agreementFile.files[0].name : "No file chosen";
  });

  const dualAmountBtn = document.getElementById("dualAmountBtn");
  const dualAmountResult = document.getElementById("dualAmountResult");
  dualAmountBtn.addEventListener("click", () => {
    if (!currentRecord) {
      dualAmountResult.textContent = "Look up a borrower by Aadhar number first.";
      return;
    }
    const paying = Number(payingAmountInput.value.replace(/,/g, "") || 0);
    if (!paying || paying <= 0) {
      dualAmountResult.textContent = "Enter a paying amount first.";
      return;
    }
    const dual = currentRecord.amount - paying;
    dualAmountResult.textContent =
      dual >= 0 ? `${currentRecord.amount} − ${paying} = ${dual}` : `${currentRecord.amount} − ${paying} = ${dual} (exceeds balance)`;
    updateBalancePreview();
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
    ["bname", "aadhar", "payingAmount", "agreementFile", "password", "confirmPassword"].forEach((id) => setError(id, ""));
  }

  function clearPasswordFields() {
    document.getElementById("password").value = "";
    document.getElementById("confirmPassword").value = "";
  }

  const form = document.getElementById("payForm");
  const resultCard = document.getElementById("resultCard");
  const resultHeading = document.getElementById("resultHeading");
  const resultList = document.getElementById("resultList");

  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const name = document.getElementById("bname").value.trim();
    const aadharDigits = aadharInput.value.replace(/\D/g, "");
    const payingAmountRaw = payingAmountInput.value.replace(/,/g, "");
    // Passwords are intentionally NOT trimmed — see login.js for why.
    const password = document.getElementById("password").value;
    const confirmPassword = document.getElementById("confirmPassword").value;

    clearAllErrors();

    const { valid, errors } = V.validateForm({
      bname: { value: name, rules: [{ test: V.isNonEmpty, message: "Borrower name is required." }] },
      aadhar: { value: aadharDigits, rules: [{ test: V.isValidAadhaar, message: "Enter a valid 12-digit Aadhar number." }] },
      payingAmount: {
        value: payingAmountRaw,
        rules: [
          { test: (v) => V.isValidAmount(v, { min: 0.01 }), message: "Enter a valid paying amount." },
          {
            test: (v) => !currentRecord || Number(v) <= currentRecord.amount,
            message: "Paying amount can't exceed the existing balance.",
          },
        ],
      },
      agreementFile: {
        value: agreementFile.files[0],
        rules: [{ test: (v) => !!v, message: "Please attach the loan agreement file to edit this record." }],
      },
      password: { value: password, rules: [{ test: (v) => v.length >= 6, message: "Password must be at least 6 characters." }] },
      confirmPassword: {
        value: confirmPassword,
        rules: [{ test: (v) => V.passwordsMatch(password, v), message: "Passwords do not match." }],
      },
    });

    const fieldOrder = ["bname", "aadhar", "payingAmount", "agreementFile", "password", "confirmPassword"];
    fieldOrder.forEach((id) => setError(id, errors[id]));

    if (!valid) {
      window.LendingToast.error("Please fix the highlighted fields");
      // Move focus to the first invalid field so keyboard and screen
      // reader users don't have to hunt for what's wrong.
      const firstInvalidId = fieldOrder.find((id) => errors[id]);
      if (firstInvalidId) {
        const el = document.getElementById(firstInvalidId);
        if (el) el.focus();
      }
      clearPasswordFields();
      return;
    }

    const confirmed = await window.LendingConfirm.ask(
      `Record a payment of ${payingAmountRaw} for ${name}? This updates the loan balance immediately.`,
      { confirmLabel: "Record payment" }
    );
    if (!confirmed) return;

    let result;
    try {
      result = await window.LendingService.recordPayment({
        borrower_name: name,
        aadhaar_number: aadharDigits,
        paying_amount: Number(payingAmountRaw),
        agreement_filename: agreementFile.files[0].name,
        password,
        confirm_password: confirmPassword,
      });
    } catch (err) {
      window.LendingToast.error(window.LendingAPI.friendlyMessage(err));
      return;
    }

    // Every field from the server is escaped before insertion, including
    // the risk label — no exceptions, since any of these could in principle
    // carry unexpected characters (corrupted record, backend bug, etc.).
    resultList.innerHTML = `
      <dt>Borrower name</dt><dd>${escapeHtml(result.borrower_name)}</dd>
      <dt>Lender name</dt><dd>${escapeHtml(result.lender_name)}</dd>
      <dt>Phone number</dt><dd>${escapeHtml(result.phone_number || "—")}</dd>
      <dt>Old amount</dt><dd>${escapeHtml(result.old_amount)}</dd>
      <dt>Paying amount</dt><dd>${escapeHtml(result.paying_amount)}</dd>
      <dt>New balance</dt><dd>${escapeHtml(result.new_amount)}</dd>
      <dt>Loan agreement</dt><dd>${escapeHtml(result.agreement_filename || "—")}</dd>
    `;

    const riskRaw = result.risk && result.risk.risk ? String(result.risk.risk) : "—";
    const riskClass = escapeHtml(riskRaw.toLowerCase());
    const riskLabel = escapeHtml(riskRaw);
    const badge = document.createElement("div");
    badge.className = "risk-badge-row";
    badge.innerHTML = `<span>Risk level:</span><span class="risk-badge ${riskClass}">${riskLabel}</span>`;
    resultCard.appendChild(badge);

    resultCard.classList.remove("hidden");
    window.LendingToast.success("Payment recorded successfully");
    resultCard.scrollIntoView({ behavior: "smooth", block: "start" });
    // Move focus to the result heading so screen reader/keyboard users
    // know the page changed and can immediately read the outcome.
    resultHeading.focus();

    form.reset();
    resetBalancePreview();
    dualAmountResult.textContent = "";
    agreementFileName.textContent = "No file chosen";
  });

  function escapeHtml(str) {
    return String(str).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }
})();