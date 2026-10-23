# ChuraBell content

The public content file for the ChuraBell app (Okinawa), by 21 FLUX.

- `content.json`: places, events, medical info and more. The app downloads it from
  https://21flux-japan.github.io/churabell-content/content.json
- `validate.py`: checks `content.json`. Every change is checked automatically, and the file is only
  published when the check passes, so a broken file never reaches the app.

No user data is stored here.
