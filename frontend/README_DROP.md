# Mandi-Setu frontend — drop from the app repository

This directory is a **copy** of the React Native app, extracted from the
frontend repository at commit `b04f478` (branch `pranay`). It is here so
the API can be wired against the real screens instead of against a guess.

**Do not edit files here expecting the change to survive.** The next drop
replaces this directory wholesale. Frontend changes belong in the app repo; if
you need one, say so and it will be made there and re-dropped.

## What it is

React Native CLI 0.76 (**not** Expo), one codebase, two navigators selected by
the JWT `role` claim. No web build. TanStack Query + Context for state, no
Redux. Charts are hand-rolled `react-native-svg`.

## Running it

```bash
cd frontend
npm install
npx react-native run-android    # needs JDK 17 exactly, and an Android SDK
```

From an emulator the host is `10.0.2.2`, not `localhost`. On a physical device,
`adb reverse tcp:8000 tcp:8000` first.

## Pointing it at your API

`src/config.ts` holds `API_BASE_URL` and a `USE_FIXTURES` flag. With
`USE_FIXTURES = true` every screen renders from `src/fixtures/` and makes no
network call at all — that is how the app was built before the API existed, and
it is also the airplane-mode demo path. Flip it to `false` to hit a live API.

## The wire contract

`src/types/api.ts` is the operative contract from the app's side: every request
and response shape the app actually sends and parses, in `snake_case`, read
directly off the wire with no aliasing layer. If your response disagrees with a
type in that file, the app will not render it — that file is the thing to
reconcile against.

Three specifics worth knowing before you wire anything:

- **All money is integer paise.** Fields end `_paise` and are integers. Never
  send rupees, never send a float. Quantities are integer kilograms (`_kg`);
  rates and shares are basis points (`_bps`, 10000 = 100%).
- **`NO_ADVICE` is a 200 with a body**, not an error. The verdict screen renders
  a refusal through the same success path as every other action. A 4xx/5xx there
  produces a retry screen, which is the wrong thing for a model that has
  correctly declined to answer.
- **`pledge_quote: null`** makes the pledge card disappear entirely — no empty
  state, no placeholder. `is_worthwhile` is the server's decision and the app
  never re-derives it. Send `null` when interest ≥ expected gain.

`docs/FRONTEND_NEEDS_BACKEND.md` and `docs/FRONTEND_NEEDS_AI.md` in this
directory are the full endpoint-by-endpoint asks, including the open questions
that still need an answer from your side.

## Tests

```bash
npx tsc --noEmit
npx jest
```

Both pass at the dropped commit. The suites are worth a look when wiring: the
fixture tests assert the exact response shapes the app expects, so a failing one
after you swap in a live API is telling you the contract drifted.
