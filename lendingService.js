/**
 * shared/js/lendingService.js
 *
 * Domain service layer sitting on top of apiClient.js.
 * Pages call these functions instead of knowing any endpoint URLs —
 * this is the "services/loanService.js, borrowerService.js..." layer
 * called out in the code review. Kept as one file here since the
 * backend already groups these under /api/lending/*; split further
 * (authService.js, loanService.js, paymentService.js) if the API grows.
 *
 * ⚠️ PII note: lookupBorrower/checkDuplicate currently send the Aadhaar
 * number as part of the URL (path or query string). URLs are commonly
 * logged by browsers, proxies, and server access logs, so this is worth
 * revisiting with whoever owns backend/infra — a POST-with-body lookup
 * would avoid a government ID number ever landing in a URL/log line.
 * Not changed here since it requires a backend contract change; flagging
 * so it isn't lost.
 */
(function (window) {
  "use strict";

  const api = window.LendingAPI;

  /**
   * Normalizes an Aadhaar value to digits only and throws a clear,
   * local error before a request is ever made if it's not 12 digits —
   * cheaper and clearer than letting a malformed URL reach the backend.
   * @param {string} aadhaar
   * @returns {string} exactly 12 digits
   */
  function requireAadhaar(aadhaar) {
    const digits = String(aadhaar || "").replace(/\D/g, "");
    if (digits.length !== 12) {
      throw new api.ApiError("Aadhaar number must be exactly 12 digits.", { code: "VALIDATION" });
    }
    return digits;
  }

  /**
   * Validates a monetary amount is a finite, non-negative number.
   * Deliberately does NOT default invalid input to 0 — a silent 0 could
   * produce a misleading duplicate-check or payment result rather than
   * failing loudly at the point of the mistake.
   * @param {*} amount
   * @param {{ allowZero?: boolean }} [opts]
   * @returns {number}
   */
  function requireAmount(amount, { allowZero = true } = {}) {
    const n = Number(amount);
    if (!Number.isFinite(n) || n < 0 || (!allowZero && n === 0)) {
      throw new api.ApiError("Amount must be a valid non-negative number.", { code: "VALIDATION" });
    }
    return n;
  }

  window.LendingService = {
    /**
     * Look up a borrower/loan record by Aadhaar number.
     * @param {string} aadhaar - 12-digit Aadhaar number (formatting/spaces are stripped)
     * @returns {Promise<{ record: object }>}
     */
    lookupBorrower(aadhaar) {
      const digits = requireAadhaar(aadhaar);
      return api.get(`/api/lending/${encodeURIComponent(digits)}`);
    },

    /**
     * Live duplicate check used while filling out the "enter lender" form.
     * @param {string} aadhaar - 12-digit Aadhaar number
     * @param {number} [newAmount] - the amount currently entered in the form; required, not defaulted
     * @returns {Promise<{ duplicate: object|null }>}
     */
    checkDuplicate(aadhaar, newAmount) {
      const digits = requireAadhaar(aadhaar);
      const amount = requireAmount(newAmount, { allowZero: true });
      const params = new URLSearchParams({
        aadhaar_number: digits,
        new_amount: String(amount),
      });
      return api.get(`/api/lending/check-duplicate?${params.toString()}`);
    },

    /**
     * Create a new lender/loan record.
     * @param {object} payload - form fields for the new record (name, aadhaar_number, amount, etc.)
     * @returns {Promise<object>} the created record, as returned by the backend
     */
    createLoan(payload) {
      return api.post("/api/lending/create", payload);
    },

    /**
     * Update an existing loan/borrower record.
     * TODO: confirm the exact endpoint + method with backend — assumed
     * PUT /api/lending/update based on the existing REST-ish pattern
     * (create/remove/pay), but this hasn't been verified against a real
     * route yet. Used by the registry page's "Edit Borrower" flow.
     * @param {string} id - borrower/record ID (e.g. "BR-0001") or Aadhaar, whichever the backend expects
     * @param {object} payload - updated fields
     * @returns {Promise<object>} the updated record
     */
    updateLoan(id, payload) {
      if (!id) {
        throw new api.ApiError("A record ID is required to update a loan.", { code: "VALIDATION" });
      }
      return api.put(`/api/lending/update/${encodeURIComponent(id)}`, payload);
    },

    /**
     * Remove a loan record.
     * @param {object} payload - { borrower_name, aadhaar_number, password, confirm_password }
     * @returns {Promise<{ message: string }>}
     */
    removeLoan(payload) {
      return api.delete("/api/lending/remove", payload);
    },

    /**
     * Record a payment against an existing loan.
     * @param {object} payload - { borrower_name, aadhaar_number, paying_amount, agreement_filename, password, confirm_password }
     * @returns {Promise<object>} the updated record with old/new balance and risk info
     */
    recordPayment(payload) {
      return api.post("/api/lending/pay", payload);
    },

    /**
     * List/query loan records for the registry's "Query Records" tab.
     * TODO: confirm the exact endpoint, param names, and response shape
     * with backend — assumed GET /api/lending/list with optional filter/
     * sort query params, following the same pattern as checkDuplicate.
     * Currently unverified; the registry page cannot fully implement its
     * Query tab against a real backend until this is confirmed.
     * @param {{ filter?: string, sort?: 'recent'|'name'|'amount' }} [options]
     * @returns {Promise<{ records: object[], count: number }>}
     */
    listLoans({ filter = "", sort = "recent" } = {}) {
      const params = new URLSearchParams();
      if (filter) params.set("filter", filter);
      if (sort) params.set("sort", sort);
      const qs = params.toString();
      return api.get(`/api/lending/list${qs ? `?${qs}` : ""}`);
    },
  };
})(window);