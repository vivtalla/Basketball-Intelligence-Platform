"""Sprint 78 (Team CF1): Server-side share-card image generation.

Pure-Python rendering of broadsheet-styled share cards using Pillow. Each
card is 1200x630 (the OG default, also good for Instagram + X). Style
echoes Sprint 77 broadsheet chrome:

- Parchment ground (#FFF9F1)
- Forest ink for primary copy (#1F3D2A)
- Gold accent bar + numbers (#B5832A)
- Mono uppercase kicker
- Large tabular-nums stat lines

If a TTF system font is available the renderer uses it; otherwise it
falls back to Pillow's default bitmap font. Either way the output is a
valid PNG byte-string.

Public surface:
- ``render_player_card(db, player_id, season) -> bytes``
- ``render_game_card(db, game_id) -> bytes``
- ``render_series_card(db, series_id) -> bytes``
- ``render_milestone_card(db, player_id, milestone_key) -> bytes``

All four return ``bytes`` (PNG). Errors during data lookup degrade
gracefully — the renderer always returns a valid 1200x630 PNG so the
share endpoint can always answer with ``image/png``.
"""
from __future__ import annotations

import io
import logging
import os
from typing import List, Optional, Tuple

from PIL import Image, ImageDraw, ImageFont
from sqlalchemy.orm import Session

from db.models import GameLog, Player, PlayoffSeries, SeasonStat, Team

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Card constants
# ---------------------------------------------------------------------------

CARD_W = 1200
CARD_H = 630

# Broadsheet palette (matches Sprint 77 CSS variables).
PARCHMENT = (255, 249, 241)
PARCHMENT_ALT = (250, 241, 224)
INK = (31, 61, 42)            # forest / primary ink
INK_MUTED = (110, 100, 84)    # warm muted ink
GOLD = (181, 131, 42)         # accent
DANGER = (224, 87, 60)        # danger ink
RULE = (212, 196, 168)        # parchment border


# ---------------------------------------------------------------------------
# Font loading
# ---------------------------------------------------------------------------

# Candidate system fonts. We try a serif first (broadsheet feel), then a
# sans, then mono. If none are present we fall back to Pillow's default
# (still produces a valid PNG).
_SERIF_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/Times New Roman.ttf",
    "/System/Library/Fonts/Supplemental/Times New Roman Bold.ttf",
    "/System/Library/Fonts/NewYork.ttf",
    "/System/Library/Fonts/Georgia.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
]
_SANS_CANDIDATES = [
    "/System/Library/Fonts/Helvetica.ttc",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]
_MONO_CANDIDATES = [
    "/System/Library/Fonts/Menlo.ttc",
    "/System/Library/Fonts/Monaco.ttf",
    "/System/Library/Fonts/Supplemental/Courier New.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
]


def _load_font(candidates: List[str], size: int) -> ImageFont.ImageFont:
    """Try each candidate path; return the first that loads. Fallback to
    Pillow's bitmap default."""
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except (OSError, IOError):
                continue
    return ImageFont.load_default()


def _fonts():
    """Return a dict of preloaded fonts at the sizes we use across cards."""
    return {
        "kicker": _load_font(_MONO_CANDIDATES, 22),
        "kicker_sm": _load_font(_MONO_CANDIDATES, 18),
        "title_xl": _load_font(_SERIF_CANDIDATES, 96),
        "title_lg": _load_font(_SERIF_CANDIDATES, 72),
        "title_md": _load_font(_SERIF_CANDIDATES, 56),
        "subtitle": _load_font(_SERIF_CANDIDATES, 32),
        "stat_xl": _load_font(_SANS_CANDIDATES, 84),
        "stat_lg": _load_font(_SANS_CANDIDATES, 56),
        "stat_label": _load_font(_MONO_CANDIDATES, 16),
        "body": _load_font(_SERIF_CANDIDATES, 26),
        "footer": _load_font(_MONO_CANDIDATES, 16),
    }


# ---------------------------------------------------------------------------
# Drawing primitives
# ---------------------------------------------------------------------------


def _new_canvas() -> Tuple[Image.Image, ImageDraw.ImageDraw]:
    """Make a parchment-ground 1200x630 canvas with a faint texture wash
    and the 36px gold accent bar across the top."""
    img = Image.new("RGB", (CARD_W, CARD_H), PARCHMENT)
    draw = ImageDraw.Draw(img)

    # Faint horizontal "newsprint" rules — keeps the art from looking flat.
    for y in range(0, CARD_H, 4):
        draw.line([(0, y), (CARD_W, y)], fill=PARCHMENT_ALT, width=1)

    # Gold accent bar (top).
    draw.rectangle([(0, 0), (CARD_W, 12)], fill=GOLD)

    # Inner border rule (broadsheet edge).
    draw.rectangle(
        [(36, 36), (CARD_W - 36, CARD_H - 36)],
        outline=RULE,
        width=2,
    )

    return img, draw


def _measure(draw: ImageDraw.ImageDraw, text: str, font) -> Tuple[int, int]:
    """Measure (width, height) of ``text`` in ``font``. Uses textbbox for
    accuracy with Pillow >= 8."""
    if not text:
        return (0, 0)
    try:
        bbox = draw.textbbox((0, 0), text, font=font)
        return (bbox[2] - bbox[0], bbox[3] - bbox[1])
    except AttributeError:
        # Fallback for very old Pillow.
        return draw.textsize(text, font=font)


def _draw_kicker(
    draw: ImageDraw.ImageDraw, x: int, y: int, text: str, font, color=GOLD
) -> int:
    """Draw an uppercase, letter-spaced mono kicker. Returns the y after."""
    upper = text.upper()
    spaced = "  ".join(list(upper))  # cheap letter-spacing
    draw.text((x, y), spaced, font=font, fill=color)
    _, h = _measure(draw, spaced, font)
    return y + h + 4


def _draw_footer(draw: ImageDraw.ImageDraw, font) -> None:
    """The standard CourtVue Labs footer line at the bottom rule."""
    label = "COURTVUE LABS  ·  COURTVUELABS.COM"
    w, h = _measure(draw, label, font)
    draw.text(
        (CARD_W - 36 - 12 - w, CARD_H - 36 - 12 - h),
        label,
        font=font,
        fill=INK_MUTED,
    )


def _to_png_bytes(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def _placeholder_card(headline: str, subhead: str) -> bytes:
    """Last-ditch card used when an entity isn't found. Still 1200x630 PNG."""
    img, draw = _new_canvas()
    fonts = _fonts()
    y = 100
    y = _draw_kicker(draw, 60, y, "COURTVUE LABS", fonts["kicker"])
    y += 16
    draw.text((60, y), headline, font=fonts["title_lg"], fill=INK)
    _, h = _measure(draw, headline, fonts["title_lg"])
    y += h + 24
    draw.text((60, y), subhead, font=fonts["body"], fill=INK_MUTED)
    _draw_footer(draw, fonts["footer"])
    return _to_png_bytes(img)


# ---------------------------------------------------------------------------
# Helpers — DB lookups (defensive, do not raise)
# ---------------------------------------------------------------------------


def _player_team(db: Session, player: Player) -> Optional[Team]:
    if player is None or player.team_id is None:
        return None
    return db.query(Team).filter(Team.id == player.team_id).first()


def _season_stat(
    db: Session, player_id: int, season: str, is_playoff: bool = False
) -> Optional[SeasonStat]:
    """Pick the most relevant SeasonStat row for the (player, season). If
    the requested split isn't there, fall back to the regular-season row."""
    primary = (
        db.query(SeasonStat)
        .filter(
            SeasonStat.player_id == player_id,
            SeasonStat.season == season,
            SeasonStat.is_playoff == is_playoff,
        )
        .order_by(SeasonStat.gp.desc())
        .first()
    )
    if primary is not None:
        return primary
    return (
        db.query(SeasonStat)
        .filter(
            SeasonStat.player_id == player_id,
            SeasonStat.season == season,
        )
        .order_by(SeasonStat.gp.desc())
        .first()
    )


def _format_pct(value: Optional[float]) -> str:
    if value is None:
        return "—"
    return "{:.1f}%".format(value * 100.0)


def _format_avg(value: Optional[float]) -> str:
    if value is None:
        return "—"
    return "{:.1f}".format(value)


# ---------------------------------------------------------------------------
# Player card
# ---------------------------------------------------------------------------


def render_player_card(db: Session, player_id: int, season: str) -> bytes:
    """Generate a player season card. PNG bytes, always 1200x630."""
    try:
        player = db.query(Player).filter(Player.id == player_id).first()
        if player is None:
            return _placeholder_card("Player not found", f"#{player_id} · {season}")

        team = _player_team(db, player)
        stat = _season_stat(db, player_id, season, is_playoff=False)

        img, draw = _new_canvas()
        fonts = _fonts()

        # Kicker
        kicker_text = (
            f"{(team.abbreviation if team else 'NBA')} · {season}"
        )
        y = 88
        y = _draw_kicker(draw, 60, y, kicker_text, fonts["kicker"])
        y += 12

        # Headline — player full name. Auto-shrink to fit width.
        full_name = player.full_name or f"Player #{player_id}"
        title_font = fonts["title_xl"]
        max_w = CARD_W - 120
        title_w, _ = _measure(draw, full_name, title_font)
        if title_w > max_w:
            title_font = fonts["title_lg"]
            title_w, _ = _measure(draw, full_name, title_font)
        if title_w > max_w:
            title_font = fonts["title_md"]
        draw.text((60, y), full_name, font=title_font, fill=INK)
        _, title_h = _measure(draw, full_name, title_font)
        y += title_h + 8

        # Position / team / jersey line
        pieces = []
        if player.jersey:
            pieces.append(f"#{player.jersey}")
        if player.position:
            pieces.append(player.position)
        if team and team.name:
            pieces.append(team.name)
        elif team and team.abbreviation:
            pieces.append(team.abbreviation)
        meta_line = "  ·  ".join(pieces) if pieces else "—"
        draw.text((60, y), meta_line, font=fonts["body"], fill=INK_MUTED)
        _, meta_h = _measure(draw, meta_line, fonts["body"])
        y += meta_h + 32

        # Gold rule
        draw.rectangle([(60, y), (60 + 80, y + 4)], fill=GOLD)
        y += 28

        # Stat row — PPG / RPG / APG / TS%
        if stat is None:
            draw.text(
                (60, y),
                f"No {season} season data on file.",
                font=fonts["body"],
                fill=INK_MUTED,
            )
        else:
            stats = [
                ("PPG", _format_avg(stat.pts_pg)),
                ("RPG", _format_avg(stat.reb_pg)),
                ("APG", _format_avg(stat.ast_pg)),
                ("TS%", _format_pct(stat.ts_pct)),
            ]
            col_w = (CARD_W - 120) // len(stats)
            for i, (label, value) in enumerate(stats):
                cx = 60 + i * col_w
                draw.text((cx, y), value, font=fonts["stat_xl"], fill=INK)
                _, vh = _measure(draw, value, fonts["stat_xl"])
                draw.text(
                    (cx, y + vh + 6),
                    label,
                    font=fonts["stat_label"],
                    fill=GOLD,
                )

        _draw_footer(draw, fonts["footer"])
        return _to_png_bytes(img)
    except Exception:
        logger.exception("render_player_card failed for %s/%s", player_id, season)
        return _placeholder_card("Card unavailable", f"Player #{player_id}")


# ---------------------------------------------------------------------------
# Game card
# ---------------------------------------------------------------------------


def _team_for(db: Session, team_id: Optional[int]) -> Optional[Team]:
    if team_id is None:
        return None
    return db.query(Team).filter(Team.id == team_id).first()


def render_game_card(db: Session, game_id: str) -> bytes:
    """Generate a game-recap card."""
    try:
        game = db.query(GameLog).filter(GameLog.game_id == game_id).first()
        if game is None:
            return _placeholder_card("Game not found", f"Game {game_id}")

        home = _team_for(db, game.home_team_id)
        away = _team_for(db, game.away_team_id)

        img, draw = _new_canvas()
        fonts = _fonts()

        # Kicker — date + season type + game id
        date_str = game.game_date.isoformat() if game.game_date else ""
        season_type = (game.season_type or "Regular Season").upper()
        kicker = f"{season_type} · {date_str} · {game.season or ''}".strip(" ·")
        y = 80
        y = _draw_kicker(draw, 60, y, kicker, fonts["kicker"])
        y += 12

        # Matchup line — "AWY at HOM"
        away_abbr = away.abbreviation if away else "AWY"
        home_abbr = home.abbreviation if home else "HOM"
        matchup = f"{away_abbr} at {home_abbr}"
        draw.text((60, y), matchup, font=fonts["title_lg"], fill=INK)
        _, mh = _measure(draw, matchup, fonts["title_lg"])
        y += mh + 12

        # Final-score / status
        if game.home_score is not None and game.away_score is not None:
            score_line = f"{away_abbr}  {game.away_score}   ·   {home_abbr}  {game.home_score}"
            color = INK
            if game.home_score > game.away_score:
                winner = home.name if home and home.name else home_abbr
            elif game.away_score > game.home_score:
                winner = away.name if away and away.name else away_abbr
            else:
                winner = None
        else:
            score_line = "Tipoff Pending"
            color = INK_MUTED
            winner = None
        draw.text((60, y), score_line, font=fonts["stat_lg"], fill=color)
        _, sh = _measure(draw, score_line, fonts["stat_lg"])
        y += sh + 24

        # Gold rule.
        draw.rectangle([(60, y), (60 + 80, y + 4)], fill=GOLD)
        y += 24

        # Top-scorer + swing-moment line. We pull the highest scorer for the
        # game from the box-score table if present; otherwise leave a quiet
        # storyline placeholder.
        top_scorer_line = _top_scorer_line(db, game_id)
        if top_scorer_line:
            draw.text((60, y), top_scorer_line, font=fonts["body"], fill=INK)
            _, th = _measure(draw, top_scorer_line, fonts["body"])
            y += th + 8

        if winner:
            tag = f"{winner} take it."
            draw.text((60, y), tag, font=fonts["body"], fill=INK_MUTED)

        _draw_footer(draw, fonts["footer"])
        return _to_png_bytes(img)
    except Exception:
        logger.exception("render_game_card failed for %s", game_id)
        return _placeholder_card("Card unavailable", f"Game {game_id}")


def _top_scorer_line(db: Session, game_id: str) -> Optional[str]:
    """Return a ``"Top scorer: NAME — N pts"`` string from GamePlayerStat
    if available. Defensive — returns None on any miss."""
    try:
        from db.models import GamePlayerStat  # local import; not all envs have it
    except ImportError:
        return None
    try:
        rows = (
            db.query(GamePlayerStat, Player)
            .outerjoin(Player, Player.id == GamePlayerStat.player_id)
            .filter(GamePlayerStat.game_id == game_id)
            .all()
        )
    except Exception:
        return None
    if not rows:
        return None
    top = max(rows, key=lambda r: (r[0].pts or 0))
    row, player = top
    pts = row.pts or 0
    if pts <= 0:
        return None
    name = player.full_name if player else f"#{row.player_id}"
    return f"Top scorer: {name} — {pts} pts"


# ---------------------------------------------------------------------------
# Series card
# ---------------------------------------------------------------------------


def render_series_card(db: Session, series_id: str) -> bytes:
    """Generate a playoff-series card with WP-style bar."""
    try:
        series = (
            db.query(PlayoffSeries)
            .filter(PlayoffSeries.series_id == series_id)
            .first()
        )
        if series is None:
            return _placeholder_card("Series not found", series_id)

        top = _team_for(db, series.top_seed_team_id)
        bot = _team_for(db, series.bottom_seed_team_id)

        img, draw = _new_canvas()
        fonts = _fonts()

        # Kicker — round + season
        round_label = {1: "First Round", 2: "Conference Semis", 3: "Conference Finals", 4: "NBA Finals"}.get(
            int(series.round or 0), f"Round {series.round}"
        )
        kicker = f"{round_label} · {series.season or ''}".strip(" ·")
        y = 80
        y = _draw_kicker(draw, 60, y, kicker, fonts["kicker"])
        y += 12

        top_abbr = top.abbreviation if top else "TBD"
        bot_abbr = bot.abbreviation if bot else "TBD"
        matchup = f"#{series.top_seed} {top_abbr}  vs  #{series.bottom_seed} {bot_abbr}"
        draw.text((60, y), matchup, font=fonts["title_lg"], fill=INK)
        _, mh = _measure(draw, matchup, fonts["title_lg"])
        y += mh + 16

        # Series state
        if series.status == "closed":
            state_line = (
                f"{top_abbr} wins {series.top_wins}-{series.bottom_wins}"
                if (series.winner_team_id == series.top_seed_team_id)
                else f"{bot_abbr} wins {series.bottom_wins}-{series.top_wins}"
            )
        elif series.top_wins > series.bottom_wins:
            state_line = f"{top_abbr} leads {series.top_wins}-{series.bottom_wins}"
        elif series.bottom_wins > series.top_wins:
            state_line = f"{bot_abbr} leads {series.bottom_wins}-{series.top_wins}"
        else:
            state_line = f"Series tied {series.top_wins}-{series.bottom_wins}"
        draw.text((60, y), state_line, font=fonts["stat_lg"], fill=INK)
        _, sh = _measure(draw, state_line, fonts["stat_lg"])
        y += sh + 28

        # Win-probability bar — closed-form from current state.
        wp_top = _series_wp(series.top_wins or 0, series.bottom_wins or 0)
        bar_x = 60
        bar_y = y
        bar_w = CARD_W - 120
        bar_h = 28
        # background
        draw.rectangle(
            [(bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h)],
            fill=PARCHMENT_ALT,
            outline=RULE,
            width=1,
        )
        # top-seed share
        top_w = max(0, min(bar_w, int(round(wp_top * bar_w))))
        if top_w > 0:
            draw.rectangle(
                [(bar_x, bar_y), (bar_x + top_w, bar_y + bar_h)],
                fill=GOLD,
            )
        # bottom-seed share
        if top_w < bar_w:
            draw.rectangle(
                [(bar_x + top_w, bar_y), (bar_x + bar_w, bar_y + bar_h)],
                fill=DANGER,
            )
        y += bar_h + 8

        # Bar caption
        cap = f"{top_abbr} {int(round(wp_top * 100))}%   ·   {bot_abbr} {int(round((1 - wp_top) * 100))}%"
        draw.text((bar_x, y), cap, font=fonts["stat_label"], fill=INK_MUTED)

        _draw_footer(draw, fonts["footer"])
        return _to_png_bytes(img)
    except Exception:
        logger.exception("render_series_card failed for %s", series_id)
        return _placeholder_card("Card unavailable", series_id)


def _series_wp(top_wins: int, bot_wins: int) -> float:
    """Closed-form P(top wins series) under fair-coin remaining games."""
    target = 4
    if top_wins >= target:
        return 1.0
    if bot_wins >= target:
        return 0.0
    need_top = target - top_wins
    need_bot = target - bot_wins
    memo = {}

    def prob(t: int, b: int) -> float:
        if t == 0:
            return 1.0
        if b == 0:
            return 0.0
        key = (t, b)
        if key in memo:
            return memo[key]
        v = 0.5 * prob(t - 1, b) + 0.5 * prob(t, b - 1)
        memo[key] = v
        return v

    return prob(need_top, need_bot)


# ---------------------------------------------------------------------------
# Milestone card (placeholder — CF5 owns milestone tables)
# ---------------------------------------------------------------------------


def render_milestone_card(db: Session, player_id: int, milestone_key: str) -> bytes:
    """Stub milestone card. CF5 owns the milestone schema; until that lands
    we render a generic broadsheet "milestone in progress" card so the
    endpoint shape is stable."""
    try:
        player = db.query(Player).filter(Player.id == player_id).first()
        name = player.full_name if player else f"Player #{player_id}"
        team = _player_team(db, player) if player else None

        img, draw = _new_canvas()
        fonts = _fonts()

        kicker = f"MILESTONE · {milestone_key.upper()}"
        y = 88
        y = _draw_kicker(draw, 60, y, kicker, fonts["kicker"])
        y += 12

        title_font = fonts["title_xl"]
        if _measure(draw, name, title_font)[0] > CARD_W - 120:
            title_font = fonts["title_lg"]
        draw.text((60, y), name, font=title_font, fill=INK)
        _, th = _measure(draw, name, title_font)
        y += th + 16

        sub = (
            f"{team.name} · " if team and team.name else ""
        ) + "Milestone tracking in progress."
        draw.text((60, y), sub, font=fonts["body"], fill=INK_MUTED)
        _, sh = _measure(draw, sub, fonts["body"])
        y += sh + 32

        # Gold rule
        draw.rectangle([(60, y), (60 + 80, y + 4)], fill=GOLD)
        y += 24
        draw.text(
            (60, y),
            "Full milestone reel arrives with the next edition.",
            font=fonts["body"],
            fill=INK,
        )
        _draw_footer(draw, fonts["footer"])
        return _to_png_bytes(img)
    except Exception:
        logger.exception(
            "render_milestone_card failed for %s/%s", player_id, milestone_key
        )
        return _placeholder_card("Card unavailable", f"Player #{player_id}")
