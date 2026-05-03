# OG image fonts

This directory holds self-hosted Source Serif 4 + Source Sans 3 .woff2 files used
by `frontend/src/app/og/route.tsx` (Sprint 86 Stream D).

## Required files

- `SourceSerif4-Bold.woff2` — 700 weight, used for the "CourtVue" wordmark
- `SourceSans3-Bold.woff2` — 700 weight, used for kickers, stat callouts, footer
- `SourceSans3-Regular.woff2` — 400 weight, used for taglines and body copy

## Sourcing

Download from Google Fonts (https://fonts.google.com/specimen/Source+Serif+4 and
https://fonts.google.com/specimen/Source+Sans+3) and extract the listed weights
to this directory.

The fastest CLI path:

```bash
# 1. Get the CSS that lists the woff2 URLs (UA-spoof to get .woff2 not .ttf)
curl -s -A "Mozilla/5.0" \
  'https://fonts.googleapis.com/css2?family=Source+Serif+4:wght@700&family=Source+Sans+3:wght@400;700&display=swap' \
  > /tmp/fonts.css

# 2. Extract the latin .woff2 URLs (one per family/weight)
grep -oE 'https://[^)]+\.woff2' /tmp/fonts.css | sort -u

# 3. Download each into this directory under the canonical names listed above.
```

If the files are missing at build time, `route.tsx` falls back to Satori's
default Inter — the build does not break, but the visual identity reverts to
the Sprint 83 baseline.
