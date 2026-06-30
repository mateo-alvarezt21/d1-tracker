# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

**Mi Canasta D1** — a single-page meal-planning / grocery-budgeting web app for Colombia's Tiendas D1 supermarket. The UI and all content are in **Spanish (es-CO)**, and money is formatted in Colombian pesos (COP). Tagline: "Planea tu mercado en Tiendas D1."

The user enters a budget, number of days, number of people, a daily calorie target, and dietary preferences. The app generates a meal plan (breakfast/lunch/dinner per day), a categorized shopping list with real-looking D1 product prices, and per-recipe detail modals — all from hard-coded mock data. There is **no backend and no API**; nothing is persisted (state is in-memory only and resets on reload).

## Stack & running

- **Pure static site**: vanilla HTML + CSS + a single IIFE in `app.js`. No build step, no framework, no bundler, no dependencies, no `package.json`, no tests, no lint config. The only external resource is the Nunito font from Google Fonts.
- **Run it** by opening `index.html` directly, or serve the folder over HTTP (clipboard copy and fonts behave better over `http://`):
  ```bash
  python -m http.server 8000   # then open http://localhost:8000
  # or: npx serve .
  ```
- To change behavior, edit `app.js`/`styles.css` and refresh the browser. There is nothing to compile.

## Files

- `index.html` — static shell. Defines the persistent DOM skeleton: landing section, app view (header + progress bar + `#step1`/`#step2`/`#step3` panels), loading overlay, and the recipe modal. `#step1`'s form is authored in HTML; `#step2` and `#step3` are empty containers filled by JS.
- `app.js` — the entire application (single IIFE, strict mode). Contains state, mock data, compute functions, renderers, and event wiring.
- `styles.css` — all styling. Brand design tokens live in `:root` (`--red #E30613`, `--yellow #FFD100`, `--green #1aa563`, etc.). The `.hidden` class (`display:none!important`) is the universal show/hide mechanism used by the JS.

## Architecture (app.js)

A hand-rolled, framework-free state→render pattern. Understanding these pieces lets you work anywhere in the file:

- **Single `state` object** (view, loading, step 1–3, budget, days, people, calories, diet[], checked{}, recipe, copied) is the one source of truth.
- **Mock data is the model**: `recipes` (keyed `b1..b4` breakfast, `l1..l4` lunch, `d1..d4` dinner — note `dPool`/dinner ids `d1..d4` and shopping `Lácteos` ids `l1..l3` are separate keyspaces), the `bPool`/`lPool`/`dPool` rotation arrays, and `shopBase` (categorized grocery items with base quantities/prices). Editing menus or prices means editing these literals.
- **Pure compute functions** derive everything from `state` + mock data: `scaledShop()` scales quantities by `(days × people)/(7 × 4)` baseline; `computePlan()` rotates pool items across days and multiplies cost by `round(people/2)`; `computeFeasibility()` (step 1 budget check) and `computeTotals()` (step 3, subtracts items marked "ya tengo") produce the budget-OK / over-budget messaging and colors.
- **`render*()` functions build HTML strings** and assign `innerHTML`. `render()` is the master that calls all sub-renderers; individual handlers call the narrowest renderer (e.g. `renderStep1`, `renderFeasibility`, `renderDietPills`) to avoid clobbering inputs/focus. When adding UI, follow this: mutate `state`, then call the smallest renderer that reflects the change.
- **Event handling is delegated**: listeners are attached to stable container elements (`el.step2`, `el.step3`, `el.dayPills`, `el.progressSteps`, …) and dispatch on `data-action` / `data-*` attributes via `e.target.closest(...)`. Because panels are re-rendered via `innerHTML`, never bind listeners to elements created inside a renderer — add a `data-action` and handle it on the container.
- **Navigation**: `setStep(n)` switches the 3 wizard steps; the progress bar's 4th item ("Recetas") opens a recipe modal rather than a step. `runLoading(msg, after)` shows the overlay for a fixed ~1.9s timeout before running `after()` (purely cosmetic fake latency).
- **Always escape interpolated text** with the existing `escapeHtml()` when injecting any data-derived string into an `innerHTML` template, matching current usage. `fmt(n)` formats COP currency.

## Conventions

- Keep everything dependency-free and in these three files — do not introduce a build system, framework, or npm packages unless explicitly asked.
- All user-facing copy is Spanish; preserve tone and existing wording.
- Author/brand footer credits "Mateo, de Mainics."
