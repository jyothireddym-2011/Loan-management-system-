# Restructured into the review's recommended layout

This is the same code from `lendingfrontend-refactor-1.zip`, reorganized into
the `src/` layout the review document proposed:

```
src/
├── components/   toast.js, confirmDialog.js       (reusable UI widgets)
├── pages/        one folder per screen, html + its own js
│   ├── login/
│   ├── enter-lender/
│   ├── pay/
│   ├── remove/
│   └── loan-registry/
├── services/     apiClient.js, lendingService.js  (the API layer)
├── utils/        validators.js                    (shared validation rules)
├── assets/       css/components.css
└── layouts/      empty — see note below
```

## What changed to make this work

This project has no build tool (no bundler, no npm), so it's plain
`<script src="...">` / `<link href="...">` tags — moving files means every
relative path in every `.html` had to be rewritten by hand. That's done:
each page now points at `../../services/...`, `../../utils/...`,
`../../components/...`, and `../../assets/css/components.css` instead of
the old `../shared/...` paths. Cross-page links (e.g. the "Back to services"
link in `pay.html`/`remove.html`, and the duplicate-borrower link in
`enter-lender.html`) were updated to the new `pages/<name>/` paths too.

## `layouts/` is empty, and `hooks/` doesn't exist

Two items from the review's folder list don't map onto this codebase as-is:

- **`hooks/`** is a React concept (custom hooks). There's no React here, so
  there's nothing to put in it — I left it out rather than create a folder
  with nothing meaningful inside.
- **`layouts/`** would hold a shared page shell (header/nav/footer) if one
  existed. Right now every page is a fully standalone `.html` file with no
  common chrome, so there's no layout markup to extract yet. If you want
  one, the pattern would be: pull the shared `<head>` tags + any shared nav
  markup into `layouts/main.html`, and load it via a small `fetch()` +
  inject script, or a templating step — but that's a real feature to build,
  not a rename, so I didn't fabricate a layout file.

## Files referenced but not present in the zip

The original app referenced several files that this zip never included
(they were presumably left out on purpose, or never checked in). These
`<link>`/`<script>` tags were **removed** during the move rather than
pointed at broken paths:

- Per-page stylesheets: `login/css/style.css`, `enter-lender.css`,
  `pay.css`, `remove.css`, `style.css` (loan registry)
- `api-config.js` (defined `API_BASE`, loaded before `apiClient.js`)
- `service-app/service.html` (the "Back to services" links now point at
  `pages/loan-registry/index.html` as the closest stand-in — adjust if you
  have an actual services landing page)
- `Loan_Agreement_Form-4.docx` (download link in the loan registry page)

If you have these files, drop the per-page CSS into `assets/css/<page>.css`
and add a `<link>` back in that page's `.html`, and put `api-config.js`
in `services/` alongside `apiClient.js`.

## Everything else is unchanged

No logic was touched — `apiClient.js`, `lendingService.js`,
`validators.js`, `toast.js`, `confirmDialog.js`, and each page's JS are
byte-for-byte the same as in the original zip. `ORIGINAL_README.md` (this
folder) has the original review-response writeup for context on what the
shared layer actually does.
