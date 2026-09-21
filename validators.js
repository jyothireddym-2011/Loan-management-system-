/**
 * shared/js/validators.js
 *
 * Field-level validation used across every form (login, enter-lender,
 * pay, remove). Centralizing these means a rule only changes in one
 * place, and every page shows the same error copy.
 *
 * Note: some of these are deliberately *lenient* checksum-wise
 * (see isValidAadhaar) — real Aadhaar/phone validity checks belong on
 * the backend as the source of truth. These exist to reject obviously
 * malformed input early and give fast, friendly feedback, not to be
 * the final authority.
 */
(function (window) {
  "use strict";

  const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  // Indian mobile numbers always start with 6, 7, 8, or 9.
  const PHONE_RE = /^[6-9]\d{9}$/;
  const MIN_PASSWORD_LENGTH = 6;

  /** @param {*} raw @returns {string} digits only, e.g. "123456789012" */
  function aadhaarDigits(raw) {
    return String(raw || "").replace(/\D/g, "");
  }

  /** @param {string} raw @returns {string} spaced as "1234 5678 9012" */
  function formatAadhaar(raw) {
    const digits = aadhaarDigits(raw).slice(0, 12);
    return digits.replace(/(\d{4})(?=\d)/g, "$1 ");
  }

  /**
   * Checks an Aadhaar number is plausibly well-formed: exactly 12 digits,
   * not all-zero, and doesn't start with 0 or 1 (real Aadhaar numbers
   * never do). Does NOT verify the Verhoeff checksum — that's a deeper
   * check best left to the backend, which has the authoritative rules.
   * This exists to catch obviously-fake input (e.g. "000000000000")
   * before it ever reaches the network.
   * @param {*} raw
   * @returns {boolean}
   */
  function isValidAadhaar(raw) {
    const digits = aadhaarDigits(raw);
    if (digits.length !== 12) return false;
    if (/^0+$/.test(digits)) return false;
    if (/^[01]/.test(digits)) return false;
    return true;
  }

  /** @param {*} raw @returns {boolean} true if a 10-digit Indian mobile number */
  function isValidPhone(raw) {
    return PHONE_RE.test(String(raw || "").trim());
  }

  /** @param {*} raw @returns {boolean} */
  function isValidEmail(raw) {
    return EMAIL_RE.test(String(raw || "").trim());
  }

  /** @param {*} raw @param {{min?: number}} [opts] @returns {boolean} */
  function isValidAmount(raw, { min = 0 } = {}) {
    const n = Number(raw);
    return Number.isFinite(n) && n >= min;
  }

  /** @param {*} raw @returns {boolean} true if a non-empty, non-whitespace string */
  function isNonEmpty(raw) {
    return String(raw || "").trim().length > 0;
  }

  /**
   * Checks a password meets the app-wide minimum length. This is the
   * single source of truth for that rule — every form should call this
   * instead of inlining `v.length >= 6`, so the minimum only ever
   * changes in one place.
   * @param {*} raw
   * @returns {boolean}
   */
  function isValidPassword(raw) {
    return typeof raw === "string" && raw.length >= MIN_PASSWORD_LENGTH;
  }

  /**
   * Pure equality check, independent of the length rule — composable
   * with isValidPassword via validateForm's rule-array pattern rather
   * than being bundled into one function.
   * @param {*} a
   * @param {*} b
   * @returns {boolean}
   */
  function valuesMatch(a, b) {
    return a === b;
  }

  /**
   * @deprecated Use isValidPassword(a) + valuesMatch(a, b) as two separate
   * rules instead — kept here only so any not-yet-updated caller doesn't
   * break. Will be removed once every page is migrated.
   * @param {*} a
   * @param {*} b
   * @returns {boolean}
   */
  function passwordsMatch(a, b) {
    return isValidPassword(a) && valuesMatch(a, b);
  }

  /**
   * Runs a set of {value, rules} field checks and returns
   * { valid: boolean, errors: { fieldName: message } }.
   * Lets a page declare validation once instead of a chain of ifs.
   * Rules for a field are checked in order; the first failing rule's
   * message is recorded and remaining rules for that field are skipped.
   * @param {Object.<string, {value: *, rules: Array<{test: Function, message: string}>}>} fields
   * @returns {{valid: boolean, errors: Object.<string, string>}}
   */
  function validateForm(fields) {
    const errors = {};
    for (const [name, { value, rules }] of Object.entries(fields)) {
      for (const rule of rules) {
        if (!rule.test(value)) {
          errors[name] = rule.message;
          break;
        }
      }
    }
    return { valid: Object.keys(errors).length === 0, errors };
  }

  window.LendingValidators = {
    MIN_PASSWORD_LENGTH,
    formatAadhaar,
    isValidAadhaar,
    isValidPhone,
    isValidEmail,
    isValidAmount,
    isNonEmpty,
    isValidPassword,
    valuesMatch,
    passwordsMatch, // deprecated, see note above
    validateForm,
  };
})(window);