#!/usr/bin/env python3
"""Build the files GitHub Pages serves, from the files in this repo.

  content.json        copied as is (the app + website read it)
  places-index.json   slim list/filter index for the website's Places page
  safety.json         medical, phone_lines, holidays, kids_rotation (unchanged copy)
                      for the website's Medical & Safety page
  traffic.json        official travel-status lines (website + app), checked here
  evacuation.json     GSI tsunami shelters (website Safety page), checked + copied
  shelters_rain.json  GSI/Okinawa Pref rain & flood shelters (website Safety page), checked + copied

Usage: python3 scripts/build_derived.py OUT_DIR
Never edit the generated files; edit content.json / traffic.json and push.
"""
from __future__ import annotations
import json, shutil, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from places_index import build_places_index  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SAFETY_KEYS = ("medical", "phone_lines", "holidays", "kids_rotation")


def dump(path: Path, obj) -> None:
  path.write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":")))


def check_traffic(t) -> None:
  if not isinstance(t, dict) or not isinstance(t.get("items"), list):
    raise SystemExit("traffic.json: needs an object with an \"items\" list")
  for i, it in enumerate(t["items"]):
    if not isinstance(it, dict) or not it.get("id"):
      raise SystemExit(f"traffic.json: items[{i}] needs an \"id\"")


def main() -> int:
  out = Path(sys.argv[1] if len(sys.argv) > 1 else "site")
  out.mkdir(parents=True, exist_ok=True)
  c = json.loads((ROOT / "content.json").read_text())
  shutil.copyfile(ROOT / "content.json", out / "content.json")
  idx = build_places_index(c)
  dump(out / "places-index.json", idx)
  safety = {"version": c.get("version"), "updated": c.get("updated"), "schema": "safety-v1", "source": "content.json"}
  for k in SAFETY_KEYS:
    if k in c:
      safety[k] = c[k]
  dump(out / "safety.json", safety)
  t = json.loads((ROOT / "traffic.json").read_text())
  check_traffic(t)
  dump(out / "traffic.json", t)
  for name in ("evacuation.json", "shelters_rain.json"):
    shelters = json.loads((ROOT / name).read_text())
    if not isinstance(shelters, dict):
      raise SystemExit(f"{name}: needs a JSON object")
    shutil.copyfile(ROOT / name, out / name)
  print(f"built {out}: places={len(idx['places'])} restaurants={len(idx['restaurants'])} "
        f"medical={len(safety.get('medical') or [])} traffic_items={len(t['items'])}")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
