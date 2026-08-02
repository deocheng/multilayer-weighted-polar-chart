#!/usr/bin/env python3
"""Team shot distribution radial chart — fixed-angle sectors, LEFT-EDGE ALIGNED.

Layout (multilayer weighted polar chart):
- Polar zero at 12 o'clock, data runs clockwise.
- Each player occupies a FIXED angular sector (default 45 deg), separated by a
  small gap. The remaining angle becomes a large label gap centered upper-left.
- Each distance ring has EQUAL radial thickness; its drawn angular span starts
  strictly from the sector START EDGE (left-aligned) and extends clockwise by the
  player's normalized weight.
- CLUTCH shots are rendered as a high-contrast YELLOW overlay at the left edge
  of each ring's wedge (the "sinking" second dimension).
- Per-ring data labels drawn ON the wedge: white "makes/attempts" (FG rate) with
  yellow "clutch_makes/clutch_attempts" directly below; 0/0 for empty, — for no clutch.
- Center holds only a compact title + total attempts; the legend is a frameless
  strip sunk into the background below the chart.
"""
from __future__ import annotations

import math
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import psycopg2
from dotenv import load_dotenv

load_dotenv(Path(__file__).with_name(".env"))

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "5433")),
    "dbname": os.getenv("DB_NAME", "nba"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", ""),
}

DIST_BUCKETS = [
    ("0-8 ft (Rim)", 0, 8),
    ("8-16 ft (Mid)", 8, 16),
    ("16-24 ft (Long Mid)", 16, 24),
    ("24+ ft (3PT)", 24, 999),
]

# Volume color: light = low, deep blue = high
BASE_COLOR_STOPS = [(0.0, "#e2e8f0"), (0.2, "#bfdbfe"), (0.45, "#60a5fa"), (0.72, "#2563eb"), (1.0, "#1e3a8a")]
# Clutch / late-game "sinking" dimension — high contrast YELLOW
CLUTCH_COLOR = "#facc15"
CLUTCH_EDGE = "#854d0e"
# Makes (命中数) dimension — green
MAKE_COLOR = "#4ade80"
GAP_COLOR = "#0b1120"
RING_BG = "#ffffff"          # unified sector background (white)
BG_COLOR = "#ffffff"

PLAYER_SECTOR_DEG = 45.0      # each player sector angle
INTER_PLAYER_GAP_DEG = 5.0    # gap between player sectors
MAX_SECTORS = 7               # layout fits up to 7 fixed 45° sectors with a small gap

ALL_TEAMS = [
    "ATL", "BOS", "BRK", "BKN", "CHI", "CLE", "DAL", "DEN", "DET", "GSW",
    "HOU", "IND", "LAC", "LAL", "MEM", "MIA", "MIL", "MIN", "NOP", "NYK",
    "OKC", "ORL", "PHI", "PHX", "POR", "SAC", "SAS", "TOR", "UTA", "WAS",
]


@dataclass
class Segment:
    bucket: str
    attempts: int
    makes: int
    clutch_attempts: int
    clutch_makes: int

    @property
    def fg_pct(self) -> float:
        return self.makes / self.attempts if self.attempts else 0.0

    @property
    def clutch_share(self) -> float:
        return self.clutch_attempts / self.attempts if self.attempts else 0.0


@dataclass
class PlayerSector:
    name: str
    total: int
    segments: List[Segment]


def polar_to_cartesian(cx: float, cy: float, r: float, angle: float) -> Tuple[float, float]:
    return cx + r * math.cos(angle), cy + r * math.sin(angle)


def ref_to_svg(theta: float) -> float:
    # reference theta: 0 at 12 o'clock, increasing clockwise
    return theta - math.pi / 2


def normalize_angle(alpha: float) -> float:
    return alpha % (2 * math.pi)


def annular_sector_path(cx: float, cy: float, r1: float, r2: float, start: float, end: float) -> str:
    x1, y1 = polar_to_cartesian(cx, cy, r1, start)
    x2, y2 = polar_to_cartesian(cx, cy, r2, start)
    x3, y3 = polar_to_cartesian(cx, cy, r2, end)
    x4, y4 = polar_to_cartesian(cx, cy, r1, end)
    span = (end - start) % (2 * math.pi)
    large_arc = 1 if span > math.pi else 0
    return (
        f"M {x1:.2f} {y1:.2f} "
        f"L {x2:.2f} {y2:.2f} "
        f"A {r2:.2f} {r2:.2f} 0 {large_arc} 1 {x3:.2f} {y3:.2f} "
        f"L {x4:.2f} {y4:.2f} "
        f"A {r1:.2f} {r1:.2f} 0 {large_arc} 0 {x1:.2f} {y1:.2f} Z"
    )


def interpolate_color(stops: List[Tuple[float, str]], t: float) -> str:
    t = max(0.0, min(1.0, t))

    def hex_to_rgb(h: str) -> Tuple[int, int, int]:
        h = h.lstrip("#")
        return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))

    for i in range(len(stops) - 1):
        p0, c0 = stops[i]
        p1, c1 = stops[i + 1]
        if p0 <= t <= p1:
            if p1 == p0:
                return c0
            local = (t - p0) / (p1 - p0)
            r0, g0, b0 = hex_to_rgb(c0)
            r1, g1, b1 = hex_to_rgb(c1)
            r = int(r0 + (r1 - r0) * local)
            g = int(g0 + (g1 - g0) * local)
            b = int(b0 + (b1 - b0) * local)
            return f"#{r:02x}{g:02x}{b:02x}"
    return stops[-1][1]


def fetch_team_data(season: int, team: str, top_n: int = 5):
    query = """
        SELECT player_slug,
               CASE
                   WHEN shot_distance < 8 THEN '0-8 ft (Rim)'
                   WHEN shot_distance < 16 THEN '8-16 ft (Mid)'
                   WHEN shot_distance < 24 THEN '16-24 ft (Long Mid)'
                   ELSE '24+ ft (3PT)'
               END AS bucket,
               COUNT(*) AS attempts,
               SUM(CASE WHEN is_make THEN 1 ELSE 0 END) AS makes,
               SUM(CASE WHEN is_clutch THEN 1 ELSE 0 END) AS clutch_attempts,
               SUM(CASE WHEN is_clutch AND is_make THEN 1 ELSE 0 END) AS clutch_makes
        FROM fct_pbp_shots
        WHERE season = %s AND team = %s AND shot_distance IS NOT NULL
        GROUP BY player_slug, bucket
    """
    with psycopg2.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:
            cur.execute(query, (season, team))
            rows = cur.fetchall()

    raw: Dict[str, Dict[str, Dict[str, int]]] = {}
    for player, bucket, att, mk, c_att, c_mk in rows:
        raw.setdefault(player, {})[bucket] = {
            "attempts": att, "makes": mk,
            "clutch_attempts": c_att, "clutch_makes": c_mk,
        }

    player_totals = {
        p: sum(d["attempts"] for d in buckets.values())
        for p, buckets in raw.items()
    }
    sorted_players = sorted(player_totals.items(), key=lambda x: x[1], reverse=True)
    top_players = sorted_players[:top_n]
    others_total = sum(t for _, t in sorted_players[top_n:])
    team_total = sum(t for _, t in sorted_players)

    # Real per-distance-band team totals (includes bench) — drives the
    # bi-proportional RADIAL thickness of each ring.
    zone_totals = {name: 0 for name, _, _ in DIST_BUCKETS}
    for buckets in raw.values():
        for name, _, _ in DIST_BUCKETS:
            zone_totals[name] += buckets.get(name, {}).get("attempts", 0)

    sectors: List[PlayerSector] = []
    for player, total in top_players:
        segments = [
            Segment(
                bucket=name,
                attempts=raw[player].get(name, {}).get("attempts", 0),
                makes=raw[player].get(name, {}).get("makes", 0),
                clutch_attempts=raw[player].get(name, {}).get("clutch_attempts", 0),
                clutch_makes=raw[player].get(name, {}).get("clutch_makes", 0),
            )
            for name, _, _ in DIST_BUCKETS
        ]
        sectors.append(PlayerSector(player, total, segments))

    # Add bench only if it won't overflow the 7-sector layout budget.
    if others_total > 0 and len(top_players) <= MAX_SECTORS - 1:
        sectors.append(PlayerSector(
            "Bench / Others", others_total,
            [Segment(name, 0, 0, 0, 0) for name, _, _ in DIST_BUCKETS]))

    return sectors, zone_totals, team_total


def render(season: int, team: str, top_n: int = 5) -> str:
    top_n = min(max(top_n, 1), MAX_SECTORS)
    sectors, zone_totals, team_total = fetch_team_data(season, team, top_n)

    width, height = 1320, 1320
    cx, cy = width / 2, height / 2 + 20
    inner_radius, outer_radius = 160, 500

    player_radial_span = outer_radius - inner_radius
    # Bi-proportional RADIAL thickness: each ring's thickness is proportional
    # to the team's real shot volume in that distance band (zone_totals), so
    # the proportions are faithful (e.g. rim ~59%, long-mid ~4%). A near-zero
    # floor (4px) only guards against a degenerate zero-width ring.
    MIN_RING_TH = 4.0
    RING_GAP = 12.0  # px of blank space left BETWEEN concentric distance rings
    zone_vals = [zone_totals.get(name, 0) for name, _, _ in DIST_BUCKETS]
    zone_sum = sum(zone_vals) or 1
    n_gaps = len(DIST_BUCKETS) - 1
    floor_total = MIN_RING_TH * len(DIST_BUCKETS)
    # Reserve gap space up-front so the rings keep their TRUE proportional
    # thickness — the gap is extra whitespace, not carved out of a ring.
    remaining = max(player_radial_span - floor_total - n_gaps * RING_GAP, 0.0)
    ring_thicknesses = [MIN_RING_TH + remaining * (z / zone_sum) for z in zone_vals]
    # Per-ring inner/outer radii; a RING_GAP of blank space sits between rings.
    ring_inner: List[float] = []
    ring_outer: List[float] = []
    cur = inner_radius
    for idx, th in enumerate(ring_thicknesses):
        r0 = cur + (RING_GAP if idx > 0 else 0)
        r1 = r0 + th
        ring_inner.append(r0)
        ring_outer.append(r1)
        cur = r1

    top_sectors = [s for s in sectors if s.name != "Bench / Others"]
    bench_sector = next((s for s in sectors if s.name == "Bench / Others"), None)

    sector_angle = math.radians(PLAYER_SECTOR_DEG)
    inter_gap = math.radians(INTER_PLAYER_GAP_DEG)
    num_players = len(top_sectors)
    data_span = num_players * sector_angle + max(0, num_players - 1) * inter_gap
    gap_width = 2 * math.pi - data_span

    theta_ranges: List[Tuple[float, float, PlayerSector]] = []
    cur_theta = 0.0
    for sec in top_sectors:
        theta_ranges.append((cur_theta, cur_theta + sector_angle, sec))
        cur_theta += sector_angle + inter_gap

    parts: List[str] = [
        f'<svg viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" '
        f'style="background:{BG_COLOR};font-family:system-ui,-apple-system,sans-serif;">',
        '<defs>',
        f'<radialGradient id="bgGrad" cx="{cx}" cy="{cy}" r="{outer_radius}" gradientUnits="userSpaceOnUse">',
        '<stop offset="0%" stop-color="#ffffff"/><stop offset="70%" stop-color="#ffffff"/><stop offset="100%" stop-color="#ffffff"/>',
        '</radialGradient>',
        '</defs>',
    ]

    # Header
    bench_total = bench_sector.total if bench_sector else 0
    bench_pct = (bench_total / team_total * 100) if team_total else 0
    parts.append(f'<text x="{cx}" y="50" text-anchor="middle" fill="#0f172a" font-size="23" font-weight="700">{team} · 球队出手分布 — {season}</text>')
    subtitle = f"固定 {int(PLAYER_SECTOR_DEG)}° 扇形 · 边线左对齐 · {int(math.degrees(gap_width))}° 留白 · 白字=命中数/出手数 · 黄字=关键时刻 · 总出手 {team_total}"
    if bench_total:
        subtitle += f" · 替补/其他人: {bench_total} ({bench_pct:.1f}%)"
    parts.append(f'<text x="{cx}" y="78" text-anchor="middle" fill="#475569" font-size="13">{subtitle}</text>')

    parts.append(f'<circle cx="{cx}" cy="{cy}" r="{outer_radius}" fill="url(#bgGrad)" stroke="none"/>')

    # Unified ring background across the whole data span (no color difference
    # between player sectors and the 12 o'clock gap — both share RING_BG).
    ring_bg = annular_sector_path(cx, cy, inner_radius, outer_radius, 0, 2 * math.pi)
    parts.append(f'<path d="{ring_bg}" fill="{RING_BG}" stroke="none"/>')

    # Peer-relative normalization: each distance ring's angular width is scaled by
    # the player's attempts in that band DIVIDED BY THE MAX across all shown players
    # in the same band (NOT the player's own max). This keeps cross-player comparison
    # faithful — e.g. KJ rim 753 vs Vassell rim 313 renders as a ~2.4x wider wedge,
    # not two identical full wedges.
    bucket_max = {name: 1 for name, _, _ in DIST_BUCKETS}
    for sec in sectors:
        for seg in sec.segments:
            if seg.attempts > bucket_max[seg.bucket]:
                bucket_max[seg.bucket] = seg.attempts

    # Player sectors — FIXED-ANGLE, LEFT-EDGE ALIGNED, with clutch overlay + data labels
    label_specs: List[dict] = []
    for theta_start, theta_end, sec in theta_ranges:
        theta_mid = (theta_start + theta_end) / 2
        sector_span = theta_end - theta_start

        start_svg = ref_to_svg(theta_start)
        end_svg = ref_to_svg(theta_end)
        mid_svg = ref_to_svg(theta_mid)

        for i, seg in enumerate(sec.segments):
            r = ring_inner[i]
            r_next = ring_outer[i]
            thickness = r_next - r
            if seg.attempts == 0:
                path = annular_sector_path(cx, cy, r, r_next, start_svg, end_svg)
                parts.append(f'<path d="{path}" fill="{RING_BG}" stroke="none"/>')
                # Consistency label on the empty ring slot
                mx, my = polar_to_cartesian(cx, cy, r + thickness / 2, mid_svg)
                parts.append(f'<text x="{mx:.1f}" y="{my + 3:.1f}" text-anchor="middle" fill="#475569" font-size="9.5" paint-order="stroke" stroke="#020617" stroke-width="2.5">0/0</text>')
                continue

            # Peer-relative (same distance band), linear — no compression, so the
            # wedge width is faithful to the ratio vs the band's top shooter.
            raw_weight = seg.attempts / bucket_max[seg.bucket]
            weight = raw_weight
            base_color = interpolate_color(BASE_COLOR_STOPS, weight)
            draw_span = sector_span * weight

            draw_start_svg = ref_to_svg(theta_start)
            draw_end_svg = ref_to_svg(theta_start + draw_span)

            # Base wedge (total attempts)
            path = annular_sector_path(cx, cy, r, r_next, draw_start_svg, draw_end_svg)
            parts.append(f'<path d="{path}" fill="{base_color}" stroke="none"/>')

            # Clutch overlay (yellow, "sinking" dimension) at left edge of the wedge
            if seg.clutch_attempts > 0:
                clutch_span = draw_span * seg.clutch_share
                if clutch_span > 1e-4:
                    c_end_svg = ref_to_svg(theta_start + clutch_span)
                    cpath = annular_sector_path(cx, cy, r, r_next, draw_start_svg, c_end_svg)
                    parts.append(f'<path d="{cpath}" fill="{CLUTCH_COLOR}" stroke="none"/>')

            # Data label drawn ON the wedge (after wedge => never occluded),
            # centered on the wedge's angular midpoint.
            # Line 1: makes/attempts  => overall FG rate (命中数/出手数)
            # Line 2: clutch_makes/clutch_attempts => same format for clutch data
            draw_mid_svg = ref_to_svg(theta_start + draw_span / 2)
            mx, my = polar_to_cartesian(cx, cy, r + thickness / 2, draw_mid_svg)
            # Thin rings can't host the full two-line label; tighten spacing/font.
            if thickness >= 26:
                fs1, fs2, off1, off2 = 10.5, 9.5, -4, 9
            else:
                fs1, fs2, off1, off2 = 9, 8, -3, 8
            parts.append(f'<text x="{mx:.1f}" y="{my + off1:.1f}" text-anchor="middle" fill="#f8fafc" font-size="{fs1}" font-weight="700" paint-order="stroke" stroke="#020617" stroke-width="3">{seg.makes}/{seg.attempts}</text>')
            if seg.clutch_attempts > 0:
                parts.append(f'<text x="{mx:.1f}" y="{my + off2:.1f}" text-anchor="middle" fill="{CLUTCH_COLOR}" font-size="{fs2}" font-weight="700" paint-order="stroke" stroke="#020617" stroke-width="3">{seg.clutch_makes}/{seg.clutch_attempts}</text>')
            else:
                parts.append(f'<text x="{mx:.1f}" y="{my + off2:.1f}" text-anchor="middle" fill="#475569" font-size="{fs2}" paint-order="stroke" stroke="#020617" stroke-width="3">—</text>')

        lx, ly = polar_to_cartesian(cx, cy, outer_radius + 14, mid_svg)
        label_specs.append({"x": lx, "y": ly, "line1": sec.name, "line2": f"{sec.total} 次"})

    # Player labels (NO pill box — just text with a dark outline for readability)
    for spec in label_specs:
        x, y = spec["x"], spec["y"]
        anchor = "end" if x < cx - 20 else ("start" if x > cx + 20 else "middle")
        tx = x - 12 if anchor == "end" else (x + 12 if anchor == "start" else x)
        parts.append(f'<text x="{tx:.1f}" y="{y + 1:.1f}" text-anchor="{anchor}" fill="#0f172a" font-size="13.5" font-weight="700" paint-order="stroke" stroke="#ffffff" stroke-width="3.5">{spec["line1"]}</text>')
        parts.append(f'<text x="{tx:.1f}" y="{y + 18:.1f}" text-anchor="{anchor}" fill="#475569" font-size="11" paint-order="stroke" stroke="#ffffff" stroke-width="3">总出手 {spec["line2"]}</text>')

    # Distance ring labels (vertical, left side of the 12 o'clock axis)
    label_x = cx - 12
    r_pos = outer_radius
    for (name, _, _), th in zip(reversed(DIST_BUCKETS), reversed(ring_thicknesses)):
        r_mid = r_pos - th / 2
        y = cy - r_mid
        parts.append(f'<text x="{label_x:.1f}" y="{y:.1f}" text-anchor="end" dominant-baseline="middle" fill="#0f172a" font-size="12" font-weight="600">{name}</text>')
        r_pos -= (th + RING_GAP)

    # Center: single merged player-data block (ranking + per-distance), centred
    # in the hole — combines the former centre "出手排名" and gap "球员数据".
    parts.append(f'<circle cx="{cx}" cy="{cy}" r="{inner_radius}" fill="{BG_COLOR}"/>')
    parts.append(f'<text x="{cx}" y="{cy - 54:.1f}" text-anchor="middle" fill="#0f172a" font-size="13" font-weight="800" paint-order="stroke" stroke="#ffffff" stroke-width="3.5">球员出手数据</text>')
    parts.append(f'<text x="{cx}" y="{cy - 32:.1f}" text-anchor="middle" fill="#475569" font-size="9">总·命中率　　篮/中/长/3分</text>')
    ry = cy - 13
    rlh = 17
    for i, sec in enumerate(top_sectors):
        a = [s.attempts for s in sec.segments]
        tot_mk = sum(s.makes for s in sec.segments)
        fg = (tot_mk / sec.total * 100) if sec.total else 0.0
        nm = sec.name.replace(". ", ".")
        line = f"{i+1} {nm} {sec.total}·{fg:.0f}%  {a[0]}/{a[1]}/{a[2]}/{a[3]}"
        parts.append(f'<text x="{cx:.1f}" y="{ry + i * rlh:.1f}" text-anchor="middle" fill="#1e293b" font-size="10" font-weight="600" paint-order="stroke" stroke="#ffffff" stroke-width="2.5">{line}</text>')

    # Legend strip — plain text sunk into the background below the chart (no card)
    legend = [
        ("#1e3a8a", "深蓝=占比高"),
        ("#e2e8f0", "浅色=占比低"),
        (CLUTCH_COLOR, "黄=关键时刻"),
        ("#f8fafc", "白字=命中数/出手数(命中率)"),
        (CLUTCH_COLOR, "黄字=关键时刻 命中数/出手数"),
    ]
    legend_y = cy + outer_radius + 55
    total_w = sum(26 + len(t) * 12 + 24 for _, t in legend)
    x = cx - total_w / 2
    for color, text in legend:
        parts.append(f'<rect x="{x:.1f}" y="{legend_y - 11:.1f}" width="13" height="13" rx="3" fill="{color}"/>')
        parts.append(f'<text x="{x + 20:.1f}" y="{legend_y:.1f}" fill="#334155" font-size="12.5">{text}</text>')
        x += 26 + len(text) * 12 + 24
    parts.append(f'<text x="{cx}" y="{legend_y + 28:.1f}" text-anchor="middle" fill="#475569" font-size="11.5">扇形从左边线起向右填充 · 内圈=篮下 外圈=三分 · 环厚=全队该距离带出手占比(真实比例) · 同环宽度=该球员此距离出手÷全队该距离最高者(真实倍数)</text>')

    parts.append("</svg>")

    team_options = "".join(
        f'<option value="{t}" {"selected" if team == t else ""}>{t}</option>' for t in ALL_TEAMS)
    topn_options = "".join(
        f'<option value="{n}" {"selected" if top_n == n else ""}>{n} 人</option>' for n in (5, 6, 7))

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{team} 出手分布 {season}</title>
<style>
body {{ margin: 0; background: {BG_COLOR}; color: #0f172a; display: flex; flex-direction: column; align-items: center; min-height: 100vh; font-family: system-ui, sans-serif; }}
.container {{ width: 98vw; max-width: 1340px; padding: 16px; }}
.controls {{ margin-bottom: 16px; display: flex; gap: 12px; align-items: center; justify-content: center; flex-wrap: wrap; }}
.controls label {{ font-size: 14px; color: #475569; }}
.controls input, .controls select {{ background: #f8fafc; color: #0f172a; border: 1px solid #cbd5e1; border-radius: 4px; padding: 6px 10px; }}
.controls button {{ background: #3b82f6; color: #fff; border: none; border-radius: 4px; padding: 7px 16px; cursor: pointer; font-weight: 600; }}
.chart {{ border-radius: 12px; overflow: hidden; box-shadow: 0 10px 40px rgba(0,0,0,0.5); }}
.note {{ margin-top: 16px; color: #475569; font-size: 13px; text-align: center; max-width: 900px; }}
</style>
</head>
<body>
<div class="container">
  <div class="controls">
    <label>赛季: <input type="number" id="season" value="{season}" min="1997" max="2026"></label>
    <label>球队:
      <select id="team">{team_options}</select>
    </label>
    <label>人数:
      <select id="topn">{topn_options}</select>
    </label>
    <button onclick="reload()">生成</button>
  </div>
  <div class="chart">{''.join(parts)}</div>
  <p class="note">每个球员固定 {int(PLAYER_SECTOR_DEG)}° 扇形，从左边线起向右填充；环的径向厚度按该距离带全队出手占比分配（最内圈篮下最厚、长中距最薄）。同一距离环内，扇形宽度 = 该球员此距离出手 ÷ 全队该距离最高球员出手（真实倍数，不作压缩，故 753 与 313 会呈现约 2.4 倍宽差）。黄色为该球员此距离中的关键时刻出手（is_clutch，含最后5秒），环内白字为命中数/出手数（整体命中率），其正下方黄字为关键时刻 命中数/出手数。</p>
</div>
<script>
function reload() {{
  const s = document.getElementById('season').value;
  const t = document.getElementById('team').value;
  const n = document.getElementById('topn').value;
  window.location.search = `?season=${{s}}&team=${{t}}&top=${{n}}`;
}}
</script>
</body>
</html>"""


def main():
    import sys
    season = int(sys.argv[1]) if len(sys.argv) > 1 else 2025
    team = sys.argv[2].upper() if len(sys.argv) > 2 else "BOS"
    top_n = int(sys.argv[3]) if len(sys.argv) > 3 else 5

    html = render(season, team, top_n)
    out_path = Path(__file__).with_suffix(".html")
    out_path.write_text(html, encoding="utf-8")
    print(f"Wrote {out_path} for {team} {season} (top {top_n})")


if __name__ == "__main__":
    main()
