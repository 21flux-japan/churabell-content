#!/usr/bin/env python3
"""Slim list/filter index logic (places-index.json). Used by build_derived.py."""
from __future__ import annotations
import json, sys
from pathlib import Path


NEST_BOOL = {
  "beach": ("lifeguard", "toilets"),
  "castle": ("world_heritage",),
  "shrine": ("ryukyu_hassha",),
  "park": ("playground",),
  "family": ("under_6",),
  "activity": ("water", "kids_ok"),
}
VIEW_BOOL = ("sunset", "sunrise", "night")


def pick_nested(p: dict) -> dict:
  out = {}
  for key, fields in NEST_BOOL.items():
    src = p.get(key)
    if not isinstance(src, dict):
      continue
    sub = {f: True for f in fields if src.get(f)}
    if key == "activity" and src.get("setting"):
      sub["setting"] = src["setting"]
    if sub:
      out[key] = sub
  mus = p.get("museum")
  if isinstance(mus, dict) and mus.get("type"):
    out["museum"] = {"type": mus["type"]}
  v = p.get("viewpoint")
  if isinstance(v, dict):
    sub = {f: True for f in VIEW_BOOL if v.get(f) is True}
    if v.get("access"):
      sub["access"] = v["access"]
    if sub:
      out["viewpoint"] = sub
  return out


def slim_place(p: dict, kind: str = "place") -> dict:
  o = {
    "id": p.get("id"),
    "category": p.get("category") or ("restaurants" if kind == "restaurant" else None),
    "title_en": p.get("title_en") or p.get("name_en"),
    "title_ja": p.get("title_ja") or p.get("name_ja"),
    "title_ko": p.get("title_ko") or p.get("name_ko"),
    "title_kana": p.get("title_kana"),
    "name_en": p.get("name_en"),
    "name_ja": p.get("name_ja"),
    "name_ko": p.get("name_ko"),
    "area": p.get("area"),
    "lat": p.get("lat"),
    "lng": p.get("lng"),
    "island": p.get("island"),
    "also_in": p.get("also_in") or None,
    "shop_type": p.get("shop_type") or p.get("shopType"),
    "hours_en": p.get("hours_en"),
    "hours_ja": p.get("hours_ja"),
    "hours_ko": p.get("hours_ko"),
    "closed_days": p.get("closed_days") or None,
    "closed_dates": p.get("closed_dates") or None,
    "desc_en": p.get("desc_en"),
    "desc_ja": p.get("desc_ja"),
    "locality_en": p.get("locality_en"),
    "locality_ja": p.get("locality_ja"),
  }
  if p.get("indoor"):
    o["indoor"] = True
  if p.get("covered"):
    o["covered"] = True
  if p.get("free") is True or p.get("fee_free") is True:
    o["free"] = True
  if p.get("fee_en") or p.get("fee_ja") or p.get("fee"):
    o["has_fee"] = True
  if p.get("resident_discount") or p.get("residentDiscount"):
    o["resident_discount"] = True
  if p.get("example"):
    o["example"] = True
  o.update(pick_nested(p))
  if kind == "restaurant":
    o["cuisine"] = p.get("cuisine") or p.get("cuisines")
    for lab in ("cuisine_label_en", "cuisine_label_ja", "cuisine_label_ko"):
      if p.get(lab):
        o[lab] = p[lab]
    pr = p.get("price_range")
    if isinstance(pr, int) and 1 <= pr <= 3:
      o["price_range"] = pr
    pay = p.get("payment")
    if pay:
      o["payment"] = pay
    if p.get("english_menu") is True:
      o["english_menu"] = True
    if p.get("takeaway") is True:
      o["takeaway"] = True
    kids = p.get("kids")
    if isinstance(kids, dict):
      ksub = {}
      for f in ("kids_friendly", "kids_menu", "high_chairs", "stroller_access", "play_corner", "nursing_changing"):
        if kids.get(f) is True:
          ksub[f] = True
      if ksub:
        o["kids"] = ksub
    park = p.get("parking")
    pe = p.get("parking_en") or p.get("parking_ja") or (park if isinstance(park, str) else None)
    if isinstance(park, dict):
      # Keep typed parking so list "Parking" filter + detail preview stay accurate
      o["parking"] = {k: park[k] for k in ("type", "spaces") if k in park and park[k] not in (None, "")}
      if pe:
        o["parking_en"] = pe
    elif pe:
      o["parking_en"] = pe
  return {k: v for k, v in o.items() if v not in (None, False, "", [], {})}


def build_places_index(c: dict) -> dict:
  return {
    "version": c.get("version"),
    "updated": c.get("updated"),
    "schema": "places-index-v1",
    "source": "content.json",
    "places": [slim_place(p) for p in c.get("places") or []],
    "restaurants": [slim_place(r, "restaurant") for r in c.get("restaurants") or []],
  }
