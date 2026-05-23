# mp4maker

ScriptForge JSON + FlowGenie 이미지 + VoiceWright(슈퍼톤) 오디오/자막 번들을
로컬 PC에서 ffmpeg로 직접 MP4로 합성하는 도구.

원래 파이프라인의 마지막 단계인 SceneWeaver-CapCut(CapCut 데스크톱 드래프트 생성)을
대체해, CapCut 의존 없이 1080p 30fps MP4(burn-in 자막) + Shotcut용 MLT XML을 산출한다.

## 디렉토리 구조

```
260523-mp4-maker/           ← 본 레포 루트
├── mp4maker/               Python 패키지 (도구 소스)
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli.py
│   ├── bundle.py
│   ├── timeline.py
│   ├── subtitles.py
│   ├── fonts.py
│   ├── kenburns.py
│   ├── ffmpeg_runner.py
│   ├── render_scene.py
│   ├── concat.py
│   ├── mlt.py
│   └── report.py
├── _assets/                작업 번들 (git 제외)
│   ├── ch01_bundle/
│   ├── ch02_bundle/
│   └── ch04_bundle/
│       ├── script/   chNN_script.json
│       ├── images/   chNN_XX_*.{jpeg,jpg,png}
│       ├── audio/    chNN_XX_narration.wav
│       ├── subtitles/ chNN_XX_narration.srt (+ chNN.srt)
│       └── draft/    ← 본 도구의 산출물 위치
├── requirements.txt
└── README.md
```

## 사전 준비

1. **Python 3.11+**
2. **ffmpeg 7.x** (PATH에 등록)
   ```powershell
   winget install Gyan.FFmpeg
   ```
3. **Python 패키지**
   ```powershell
   pip install -r requirements.txt
   ```
4. **한글 폰트** (자동 탐지: Pretendard → 나눔고딕 → 맑은 고딕)

## 실행

레포 루트에서 실행:

```powershell
cd d:\00work\260523-mp4-maker

# 풀 렌더
python -m mp4maker _assets\ch04_bundle

# 단일 씬만 (디버깅)
python -m mp4maker _assets\ch04_bundle --only 1 --keep-work

# 환경 점검만
python -m mp4maker --probe
```

### 옵션

| 옵션 | 기본값 | 설명 |
|------|--------|------|
| `--resolution` | 1920x1080 | 출력 해상도 |
| `--fps` | 30 | 프레임레이트 |
| `--crossfade` | 0.6 | 씬 간 크로스페이드 (초) |
| `--kenburns` | auto | `auto` 또는 `off` |
| `--no-soft-sub` | (off) | softsub mp4를 만들지 않음 |
| `--no-mlt` | (off) | MLT XML을 만들지 않음 |
| `--keep-work` | (off) | `_work/` 임시 폴더 보존 |
| `--jobs` | CPU 코어 수 | 씬 병렬 렌더 수 |
| `--only` | (없음) | 특정 씬만 (예: `--only 1` 또는 `--only 1,3,5`) |

## 산출물 (각 번들의 draft/)

```
chNN_final.mp4              burn-in 본편 (제출용)
chNN_final_softsub.mp4      burn-in + soft sub 트랙 임베드
chNN.srt                    동봉용 SRT
chNN_project.mlt            Shotcut/Kdenlive 프로젝트
render_report.json          씬별 길이·사용 파일·렌더 시간·경고
_work/                      디버깅 임시 (기본 자동 삭제, --keep-work 시 보존)
```

## 검증 순서

```powershell
# 1) 환경 점검
python -m mp4maker --probe

# 2) ch04 1씬만 렌더 (폰트·자막·Ken Burns 시각 확인)
python -m mp4maker _assets\ch04_bundle --only 1 --keep-work

# 3) ch04 풀 렌더
python -m mp4maker _assets\ch04_bundle

# 4) Shotcut에서 draft/ch04_project.mlt 열어 검수

# 5) 1·2장 동일 명령
python -m mp4maker _assets\ch01_bundle
python -m mp4maker _assets\ch02_bundle
```
