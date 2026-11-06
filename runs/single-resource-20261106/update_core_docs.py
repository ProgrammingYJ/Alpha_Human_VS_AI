"""Reconcile reviewed current policy; keep dated experiment history intact."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATE = "2026-11-06"

def reviewed(name):
    path = ROOT / name
    text = path.read_text(encoding="utf-8")
    text = text.replace("최종 검토: 2026-11-05", "최종 검토: " + DATE, 1)
    text = text.replace("이번 작업 검토:", "이전 작업 검토:")
    return path, text

path, text = reviewed("AGENTS.md")
text = text.replace("## 최신 확정 요구사항 (2026-11-05)", "## 최신 확정 요구사항 (2026-11-06)", 1)
text = text.replace("| A/B 추론 | 11/05 사용자 병렬 요청이 기존 운영 FIFO 정책을 대체. 기본 parallel 독립 슬롯2개·공유 가중치·CUDA 스트림2개로 준비/카운트다운/추론을 함께 진행. serial은 명시적 비교/복구 모드 |",
    "| 단일 추론 | 11/06 요청으로 내일11/07은 단일 운영. 내부 A만 유지하고 일반 화면 A/B 선택·구역명을 없앤다. 기본 single 작업1개/CUDA stream1개와 협력적 작업시간 예산0.30. 과거 병렬/직렬은 명시적 복구용 |")
text = text.replace("- 새 방은 remote·lane A/B를 명시한다.", "- 현재 단일 운영은 remote·내부 A를 사용하며 새 방 요청의 lane 생략도 A로 처리한다. B 생성·참가를 차단한다. 명시적 dual 복구에서만 A/B를 선택한다.", 1)
start = text.index("- PC의 `Start-Alpha-Remote.cmd`")
end = text.index("\n- 서버는 engine heartbeat", start)
text = text[:start] + "- PC의 `Start-Alpha-Remote.cmd` 기본은 single·GPU 협력적 시간 예산0.30·CPU intraop4/interop1·자체 BelowNormal이다. 모델 세 벌을 한 번 로드하고 한 worker/한 CUDA stream으로 내부 A 한 방을 지속 처리한다. 코드는 숨김 입력에8자리만 넣으며 `A CODE8`도 호환한다. B 초기 인자/stdin은 모델 로드/HTTP 전에, 대화형 B는 예열 뒤 참가 HTTP 전에 거부한다. 같은 방의 다음 참가자는 모델/코드를 다시 입력하지 않는다. SharedModels 직접 API의 parallel/1.0 기본값은 기존 테스트·라이브러리 호환용이며 운영 CLI는 single/0.30을 명시 전달한다. 메모리/토큰·코드는 파일/로그에 남기지 않는다." + text[end:]
old = "A/B는 같은 PC에서 기본 parallel의 독립 슬롯2개로 준비·카운트다운·추론을 함께 진행한다."
text = text.replace(old, "11/05 병렬 운영 이력: 당시 A/B는 같은 PC에서 parallel의 독립 슬롯2개로 준비·카운트다운·추론을 함께 진행했다. 11/06부터 기본은 단일 A이며 다음 설명의 두 레인 측정은 이력이다.", 1)
text = text.replace("현재 기본값을 parallel로 변경했다", "11/05 기본값을 parallel로 변경했으며 11/06 단일 운영이 이를 대체했다", 1)
intro = """## 단일 운영과 협력적 GPU 시간 예산 (2026-11-06)

사용자는 내일11/07 부스에서 A 하나만 운영하고 CTF/Codex 작업과 PC를 함께 사용하므로 A/B 분할을 없애고 GPU 자원30%를 요청했다. 이 요청이11/05 기본 병렬 정책을 대체한다. 웹 기본/운영 환경 `ARENA_OPERATION_MODE=single`은 내부 A를 유지하되 화면 A/B 선택·구역명을 제거하고 B 생성/참가·이전 B 접근을 차단한다. 인간/AI 표시 주소는 기존 두 호스트의 기본 주소를 사용한다. 기존 A 방·코드와 정상 참가자 교체의 same-room next는 유지한다.

기본 실행기는 `--inference-mode single --gpu-duty-cycle 0.30 --cpu-threads 4`다. GPU 작업1개/stream1개에 모델 weights 한 세트를 공유하고 CPU intraop4/interop1·해당 프로세스 BelowNormal을 적용한다. 이 Windows WDDM/RTX4070Laptop 환경에 하드웨어 SM30% 고정 분할을 적용한 것이 아니다. 모델 작업+동기화 구간마다 작업시간의2.333배를 쉬는 협력적 벽시계 예산이며 마지막 청크 뒤에도 대기한다. 순간 GPU 사용률·다른 앱을 합친 장치 사용률·VRAM 상한·CTF70% 예약은 보장하지 않는다. 전역 전력/클럭/드라이버와 다른 프로세스는 변경하지 않는다.

수치 보존을 위해 기존 모델 배치인 존재8+1·사람9·나무1×9를 유지하고 각 청크를 마친 뒤 자기 stream만 동기화/대기한다. 로컬 취소/heartbeat 검사로 중단하며 대기 중 추가 상태 HTTP를 발생시키지 않는다. 실제 추론/의도한 자원 대기·네트워크·250ms 선택 시간은 분리 기록한다. 원래 batching 대비 첫1장 분할 실험의 점수 차이와 최종 복구 검증은 STATUS에 보존한다. 학습/임계값·전처리/사진을 성능 목표에 맞춰 바꾸지 않는다.

`parallel` 복구에는 PC `--inference-mode parallel --gpu-duty-cycle 1`과 웹 `ARENA_OPERATION_MODE=dual`을 모두 명시한다. 낮은 duty cycle의 parallel은 합산30%로 오해하지 않도록 거부한다. 기존 `ARENA_SESSION_RESET_BEFORE_MS=1793862306432`를 보존하고 관리자 키·사진/과거 경기·모델을 삭제하지 않는다. 현재 배포/CPU·GPU 실측/가동·미완료의 정본은 STATUS다.

이번 작업 검토: 단일 저부하 운영 — 2026-11-06 전체 본문/이력을 다시 읽고 최신 A 단일 요구·협력적30%/하드웨어 제한 경계·CPU4·기존 배치 보존·B 차단/명시적 dual 복구를 대조했다. protocol3·세 역할 사진 준비/공통 출발·250ms/500ms·학교 미사용·40%/ONNX/Pi/legacy OS 미완료를 보존한다. 실제 검사/배포/측정·PC 가동 및 문서 전체 점검은 STATUS/CHANGELOG에 기록한다.

"""
anchor = text.index("## 운영 연결 전체 초기화")
text = text[:anchor] + intro + text[anchor:]
path.write_text(text, encoding="utf-8")

path, text = reviewed("README.md")
text = text.replace("[인간 A](https://human.marulee.dev/?lane=A&reset=1)·[봇 A](https://bot.marulee.dev/?lane=A&reset=1)·[인간 B](https://human.marulee.dev/?lane=B&reset=1)·[봇 B](https://bot.marulee.dev/?lane=B&reset=1)", "[인간 화면](https://human.marulee.dev/?reset=1)·[AI 표시 화면](https://bot.marulee.dev/?reset=1)", 1)
text = text.replace("인간 A/B에서 새 방을 만들고 새 코드를 같은 레인의 봇 표시 화면과 켜 둔 PC 콘솔에 한 번씩 연결합니다.", "인간 화면에서 새 방을 만들고 새 코드를 AI 표시 화면과 PC 콘솔에 한 번씩 연결합니다. PC에는8자리코드만 입력합니다.", 1)
text = text.replace("기본 parallel에서는 A/B 두 슬롯을 함께 사용하므로 다른 레인의 준비·카운트다운·추론 종료를 기다리지 않습니다.", "현재는 단일 worker/stream으로 한 대결만 운영합니다.", 1)
start = text.index("11/05 외부 컴퓨터 시험 준비:")
end = text.index("## 기존 PC 마우스 입력 (legacy)", start)
operation = """## 단일 부스 운영 (11/07)

사용자 최신 요청으로 **한 대결만 운영**합니다. 화면의 A/B 선택과 구역명은 제거했고 내부 호환 값 A만 사용합니다. B 연결은 차단합니다. 기존11/05 병렬 운영·측정은 이력으로 STATUS에 보존합니다.

| 역할 | 주소 |
|---|---|
| 참가자 | https://human.marulee.dev/ |
| AI 선택 표시 | https://bot.marulee.dev/ |

1. 모델 PC와 두 브라우저 화면을 켭니다. 다른 컴퓨터의 Chrome에도 접속할 수 있고 화면용 컴퓨터에는 Python/ML 설치가 필요 없습니다.
2. [Start-Alpha-Remote.cmd](Start-Alpha-Remote.cmd)를 한 번 실행합니다. 기본 단일·협력적 GPU 시간 예산30%·CPU4/interop1·자체 BelowNormal 설정으로 모델을 한 번 로드/예열합니다.
3. 인간 화면에서 방을 만들고8자리코드를 AI 표시 화면에 입력합니다. PC 콘솔에도 **8자리코드만** 숨겨 입력합니다. `A 코드`는 호환하지만 B는 연결하지 않습니다.
4. PC/AI 표시 준비 뒤 인간이 시작합니다. 인간·AI 표시의 사진9장 디코딩과 PC RGB 수신이 모두 끝나면 약2초 공통 출발합니다. 출발 후 고정 ML 판별1회와 선택 계획1회를 수행합니다. 서버는500ms 여유 뒤250ms 간격 선택/제출을 재생합니다.
5. 종료 뒤 인간 화면의 **다음 참가자 준비 → 대결 시작하기**로 같은 방을 계속 씁니다. AI 표시·PC의 코드는 다시 넣지 않습니다. 모델이0개로 예측해도 그대로 제출하고 자동 재추론/임의 오답을 넣지 않습니다.
6. 마감은 PC 콘솔 `quit`입니다. `stop`은 단일 작업을 중단하는 명령이며 이미 수락한 서버 계획을 취소하지 않습니다. 코드/토큰은 메모리에만 있으므로 엔진 재시작 후 새 최초 연결이 필요합니다.

### GPU30%의 의미

이 Windows PC는 SM 자원을30%로 고정 분할하지 않습니다. 모델 청크를 완료/동기화한 작업시간 `t` 뒤 `2.333×t`를 쉬어 **협력적 작업 시간 예산30%**를 적용합니다. 원래 배치(존재8+1·사람9·나무1×9)를 유지하고 마지막 대기도 포함합니다. 개별 작업 중 GPU 사용률은 높을 수 있으며 VRAM 상한이나 CTF70% 고정 예약이 아닙니다. 다른 앱/전력/클럭 설정은 바꾸지 않습니다.

실제 GPU 비교에서 네 유형을 각3회 실행해 기존과 선택·점수가 같았고 OOM은 없었습니다. PyTorch 예약 메모리 최고치는1154MiB, 관측 작업시간 비율 최대29.9991%였습니다. 예산을 적용한 저장 RGB 한 문제의 중앙값은 건물0.233초·연못0.236초·사람1.093초·나무4.719초였습니다. 이는 고정 사진9장의 검사이며 현장 정확도·다른 앱 동시 운용 속도를 보장하지 않습니다. 상세/첫 실험 실패·커널 추적은 [STATUS](docs/STATUS.md)가 정본입니다.

각 방의 protocol3·세 역할 사진 준비·같은 출발선과250ms 선택 간격은 유지합니다. 자원 확보를 위한 휴식과 통신 지연을 구분합니다. 실제 CTF 부하와 함께 돌리는 현장 리허설은 남아 있습니다. 기존 OS 좌표 보정은 현재 원격 운영에 필요하지 않습니다.

"""
text = text[:start] + operation + text[end:]
text = text.replace("scripts/check_docs.py --date 2026-11-05", "scripts/check_docs.py --date 2026-11-06", 1)
text += "\n이번 작업 검토: 단일 저부하 운영 — 2026-11-06 전체 본문/이력을 재독하고 두 역할 주소·8자리코드 입력·단일worker/stream·협력적30%·원래 배치/고정 모델·CPU4와 실제 CUDA 출력/시간/메모리 검사를 반영했다. B와 기본 병렬은 현재 운영에서 제외하며 과거 이력은 보존한다. 새 게시/공개 경기/PC 가동 및 전체 문서 점검은 STATUS/CHANGELOG를 따른다.\n"
path.write_text(text, encoding="utf-8")

path, text = reviewed("docs/README.md")
start = text.index("이번 최신 작업은")
end = text.index("프로젝트가 직접 관리하는 Markdown", start)
text = text[:start] + """이번 최신 작업은11/07 A 하나의 부스 운영을 위한 **단일 대결과 협력적 GPU 작업시간 예산30%**입니다. 웹 A/B 선택·구역명 제거/B 차단, PC 한 worker/stream·CPU4/interop1/BelowNormal·8자리코드만 입력을 반영합니다. 고정 SM/순간 GPU/VRAM30% 제한과 구분하고 기존 배치·가중치/임계값·사진/학교 정책과250ms/500ms/프로토콜3을 유지합니다. 초기화 생성시각 경계도 보존합니다.

이번 작업 검토: 단일 저부하 운영 — 2026-11-06 아래13개 전체 본문/이력과 색인을 분담 재독하고 현재 단일 운영·실제 작업/대기·CPU/GPU/VRAM 측정의 구분을 대조했습니다. 새 Markdown은 없습니다. 실제 CUDA/공개 연결·게시·가동과 미완료/문서 검사 결과는 STATUS/CHANGELOG가 정본입니다.

""" + text[end:]
text = text.replace("컴퓨터 브라우저 운영·A/B 최초 연결", "단일 브라우저 운영·최초 연결/저부하 실행", 1)
text = text.replace("scripts/check_docs.py --date 2026-11-05", "scripts/check_docs.py --date 2026-11-06", 1)
text = text.replace("현재 작업은 사용자 병렬 요청에 따른 A/B 독립 슬롯2개·CUDA2스트림 운영 적용이다.", "현재 작업은 단일 A·한 worker/stream·협력적30% 작업시간 예산과 CPU4로 부스/CTF 병행 여유를 만드는 것이다. 과거 병렬 실험은 이력이다.", 1)
text = text.replace("엔진은 한 개에 A/B를 함께 연결한다.", "이 문단은11/05 당시 A/B 운영 이력이며 현재는 한 엔진에 한 코드만 연결한다.", 1)
path.write_text(text, encoding="utf-8")
print("Reviewed policy/README/index updated for 2026-11-06")
