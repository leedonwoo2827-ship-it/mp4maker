# mp4maker

ScriptForge JSON + FlowGenie 이미지 + VoiceWright(또는 Supertone) 오디오/자막 번들을
**로컬 PC에서 ffmpeg로 직접 MP4로 합성**하는 도구. CapCut 없이도 완결되는 파이프라인.

CLI와 **웹 UI(Streamlit)** 둘 다 제공. CLI는 자동화·CI에, 웹 UI는 자막/모션 미세조정에.

## 주요 기능

| # | 항목 | 산출물 / 동작 |
|---|---|---|
| 1 | **풀 렌더** | `chNN_final.mp4` (1080p 30fps, burn-in 자막, Ken Burns, 씬 크로스페이드) |
| 2 | **softsub MP4** | `chNN_final_softsub.mp4` (자막 트랙 별도 임베드) |
| 3 | **SRT 동봉** | `chNN.srt` (UTF-8 정규화) |
| 4 | **Shotcut 프로젝트** | `chNN_project.mlt` (GUI에서 미세조정 후 melt.exe로 재렌더 가능) |
| 5 | **렌더 리포트** | `render_report.json` (씬별 길이·렌더 시간·경고) |

## 설치

### Windows
```powershell
setup.bat
```

### macOS / Linux
```bash
chmod +x setup.sh run.sh
./setup.sh
```

스크립트가 자동으로 처리하는 것:
- 가상환경 `.venv/` 생성
- `requirements.txt` 설치 (`pysrt`, `lxml`, `streamlit`)
- ffmpeg 존재 확인 (없으면 설치 명령 안내)
- `_assets/` 폴더 생성

**ffmpeg는 별도 설치 필요** (보안상 자동 설치 안 함):
- Windows: `winget install Gyan.FFmpeg`
- macOS: `brew install ffmpeg`
- Ubuntu/Debian: `sudo apt install ffmpeg`

설치 후 새 터미널을 열어주세요 (PATH 갱신).

## 실행

### Windows
```powershell
run.bat
```

### macOS / Linux
```bash
./run.sh
```

브라우저 탭이 자동으로 열리며 `http://localhost:8501` 에 UI가 뜹니다.
사이드바에서 번들·해상도·자막 옵션을 고르고 **▶ 렌더 시작** 버튼을 누르면 진행률 바와 실시간 로그가 표시됩니다.

CLI를 직접 쓰고 싶다면:
```powershell
.venv\Scripts\activate           # Windows
source .venv/bin/activate        # macOS/Linux
python -m mp4maker --probe
python -m mp4maker _assets\ch04_bundle
```

자세한 옵션은 [docs/CLI.md](docs/CLI.md) 참고.

## 폴더 구조

레포에는 **소스 코드만** 들어 있습니다. 영상 만들 재료는 용량이 커서 git에 올리지 않으며, **사용자가 `_assets/` 폴더에 직접 채워야** 합니다.

```
mp4maker-repo/
├── mp4maker/                  도구 소스 (Python 패키지)
├── app.py                     웹 UI (Streamlit)
├── setup.bat / setup.sh       환경 셋업
├── run.bat / run.sh           웹 UI 실행
├── requirements.txt
├── README.md
├── docs/                      상세 문서
└── _assets/                   ← 사용자가 채움 (git 제외)
    ├── ch01_bundle/
    ├── ch02_bundle/
    └── chNN_bundle/
        ├── script/      chNN_script.json
        ├── images/      chNN_XX_*.{jpeg,jpg,png}
        ├── audio/       chNN_XX_narration.wav
        ├── subtitles/   chNN_XX_narration.srt (+ chNN.srt 통합본)
        └── draft/       도구가 산출물을 채움
```

각 폴더의 출처:
- `script/` — [ScriptForge](https://github.com/leedonwoo2827-ship-it/scriptforge)
- `images/` — [FlowGenie](https://github.com/leedonwoo2827-ship-it/flowgenie) (veo3 크롬 확장)
- `audio/` + `subtitles/` — [VoiceWright](https://github.com/leedonwoo2827-ship-it/voicewright) 또는 Supertone 3

번들 스키마·파일명 규칙 전체는 [docs/BUNDLE_FORMAT.md](docs/BUNDLE_FORMAT.md) 참고.

## 문서

| 문서 | 내용 |
|---|---|
| [docs/BUNDLE_FORMAT.md](docs/BUNDLE_FORMAT.md) | `_assets/chNN_bundle/` 폴더·파일 명명 규칙, JSON 스키마, 자막 우선순위, 무결성 검증 |
| [docs/CLI.md](docs/CLI.md) | 모든 CLI 옵션, 자주 쓰는 조합, stdout 태그 (진행률 파싱용) |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | 처리 파이프라인, 모듈 책임, 핵심 결정(자막 자동 분할·Ken Burns·MLT 등), ffmpeg filter graph |

## 검증 순서 (처음 받았을 때)

1. `setup.bat` / `./setup.sh` — 환경 셋업
2. ffmpeg 설치 (winget/brew/apt) → 새 터미널 열기
3. `_assets/chNN_bundle/` 채워 넣기
4. `run.bat` / `./run.sh` → 웹 UI에서 "환경 점검" 버튼
5. ch04 번들 1씬만 렌더 (사이드바 "특정 씬만" → 1) → 자막·Ken Burns 시각 확인
6. 만족하면 풀 렌더
7. Shotcut에서 `draft/chNN_project.mlt` 열어 수동 검수 (선택)

## 파이프라인 전체

```
StoryLens   →   ScriptForge   →   FlowGenie     →   VoiceWright/Supertone   →   mp4maker
(상담/기획)     (대본 JSON)      (장면 이미지)      (자막 + 음성)               (로컬 MP4)
```

원본 SceneWeaver-CapCut(CapCut 데스크톱 드래프트 생성) 자리를 mp4maker가 대체.
입력 인터페이스(폴더 구조·명명 규칙·JSON 스키마)는 호환을 유지하므로 같은 번들을 양쪽 어디에도 넣을 수 있습니다.

## 라이선스

MIT (예정).
