# ChuraBell content

The public content for the ChuraBell app and website (Okinawa), by 21 FLUX.
This repo is the single source of truth: the app and churabell.com read only what
GitHub Pages publishes from here.

Edit (and push to `main`):
- `content.json`: places, restaurants, events, medical info and more.
- `traffic.json`: official travel-status lines (monorail, ferry, airport, roads). See `TRAFFIC.md`.
- `evacuation.json`, `shelters_rain.json`: official shelter lists (GSI, Okinawa Prefecture).

Published at https://21flux-japan.github.io/churabell-content/ :
- `content.json` — as is (app + website)
- `places-index.json` — slim list/filter index, generated (website Places page)
- `safety.json` — medical, phone lines, holidays, kids rotation, generated (website Medical & Safety page)
- `traffic.json` — checked and published (website + app)
- `evacuation.json`, `shelters_rain.json` — checked and published (website Medical & Safety page)

How publishing works: every push to `main` runs **Validate and publish**
(`.github/workflows/publish.yml`): `validate.py` checks `content.json`, then
`scripts/build_derived.py` builds the files above, and only then is the site deployed —
so a broken file never reaches the app or website. Never commit the generated files.

No user data is stored here.
