// login.js — Ledgerline login page logic
//
// Demonstrates two states on the same page:
//   1. No lender signed in yet  -> show the email/password/contact form
//   2. Lender already signed in -> show their details + Continue + Logout
//
// ⚠️ DEMO ONLY — NOT REAL AUTHENTICATION.
// `session` is kept in memory only (no localStorage/sessionStorage/backend
// call), so it resets on refresh, and ANY syntactically valid email +
// non-empty password + 10-digit number will "succeed." There is no password
// check against a real account. Before this ships anywhere reachable by
// non-developers (staging, demos, QA), wire this to the actual backend
// session/token (see the Flask "frontend" module — read session['lender']
// there, or call GET /api/auth/me here) and remove the console warning below.
console.warn(
  "[Ledgerline] login.js is running in DEMO MODE — no real authentication is happening."
);

const V = window.LendingValidators;

let session = null;

const loginCard = document.getElementById('loginCard');
const sessionCard = document.getElementById('sessionCard');
const loginForm = document.getElementById('loginForm');
const loginError = document.getElementById('loginError');
const loginHeading = document.getElementById('loginHeading');
const sessionHeading = document.getElementById('sessionHeading');

const fieldErrorEls = {
  email: document.getElementById('err-email'),
  password: document.getElementById('err-password'),
  contact: document.getElementById('err-contact'),
};

const FIELD_MESSAGES = {
  email: 'Enter a valid email address.',
  password: 'Enter your password.',
  contact: 'Enter a valid 10-digit mobile number.',
};

function clearFieldErrors() {
  Object.values(fieldErrorEls).forEach((el) => (el.textContent = ''));
}

function showSummaryError(message) {
  loginError.textContent = message;
  loginError.classList.add('visible');
}

function hideSummaryError() {
  loginError.textContent = '';
  loginError.classList.remove('visible');
}

function renderState() {
  if (session) {
    loginCard.classList.add('hidden');
    sessionCard.classList.remove('hidden');
    document.getElementById('sessionEmail').textContent = session.email;
    document.getElementById('sessionContact').textContent = session.contact;
    // Move focus to the new heading so screen reader and keyboard users
    // know the page state changed, rather than focus silently vanishing
    // with the removed submit button.
    sessionHeading.focus();
  } else {
    loginCard.classList.remove('hidden');
    sessionCard.classList.add('hidden');
    loginForm.reset();
    hideSummaryError();
    clearFieldErrors();
    loginHeading.focus();
  }
}

loginForm.addEventListener('submit', function (e) {
  e.preventDefault();

  const email = document.getElementById('email').value.trim();
  // Password is intentionally NOT trimmed — a leading/trailing space is
  // part of the value the user typed, and silently stripping it would
  // cause confusing mismatches once this is wired to real auth.
  const password = document.getElementById('password').value;
  const contact = document.getElementById('contact').value.trim();

  clearFieldErrors();

  const { valid, errors } = V.validateForm({
    email: { value: email, rules: [{ test: V.isValidEmail, message: 'invalid' }] },
    password: { value: password, rules: [{ test: V.isNonEmpty, message: 'invalid' }] },
    contact: { value: contact, rules: [{ test: V.isValidPhone, message: 'invalid' }] },
  });

  if (!valid) {
    // Show a specific message under each invalid field...
    Object.keys(errors || {}).forEach((field) => {
      if (fieldErrorEls[field]) {
        fieldErrorEls[field].textContent = FIELD_MESSAGES[field] || 'This field is invalid.';
      }
    });
    // ...plus one assertive summary so screen reader users get an
    // immediate, unambiguous "the form did not submit" announcement.
    showSummaryError('Please fix the highlighted fields and try again.');

    // Move focus to the first invalid field for keyboard/screen reader users.
    const firstInvalid = Object.keys(errors || {})[0];
    if (firstInvalid) {
      document.getElementById(firstInvalid).focus();
    }
    return;
  }

  hideSummaryError();

  // In the real app, this is where you'd call the backend, e.g.:
  //   const res = await fetch('/api/login', { method: 'POST', body: ... });
  //   if (!res.ok) { showSummaryError('Incorrect email or password.'); return; }
  // For this standalone demo, we just record the details as "already collected."
  session = { email, contact };
  window.LendingToast.success('Signed in (demo mode — not a real session)');
  renderState();
});

// Password visibility toggle
document.querySelectorAll('.password-toggle').forEach((btn) => {
  btn.addEventListener('click', () => {
    const input = document.getElementById(btn.dataset.target);
    const showing = input.type === 'text';
    input.type = showing ? 'password' : 'text';
    btn.setAttribute('aria-pressed', String(!showing));
    btn.querySelector('[aria-hidden="true"]').textContent = showing ? 'Show' : 'Hide';
    btn.querySelector('.visually-hidden').textContent = showing ? 'Show password' : 'Hide password';
  });
});

document.getElementById('continueBtn').addEventListener('click', function () {
  // In the real app this would navigate to the services/dashboard page.
  window.location.href = 'services.html';
});

document.getElementById('logoutBtn').addEventListener('click', function () {
  session = null;
  renderState();
});

renderState();