# Traffic alerts data (`traffic.json`)

Structured status lines for monorail, ferry, airport (terminal/ops only), and roads.
Read by the website and the Android app from https://21flux-japan.github.io/churabell-content/traffic.json — not scraped from HTML pages.

## When to publish an item

Only when an **official operator or authority** has published a clear status statement
(suspension, cancellation, terminal notice, road closure, etc.). Quiet/normal days
leave `"items": []` — the live site must not invent sample disruptions.

## Allowed sources (examples)

- Yui Rail (沖縄都市モノレール) official notices
- Naha Airport terminal / ops notices (not flight-by-flight lists)
- Ferry operator status statements (e.g. A-Line, Marix, Kume Line)
- Okinawa Prefecture / OGB road notices

Do **not** scrape operator websites into this file. Prefer copy from an official
statement you already have (press release, official status page text you are
authorized to relay), or leave empty until a structured official feed exists.

## Schema

```json
{
  "version": 1,
  "updated": "2026-11-05T12:00:00+09:00",
  "items": [
    {
      "id": "yui-20261105-1",
      "category": "monorail",
      "status": "active",
      "severity": "STATUS",
      "titleEn": "Yui Rail suspended (all lines)",
      "titleJa": "ゆいレール全線運休",
      "titleKo": "유이레일 전 노선 운행 중단",
      "sourceEn": "Yui Rail",
      "sourceJa": "沖縄都市モノレール",
      "sourceKo": "유이레일",
      "updated": "2026-11-05T10:30:00+09:00",
      "areas": ["4720100", "4720800", "4721200"]
    }
  ]
}
```

- `category`: `monorail` | `ferry` | `airport` | `roads`
- `status`: `active` | `ended` (ended items may still show briefly; prefer remove)
- `severity`: usually `STATUS` (calm travel tag; not a JMA warning)
- `areas`: municipality codes from `areas.js` — used for home-city filter + “Other areas” foldout
- Airport items: general terminal/ops status only — never flight-by-flight cancellations

Sample/mock data must never be committed to this file.
