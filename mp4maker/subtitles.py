"""Align per-scene SRT files.

If a scene has its own chNN_XX_narration.srt, use it directly (re-timed to start at 0).
Otherwise, extract its slice from the combined chNN.srt by character-proportional split,
following the SceneWeaver-CapCut convention.
"""
from __future__ import annotations

import re
from pathlib import Path

import pysrt

from .bundle import Bundle, Scene
from .timeline import TimelineEntry


_PUNCT = re.compile(r"(?<=[\.\?\!。！？])\s+")
_MAX_CUE = 7.0
_MIN_CUE = 1.5
_MAX_LINE_CHARS = 30   # one-line guideline; longer lines wrap on ffmpeg side


def write_scene_srts(
    bundle: Bundle,
    timeline: list[TimelineEntry],
    work_dir: Path,
) -> dict[int, Path]:
    """For every scene, write `work_dir / scNN.srt` with cues starting at 00:00:00.

    Returns: {scene_index: path_to_srt}
    """
    work_dir.mkdir(parents=True, exist_ok=True)
    out: dict[int, Path] = {}

    combined = _load_combined(bundle.combined_srt_path) if bundle.combined_srt_path else None

    for entry in timeline:
        scene = entry.scene
        if scene.subtitle_path and scene.subtitle_path.exists():
            cues = _load_srt(scene.subtitle_path)
            cues = _rebase_to_zero(cues, scene_duration=entry.duration)
        elif combined is not None:
            cues = _slice_from_combined(
                combined,
                scene_idx=scene.index,
                total_scenes=len(timeline),
                scene_duration=entry.duration,
            )
        else:
            cues = _from_narration_text(scene.narration_text, entry.duration)

        path = work_dir / f"sc{scene.index:02d}.srt"
        _write_srt(cues, path)
        out[scene.index] = path

    return out


def _load_srt(path: Path) -> list[pysrt.SubRipItem]:
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    subs = pysrt.from_string(text)
    return list(subs)


def _load_combined(path: Path) -> list[pysrt.SubRipItem]:
    return _load_srt(path)


def _rebase_to_zero(cues: list[pysrt.SubRipItem], scene_duration: float) -> list[pysrt.SubRipItem]:
    """Shift first cue start to 00:00:00 and cap last cue end at scene_duration."""
    if not cues:
        return cues
    first_start_ms = _to_ms(cues[0].start)
    rebased: list[pysrt.SubRipItem] = []
    for i, c in enumerate(cues, start=1):
        start_ms = max(0, _to_ms(c.start) - first_start_ms)
        end_ms = max(start_ms + int(_MIN_CUE * 1000), _to_ms(c.end) - first_start_ms)
        end_ms = min(end_ms, int(scene_duration * 1000))
        if end_ms <= start_ms:
            end_ms = min(int(scene_duration * 1000), start_ms + int(_MIN_CUE * 1000))
        rebased.append(pysrt.SubRipItem(
            index=i,
            start=_from_ms(start_ms),
            end=_from_ms(end_ms),
            text=c.text,
        ))
    return rebased


def _slice_from_combined(
    cues: list[pysrt.SubRipItem],
    scene_idx: int,
    total_scenes: int,
    scene_duration: float,
) -> list[pysrt.SubRipItem]:
    """Pick the cue with matching index, or the Nth block. Combined SRT has one block per scene."""
    if 1 <= scene_idx <= len(cues):
        c = cues[scene_idx - 1]
        end_ms = min(int(scene_duration * 1000), _to_ms(c.end) - _to_ms(c.start))
        if end_ms < int(_MIN_CUE * 1000):
            end_ms = int(scene_duration * 1000)
        return [pysrt.SubRipItem(
            index=1,
            start=_from_ms(0),
            end=_from_ms(end_ms),
            text=c.text,
        )]
    return []


def _from_narration_text(text: str, scene_duration: float) -> list[pysrt.SubRipItem]:
    """Fallback: split narration into sentences proportional to char counts."""
    if not text.strip():
        return []
    parts = [p.strip() for p in _PUNCT.split(text) if p.strip()]
    if not parts:
        parts = [text.strip()]
    total_chars = sum(len(p) for p in parts) or 1
    cues: list[pysrt.SubRipItem] = []
    cursor_ms = 0
    end_cap_ms = int(scene_duration * 1000)
    for i, p in enumerate(parts, start=1):
        share = len(p) / total_chars
        dur_ms = int(scene_duration * 1000 * share)
        dur_ms = max(int(_MIN_CUE * 1000), min(int(_MAX_CUE * 1000), dur_ms))
        start_ms = cursor_ms
        end_ms = min(end_cap_ms, start_ms + dur_ms)
        if i == len(parts):
            end_ms = end_cap_ms
        cues.append(pysrt.SubRipItem(
            index=i,
            start=_from_ms(start_ms),
            end=_from_ms(end_ms),
            text=p,
        ))
        cursor_ms = end_ms
    return cues


def _write_srt(cues: list[pysrt.SubRipItem], path: Path) -> None:
    if not cues:
        path.write_text("", encoding="utf-8")
        return
    subs = pysrt.SubRipFile(items=cues)
    subs.save(str(path), encoding="utf-8")


def _to_ms(t: pysrt.SubRipTime) -> int:
    return ((t.hours * 60 + t.minutes) * 60 + t.seconds) * 1000 + t.milliseconds


def _from_ms(ms: int) -> pysrt.SubRipTime:
    ms = max(0, int(ms))
    h, rem = divmod(ms, 3_600_000)
    m, rem = divmod(rem, 60_000)
    s, ms = divmod(rem, 1000)
    return pysrt.SubRipTime(hours=h, minutes=m, seconds=s, milliseconds=ms)


def copy_combined_for_softsub(bundle: Bundle, dest: Path) -> Path | None:
    """Copy the combined SRT to draft/ for soft-sub muxing and SRT side-car."""
    if bundle.combined_srt_path is None:
        return None
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(
        bundle.combined_srt_path.read_text(encoding="utf-8-sig", errors="replace"),
        encoding="utf-8",
    )
    return dest
