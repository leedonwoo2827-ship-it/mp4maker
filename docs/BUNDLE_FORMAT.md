# Bundle Format

mp4maker가 `_assets/chNN_bundle/` 폴더를 어떻게 읽는지 정리한 문서.

## 폴더 트리

각 장(chapter)은 하나의 번들 폴더입니다. 이름 규칙: `chNN_bundle` (NN은 2자리 숫자).

```
_assets/
└── ch04_bundle/
    ├── script/
    │   └── ch04_script.json               필수
    ├── images/
    │   ├── ch04_01_*.{jpeg,jpg,png}       씬당 1장
    │   ├── ch04_02_*.{jpeg,jpg,png}
    │   └── ...
    ├── audio/
    │   ├── ch04_01_narration.{wav,mp3,m4a,flac}    씬당 1개
    │   ├── ch04_02_narration.{wav,mp3,m4a,flac}
    │   └── ...
    ├── subtitles/
    │   ├── ch04_01_narration.srt          씬별 SRT (우선 사용)
    │   ├── ch04_02_narration.srt
    │   ├── ...
    │   └── ch04.srt                       통합 SRT (개별 SRT 없을 때 폴백)
    └── draft/                             도구가 만들어 채움
```

## 파일 명명 규칙

| 종류 | 패턴 | 예 |
|---|---|---|
| 스크립트 JSON | `chNN_script.json` (1개만) | `ch04_script.json` |
| 이미지 | `chNN_XX*.{jpeg,jpg,png,webp}` | `ch04_01_opening.jpeg` |
| 오디오 | `chNN_XX_narration.{wav,mp3,m4a,flac}` | `ch04_01_narration.wav` |
| 씬별 자막 | `chNN_XX_narration.srt` 또는 `chNN_XX.srt` | `ch04_01_narration.srt` |
| 통합 자막 | `chNN.srt` | `ch04.srt` |

**NN, XX는 모두 2자리 0-padded 숫자** (`01`, `02`, ... `19`).

## 파일명 자동 폴백

JSON의 `image_filename` 필드가 실제 파일과 살짝 달라도 도구가 자동 매칭합니다.

| JSON에 적힘 | 실제 파일 | 결과 |
|---|---|---|
| `ch04_01_opening.png` | `ch04_01_opening.png` | exact match |
| `ch04_01_opening.png` | `ch04_01_opening.jpeg` | stem match (확장자 다름) |
| `ch04_01_opening.png` | `ch04_01_opening_1.jpeg` | prefix glob fallback |
| (이미지 못 찾음) | — | 에러 메시지 + 누락 씬 번호 출력, 종료 |

## script JSON 스키마

```json
{
  "version": "1.0",
  "chapter": 4,
  "title": "웹이 연 학습의 문",
  "subtitle": "학습은 구조화된 데이터가 되었다",
  "part": "제2부 연결되는 배움 (1990-2012)",
  "genre": "classic-documentary-full",
  "aspect_ratio": "16:9",
  "total_duration_seconds": 827,
  "default_model": "nano_banana",
  "narration_style": { "tone": "...", "person": "3인칭", "tempo": "measured" },
  "scenes": [
    {
      "scene": 1,
      "scene_type": "opening_title",
      "title": "오프닝 타이틀",
      "narration_text": "1989년, 한 장의 제안서가...",
      "narration_seconds": 18,
      "prompt": "Series opening title sequence, ...",
      "model": "nano_banana",
      "image_filename": "ch04_01_opening_title.png",
      "visual_description": "...",
      "scene_meta": {
        "era": "opening",
        "mood": "opening",
        "transition_hint": "fade_in",
        "text_overlay": "4장. 웹이 연 학습의 문",
        "subtitle": "...",
        "bgm_hint": "opening_orchestral_swell"
      }
    }
  ]
}
```

### 도구가 실제로 쓰는 필드

| 필드 | 용도 |
|---|---|
| `chapter` | 번들 ID (`ch04`) 결정. 누락 시 파일명에서 추출. |
| `title` | 리포트·UI 표시 |
| `scenes[].scene` | 1-based 인덱스 |
| `scenes[].title` | 진행 로그·리포트 표시 |
| `scenes[].narration_text` | 자막 자동 생성 폴백 (SRT가 없을 때) |
| `scenes[].narration_seconds` | hint만 (실제 길이는 ffprobe로 측정) |
| `scenes[].image_filename` | 이미지 파일 매칭 시작점 |
| `scenes[].scene_meta` | 리포트에 보존 (지금은 렌더 영향 없음) |

`prompt`, `visual_description`, `model`, `bgm_hint` 등 다른 필드는 **현재 무시**합니다.

## 자막 우선순위

1. `subtitles/chNN_XX_narration.srt` 존재 → 그대로 사용 (영상 시작 0초로 재정렬)
2. 없으면 `subtitles/chNN.srt`에서 N번째 블록 추출
3. 둘 다 없으면 `narration_text`를 문장 단위로 쪼개 비례 시간 배분

자동 분할(`--split-subs`, 기본 ON)이 켜져 있으면 5초 넘는 cue는 `.`/`?`/`!` 기준으로 자동 분할.
자세한 내용은 [CLI.md](CLI.md) 참고.

## 무결성 검증

`bundle.py`가 로딩 시점에 검증합니다:

- 씬마다 이미지 + 오디오가 있어야 함 (없으면 에러로 종료, 누락 씬 번호 출력)
- 자막은 씬별/통합 중 **하나라도** 있으면 통과 (둘 다 없으면 `narration_text`로 자동 생성)
- 파일 인코딩은 SRT의 경우 `utf-8-sig`로 읽어 BOM 제거
