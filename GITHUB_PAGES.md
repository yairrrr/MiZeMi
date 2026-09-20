# MiZeMi project page

The presentation site in `docs/` is plain HTML, CSS and the **unchanged original** `frontend/src/assets/mizemi-logo.png`. It has no JavaScript, build command, dependencies, backend, analytics, cookies or environment configuration. Its example round is an illustration, not a playable room. All play links open the real Render application in the same tab.

- **Project / landing page:** https://yairrrr.github.io/MiZeMi/
- **Live multiplayer application:** https://mizemi-frontend.onrender.com

The existing Render frontend, backend and Neon database remain separate. Only `docs/` is published by Pages. Styles and image references are relative, so they resolve under `/MiZeMi/` as well as other preview prefixes. The canonical/social metadata uses the public project URL. The only image is the existing 1.4 MB logo; it is reused as the favicon and does not require a second image download. There are no third-party font or script requests.

## Enable GitHub Pages manually

Nothing has been pushed, merged, deployed or enabled by this change.

1. Push the `codex/github-pages-landing` branch yourself, open a pull request and merge the reviewed landing-page changes into `main`. Ensure `main` contains `docs/index.html`, `docs/.nojekyll`, and both files in `docs/assets/`.
2. On GitHub, open **yairrrr/MiZeMi → Settings → Pages** (under **Code, planning, and automation**).
3. Under **Build and deployment → Source**, select **Deploy from a branch**.
4. Select branch **main** and folder **/docs**, then click **Save**.
5. Wait for the Pages publication to finish. The Pages settings screen will show the site link; publication progress also appears under **Actions**.
6. Open **https://yairrrr.github.io/MiZeMi/**. Check the logo and the play button, which should take you to **https://mizemi-frontend.onrender.com**.

No custom GitHub Actions workflow is needed because there is nothing to compile. `.nojekyll` tells Pages to serve the static files. No custom domain, repository visibility change, Render change or Neon change is required. See [GitHub’s publishing-source documentation](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site).

## Preview locally

From the repository root:

```sh
python3 -m http.server 4317 --bind 127.0.0.1 --directory docs
```

Open **http://127.0.0.1:4317/**. To reproduce the exact project prefix, use a temporary preview directory (the symlink is local only and is not part of the published site):

```sh
preview_dir=$(mktemp -d)
ln -s "$PWD/docs" "$preview_dir/MiZeMi"
python3 -m http.server 4317 --bind 127.0.0.1 --directory "$preview_dir"
```

Open **http://127.0.0.1:4317/MiZeMi/**. Stop the first server before starting the second. No Node installation or frontend build is needed to preview this page.

## Maintain the page

- Edit `docs/index.html` and `docs/assets/styles.css`; do not change game code to update this presentation.
- Keep the public Render URL consistent in all play links and the README.
- If the official logo changes, copy the actual repository asset into `docs/assets/` unchanged.
- Keep all publishable content in `docs/` public. Never put environment files, tokens or credentials there.
- Preserve the skip link, heading order, language attributes, visible keyboard focus, reduced-motion support and mobile layouts.

## Verification — 2026-09-15

Local Chromium checks used **http://127.0.0.1:4317/MiZeMi/**, not just the domain root.

- Visually reviewed desktop (1440 × 1000), mobile (390 × 844), the complete page and the mobile steps/features sections. The original logo, cream background, purple CTA, rounded cards and yellow/teal accents match the application.
- Checked widths **320, 375, 390, 600, 768, 960, 1024, 1440 and 1920 px**: no horizontal overflow or clipped content. At 200% text size, the desktop page still reflows without horizontal overflow.
- All assets loaded under `/MiZeMi/`; every logo copy matched the original SHA-256. Published files total **1,449,478 bytes**, of which **1,426,677 bytes** are the unchanged logo.
- Zero console errors, failed resource requests or third-party resource requests on the landing page. No scripts, forms, frames, credentials or environment configuration are present.
- All four play links use the public Render URL with no new-tab target. Clicking the hero CTA navigated the same browser tab to the live application: **HTTP 200**, title **MiZeMi**.
- Keyboard-tested all seven desktop links, the skip-to-main link, its visible focus outline and the “How it works” anchor. Interactive targets are at least 44 px high. Reduced-motion preferences are respected. Hebrew snippets carry `lang="he"` and `dir="rtl"`; lists retain explicit list semantics.
- Checked twelve text/background and focus color combinations. Text contrast ranged from **5.40:1 to 14.54:1**; the primary button is **6.33:1**. This is a basics check, not a claim of a complete accessibility certification.
- README project/live links match the requested public URLs.

Repository checks:

| Command | Result |
| --- | --- |
| `npm --prefix frontend run type-check` | Passed |
| `npm --prefix frontend test` | 300 passed in 12 files |
| `npm --prefix frontend run build` | Passed |
| `.venv/bin/python -m pytest backend/tests -q` | 1,186 passed; 2 optional live PostgreSQL cases skipped; one existing Starlette deprecation warning |
| `npm --prefix frontend run test:e2e` | 2 passed, 1 failed at the existing knowledge-explanation assertion described below |
| `.venv/bin/python scripts/check_secrets.py` | Zero high-confidence findings; zero local real environment files |
| `git diff --check` | Passed |

**Existing E2E limitation:** the Hebrew knowledge scenario completed the game, score checks, privacy checks, reconnects and final leaderboard, then failed `frontend/e2e/classroom.spec.ts:212`. That assertion requires one explanation to contain both specific film titles “המסור” and “לזמן את הרוע”. The game source and test are unchanged by this landing-page work; this result does not constitute a fully passing E2E suite. The assertion was left for the question-engine/test-maintenance work rather than changing game behavior in a presentation-only change.


## Legal/accessibility follow-up — 18 September 2026

The landing footer now points intentionally to `https://mizemi-frontend.onrender.com/privacy?lang=en`, `/terms?lang=en` and `/accessibility?lang=en`, plus Hebrew privacy. There is one authoritative bilingual copy in the game application. Its routes must be deployed in a separately authorized release before these new links are advertised. Local tests verify exact destinations; no deployment/visibility change has been made.

Landmark semantics, keyboard focus, numeric sample-result meaning, and text enlargement/reflow at 320px were checked and improved. The earlier E2E limitation above is historical; the current complete-suite result is recorded in `LEGAL_IMPLEMENTATION_REPORT.md`. No logo or dataset license was changed.
