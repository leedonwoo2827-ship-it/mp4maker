"""mp4maker web UI (Streamlit). Wraps the CLI so all rendering logic stays in one place.

Launch:
    python -m streamlit run app.py
"""
from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

import streamlit as st


_SCENES_PLAN = re.compile(r"\[plan\][^\n]*scenes=(\d+)")
_SCENE_DONE = re.compile(r"\[scene\]\s+sc(\d+)\s+done.*progress=(\d+)/(\d+)")
_SCENE_START = re.compile(r"\[scene\]\s+sc(\d+)\s+start")
_STAGE = re.compile(r"\[stage\]\s+(\w+)")

PROJECT_ROOT = Path(__file__).parent.resolve()
ASSETS_DIR = PROJECT_ROOT / "_assets"


def list_bundles() -> list[Path]:
    if not ASSETS_DIR.is_dir():
        return []
    out: list[Path] = []
    for p in sorted(ASSETS_DIR.iterdir()):
        if p.is_dir() and (p / "script").is_dir() and any((p / "script").glob("*_script.json")):
            out.append(p)
    return out


def load_bundle_safe(bundle_dir: Path):
    """Best-effort load for scene metadata. Returns None on failure (UI keeps working)."""
    try:
        from mp4maker.bundle import load_bundle
        return load_bundle(bundle_dir)
    except Exception:
        return None


def run_streaming(
    cmd: list[str],
    log_container,
    progress_bar=None,
    stage_container=None,
) -> int:
    """Run cmd, stream stdout line-by-line into the given Streamlit container.

    Parses mp4maker's tagged output to update progress_bar and stage_container:
      [plan] ... scenes=N           -> total
      [scene] scNN start            -> stage = "씬 NN 시작"
      [scene] scNN done progress=K/N -> bar = K/(N+3), stage = "씬 K/N"
      [stage] concat|softsub|mlt    -> bar advances per post-stage
    """
    env = os.environ.copy()
    env.setdefault("PYTHONIOENCODING", "utf-8")
    env.setdefault("PYTHONUNBUFFERED", "1")
    proc = subprocess.Popen(
        cmd,
        cwd=str(PROJECT_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
        env=env,
    )
    lines: list[str] = []
    total = 0
    done = 0
    # The progress denominator: N scene renders + concat + softsub + mlt = N + 3 buckets.
    POST_BUCKETS = 3

    def _bar(frac: float, label: str) -> None:
        if progress_bar is not None:
            try:
                progress_bar.progress(max(0.0, min(1.0, frac)), text=label)
            except Exception:
                pass
        if stage_container is not None:
            stage_container.markdown(f"**진행 상태:** {label}")

    assert proc.stdout is not None
    for line in proc.stdout:
        ln = line.rstrip()
        lines.append(ln)
        # show last 200 lines to keep the page snappy
        log_container.code("\n".join(lines[-200:]), language="text")

        m = _SCENES_PLAN.search(ln)
        if m:
            total = int(m.group(1))
            _bar(0.02, f"준비 완료 · 총 {total}씬")
            continue

        m = _SCENE_START.search(ln)
        if m and total:
            _bar(done / (total + POST_BUCKETS), f"씬 sc{int(m.group(1)):02d} 렌더 중 · {done}/{total} 완료")
            continue

        m = _SCENE_DONE.search(ln)
        if m:
            done = int(m.group(2))
            total = int(m.group(3))
            _bar(done / (total + POST_BUCKETS), f"씬 {done}/{total} 완료")
            continue

        m = _STAGE.search(ln)
        if m and total:
            stage = m.group(1)
            extra = {"concat": 1, "softsub": 2, "mlt": 3}.get(stage, 0)
            label = {"concat": "씬 연결 (xfade)", "softsub": "softsub 임베드", "mlt": "MLT XML 생성"}.get(stage, stage)
            _bar((total + extra) / (total + POST_BUCKETS), label)
            continue

        if ln.startswith("[total]"):
            _bar(1.0, "완료")

    proc.wait()
    if proc.returncode == 0:
        _bar(1.0, "완료")
    return proc.returncode


def open_in_explorer(path: Path) -> None:
    if sys.platform == "win32":
        os.startfile(str(path))  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])


# ── Page ─────────────────────────────────────────────────────────────────
st.set_page_config(page_title="mp4maker", layout="wide", page_icon="🎬")
st.title("🎬 mp4maker")
st.caption("ScriptForge → FlowGenie → VoiceWright 번들을 로컬 MP4로 합성")


# ── Sidebar: bundle & options ────────────────────────────────────────────
with st.sidebar:
    st.header("번들")
    bundles = list_bundles()
    if not bundles:
        st.error(f"`_assets/` 아래 `chNN_bundle` 폴더를 찾지 못했습니다.\n\n경로: `{ASSETS_DIR}`")
        st.stop()

    bundle = st.selectbox(
        "대상",
        bundles,
        format_func=lambda p: p.name,
        index=0,
    )

    b = load_bundle_safe(bundle)
    if b:
        st.caption(
            f"`{b.chapter_id}` · 씬 {len(b.scenes)}개 · "
            f"제목: {b.title or '(없음)'} · "
            f"hint {b.total_duration_hint:.0f}s"
        )
        if b.warnings:
            for w in b.warnings:
                st.warning(w)
    else:
        st.warning("번들 로드 미리보기 실패 (실행은 가능할 수 있음)")

    st.divider()
    st.header("출력 사양")
    resolution = st.selectbox("해상도", ["1920x1080", "1280x720", "3840x2160"], index=0)
    fps = st.selectbox("FPS", [30, 24, 60], index=0)
    crossfade = st.slider("씬 크로스페이드 (초)", 0.0, 1.5, 0.6, 0.1)
    kenburns = st.radio("Ken Burns", ["auto", "off"], horizontal=True)
    font_size = st.slider("자막 폰트 크기", 8, 24, 16, 1,
                          help="ASS 단위. 16 권장 — 1080p에서 한 줄 문장이 깔끔하게 들어가는 크기.")
    margin_v = st.slider("자막 하단 여백", 10, 120, 40, 5,
                         help="값이 작을수록 자막이 영상 하단에 가까워집니다.")
    st.markdown("**자막 분할**")
    split_subs = st.checkbox(
        "긴 자막을 문장 단위로 자동 분할",
        value=True,
        help="ON이면 18초짜리 한 덩어리 자막을 마침표·물음표·느낌표 기준으로 잘라 차례대로 표시. "
             "원본 SRT를 그대로 쓰고 싶으면 OFF.",
    )
    max_cue_seconds = st.slider(
        "분할 시 한 자막당 최대 길이 (초)",
        2.0, 8.0, 5.0, 0.5,
        disabled=not split_subs,
    )

    st.divider()
    st.header("실행")
    cpu = os.cpu_count() or 8
    jobs = st.slider("병렬 작업 (CPU 코어)", 1, cpu, max(1, cpu - 1))
    soft_sub = st.checkbox("softsub MP4 동시 생성", True)
    mlt = st.checkbox("MLT XML 동시 생성 (Shotcut용)", True)
    keep_work = st.checkbox("`_work/` 폴더 보존 (디버깅)", False)

    st.divider()
    st.header("씬 범위")
    range_mode = st.radio(
        "범위",
        ["전체", "특정 씬만"],
        horizontal=True,
        label_visibility="collapsed",
    )
    only_scenes: list[int] = []
    if range_mode == "특정 씬만":
        if b:
            options = [s.index for s in b.scenes]
            only_scenes = st.multiselect(
                "씬 번호",
                options,
                default=[1],
                help="여러 개 선택 가능. 디버깅 시 1씬만 골라 빠르게 확인하세요.",
            )
        else:
            text = st.text_input("씬 번호 (콤마 구분)", "1")
            try:
                only_scenes = [int(x.strip()) for x in text.split(",") if x.strip()]
            except ValueError:
                st.error("숫자만 콤마로 구분해 입력하세요")


# ── Derived paths ────────────────────────────────────────────────────────
draft_dir = bundle / "draft"
work_dir = draft_dir / "_work"
chapter_id = bundle.name.replace("_bundle", "") if bundle.name.endswith("_bundle") else bundle.name
final_mp4 = draft_dir / f"{chapter_id}_final.mp4"
softsub_mp4 = draft_dir / f"{chapter_id}_final_softsub.mp4"
side_srt = draft_dir / f"{chapter_id}.srt"
mlt_path = draft_dir / f"{chapter_id}_project.mlt"
report_json = draft_dir / "render_report.json"
sample_sc01 = work_dir / "sc01.mp4"


# ── Main: actions ────────────────────────────────────────────────────────
c1, c2, c3, c4 = st.columns([1, 1, 1, 1])
do_probe = c1.button("🔍 환경 점검", use_container_width=True)
do_render = c2.button("▶ 렌더 시작", type="primary", use_container_width=True)
do_open = c3.button(
    "📂 draft 폴더 열기",
    use_container_width=True,
    disabled=not draft_dir.exists(),
)
do_dryrun = c4.button("🧪 Dry-run (검증만)", use_container_width=True)

stage_box = st.empty()
progress_bar = st.progress(0.0, text="대기 중")
log_box = st.empty()

if do_open:
    open_in_explorer(draft_dir)
    st.toast(f"열림: {draft_dir.name}")

if do_probe:
    with st.status("환경 점검 중...", expanded=True):
        rc = run_streaming([sys.executable, "-m", "mp4maker", "--probe"], log_box)
        st.success("환경 점검 완료") if rc == 0 else st.error(f"실패 (exit {rc})")

if do_dryrun:
    with st.status("Dry-run 중...", expanded=True):
        rc = run_streaming(
            [sys.executable, "-m", "mp4maker", str(bundle), "--dry-run"],
            log_box,
        )
        st.success("Dry-run OK") if rc == 0 else st.error(f"실패 (exit {rc})")

if do_render:
    cmd = [sys.executable, "-m", "mp4maker", str(bundle)]
    cmd += [
        "--resolution", resolution,
        "--fps", str(fps),
        "--crossfade", f"{crossfade:.2f}",
        "--kenburns", kenburns,
        "--font-size", str(font_size),
        "--margin-v", str(margin_v),
        "--jobs", str(jobs),
        "--max-cue-seconds", f"{max_cue_seconds:.1f}",
    ]
    if not split_subs:
        cmd.append("--no-split-subs")
    if not soft_sub:
        cmd.append("--no-soft-sub")
    if not mlt:
        cmd.append("--no-mlt")
    if keep_work:
        cmd.append("--keep-work")
    if only_scenes:
        cmd += ["--only", ",".join(str(i) for i in sorted(only_scenes))]

    st.markdown("**실행 명령**")
    st.code(" ".join(shlex.quote(a) for a in cmd), language="powershell")

    with st.status("렌더링 중... (한참 걸릴 수 있음)", expanded=True):
        rc = run_streaming(cmd, log_box, progress_bar=progress_bar, stage_container=stage_box)
        if rc == 0:
            st.success("렌더 완료")
            st.balloons()
        else:
            st.error(f"렌더 실패 (exit {rc}) — 로그를 확인하세요")


# ── Outputs ──────────────────────────────────────────────────────────────
st.divider()
st.subheader("산출물")

if not draft_dir.exists():
    st.info("아직 렌더 결과가 없습니다. 사이드바에서 옵션을 정하고 **렌더 시작**을 누르세요.")
else:
    left, right = st.columns([3, 2])

    with left:
        if final_mp4.exists():
            st.markdown(f"**🎬 본편** · `{final_mp4.name}` · {final_mp4.stat().st_size / 1e6:.1f} MB")
            st.video(str(final_mp4))
        elif sample_sc01.exists():
            st.markdown(f"**🧪 씬 샘플** · `sc01.mp4` · {sample_sc01.stat().st_size / 1e6:.1f} MB")
            st.video(str(sample_sc01))
        else:
            st.caption("본편 또는 씬 샘플이 아직 없습니다 (특정 씬 렌더 시 `--keep-work` 켜면 `_work/sc01.mp4`로 미리보기 가능)")

    with right:
        st.markdown("**다운로드 / 열기**")
        if final_mp4.exists():
            with open(final_mp4, "rb") as f:
                st.download_button(
                    f"⬇ 본편 ({final_mp4.stat().st_size / 1e6:.1f} MB)",
                    f, file_name=final_mp4.name, mime="video/mp4",
                    use_container_width=True,
                )
        if softsub_mp4.exists():
            with open(softsub_mp4, "rb") as f:
                st.download_button(
                    f"⬇ softsub ({softsub_mp4.stat().st_size / 1e6:.1f} MB)",
                    f, file_name=softsub_mp4.name, mime="video/mp4",
                    use_container_width=True,
                )
        if side_srt.exists():
            with open(side_srt, "rb") as f:
                st.download_button(
                    f"⬇ SRT ({side_srt.stat().st_size / 1024:.1f} KB)",
                    f, file_name=side_srt.name, mime="application/x-subrip",
                    use_container_width=True,
                )
        if mlt_path.exists():
            with open(mlt_path, "rb") as f:
                st.download_button(
                    f"⬇ MLT (Shotcut)",
                    f, file_name=mlt_path.name, mime="application/xml",
                    use_container_width=True,
                )

        if report_json.exists():
            st.markdown("---")
            st.markdown("**📊 render_report.json**")
            try:
                data = json.loads(report_json.read_text(encoding="utf-8"))
                st.caption(
                    f"총 출력 길이: {data.get('total_output_seconds', 0):.1f}s · "
                    f"총 렌더 시간: {data.get('total_render_seconds', 0):.1f}s"
                )
                with st.expander("씬별 상세"):
                    rows = [
                        {
                            "씬": s["scene"],
                            "제목": s["title"],
                            "길이(s)": s["duration_seconds"],
                            "렌더(s)": s.get("render_seconds"),
                            "경고": ", ".join(s.get("warnings", [])) or "—",
                        }
                        for s in data.get("scenes", [])
                    ]
                    st.dataframe(rows, use_container_width=True, hide_index=True)
            except Exception as e:
                st.warning(f"리포트 파싱 실패: {e}")
