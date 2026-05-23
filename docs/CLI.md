# CLI Reference

웹 UI는 내부적으로 이 CLI를 호출합니다. 자동화·디버깅에 유용합니다.

## 진입

```powershell
# venv 활성화 후
python -m mp4maker <bundle_dir> [options]
python -m mp4maker --probe
```

## 명령 모드

| 명령 | 동작 |
|---|---|
| `python -m mp4maker --probe` | ffmpeg/ffprobe/폰트/Python 패키지 점검만 |
| `python -m mp4maker <bundle> --dry-run` | 번들 검증 + 씬 계획 출력 (ffmpeg 호출 X) |
| `python -m mp4maker <bundle>` | 풀 렌더 |
| `python -m mp4maker <bundle> --only 1` | 특정 씬만 |
| `python -m mp4maker <bundle> --only 1,3,5` | 여러 씬 |

## 옵션 전체

| 옵션 | 기본값 | 설명 |
|---|---|---|
| `--resolution WxH` | `1920x1080` | 출력 해상도 |
| `--fps N` | `30` | 프레임레이트 |
| `--crossfade SEC` | `0.6` | 씬 간 크로스페이드 시간 (xfade + acrossfade) |
| `--kenburns {auto,off}` | `auto` | 씬 인덱스별 결정적 줌/팬 모션 |
| `--font-size N` | `16` | 자막 폰트 크기 (ASS 단위, libass가 영상 높이에 맞게 자동 스케일) |
| `--margin-v N` | `40` | 자막 하단 여백 (값 작을수록 영상 하단에 가까움) |
| `--no-split-subs` | (off) | 긴 자막을 문장 단위로 쪼개지 않고 원본 그대로 |
| `--max-cue-seconds SEC` | `5.0` | 자동 분할 시 한 자막당 최대 길이 |
| `--no-soft-sub` | (off) | softsub mp4를 만들지 않음 |
| `--no-mlt` | (off) | MLT XML을 만들지 않음 |
| `--keep-work` | (off) | `_work/` 임시 폴더 보존 (디버깅용) |
| `--jobs N` | CPU-1 | 씬 병렬 렌더 수 |
| `--only LIST` | (없음) | 특정 씬만 (`1` 또는 `1,3,5`) |
| `--version` | — | 버전 출력 후 종료 |

## 자주 쓰는 조합

```powershell
# 1) 환경 점검
python -m mp4maker --probe

# 2) 1씬 빠른 검증 (1080p, Ken Burns 켬, _work 보존)
python -m mp4maker _assets\ch04_bundle --only 1 --keep-work

# 3) 풀 렌더 (기본 옵션)
python -m mp4maker _assets\ch04_bundle

# 4) 자막 폰트 더 크게, 화면 더 위로
python -m mp4maker _assets\ch04_bundle --font-size 20 --margin-v 80

# 5) 자막 자동 분할 끄고 원본 SRT 그대로
python -m mp4maker _assets\ch04_bundle --no-split-subs

# 6) Ken Burns 끄고 정적 이미지로
python -m mp4maker _assets\ch04_bundle --kenburns off

# 7) softsub/MLT 안 만들고 본편만
python -m mp4maker _assets\ch04_bundle --no-soft-sub --no-mlt

# 8) 720p 미리보기 (렌더 1.5~2배 빠름)
python -m mp4maker _assets\ch04_bundle --resolution 1280x720

# 9) 단일 코어 (디버깅, 로그 순서 보장)
python -m mp4maker _assets\ch04_bundle --jobs 1
```

## 종료 코드

| 코드 | 의미 |
|---|---|
| `0` | 성공 |
| `2` | 사용자 입력 오류 (잘못된 옵션, 누락된 번들, ffmpeg/번들 검증 실패 등) |

## stdout 태그 (진행률 파싱용)

웹 UI는 다음 태그를 파싱해 진행률 바를 갱신합니다:

```
[bundle] loading: <path>
[bundle] chNN '<title>'  scenes=N
[font]   <font name> (<path>)
[probe]  measuring audio durations via ffprobe...
[plan]   scenes=N  expected final length=Ts
[subs]   writing per-scene SRTs to <work_dir>  split=<mode>
[render] N scenes  jobs=J  res=WxH@FPSfps
[scene]  scNN start  (T.Ts)
[scene]  scNN done  (T.Ts)  progress=K/N
[stage]  concat  crossfade=0.6s
[done]   <output path>
[stage]  softsub
[done]   <output path>
[stage]  mlt
[done]   <output path>
[done]   <report_path>
[clean]  removed <work_dir>
[total]  T.Ts
```

자동화 스크립트에서 외부 진행률 모니터링이 필요하면 같은 태그를 grep하면 됩니다.
