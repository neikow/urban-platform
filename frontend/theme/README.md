# The theme

What the website's look is made of, kept apart so that the control plane (a private
repository that includes this one as a git submodule) builds its preview of a new
website from the same sources.

| File | |
|---|---|
| `theme.css` | daisyUI theme (colours, geometry) and Tailwind `@theme` (fonts, type scale). Import it after `tailwindcss` |
| `fonts.json` | The fonts offered, by id: family, kind (`sans`, `serif`), roles (`body`, `display`), and the defaults |
| `fonts/<id>.css` | One stylesheet per font (self-hosted with fontsource), built to `dist/font-<id>.css` |
| `derive.ts` | A website's overrides as CSS variables: colours, derived shades, text on buttons, fonts |
| `test-cases.json` | Expected overrides, checked by `derive.test.ts` and by the Python mirror (`core.branding.theme_variables`, `core/tests/test_branding_theme.py`) |

A website overrides at most: main and secondary colours, background and text colours
(contrast of 4.5:1 at least), the text and title fonts (`core.models.Branding`, set by
the association or initially by the platform, see `deploy/README.md`).

Adding a font: `npm i -D @fontsource-variable/<name>`, an entry in `fonts.json`, its
`fonts/<id>.css`. Changing the derivation: change `derive.ts` and `core/branding.py`
together, and `test-cases.json`.
