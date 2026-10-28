#!/usr/bin/env python3
"""Validate a ChuraBell content.json file (schema "nuchi-ping-content", version 12; older versions are still accepted).

Usage:  python3 validate.py content.json
Exit code 0 = OK (warnings may be printed), 1 = errors found.
No extra packages needed (Python 3.8+). Tests: python3 -m unittest test_validate.py
"""
import json, re, sys
from datetime import date, datetime

CURRENT_VERSION = 13
# v0.14.0 (schema 13): optional "family" object (ages_*, setting indoor|outdoor|both, nursing_room, diaper_changing,
# stroller, under_6) and optional "also_in" (extra Explore tiles for the same place — multi-tile, one record).
# Missing family keys = not confirmed (never "unknown"). Older apps reject schema 13 until they update.
# v0.15.0 keeps schema 13 and adds optional "museum" (type, closed_*, last_entry_*, photography, guide_en, guide_ko,
# audio_guide, visit_time_*, free_basis). Older 0.14 apps ignore the unknown key; do NOT bump version for museum alone.
# v0.13.0 (schema 12): parks & gardens — optional "park" object on places (kind = public / private; toilets / playground /
# bbq / pets = true/false only when an official source says so; highlight_* text; free_basis). Missing key = not confirmed.
# Every parks_gardens place must have Free or a fee. park.free_basis:
#   official    = an official source states free entry;
#   public_park = a public (prefectural / city / town / village / national) park with no fee stated by any official source —
#                 "public parks are Free unless an official source states a fee; approved by owner 2026-10-22".
#                 Only for kind "public"; private gardens need "official" or a confirmed fee (else they are left out).
PARK_BOOLS = ("toilets", "playground", "bbq", "pets")
PARK_TEXTS = ("highlight",)
PARK_KINDS = {"public", "private"}
PARK_FREE_BASES = {"official", "public_park"}
# v0.12.1: shrine.free_basis (see FREE_BASES).
# v0.12.0 (schema 11): shrines, temples & utaki — optional "shrine" object on places (ryukyu_hassha / world_heritage /
# toilets / goshuin = true/false only when an official source says so; kind = shrine / temple / utaki / confucian;
# goshuin_*, designation_*, walking_*, festival_*, new_year_*, photo_*, notes_* texts). Missing key = not confirmed.
SHRINE_BOOLS = ("ryukyu_hassha", "world_heritage", "toilets", "goshuin")
SHRINE_TEXTS = ("goshuin", "designation", "walking", "festival", "new_year", "photo", "notes")
SHRINE_KINDS = {"shrine", "temple", "utaki", "confucian"}
# v0.12.1: why a shrine/temple entry is marked free (no "Free" badge without one of these or a confirmed fee_* text):
#   official       = an official source states free entry;
#   shrine_grounds = Shinto shrine grounds — free to enter by general practice (owner-approved basis; kind must be "shrine");
#   no_fee_stated  = a temple that is plainly open to visitors with no fee stated anywhere official (not caves / paid areas);
#   owner_no_fee   = v0.12.2: temples, utaki, caves and open grounds with no fee stated by any official source are free to
#                    enter — "free entry to grounds, no fee stated by official sources; approved by owner 2026-10-22".
# v0.12.2: every shrines_temples place must be either free (with a basis or fee text) or have a confirmed fee_* text.
FREE_BASES = {"official", "shrine_grounds", "no_fee_stated", "owner_no_fee"}
# v0.12.3: beach.free_basis / castle.free_basis — "official" or "owner_no_fee" (free entry, no fee stated by official
# sources; approved by owner 2026-10-22). Shrines & temples, castles and beaches must each have Free or a fee.
# v0.11.0 (schema 10): castles — optional "castle" object on places (world_heritage / toilets = true/false only when an
# official source says so; designation = national / prefectural / municipal historic site; walking_*, visit_time_*,
# restoration_*, guide_* texts). A missing key = not confirmed (the app shows nothing, never "unknown").
CASTLE_BOOLS = ("world_heritage", "toilets")
CASTLE_TEXTS = ("walking", "visit_time", "restoration", "guide")
CASTLE_DESIGNATIONS = {"national", "prefectural", "municipal"}
# v0.10.0 (schema 9): beaches — optional "beach" object on places (toilets, lifeguard, showers, jellyfish_net = true/false
# only when an official source says so; lifeguard_note_*, season_*, swim_hours_*), optional place "island" key,
# optional "sources": [https URLs]. A missing key = not confirmed (the app shows nothing, never "unknown").
BEACH_BOOLS = ("toilets", "lifeguard", "showers", "jellyfish_net")
BEACH_TEXTS = ("lifeguard_note", "season", "swim_hours")
# island ids without an "islands" record (no clinic card) that a place may still name — directions stay on that island.
EXTRA_PLACE_ISLANDS = {"kume", "minna", "tsuken", "izena", "iheya", "ikei", "kudaka", "ou", "tarama", "hatoma", "kuroshima", "aragusuku"}
# v0.9.4 (schema 8): small islands — "islands" list, medical "island" key, type "island_clinic" (+ "hours_by_day").
ISLAND_AIRLIFT = {"coast_guard", "jsdf"}
# v0.9.3 (schema 7): optional shop label on shopping places — same list as the app (Place.SHOP_TYPES).
SHOP_TYPES = {"mall", "outlet", "department_store", "street", "arcade", "market"}
# v0.9.2 (schema 6): help phone lines, holiday list, kids' ER rotation — same lists as the app (PhoneLine.KINDS, DayHours.KEYS).
PHONE_LINE_KINDS = {"emergency", "advice", "advice_child", "tourist", "visitor_hotline", "info"}
PHONE_LINE_AUDIENCES = {"all", "foreigners"}  # v0.9.6
SHORT_NUMBER_RE = re.compile(r"#\d{4,5}|\d{3}")
DAY_HOURS_KEYS = {"mon", "tue", "wed", "thu", "fri", "sat", "sun", "holiday"}
HM_RE = re.compile(r"\d{1,2}[:：]\d{2}")
ENTRY_GROUPS = {"jp", "us", "dod"}
VISITOR_TYPES = {"japanese", "resident", "tourist", "us_id"}
PARKING_TYPES = {"free", "paid", "limited", "none", "temporary"}
TRANSIT_KINDS = {"yui_rail", "monorail", "rail", "bus"}
BUSY_KEYS = {"weekends", "new_year", "holidays", "summer", "events"}
# Place categories since app v0.6.0 (schema 3). Old values still work in the app (mapped) but the checker asks you to update them.
CATEGORIES = {"parks_gardens", "shrines_temples", "castles", "beaches", "viewpoints", "activities", "museums", "kids", "shopping"}
LEGACY_CATEGORIES = {"parks": "parks_gardens", "park": "parks_gardens", "gardens": "parks_gardens", "garden": "parks_gardens",
                     "shrines": "shrines_temples", "shrine": "shrines_temples", "temples": "shrines_temples", "temple": "shrines_temples",
                     "castle": "castles", "beach": "beaches", "viewpoint": "viewpoints", "activity": "activities", "museum": "museums",
                     "shop": "shopping", "shops": "shopping"}
# Medical help (schema 3) — same lists as the app (MedicalType, MedicalParser.LANGUAGES).
MEDICAL_TYPES = {"hospital_er": "hospital with 24 h emergency room", "night_clinic": "night / holiday clinic",
                 "pediatrics": "children's clinic", "clinic": "general clinic",
                 "island_clinic": "small-island clinic (v0.9.4; shown only on its island)"}
MEDICAL_LANGS = {"en", "zh", "ko", "es", "pt", "tl", "vi", "th", "id", "ne", "fr", "de", "ru", "interpreter"}
H24_RE = re.compile(r"(?i)\b24\s*(h|hrs?|hours?)\b|24時間|24/7|24시간|24\s*Std")
OFFICIAL_HINTS = ("jnto", "japan national tourism", "okinawa prefecture", "沖縄県", "oihf", "国際交流", "mhlw", "厚生労働省", "医療情報ネット",
                  "navii", "official", "公式", "hospital website", "病院", "phoned", "電話確認")
EMERGENCY_NUMBERS = {"119", "110", "118"}
MEDICAL_MAX_AGE_DAYS = 92   # medical entries should be re-checked at least every 3 months
EVENT_CATEGORIES = {"festival", "market", "illumination", "base_event", "sports", "culture", "music", "food", "other"}
KNOWN_TAGS = {"open_to_public", "id_required", "family_friendly", "base_event", "sacred_site"}
# Same lists as the app (RestaurantParser.CUISINES, Payment).
CUISINES = {"okinawa_soba", "okinawan", "taco_rice", "cafe", "burger", "japanese", "sushi", "ramen", "izakaya", "yakiniku",
            "western", "italian", "international", "bakery", "sweets", "other"}
PAYMENTS = {"cash_only": "cash only", "card_ok": "cash and card", "card_only": "card / cashless only"}
KIDS_KEYS = ("kids_friendly", "kids_menu", "high_chairs", "stroller_access", "play_corner", "nursing_changing")
DAYS = {"mon", "tue", "wed", "thu", "fri", "sat", "sun"}
MENU_MAX = 4
FEATURED_MAX_PER_LIST = 2   # the app highlights at most this many per list (Promo.MAX_PER_LIST)
HOURS_RE = re.compile(r"(\d{1,2})[:：](\d{2})\s*[–—\-~〜～]\s*(\d{1,2})[:：](\d{2})")
PHONE_RE = re.compile(r"\+?[0-9][0-9\- ]{8,15}")
# Optional translations (app v0.5+): any text field "x_en"/"x_ja" may also have "x_ko" (Korean); "x_de" (German) is accepted but ignored since app v0.9.0.
# Missing ko/de → the app shows English (then Japanese). Same schema version: older apps ignore the extra keys.
EXTRA_LANGS = ("ko", "de")
LANG_TYPOS = {"kr": "ko", "kor": "ko", "korean": "ko", "ger": "de", "deu": "de", "german": "de", "jp": "ja", "eng": "en"}
HANGUL_RE = re.compile(r"[\uac00-\ud7a3]")


def is_date(s):
    try:
        date.fromisoformat(s); return True
    except Exception:
        return False


def validate(root, today=None):
    """Returns (errors, warnings) as lists of strings."""
    today = today or date.today()
    errors, warnings = [], []
    def err(where, msg): errors.append(f"ERROR   {where}: {msg}")
    def warn(where, msg): warnings.append(f"warning {where}: {msg}")

    if not isinstance(root, dict):
        return ["ERROR   top level must be an object { ... }"], []
    if root.get("schema", "nuchi-ping-content") != "nuchi-ping-content": err("root", 'schema must be "nuchi-ping-content"')
    version = root.get("version")
    if not isinstance(version, int) or version < 1: err("root", f'"version" must be a whole number ({CURRENT_VERSION})')
    elif version > CURRENT_VERSION: warn("root", f"version {version}: this validator/app understands up to version {CURRENT_VERSION}")
    elif version < 2 and (root.get("restaurants") or any("featured" in x for k in ("events", "places") for x in (root.get(k) or []) if isinstance(x, dict))):
        warn("root", f'uses restaurants/featured but "version" is {version} — set it to 2 or higher (now {CURRENT_VERSION})')
    elif version < 3 and (root.get("medical") or any(isinstance(x, dict) and ("indoor" in x or x.get("category") in CATEGORIES - {"castles", "beaches", "viewpoints", "activities", "museums", "kids"})
                                                                  for k in ("places", "restaurants") for x in (root.get(k) or []))):
        warn("root", f'uses medical / indoor / the new categories but "version" is {version} — set it to 3 or higher (now {CURRENT_VERSION})')
    elif version < 4 and any(isinstance(x, dict) and isinstance(x.get("parking"), dict) for k in ("events", "places", "restaurants") for x in (root.get(k) or [])):
        warn("root", f'uses structured "parking" but "version" is {version} — set it to 4 or higher (now {CURRENT_VERSION})')
    elif version < 5 and any(isinstance(x, dict) and isinstance(x.get("entry"), dict) for x in (root.get("events") or [])):
        warn("root", f'uses "entry" (Entry & ID) but "version" is {version} — set it to 5 or higher (now {CURRENT_VERSION})')
    elif version < 6 and (root.get("phone_lines") or root.get("holidays") or root.get("kids_rotation")):
        warn("root", f'uses phone_lines / holidays / kids_rotation but "version" is {version} — set it to 6 (now {CURRENT_VERSION})')
    elif version < 7 and any(isinstance(x, dict) and any(k in x for k in ("covered", "closed_dates", "shop_type", "last_checked")) for x in (root.get("places") or [])):
        warn("root", f'places use covered / closed_dates / shop_type / last_checked but "version" is {version} — set it to 7 (now {CURRENT_VERSION})')
    up = root.get("updated", "")
    try: datetime.fromisoformat(str(up).replace("Z", "+00:00"))
    except Exception: warn("root", '"updated" should be a date/time like "2026-10-17T21:00:00+09:00"')
    if root.get("example_data"): warn("root", '"example_data" is true — set it to false once the data is yours')
    ids = set()

    def check_id(o, where):
        if not isinstance(o.get("id"), str) or not re.fullmatch(r"[a-z0-9][a-z0-9\-_]*", o.get("id", "")):
            err(where, 'needs an "id" of lowercase letters, digits and dashes (e.g. "naha-tug-of-war-2026")')
        elif o["id"] in ids: err(where, f'duplicate id "{o["id"]}"')
        else: ids.add(o["id"])

    def check_latlng(o, where):
        lat, lng = o.get("lat"), o.get("lng")
        if lat is None or lng is None: warn(where, "no lat/lng (no directions/distance/map)")
        elif isinstance(lat, bool) or isinstance(lng, bool) or not (isinstance(lat, (int, float)) and isinstance(lng, (int, float))): err(where, "lat/lng must be numbers")
        elif not (24.0 <= lat <= 27.9 and 122.9 <= lng <= 131.5): warn(where, f"lat/lng {lat},{lng} is outside Okinawa Prefecture — swapped?")

    def check_urls(o, where):
        for k in ("url", "image"):
            v = o.get(k)
            if v and not str(v).startswith("https://"): err(where, f"{k} must start with https://")

    def check_langs(o, where):
        """_ko/_de: must be text, need an _en or _ja base, and Korean text should contain Hangul. Flags suffix typos."""
        if not isinstance(o, dict): return
        for key, v in o.items():
            m = re.fullmatch(r"(.+)_([a-z]+)", key)
            if not m: continue
            base, lang = m.groups()
            if lang in LANG_TYPOS: warn(where, f'"{key}": unknown language suffix — use "{base}_{LANG_TYPOS[lang]}" (ignored otherwise)'); continue
            if lang not in EXTRA_LANGS: continue
            if v is not None and not isinstance(v, str): err(where, f'"{key}" must be text'); continue
            if not (o.get(base + "_en") or o.get(base + "_ja")): warn(where, f'"{key}" has no "{base}_en"/"{base}_ja" — add English (fallback for other languages)')
            if lang == "ko" and v and not HANGUL_RE.search(v): warn(where, f'"{key}" contains no Korean (Hangul) text — wrong field?')

    def check_common(o, where):
        check_id(o, where)
        check_langs(o, where)
        if not (o.get("title_en") or o.get("title_ja")): err(where, "needs title_en and/or title_ja")
        if not o.get("title_en"): warn(where, "no title_en (English users will see Japanese)")
        if not o.get("title_ja"): warn(where, "no title_ja")
        check_latlng(o, where); check_urls(o, where)
        for t in o.get("tags", []) or []:
            if t not in KNOWN_TAGS: warn(where, f'unknown tag "{t}" (shown as plain text)')

    def check_bool(o, where, key):
        if key in o and not isinstance(o[key], bool): err(where, f"{key} must be true or false")

    def check_days(o, where):
        cd = o.get("closed_days", []) or []
        if not isinstance(cd, list): err(where, 'closed_days must be a list like ["mon"]'); return
        for dname in cd:
            if str(dname).lower() not in DAYS: err(where, f'closed_days entries must be one of {sorted(DAYS)} (got "{dname}")')

    def check_day_hours(v, where, key):
        if not isinstance(v, dict) or not v: err(where, f'{key} must be an object like {{"mon": "18:00-08:00", "holiday": "9:00-08:00"}}'); return
        for k, h in v.items():
            if k not in DAY_HOURS_KEYS: err(where, f'{key}: unknown day "{k}" (use {sorted(DAY_HOURS_KEYS)})')
            elif not isinstance(h, str) or not HOURS_RE.search(h): err(where, f'{key}.{k}: "{h}" needs HH:MM-HH:MM (several: "9:00-12:00, 18:00-22:00")')

    def check_checked(o, where, max_days=183, required=False):
        lc = o.get("last_checked", "")
        if not lc:
            (err if required else warn)(where, 'no last_checked date ("YYYY-MM-DD")' + (" — required for medical facilities" if required else ' — shown as "unknown"'))
            return
        if not (is_date(lc) or (len(lc) == 7 and is_date(lc + "-01"))): err(where, 'last_checked must be "YYYY-MM-DD" (or "YYYY-MM")'); return
        d = date.fromisoformat(lc if len(lc) == 10 else lc + "-01")
        if (today - d).days > max_days: warn(where, f"last_checked {lc} is more than {max_days // 30} months ago — please re-check" + (" hours, phone and languages" if required else " hours and prices"))
        if d > today: warn(where, f"last_checked {lc} is in the future")

    def check_featured(o, where):
        """Returns True if the item is featured and in date today."""
        if "featured" not in o or o["featured"] is None: return False
        f = o["featured"]
        if not isinstance(f, dict): err(where, 'featured must look like {"active": true, "until": "YYYY-MM-DD"}'); return False
        if not isinstance(f.get("active"), bool): err(where, 'featured.active must be true or false'); return False
        if not f["active"]: return False
        until = f.get("until")
        if not until or not is_date(str(until)):
            err(where, 'featured.until must be the last day as "YYYY-MM-DD" (required — without it the item is NOT featured)'); return False
        if date.fromisoformat(until) < today:
            warn(where, f"featured ended on {until} — shown as a normal item now (you can remove the featured block)"); return False
        return True

    def check_featured_count(kind, n):
        if n > FEATURED_MAX_PER_LIST:
            warn(kind, f"{n} items are featured right now; the app highlights only the first {FEATURED_MAX_PER_LIST} (closest/earliest) per list")

    def check_parking(o, where):
        """v4: optional structured parking object (see content/README.md). Unknown type = the app ignores the box."""
        if "parking" not in o or o["parking"] is None: return
        pk = o["parking"]; w = where + " parking"
        if not isinstance(pk, dict): err(where, 'parking must be an object like {"type": "free"} (the old text goes in parking_en/_ja)'); return
        check_langs(pk, w)
        if pk.get("type") not in PARKING_TYPES: err(w, f'type must be one of {sorted(PARKING_TYPES)}'); return
        def num(d, k, ww, integer=True):
            v = d.get(k)
            if v is None: return
            if isinstance(v, bool) or not isinstance(v, (int,) if integer else (int, float)) or v < 0: err(ww, f"{k} must be a {'whole ' if integer else ''}number >= 0")
        for k in ("fee_yen", "spaces", "accessible_spaces"): num(pk, k, w)
        num(pk, "height_limit_m", w, integer=False)
        check_bool(pk, w, "example")
        busy = pk.get("busy", []) or []
        if not isinstance(busy, list): err(w, 'busy must be a list like ["weekends", "new_year"]')
        else:
            for b in busy:
                if b not in BUSY_KEYS: warn(w, f'busy "{b}" unknown (ignored) — use {sorted(BUSY_KEYS)}')
        def objs(k):
            v = pk.get(k)
            if v is None: return []
            if k == "shuttle" and isinstance(v, dict): v = [v]
            if not isinstance(v, list) or not all(isinstance(x, dict) for x in v): err(w, f"{k} must be a list of objects"); return []
            return v
        for j, lot in enumerate(objs("lots")):
            lw = f"{w} lots[{j}]"; check_langs(lot, lw)
            if not (lot.get("name_en") or lot.get("name_ja")): err(lw, "needs name_en and/or name_ja")
            for k in ("fee_yen", "spaces"): num(lot, k, lw)
            num(lot, "distance_km", lw, integer=False)
            check_bool(lot, lw, "free"); check_bool(lot, lw, "accessible"); check_bool(lot, lw, "shuttle")
            if lot.get("lat") is not None or lot.get("lng") is not None: check_latlng(lot, lw)
        for j, t in enumerate(objs("transit")):
            tw = f"{w} transit[{j}]"; check_langs(t, tw)
            if str(t.get("kind", "")).lower() not in TRANSIT_KINDS: err(tw, f'kind must be one of {sorted(TRANSIT_KINDS)}')
            if not (t.get("name_en") or t.get("name_ja")): err(tw, "needs name_en and/or name_ja (station or bus stop)")
            num(t, "walk_min", tw); check_bool(t, tw, "detour")
            if t.get("lat") is not None or t.get("lng") is not None: check_latlng(t, tw)
        for j, sh in enumerate(objs("shuttle")):
            sw = f"{w} shuttle[{j}]"; check_langs(sh, sw); check_bool(sh, sw, "free")
            if not any(sh.get(k) for k in ("from_en", "from_ja", "to_en", "to_ja")): err(sw, "needs from_en/_ja or to_en/_ja")
        for j, c in enumerate(objs("closures")):
            cw = f"{w} closures[{j}]"; check_langs(c, cw)
            if not (c.get("text_en") or c.get("text_ja")): err(cw, "needs text_en and/or text_ja")
            path = c.get("path")
            if path is not None and (not isinstance(path, list) or not all(isinstance(q, list) and len(q) == 2 and all(isinstance(n, (int, float)) and not isinstance(n, bool) for n in q) for q in path)):
                err(cw, "path must be a list of [lat, lng] pairs")
        if pk.get("example") and not root.get("example_data"): warn(w, 'marked as example — remove "example" once the parking data is checked')

    def check_entry(o, where):
        """v5: optional Entry & ID object on events (see content/README.md). The app only shows it; it never decides who may enter."""
        if "entry" not in o or o["entry"] is None: return
        en = o["entry"]; w = where + " entry"
        if not isinstance(en, dict): err(where, 'entry must be an object like {"id_required": true, "types": {...}}'); return
        check_langs(en, w)
        for k in ("id_required", "bag_check", "example", "pre_registration"): check_bool(en, w, k)
        rt = en.get("restricted_to", []) or []
        if not isinstance(rt, list): err(w, 'restricted_to must be a list like ["jp", "us", "dod"]'); rt = []
        for g in rt:
            if g not in ENTRY_GROUPS: err(w, f'restricted_to "{g}" unknown — use {sorted(ENTRY_GROUPS)}')
        def litems(lst, ww, k):
            if lst is None: return
            if not isinstance(lst, list) or not all(isinstance(x, dict) for x in lst): err(ww, f"{k} must be a list of objects"); return
            for j, x in enumerate(lst):
                xw = f"{ww} {k}[{j}]"; check_langs(x, xw)
                if not (x.get("en") or x.get("ja") or x.get("name_en") or x.get("name_ja")): err(xw, 'needs "en"/"ja" (or name_en/name_ja)')
                for lk in ("ko", "de"):
                    if x.get(lk) is not None and not isinstance(x.get(lk), str): err(xw, f'"{lk}" must be text')
                if isinstance(x.get("ko"), str) and x["ko"] and not HANGUL_RE.search(x["ko"]): warn(xw, '"ko" contains no Korean (Hangul) text')
        types = en.get("types", {}) or {}
        if not isinstance(types, dict): err(w, 'types must be an object like {"tourist": {...}}'); types = {}
        for t, r in types.items():
            tw = f"{w} types.{t}"
            if t not in VISITOR_TYPES: err(tw, f'unknown visitor type — use {sorted(VISITOR_TYPES)}'); continue
            if not isinstance(r, dict): err(tw, "must be an object"); continue
            check_langs(r, tw); check_bool(r, tw, "limited")
            litems(r.get("accepted"), tw, "accepted"); litems(r.get("not_accepted"), tw, "not_accepted")
            if r.get("limited") and not rt: warn(tw, '"limited" is set but restricted_to is empty — the orange note needs restricted_to')
            if not r.get("limited") and not r.get("accepted"): warn(tw, "no accepted IDs listed (shown as \"not listed\")")
        if rt and not any(isinstance(r, dict) and r.get("limited") for r in types.values()):
            warn(w, 'restricted_to is set but no visitor type is "limited" — the note shows only before a type is chosen')
        if (en.get("id_required", True) or rt) and not types: warn(w, "id_required but no types — users only see the general gate info")
        litems(en.get("prohibited"), w, "prohibited")
        for k in ("gates_open", "last_entry"):
            v = en.get(k)
            if v is not None and (not isinstance(v, str) or not re.fullmatch(r"\d{1,2}:\d{2}", v)): err(w, f'{k} must be a time like "10:00"')
        url = en.get("source_url")
        if not url: warn(w, "no source_url — add the organiser's official notice")
        elif not str(url).startswith("https://"): err(w, "source_url must start with https://")
        srcs = en.get("sources")
        if srcs is not None and (not isinstance(srcs, list) or not all(isinstance(u, str) and u.startswith("https://") for u in srcs)):
            err(w, "sources must be a list of https:// links")
        if not en.get("last_checked"): warn(w, 'no last_checked date ("YYYY-MM-DD") — entry rules change per event')
        else: check_checked(en, w, max_days=92)
        if "id_required" in o.get("tags", []) and en.get("id_required") is False: warn(where, 'tag "id_required" but entry.id_required is false')
        if en.get("id_required", True) and "id_required" not in (o.get("tags") or []):
            warn(where, 'entry.id_required but no "id_required" tag — add it so older app versions still show the tag')
        if en.get("example") and not root.get("example_data"): warn(w, 'marked as example — remove "example" once the entry rules are checked')

    nfe = 0
    for i, e in enumerate(root.get("events", []) or []):
        w = f"events[{i}] {e.get('id', '?')}"
        check_common(e, w)
        sd, ed = e.get("start_date", ""), e.get("end_date", e.get("start_date", ""))
        if not is_date(sd): err(w, 'start_date must be "YYYY-MM-DD"')
        elif ed and not is_date(ed): err(w, 'end_date must be "YYYY-MM-DD"')
        elif ed and ed < sd: err(w, "end_date is before start_date")
        if e.get("category") and e["category"] not in EVENT_CATEGORIES: warn(w, f'event category "{e["category"]}" not in {sorted(EVENT_CATEGORIES)}')
        py = e.get("price_yen")
        if py is not None and (isinstance(py, bool) or not isinstance(py, int) or py < 0): err(w, "price_yen must be a whole number >= 0 (0 = free) or null")
        if not e.get("source"): warn(w, "no source")
        if sd and is_date(sd) and (not ed or is_date(ed)) and date.fromisoformat(ed or sd) < today: warn(w, "event is in the past (hidden in the app)")
        check_bool(e, w, "example"); check_parking(e, w); check_entry(e, w)
        nfe += check_featured(e, w)
    check_featured_count("events", nfe)

    nfp = 0
    for i, p in enumerate(root.get("places", []) or []):
        w = f"places[{i}] {p.get('id', '?')}"
        check_common(p, w)
        cat = p.get("category")
        if cat in LEGACY_CATEGORIES:
            warn(w, f'old category "{cat}" — use "{LEGACY_CATEGORIES[cat]}" (the app maps it, but please update)')
        elif cat not in CATEGORIES: err(w, f'category must be one of {sorted(CATEGORIES)}')
        check_bool(p, w, "indoor"); check_bool(p, w, "example")
        check_days(p, w)
        if p.get("example"): warn(w, "marked as example (fictional) — remove \"example\" when it is a real place")
        for t in p.get("etiquette", []) or []:
            if not isinstance(t, dict) or not (t.get("en") or t.get("ja")): err(w, 'etiquette items must look like {"en": "...", "ja": "..."} (optional "ko", "de")')
            elif any(t.get(x) is not None and not isinstance(t.get(x), str) for x in EXTRA_LANGS): err(w, 'etiquette "ko"/"de" must be text')
        check_parking(p, w)
        # v0.9.3 (schema 7)
        check_bool(p, w, "covered")
        if p.get("covered") and p.get("indoor"): warn(w, 'both "indoor" and "covered" — use "indoor" for a building, "covered" for an arcade / canopied street')
        cdates = p.get("closed_dates")
        if cdates is not None:
            if not isinstance(cdates, list) or not all(isinstance(x, str) and is_date(x) for x in cdates):
                err(w, 'closed_dates must be a list of "YYYY-MM-DD" dates (extra closing days, e.g. a market\'s 4th Sunday)')
            elif cdates and max(cdates) < today.isoformat(): warn(w, "all closed_dates are in the past — add the next ones (Open now can't see them)")
            elif cdates and today.month >= 10 and max(cdates) < f"{today.year + 1}-01-01":
                warn(w, f"closed_dates end before next year — add {today.year + 1}'s closing days")
        st = p.get("shop_type")
        if st is not None:
            if st not in SHOP_TYPES: err(w, f"shop_type must be one of {sorted(SHOP_TYPES)}")
            elif cat != "shopping": warn(w, 'shop_type is only shown for category "shopping"')
        v7 = isinstance(version, int) and version >= 7
        if "last_checked" in p: check_checked(p, w)
        elif v7 and cat == "shopping" and not p.get("example"): warn(w, 'no last_checked date ("YYYY-MM-DD") for this shopping place')
        if v7 and cat == "shopping" and p.get("free"): warn(w, 'free: true is ignored for shopping (the app shows no "Free" badge there)')
        if any(k.startswith("tax_free") for k in p): warn(w, "tax_free* is not used by the app (no tax-free info by decision, v0.9.3) — remove it")
        # v0.10.0 (schema 9): beach facts, island, sources
        v9 = isinstance(version, int) and version >= 9
        if "beach" in p and p["beach"] is not None:
            be = p["beach"]
            if not isinstance(be, dict): err(w, 'beach must be an object like {"toilets": true, "lifeguard": true}')
            else:
                check_langs(be, w + " beach")
                for k in BEACH_BOOLS:
                    if k in be and not isinstance(be[k], bool): err(w, f'beach.{k} must be true or false — leave it out when not confirmed (never "unknown")')
                known = set(BEACH_BOOLS) | {"free_basis"} | {f"{t}_{l}" for t in BEACH_TEXTS for l in ("en", "ja", "ko", "de")}
                for k in be:
                    if k not in known: warn(w, f'beach: unknown key "{k}" (ignored)')
                for t in BEACH_TEXTS:
                    if (be.get(t + "_ja") or be.get(t + "_ko")) and not be.get(t + "_en"): warn(w, f"beach.{t}_en missing (English users see nothing)")
                    if be.get(t + "_en") and not be.get(t + "_ja"): warn(w, f"beach.{t}_ja missing")
                if be.get("lifeguard") is not True and any(be.get(f"lifeguard_note_{l}") for l in ("en", "ja", "ko")):
                    warn(w, "beach.lifeguard_note_* is only shown when lifeguard is true")
                if not any(k in be for k in BEACH_BOOLS) and not any(be.get(f"{t}_{l}") for t in BEACH_TEXTS for l in ("en", "ja")):
                    warn(w, "beach object is empty — leave it out")
                if cat != "beaches": warn(w, 'beach facts are only shown for category "beaches"')
                if not v9: warn(w, f'"beach" needs "version" 9 (now {version}) — older apps ignore it')
        # v0.11.0 (schema 10): castle facts
        v10 = isinstance(version, int) and version >= 10
        if "castle" in p and p["castle"] is not None:
            co = p["castle"]
            if not isinstance(co, dict): err(w, 'castle must be an object like {"world_heritage": true, "designation": "national"}')
            else:
                check_langs(co, w + " castle")
                for k in CASTLE_BOOLS:
                    if k in co and not isinstance(co[k], bool): err(w, f'castle.{k} must be true or false — leave it out when not confirmed (never "unknown")')
                if "designation" in co and co["designation"] not in CASTLE_DESIGNATIONS:
                    err(w, f'castle.designation must be one of {sorted(CASTLE_DESIGNATIONS)} — leave it out when not confirmed')
                known = set(CASTLE_BOOLS) | {"designation", "free_basis"} | {f"{t}_{l}" for t in CASTLE_TEXTS for l in ("en", "ja", "ko", "de")}
                for k in co:
                    if k not in known: warn(w, f'castle: unknown key "{k}" (ignored)')
                for t in CASTLE_TEXTS:
                    if (co.get(t + "_ja") or co.get(t + "_ko")) and not co.get(t + "_en"): warn(w, f"castle.{t}_en missing (English users see nothing)")
                    if co.get(t + "_en") and not co.get(t + "_ja"): warn(w, f"castle.{t}_ja missing")
                if co.get("world_heritage") is True and co.get("designation") not in (None, "national"):
                    warn(w, "castle: World Heritage gusuku are national historic sites — check designation")
                if not any(k in co for k in CASTLE_BOOLS) and "designation" not in co and not any(co.get(f"{t}_{l}") for t in CASTLE_TEXTS for l in ("en", "ja")):
                    warn(w, "castle object is empty — leave it out")
                if cat != "castles": warn(w, 'castle facts are only shown for category "castles"')
                if not v10: warn(w, f'"castle" needs "version" 10 (now {version}) — older apps ignore it')
        # v0.12.0 (schema 11): shrine / temple / utaki facts
        v11 = isinstance(version, int) and version >= 11
        if "shrine" in p and p["shrine"] is not None:
            so = p["shrine"]
            if not isinstance(so, dict): err(w, 'shrine must be an object like {"ryukyu_hassha": true, "kind": "shrine"}')
            else:
                check_langs(so, w + " shrine")
                for k in SHRINE_BOOLS:
                    if k in so and not isinstance(so[k], bool): err(w, f'shrine.{k} must be true or false — leave it out when not confirmed (never "unknown")')
                if "kind" in so and so["kind"] not in SHRINE_KINDS: err(w, f'shrine.kind must be one of {sorted(SHRINE_KINDS)}')
                known = set(SHRINE_BOOLS) | {"kind", "free_basis"} | {f"{t}_{l}" for t in SHRINE_TEXTS for l in ("en", "ja", "ko", "de")}
                for k in so:
                    if k not in known: warn(w, f'shrine: unknown key "{k}" (ignored)')
                for t in SHRINE_TEXTS:
                    if (so.get(t + "_ja") or so.get(t + "_ko")) and not so.get(t + "_en"): warn(w, f"shrine.{t}_en missing (English users see nothing)")
                    if so.get(t + "_en") and not so.get(t + "_ja"): warn(w, f"shrine.{t}_ja missing")
                if so.get("goshuin") is not True and any(so.get(f"goshuin_{l}") for l in ("en", "ja", "ko")):
                    warn(w, "shrine.goshuin_* is only shown when goshuin is true")
                if so.get("ryukyu_hassha") is True and so.get("kind") in ("utaki", "confucian"):
                    warn(w, "shrine: the Ryukyu Eight Shrines are shrines (or a shrine inside a temple) — check kind")
                if not any(k in so for k in SHRINE_BOOLS) and "kind" not in so and not any(so.get(f"{t}_{l}") for t in SHRINE_TEXTS for l in ("en", "ja")):
                    warn(w, "shrine object is empty — leave it out")
                fb = so.get("free_basis")
                if fb is not None:
                    if fb not in FREE_BASES: err(w, f'shrine.free_basis must be one of {sorted(FREE_BASES)}')
                    elif fb == "shrine_grounds" and so.get("kind") != "shrine": err(w, 'shrine.free_basis "shrine_grounds" is only for Shinto shrines (kind "shrine") — temples, utaki and caves need an official source')
                    if not p.get("free"): warn(w, "shrine.free_basis is set but free is not true")
                if cat != "shrines_temples": warn(w, 'shrine facts are only shown for category "shrines_temples"')
                if not v11: warn(w, f'"shrine" needs "version" 11 (now {version}) — older apps ignore it')
        if cat == "shrines_temples" and v11 and not p.get("example") and not p.get("free") and not any(p.get(f"fee_{l}") for l in ("en", "ja")):
            err(w, 'shrines & temples need a price: free: true (with shrine.free_basis) or a confirmed fee_en / fee_ja — the app always shows Free or Fee here')
        if cat == "shrines_temples" and v11 and p.get("free") and not p.get("example"):
            so = p.get("shrine") if isinstance(p.get("shrine"), dict) else {}
            if not so.get("free_basis") and not any(p.get(f"fee_{l}") for l in ("en", "ja")):
                err(w, 'free: true on a shrine/temple needs a confirmed fee_* text or shrine.free_basis (official / shrine_grounds / no_fee_stated) — never guess')
        # v0.13.0 (schema 12): park facts
        v12 = isinstance(version, int) and version >= 12
        if "park" in p and p["park"] is not None:
            po = p["park"]
            if not isinstance(po, dict): err(w, 'park must be an object like {"kind": "public", "toilets": true}')
            else:
                check_langs(po, w + " park")
                for k in PARK_BOOLS:
                    if k in po and not isinstance(po[k], bool): err(w, f'park.{k} must be true or false — leave it out when not confirmed (never "unknown")')
                if "kind" in po and po["kind"] not in PARK_KINDS: err(w, f'park.kind must be one of {sorted(PARK_KINDS)}')
                known = set(PARK_BOOLS) | {"kind", "free_basis"} | {f"{t}_{l}" for t in PARK_TEXTS for l in ("en", "ja", "ko", "de")}
                for k in po:
                    if k not in known: warn(w, f'park: unknown key "{k}" (ignored)')
                for t in PARK_TEXTS:
                    if (po.get(t + "_ja") or po.get(t + "_ko")) and not po.get(t + "_en"): warn(w, f"park.{t}_en missing (English users see nothing)")
                    if po.get(t + "_en") and not po.get(t + "_ja"): warn(w, f"park.{t}_ja missing")
                if cat != "parks_gardens": warn(w, 'park facts are only shown for category "parks_gardens"')
                if not v12: warn(w, f'"park" needs "version" 12 (now {version}) — older apps ignore it')
        if cat == "parks_gardens" and v12 and not p.get("example"):
            po = p.get("park") if isinstance(p.get("park"), dict) else {}
            fb = po.get("free_basis")
            has_fee = any(p.get(f"fee_{l}") for l in ("en", "ja"))
            if not p.get("free") and not has_fee:
                err(w, 'parks & gardens need a price: free: true (with park.free_basis) or a confirmed fee_en / fee_ja — the app always shows Free or a fee here')
            if fb is not None:
                if fb not in PARK_FREE_BASES: err(w, f'park.free_basis must be one of {sorted(PARK_FREE_BASES)}')
                elif fb == "public_park" and po.get("kind") != "public":
                    err(w, 'park.free_basis "public_park" is only for public parks (kind "public") — private gardens need an official source or a fee')
                if not p.get("free"): warn(w, "park.free_basis is set but free is not true")
            if p.get("free") and fb is None:
                err(w, 'free: true on a park needs park.free_basis (official / public_park) — never guess')
        # v0.12.3: beaches and castles also always have a price; their free basis lives in beach / castle .free_basis
        # ("official" or the owner rule "owner_no_fee": free entry, no fee stated by official sources; approved by owner 2026-10-22).
        if cat in ("beaches", "castles") and v11 and not p.get("example"):
            ok = {"beaches": "beach", "castles": "castle"}[cat]
            bo = p.get(ok) if isinstance(p.get(ok), dict) else {}
            fb = bo.get("free_basis")
            has_fee = any(p.get(f"fee_{l}") for l in ("en", "ja"))
            if not p.get("free") and not has_fee:
                err(w, f'{cat} need a price: free: true (with {ok}.free_basis) or a confirmed fee_en / fee_ja — the app always shows Free or a fee here')
            if fb is not None:
                if fb not in ("official", "owner_no_fee"): err(w, f'{ok}.free_basis must be "official" or "owner_no_fee"')
                if not p.get("free"): warn(w, f"{ok}.free_basis is set but free is not true")
            if p.get("free") and fb is None and not has_fee:
                err(w, f'free: true on a {ok} needs a confirmed fee_* text or {ok}.free_basis — never guess')
        # v0.14.0 (schema 13): family facts + multi-tile also_in
        v13 = isinstance(version, int) and version >= 13
        FAMILY_BOOLS = ("nursing_room", "diaper_changing", "stroller", "under_6")
        FAMILY_SETTINGS = {"indoor", "outdoor", "both"}
        FAMILY_TEXTS = ("ages",)
        if "family" in p and p["family"] is not None:
            fo = p["family"]
            if not isinstance(fo, dict): err(w, 'family must be an object like {"ages_en": "…", "setting": "indoor", "under_6": true}')
            else:
                check_langs(fo, w + " family")
                for k in FAMILY_BOOLS:
                    if k in fo and not isinstance(fo[k], bool): err(w, f'family.{k} must be true or false — leave it out when not confirmed (never "unknown")')
                if "setting" in fo and fo["setting"] not in FAMILY_SETTINGS:
                    err(w, f'family.setting must be one of {sorted(FAMILY_SETTINGS)}')
                known = set(FAMILY_BOOLS) | {"setting"} | {f"{t}_{l}" for t in FAMILY_TEXTS for l in ("en", "ja", "ko", "de")}
                for k in fo:
                    if k not in known: warn(w, f'family: unknown key "{k}" (ignored)')
                for t in FAMILY_TEXTS:
                    if (fo.get(t + "_ja") or fo.get(t + "_ko")) and not fo.get(t + "_en"): warn(w, f"family.{t}_en missing (English users see nothing)")
                    if fo.get(t + "_en") and not fo.get(t + "_ja"): warn(w, f"family.{t}_ja missing")
                if not any(k in fo for k in FAMILY_BOOLS) and "setting" not in fo and not any(fo.get(f"{t}_{l}") for t in FAMILY_TEXTS for l in ("en", "ja")):
                    warn(w, "family object is empty — leave it out")
                if not v13: warn(w, f'"family" needs "version" 13 (now {version}) — older apps ignore it')
        also = p.get("also_in")
        if also is not None:
            if not isinstance(also, list): err(w, 'also_in must be a list of category keys (extra Explore tiles)')
            else:
                seen = set()
                for a in also:
                    if not isinstance(a, str) or not a.strip(): err(w, 'also_in entries must be non-empty category strings'); continue
                    k = a.strip().lower()
                    if k in LEGACY_CATEGORIES: k = LEGACY_CATEGORIES[k]
                    if k not in CATEGORIES: err(w, f'also_in category "{a}" not in {sorted(CATEGORIES)}')
                    elif k == cat: err(w, f'also_in "{k}" duplicates the primary category')
                    elif k in seen: warn(w, f'also_in "{k}" listed twice')
                    else: seen.add(k)
                if not v13: warn(w, f'"also_in" needs "version" 13 (now {version}) — older apps ignore it')
        # Kids tile (primary or also_in): every non-example place needs Free (with a reason elsewhere) or a fee — same rule as other researched tiles
        in_kids = cat == "kids" or (isinstance(also, list) and "kids" in [str(x).strip().lower() for x in also])
        if in_kids and v13 and not p.get("example"):
            if not p.get("free") and not any(p.get(f"fee_{l}") for l in ("en", "ja")):
                err(w, 'Kids & family places need a price: free: true or a confirmed fee_en / fee_ja — never guess')
            if p.get("free") and cat == "kids" and not any(p.get(f"fee_{l}") for l in ("en", "ja")):
                # free kids places (rare) — fee text optional when free; free_basis not required for kids category yet
                pass
        
        # v0.15.0 (schema 13 additive): museum facts
        MUSEUM_TYPES = {"history", "peace", "art_craft", "nature_science"}
        MUSEUM_FREE_BASES = {"official_free", "municipal_free", "permanent_free"}
        MUSEUM_BOOLS = ("photography", "guide_en", "guide_ko", "audio_guide")
        MUSEUM_TEXTS = ("closed", "last_entry", "visit_time")
        if "museum" in p and p["museum"] is not None:
            mo = p["museum"]
            if not isinstance(mo, dict): err(w, 'museum must be an object like {"type": "history", "closed_en": "…"}')
            else:
                check_langs(mo, w + " museum")
                if "type" in mo and mo["type"] not in MUSEUM_TYPES:
                    err(w, f'museum.type must be one of {sorted(MUSEUM_TYPES)}')
                for k in MUSEUM_BOOLS:
                    if k in mo and not isinstance(mo[k], bool): err(w, f'museum.{k} must be true or false — leave it out when not confirmed (never "unknown")')
                if "free_basis" in mo:
                    fb = mo["free_basis"]
                    if not isinstance(fb, str) or not fb.strip(): err(w, 'museum.free_basis must be a non-empty string')
                    elif fb.strip().lower() not in MUSEUM_FREE_BASES:
                        warn(w, f'museum.free_basis "{fb}" is not one of {sorted(MUSEUM_FREE_BASES)} — prefer those')
                known = set(MUSEUM_BOOLS) | {"type", "free_basis"} | {f"{t}_{l}" for t in MUSEUM_TEXTS for l in ("en", "ja", "ko", "de")}
                for k in mo:
                    if k not in known: warn(w, f'museum: unknown key "{k}" (ignored)')
                for tx in MUSEUM_TEXTS:
                    if (mo.get(tx + "_ja") or mo.get(tx + "_ko")) and not mo.get(tx + "_en"): warn(w, f"museum.{tx}_en missing (English users see nothing)")
                    if mo.get(tx + "_en") and not mo.get(tx + "_ja"): warn(w, f"museum.{tx}_ja missing")
                if not any(k in mo for k in list(MUSEUM_BOOLS) + ["type", "free_basis"]) and not any(mo.get(f"{tx}_{l}") for tx in MUSEUM_TEXTS for l in ("en", "ja")):
                    warn(w, "museum object is empty — leave it out")
                if not v13: warn(w, f'"museum" needs "version" 13 (now {version}) — older apps ignore it')
        in_museums = cat == "museums" or (isinstance(also, list) and "museums" in [str(x).strip().lower() for x in also])
        if in_museums and v13 and not p.get("example"):
            if not p.get("free") and not any(p.get(f"fee_{l}") for l in ("en", "ja")):
                err(w, 'Museums places need a price: free: true (with museum.free_basis) or a confirmed fee_en / fee_ja — never guess')
            if p.get("free"):
                mo = p.get("museum") if isinstance(p.get("museum"), dict) else {}
                if not (mo and mo.get("free_basis")) and not any(p.get(f"fee_{l}") for l in ("en", "ja")):
                    err(w, 'free: true on a museum needs museum.free_basis (official_free / municipal_free / …) or a fee_* reason text — museums are NOT free by default')
            if not isinstance(p.get("museum"), dict) or not p["museum"].get("type"):
                err(w, 'museums need museum.type (history / peace / art_craft / nature_science)')

        researched = cat in ("beaches", "castles") or (cat == "shrines_temples" and v11) or (cat == "parks_gardens" and v12) or (in_kids and v13) or (in_museums and v13)
        if researched and not p.get("example"):
            kind = {"beaches": "beach", "castles": "castle", "parks_gardens": "park", "museums": "museum", "kids": "family"}.get(cat, "shrine")
            if not p.get("source"): err(w, f"{cat} need a source (official pages)")
            if "last_checked" not in p: warn(w, f'no last_checked date ("YYYY-MM-DD") for this {kind}')
            if any(str(v).strip().lower() in ("unknown", "不明", "알 수 없음") for k, v in p.items() if re.fullmatch(r"(fee|parking|hours)_[a-z]+", k)):
                err(w, 'do not write "unknown" — leave the field out')
        isl = p.get("island")
        if isl is not None:
            if not isinstance(isl, str) or not re.fullmatch(r"[a-z0-9][a-z0-9\-_]*", isl): err(w, 'island must be an island id like "zamami"')
            else:
                known_isl = {x.get("id") for x in (root.get("islands") or []) if isinstance(x, dict)}
                if known_isl and isl not in known_isl and isl not in EXTRA_PLACE_ISLANDS:
                    warn(w, f'island "{isl}" is not in "islands" — directions are then only shown on that same island')
            if not v9: warn(w, f'"island" on places needs "version" 9 (now {version}) — older apps ignore it')
        srcs = p.get("sources")
        if srcs is not None:
            if not isinstance(srcs, list) or not all(isinstance(x, str) and x.startswith("https://") for x in srcs):
                err(w, 'sources must be a list of https:// URLs')
        nfp += check_featured(p, w)
    check_featured_count("places", nfp)

    nfr = 0
    for i, r in enumerate(root.get("restaurants", []) or []):
        w = f"restaurants[{i}] {r.get('id', '?') if isinstance(r, dict) else '?'}"
        if not isinstance(r, dict): err(w, "must be an object { ... }"); continue
        check_id(r, w); check_latlng(r, w); check_urls(r, w); check_langs(r, w); check_parking(r, w)
        if not (r.get("name_en") or r.get("name_ja")): err(w, "needs name_en and/or name_ja")
        if not r.get("name_en"): warn(w, "no name_en (English users will see Japanese)")
        if not r.get("name_ja"): warn(w, "no name_ja")
        if r.get("cuisine") not in CUISINES: err(w, f'cuisine must be one of {sorted(CUISINES)} (use "other" + cuisine_label_en/_ja for anything else)')
        pr = r.get("price_range")
        if pr not in (1, 2, 3) or isinstance(pr, bool): err(w, "price_range must be 1 (~¥1,000), 2 (¥1,000–3,000) or 3 (¥3,000+) per person")
        if r.get("payment") not in PAYMENTS: err(w, 'payment must be "cash_only", "card_ok" (cash and card) or "card_only" (cashless)')
        if not isinstance(r.get("english_menu"), bool): err(w, "english_menu must be true or false")
        k = r.get("kids")
        if not isinstance(k, dict): err(w, 'kids must be an object like {"kids_friendly": true, "kids_menu": false, ...}')
        else:
            for key in KIDS_KEYS:
                if key in k and not isinstance(k[key], bool): err(w, f"kids.{key} must be true or false")
                elif key not in k: warn(w, f"kids.{key} missing (treated as false / not available)")
            for key in k:
                if key not in KIDS_KEYS: warn(w, f'unknown kids field "{key}" (ignored)')
        hours = r.get("hours_en") or r.get("hours_ja") or ""
        if not hours: warn(w, "no hours_en/hours_ja")
        elif not HOURS_RE.search(hours): warn(w, f'hours "{hours}" have no "HH:MM–HH:MM" part — the app can\'t show Open/Closed for it')
        check_days(r, w); check_bool(r, w, "indoor")
        menu = r.get("menu", []) or []
        if not isinstance(menu, list): err(w, "menu must be a list"); menu = []
        if len(menu) > MENU_MAX: warn(w, f"menu has {len(menu)} items — keep it to {MENU_MAX} (kids menu / signature dishes). The app shows only {MENU_MAX}.")
        for j, m in enumerate(menu):
            mw = f"{w} menu[{j}]"
            if not isinstance(m, dict) or not (m.get("name_en") or m.get("name_ja")): err(mw, 'needs name_en/name_ja, e.g. {"name_en": "Kids plate", "name_ja": "お子さまプレート", "price_yen": 550, "is_kids": true}'); continue
            check_langs(m, mw)
            p = m.get("price_yen", m.get("price"))
            if p is not None and (isinstance(p, bool) or not isinstance(p, int) or p < 0): err(mw, "price_yen must be a whole number of yen, e.g. 800")
            if "is_kids" in m and not isinstance(m["is_kids"], bool): err(mw, "is_kids must be true or false")
        if isinstance(k, dict) and k.get("kids_menu") and not any(isinstance(m, dict) and m.get("is_kids") for m in menu):
            warn(w, 'kids.kids_menu is true but no menu item has "is_kids": true')
        ph = r.get("phone", "")
        if ph and not PHONE_RE.fullmatch(str(ph)): err(w, 'phone should look like "098-123-4567" (digits, dashes, optional +81)')
        check_checked(r, w)
        if not r.get("source"): warn(w, "no source (e.g. \"restaurant-provided info\", \"visited 2026-10\")")
        if r.get("example"): warn(w, "marked as example (fictional) — remove \"example\" when it is a real restaurant")
        nfr += check_featured(r, w)
    check_featured_count("restaurants", nfr)

    for i, m in enumerate(root.get("medical", []) or []):
        w = f"medical[{i}] {m.get('id', '?') if isinstance(m, dict) else '?'}"
        if not isinstance(m, dict): err(w, "must be an object { ... }"); continue
        island_clinic = m.get("type") == "island_clinic"
        check_id(m, w); check_urls(m, w); check_langs(m, w)
        if not island_clinic or "lat" in m: check_latlng(m, w)
        if not (m.get("name_en") or m.get("name_ja")): err(w, "needs name_en and/or name_ja")
        if not m.get("name_ja"): err(w, "needs name_ja (shown to taxi drivers and staff)")
        if not m.get("name_en"): warn(w, "no name_en (English users will see Japanese)")
        if m.get("type") not in MEDICAL_TYPES: err(w, "type must be one of: " + ", ".join(f'"{k}" ({v})' for k, v in MEDICAL_TYPES.items()))
        langs = m.get("languages", [])
        if not isinstance(langs, list): err(w, 'languages must be a list like ["en", "zh"]')
        else:
            for l in langs:
                if l == "ja": warn(w, 'languages: "ja" is implied — list only foreign languages')
                elif l not in MEDICAL_LANGS: err(w, f'unknown language "{l}" — use ISO codes {sorted(MEDICAL_LANGS)} ("interpreter" = phone interpreter)')
        for key in ("kids", "night", "weekend", "holiday"):
            if key not in m: warn(w, f"{key} missing (treated as false)")
            else: check_bool(m, w, key)
        check_bool(m, w, "example"); check_days(m, w)
        hours = m.get("hours_en") or m.get("hours_ja") or ""
        if not hours: err(w, "needs hours_en/hours_ja (incl. night/weekend/holiday times)")
        elif not H24_RE.search(hours) and not HOURS_RE.search(hours):
            warn(w, f'hours "{hours}" have no "HH:MM–HH:MM" part and no "24 hours" — the app can\'t show Open now for it')
        if island_clinic:
            # v0.9.4 (schema 8): island clinics — address optional (no taxi card), needs its island + per-day hours for Open now.
            if not m.get("island"): err(w, 'island_clinic needs "island" (an id from "islands")')
            if "hours_by_day" not in m: err(w, 'island_clinic needs "hours_by_day" ({"mon": "9:00-12:00, 13:30-16:00", ...})')
            if m.get("night") or m.get("weekend"): warn(w, "island clinics are weekday-only — night/weekend visits go through 119")
            if isinstance(version, int) and version < 8: warn(w, f'type "island_clinic" needs "version" 8 (now {version}) — older apps skip it')
        else:
            if not m.get("address_ja"): err(w, "needs address_ja (the taxi card shows it to the driver)")
            if not m.get("address_en"): warn(w, "no address_en")
        if "hours_by_day" in m: check_day_hours(m["hours_by_day"], w, "hours_by_day")
        ph = str(m.get("phone", "") or "")
        if not ph: warn(w, "no phone — people can't call ahead")
        elif ph.replace("-", "").strip() in EMERGENCY_NUMBERS: err(w, "don't list 119/110 here — emergency numbers are built into the app")
        elif not PHONE_RE.fullmatch(ph): err(w, 'phone should look like "098-123-4567" (digits, dashes, optional +81)')
        elif ph.startswith("098-000-") and not m.get("example"): warn(w, f"phone {ph} uses the fictional 098-000-xxxx pattern — real number?")
        check_checked(m, w, MEDICAL_MAX_AGE_DAYS, required=True)
        # v0.9.2 (schema 6)
        for key in ("kids_night", "er_24h"): check_bool(m, w, key)
        for key in ("er_hours", "kids_er_hours"):
            if key in m: check_day_hours(m[key], w, key)
        if isinstance(version, int) and version >= 6 and m.get("type") == "hospital_er" and "er_24h" not in m:
            warn(w, 'hospital_er without "er_24h" — set true (walk-in at any hour) or false + "er_hours" (else "24 hours" in the text decides)')
        if m.get("er_24h") is False and "er_hours" not in m and H24_RE.search(hours):
            warn(w, '"er_24h": false but no "er_hours" — the app uses the HH:MM ranges in the hours text for Open now')
        if m.get("kids_night") and not (m.get("kids") or m.get("type") == "pediatrics"):
            warn(w, '"kids_night": true but "kids" is not true')
        src = str(m.get("source", "") or "")
        if not src: err(w, "needs a source (e.g. \"JNTO medical institution search, checked by phone 2026-10-18\")")
        elif not m.get("example") and not any(h in src.lower() for h in OFFICIAL_HINTS):
            warn(w, f'source "{src}" doesn\'t name an official list (JNTO medical institution search, Okinawa Prefecture / OIHF list, MHLW list) or a phone check')
        if m.get("example"):
            if root.get("example_data"): warn(w, "FICTIONAL facility (example) — replace with a real, checked entry before publishing")
            else: err(w, 'fictional medical facility ("example": true) in a file with "example_data": false — remove it; people may go there in an emergency')
    # ---- v0.9.2 (schema 6): phone_lines, holidays, kids_rotation ----
    for i, pl in enumerate(root.get("phone_lines", []) or []):
        w = f"phone_lines[{i}] {pl.get('id', '?') if isinstance(pl, dict) else '?'}"
        if not isinstance(pl, dict): err(w, "must be an object { ... }"); continue
        check_id(pl, w); check_urls(pl, w); check_langs(pl, w)
        if not (pl.get("name_en") or pl.get("name_ja")): err(w, "needs name_en and/or name_ja")
        if pl.get("kind", "info") not in PHONE_LINE_KINDS: err(w, f'kind must be one of {sorted(PHONE_LINE_KINDS)}')
        num = str(pl.get("number", "") or "")
        if not num: err(w, "needs a number")
        elif not (SHORT_NUMBER_RE.fullmatch(num) or PHONE_RE.fullmatch(num)): err(w, f'number "{num}" should look like "098-123-4567", "#7119" or "119"')
        alt = pl.get("alt_number")
        if alt and not PHONE_RE.fullmatch(str(alt)): err(w, f'alt_number "{alt}" should look like "098-123-4567"')
        if not pl.get("source"): err(w, "needs a source (official page)")
        check_checked(pl, w, MEDICAL_MAX_AGE_DAYS, required=True)
        # v0.9.6: audience "foreigners" = hidden when the app is in Japanese (residents); default "all"
        aud = pl.get("audience", "all")
        if aud not in PHONE_LINE_AUDIENCES: err(w, f'audience must be one of {sorted(PHONE_LINE_AUDIENCES)} (default "all")')
        elif aud == "foreigners" and (pl.get("kind") in ("emergency", "advice", "advice_child") or num in ("119", "110", "#7119", "#8000")):
            err(w, 'audience "foreigners" would hide this emergency/advice line in Japanese — use "all"')
        elif aud != "foreigners" and pl.get("kind") in ("tourist", "visitor_hotline"):
            warn(w, f'kind "{pl.get("kind")}" is a line for foreign visitors — set "audience": "foreigners" (hidden in Japanese)')
        if num.startswith("0570"): 
            note = " ".join(str(pl.get(k, "")) for k in ("note_en", "note_ja"))
            if "0570" not in note: warn(w, "0570 (Navi Dial) numbers may not work from foreign phones — say so in note_en/note_ja")
    hol = root.get("holidays")
    hol_dates = set()
    if hol is not None:
        w = "holidays"
        if not isinstance(hol, dict) or not isinstance(hol.get("dates"), list): err(w, 'must be {"dates": ["2026-01-01", ...], "years": [2026], "source": ...}')
        else:
            for dd in hol["dates"]:
                if not is_date(str(dd)): err(w, f'bad date "{dd}" (use YYYY-MM-DD)')
                else: hol_dates.add(date.fromisoformat(dd))
            years = hol.get("years") or sorted({x.year for x in hol_dates})
            if not all(isinstance(y, int) for y in years): err(w, "years must be whole numbers")
            else:
                if any(x.year not in years for x in hol_dates): warn(w, "some dates are outside the listed years")
                if today.year not in years: err(w, f"no holidays for {today.year} — the kids' ER card can't tell holidays (it shows both hospitals)")
                elif today.month >= 10 and today.year + 1 not in years: warn(w, f"add next year's holidays ({today.year + 1}) before January")
            if not hol.get("source"): err(w, "needs a source (Cabinet Office 内閣府 list)")
    rot = root.get("kids_rotation")
    if rot is not None:
        w = "kids_rotation"
        med_ids = {m.get("id") for m in (root.get("medical") or []) if isinstance(m, dict)}
        if not isinstance(rot, dict): err(w, "must be an object { ... }")
        else:
            bd = rot.get("by_day")
            if not isinstance(bd, dict) or set(bd) != DAYS: err(w, f"by_day needs all 7 days {sorted(DAYS)} → medical id")
            else:
                for k, v in bd.items():
                    if v not in med_ids: err(w, f'by_day.{k}: "{v}" is not a medical id')
            for k in ("weekday_start", "end", "holiday_start"):
                if not HM_RE.fullmatch(str(rot.get(k, ""))): err(w, f'{k} must be HH:MM (e.g. "17:00")')
            for cd in rot.get("check_days", []) or []:
                if not re.fullmatch(r"\d{2}-\d{2}", str(cd)): err(w, f'check_days entries are "MM-DD" (got "{cd}")')
            if not str(rot.get("url", "")).startswith("https://"): err(w, "needs the official rotation page url (https://)")
            if not rot.get("source"): err(w, "needs a source")
            check_checked(rot, w, MEDICAL_MAX_AGE_DAYS, required=True)
            if hol is None: warn(w, 'no "holidays" list — the app shows both hospitals on every day it is unsure about')
    # ---- v0.9.4 (schema 8): islands ----
    med = [m for m in (root.get("medical") or []) if isinstance(m, dict)]
    med_ids = {m.get("id") for m in med}
    isl_ids = set()
    for i, isl in enumerate(root.get("islands", []) or []):
        w = f"islands[{i}] {isl.get('id', '?') if isinstance(isl, dict) else '?'}"
        if not isinstance(isl, dict): err(w, "must be an object { ... }"); continue
        iid = isl.get("id")
        if not isinstance(iid, str) or not re.fullmatch(r"[a-z0-9][a-z0-9\-_]*", iid or ""): err(w, 'needs an "id" of lowercase letters, digits and dashes')
        elif iid in isl_ids: err(w, f'duplicate island id "{iid}"')
        else: isl_ids.add(iid)
        check_langs(isl, w)
        if not (isl.get("name_en") and isl.get("name_ja")): err(w, "needs name_en and name_ja")
        circ = isl.get("circles")
        if not isinstance(circ, list) or not circ or not all(isinstance(c, list) and len(c) == 3 and all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in c) for c in circ):
            err(w, 'circles must be a list like [[24.326, 124.087, 2.5]] (lat, lng, radius km)')
        else:
            for lat, lng, r in circ:
                if not (24.0 <= lat <= 27.9 and 122.9 <= lng <= 131.5): err(w, f"circle {lat},{lng} is outside Okinawa Prefecture")
                if not (0 < r <= 25): err(w, f"circle radius {r} km must be between 0 and 25")
        check_bool(isl, w, "small"); check_bool(isl, w, "no_7119")
        if isl.get("small"):
            if not (isl.get("say_en") and isl.get("say_ja")): err(w, 'small island needs say_en/say_ja (the municipality to say first on 119, e.g. "Taketomi-cho" / "竹富町")')
            cl = isl.get("clinics")
            if not isinstance(cl, list) or not cl: err(w, "small island needs clinics: [medical ids]")
            else:
                for c in cl:
                    if c not in med_ids: err(w, f'clinics: "{c}" is not a medical id')
            if isl.get("airlift") not in (None, "", *ISLAND_AIRLIFT): err(w, f"airlift must be one of {sorted(ISLAND_AIRLIFT)} (or left out when not verified)")
            if (isl.get("airlift_to_en") or isl.get("airlift_to_ja")) and not isl.get("airlift"): err(w, "airlift_to_* without airlift")
            if not isl.get("source"): err(w, "needs a source (official pages)")
            check_checked(isl, w, MEDICAL_MAX_AGE_DAYS, required=True)
        if isinstance(version, int) and version < 8: warn(w, f'"islands" needs "version" 8 (now {version}) — older apps ignore it')
    if isl_ids:
        for m in med:
            w = f"medical {m.get('id', '?')}"
            if m.get("island") and m["island"] not in isl_ids: err(w, f'island "{m["island"]}" is not in "islands"')
            elif not m.get("island") and m.get("type") != "island_clinic": warn(w, 'no "island" — the app works it out from lat/lng')
    for i, n in enumerate(root.get("notices", []) or []):
        w = f"notices[{i}] {n.get('id', '?')}"
        if not n.get("id"): err(w, "needs an id")
        check_langs(n, w)
        if not (n.get("title_en") or n.get("title_ja")): err(w, "needs title_en/title_ja")
        if not n.get("source"): err(w, "notices must say their source (e.g. Kadena Air Base) — they are not JMA information")
        if n.get("expires") and not is_date(n["expires"]): err(w, 'expires must be "YYYY-MM-DD"')
    return errors, warnings


def main(path):
    try:
        with open(path, encoding="utf-8") as f: root = json.load(f)
    except json.JSONDecodeError as e:
        print(f"ERROR   not valid JSON: line {e.lineno}, column {e.colno}: {e.msg}"); return 1
    errors, warnings = validate(root)
    for line in warnings: print(line)
    for line in errors: print(line)
    if isinstance(root, dict):
        ev, pl, re_, md, no = (len(root.get(k, []) or []) for k in ("events", "places", "restaurants", "medical", "notices"))
        print(f"\n{ev} events, {pl} places, {re_} restaurants, {md} medical, {no} notices — {len(errors)} error(s), {len(warnings)} warning(s)")
        items = [x for k in ("events", "places", "restaurants", "medical", "notices") for x in (root.get(k) or []) if isinstance(x, dict)]
        n = sum(1 for x in items if any(k.endswith("_ko") and x[k] for k in x))
        print(f"Korean (_ko): {n}/{len(items)} items translated (others fall back to English)")
        if any(k.endswith("_de") for x in items for k in x):
            print("Note: _de (German) fields are ignored by the app since v0.9.0 — safe to keep or remove.")
    print("OK" if not errors else "FIX THE ERRORS ABOVE (the app skips broken items and keeps the last good file)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "content.json"))
