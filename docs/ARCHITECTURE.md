# Architecture

## 처리 파이프라인

```
load_bundle()        → bundle.py        JSON 파싱 + 파일 인벤토리 + 무결성 검증
    ↓
measure_durations()  → timeline.py      ffprobe로 각 wav의 정확한 길이
    ↓
align_subtitles()    → subtitles.py     씬별 SRT + 긴 cue 자동 분할
    ↓
render_scenes()      → render_scene.py  씬별 ffmpeg (병렬, ProcessPoolExecutor)
    ↓                                   이미지 → letterbox → Ken Burns → 자막 burn-in → mp4
concat()             → concat.py        xfade + acrossfade 체이닝
    ↓
mux_softsub()        → concat.py        soft SRT 트랙 임베드 (옵션)
    ↓
emit_mlt()           → mlt.py           Shotcut/Kdenlive MLT XML (옵션)
    ↓
emit_report()        → report.py        render_report.json
```

## 모듈 책임

| 모듈 | 역할 | 외부 의존 |
|---|---|---|
| `bundle.py` | `chNN_bundle/` 로드, 파일명 폴백, 무결성 검증, `Bundle`/`Scene` 데이터클래스 | — |
| `timeline.py` | ffprobe로 wav 길이 측정, 크로스페이드 누적 보정한 `TimelineEntry` | ffprobe |
| `subtitles.py` | 씬별 SRT 정렬, 5초+ cue를 문장 단위로 자동 분할 | pysrt |
| `fonts.py` | Windows 폰트 폴더에서 Pretendard → 나눔고딕 → 맑은 고딕 순으로 탐지 | — |
| `kenburns.py` | 씬 인덱스 % 4 → {zoom-in, zoom-out, pan-right, pan-left} 결정적 분배 | — |
| `ffmpeg_runner.py` | `subprocess` 래퍼. 실패 시 stderr 로그 + 재현 가능한 `.cmd` 덤프 | ffmpeg |
| `render_scene.py` | 씬 1개의 ffmpeg filter graph (scale → zoompan → subtitles burn-in) | ffmpeg |
| `concat.py` | `filter_complex`로 xfade + acrossfade 체이닝, softsub mov_text 임베드 | ffmpeg |
| `mlt.py` | Shotcut/Kdenlive 호환 MLT XML 생성 (producers + playlists + tractor) | lxml |
| `report.py` | `render_report.json` 작성 | — |
| `cli.py` | argparse + 오케스트레이션 + 진행 로그 출력 | — |
| `app.py` | Streamlit 웹 UI (CLI를 subprocess로 호출하고 stdout 태그 파싱) | streamlit |

## 핵심 결정

### 씬 길이는 ffprobe가 정답
JSON의 `narration_seconds`는 hint일 뿐, 실제로는 `ffprobe -show_entries format=duration`으로 측정한 wav 길이를 사용. TTS 엔진(VoiceWright/Supertone)이 텍스트와 정확히 일치하는 시간을 만들지 않으므로.

### 크로스페이드 누적 보정
씬 N의 타임라인 시작 = `sum(prior durations) - N * crossfade`. xfade는 두 씬의 끝/시작이 겹치므로 전체 길이에서 `(N-1) * crossfade`가 빠집니다.

### 자막 자동 분할
원본 SRT가 18초짜리 한 덩어리로 되어 있어도, 5초 넘으면 문장 단위(`.`/`?`/`!`/`。`/`！`/`？`)로 분할하고 문자수 비례로 시간 배분. 각 sub-cue는 [1.5s, 7s] 범위로 clamp.

### 결정적 Ken Burns
씬 인덱스(1-based) % 4로 모션 패턴을 고르므로, 같은 번들을 다시 렌더해도 똑같은 결과. zoom은 1.00 ~ 1.08 범위로 미세하게.

### 4배 오버샘플링
zoompan 이전에 `scale=W*4:H*4`로 키워뒀다가 줌인하면 픽셀이 깨지지 않음. 메모리는 좀 쓰지만 결과 품질이 확연히 좋아짐.

### libass의 ASS 단위
`--font-size 16`은 픽셀이 아니라 ASS 단위. libass가 PlayResY(기본 288) 기준으로 처리하므로 1080p에서 16 ≈ 60px로 렌더링됨. 사용자가 보는 슬라이더 범위 8~24도 이 단위.

### Subprocess 병렬
`ProcessPoolExecutor`로 씬을 병렬 렌더. 19씬을 8코어로 돌리면 3 wave (8+8+3) 정도. 진행률은 메인 프로세스가 `as_completed`로 받아 `[scene] scNN done progress=K/N` 라인을 stdout에 흘림. 웹 UI는 그걸 파싱.

### 출력 모드 두 개
- `chNN_final.mp4` — burn-in 자막 (자막이 픽셀에 합성됨, 모든 플레이어에서 보장)
- `chNN_final_softsub.mp4` — burn-in + soft sub 트랙도 임베드 (자막 끄기/언어 선택 가능)

소비처 분기를 줄이려고 둘 다 만듭니다 (`--no-soft-sub`로 끌 수 있음).

### MLT XML은 보조
ffmpeg가 메인 렌더러. MLT는 "GUI에서 손볼 수 있는 중간 산출물"로만 두고, 실제 렌더는 ffmpeg가 한 mp4가 정답. Shotcut에서 열면 같은 타임라인이 보이고, 손본 뒤 `melt.exe`로 재렌더 가능.

## 산출물 상세

| 파일 | 만든 사람 | 비고 |
|---|---|---|
| `chNN_final.mp4` | `concat.py` | H.264 yuv420p CRF 18 + AAC 192k, faststart |
| `chNN_final_softsub.mp4` | `concat.py::mux_softsub` | 위 + mov_text 자막 트랙 (재인코딩 X, copy) |
| `chNN.srt` | `subtitles.py::copy_combined_for_softsub` | 입력 통합 SRT를 UTF-8 LF로 정규화 |
| `chNN_project.mlt` | `mlt.py::write_mlt` | producers (이미지/오디오) + playlists + tractor |
| `render_report.json` | `report.py::write_report` | 씬별 길이/사용 파일/렌더 시간/경고, ensure_ascii=False |
| `_work/scNN.mp4` | `render_scene.py` | `--keep-work` 시 보존, 디버깅용 |
| `_work/scNN.srt` | `subtitles.py` | 씬별 SRT (0초 기준 재정렬, 분할 적용 후) |
| `_work/ffmpeg_*.log` | `ffmpeg_runner.py` | 실패 시 stderr + 재현 명령 덤프 |
| `_work/ffmpeg_*.cmd` | `ffmpeg_runner.py` | 그대로 더블클릭 또는 PS에 붙여넣어 재실행 가능 |

## 핵심 ffmpeg filter graph (씬 1개)

```
[0:v]
    scale=W*4:H*4:force_original_aspect_ratio=decrease,
    pad=W*4:H*4:(ow-iw)/2:(oh-ih)/2:color=black,
    setsar=1
[over];

[over]
    zoompan=z='<expr>':x='<expr>':y='<expr>':d=D_frames:fps=FPS:s=WxH
[zoomed];

[zoomed]
    subtitles='scNN.srt':force_style='FontName=...,FontSize=16,Alignment=2,MarginV=40,...'
[v]
```

## 진행률 태그 (UI용)

`[scene] scNN done progress=K/N` 같은 prefix 태그를 cli.py가 stdout에 print(..., flush=True). app.py가 정규식으로 파싱해 `st.progress` 갱신. 다른 자동화 스크립트도 같은 grep으로 진행률 추적 가능.

## 비목표 (지금 단계)

- BGM 트랙 (입력 스키마에 추가되면 자리 마련만 해둠)
- mood/era → 트랜지션·자막 스타일 매핑 (SceneWeaver-CapCut v0.3 로드맵과 같은 위치)
- GPU 인코딩 (NVENC/QSV) — libx264 안정성 우선
- 자체 GUI(데스크톱 앱) — Streamlit 웹 UI로 갈음
