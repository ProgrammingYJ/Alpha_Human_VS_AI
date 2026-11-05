"""Reconcile current operator policy after reading the managed documents."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def update(name, replacements):
    path = ROOT / name
    text = path.read_text(encoding="utf-8")
    for old, new in replacements:
        if old not in text:
            raise RuntimeError(f"Missing reviewed passage in {name}")
        text = text.replace(old, new, 1)
    path.write_text(text, encoding="utf-8")

update("AGENTS.md", [
    ("## 최신 확정 요구사항 (2026-11-02)", "## 최신 확정 요구사항 (2026-11-05)"),
    ("| 운영 화면 |", "| A/B 추론 | 11/05 사용자 병렬 요청이 기존 운영 FIFO 정책을 대체. 기본 parallel 독립 슬롯2개·공유 가중치·CUDA 스트림2개로 준비/카운트다운/추론을 함께 진행. serial은 명시적 비교/복구 모드 |\n| 운영 화면 |"),
    ("queued 관측 등록순 FIFO로 예약을 받고 begin·사진 준비·카운트다운·공개 RGB 추론까지 보유한 뒤 선택 전에 해제한다. 단일 실행기의 등록순이며 서버 전역 순서/동일 네트워크 지연 보장은 아니다.",
     "기본 parallel의 독립 슬롯2개로 A/B 각각 begin·사진 준비·카운트다운·공개 RGB 추론을 진행하고 선택 전에 슬롯을 반환한다. 모델 가중치는 한 번만 올리며 worker별 processor/진단 상태와 CUDA 스트림을 분리하고 해당 스트림만 동기화한다. --inference-mode serial을 명시할 때만 기존 FIFO다. GPU50% 고정 할당이나 동일 네트워크 지연 보장은 아니다."),
    ("A/B는 같은 PC에서 경기를 겹쳐 운영할 수 있지만 GPU 예약은 한 실행기의 FIFO로 처리한다. 모델을 방마다 중복 로드하지 않고 공유하며 A의 실제 추론이 끝나면 선택 계획 전송 전에 GPU를 해제해 A 참가자가 계속 푸는 동안 B가 시작/추론할 수 있다.",
     "A/B는 같은 PC에서 기본 parallel의 독립 슬롯2개로 준비·카운트다운·추론을 함께 진행한다. B는 A의 사진 준비나 추론 종료를 기다리는 전역 FIFO에 서지 않는다. 가중치는 공유하고 worker별 입력/processor/진단 상태·CUDA 스트림을 분리한다. 실제 GPU 겹침·출력·속도·메모리와 가동 정본은 STATUS를 따른다."),
    ("동시 추론 후보 검증(2026-11-02): 운영 FIFO는 유지한다.",
     "동시 추론 후보 검증 이력(2026-11-02): 당시에는 운영 FIFO를 유지했으나 11/05 사용자의 명시적 병렬 요청으로 현재 기본값을 parallel로 변경했다."),
    ("현재 가동 정본은 runs/server-readiness-20261105/operator-start.json과 STATUS다.",
     "이 기동은 11/05 병렬 수정 전의 FIFO 이력이며 당시 기록은 runs/server-readiness-20261105/operator-start.json이다. 새 병렬 검증/가동 정본은 STATUS와 runs/parallel-operating-20261105/다."),
    ("이번 작업 검토: 2026-11-05 전체 본문을 다시 읽고 정규 운영 엔진 기동", "이전 작업 검토(11/05 서버 기동): 2026-11-05 전체 본문을 다시 읽고 정규 운영 엔진 기동"),
])
with (ROOT / "AGENTS.md").open("a", encoding="utf-8") as file:
    file.write("\n이번 작업 검토(병렬 운영): 2026-11-05 전체 본문을 재독하고 사용자 실험에서 확인된 FIFO와 병렬 요구의 차이를 수정했다. 운영 기본값을 parallel2슬롯·공유 가중치/독립 CUDA2스트림으로 바꾸고 serial을 명시적 비교/복구 모드로 남긴다. 사진 준비/출발·250ms·고정 모델/학교 정책은 유지한다. CPU·실제 CUDA/공개 HTTP 검증, 운영 재시작 및 남은 현장 시험은 STATUS/CHANGELOG가 정본이다. 관리13개 전체를 분담 재독·갱신하고 실제 문서 점검을 실행한다.\n")

update("README.md", [
    ("인간 시작 요청 뒤 GPU 차례를 기다린 다음 사진9장을 미리 준비합니다.", "인간 시작 요청 뒤 해당 레인의 독립 추론 슬롯을 확보하고 사진9장을 미리 준비합니다. 기본 parallel에서는 A/B 두 슬롯을 함께 사용하므로 다른 레인의 준비·카운트다운·추론 종료를 기다리지 않습니다."),
    ("**운영은 기존 FIFO를 유지하며 동시 추론은 아직 적용하지 않았습니다.**", "이 수치는 11/02 후보 실험 이력입니다. **11/05 사용자 요청으로 현재 운영 기본값을 parallel로 바꾸고 A/B 독립 슬롯2개와 CUDA 스트림2개를 적용했습니다.** 새 검증 결과는 STATUS가 정본입니다."),
    ("모델은 실행기 하나에 한 번 올려 공유하며 A/B는 독립적으로 진행하고 GPU 추론만 차례로 처리합니다.", "모델은 실행기 하나에 한 번 올려 공유하며 기본 parallel에서는 A/B가 서로 다른 CUDA 스트림으로 추론합니다. 작업별 processor·입력·진단 상태는 분리합니다."),
    ("**A 참가자가 푸는 동안 B도 경기를 진행할 수 있습니다.** A의 모델 추론이 끝나면 GPU를 해제해 A의 선택 표시·인간 풀이와 B의 준비/추론을 겹칩니다. 두 레인이 시작을 동시에 요청하면 B는 경기 시작 전에 기다릴 수 있고 A/B의 절대 출발 시각은 달라집니다.",
     "**A/B는 사진 준비·카운트다운·GPU 추론을 함께 진행할 수 있습니다.** 기존 한 개 GPU 잠금을 제거하고 두 개의 독립 슬롯과 CUDA 스트림을 사용합니다. 공유 GPU 자원을 사용하므로 고정50% 할당이나 모든 조합의 속도 개선을 뜻하지 않습니다. 네트워크/각 레인의 사진 준비에 따라 A/B의 절대 출발 시각은 달라질 수 있습니다."),
    ("공개 검사에서 B의 예약 전 대기는10.438초였고", "이전 FIFO 공개 검사에서 B의 예약 전 대기는10.438초였고"),
    ("한 실행기의 FIFO 예약 대기를 경기 타이머 전에 처리하고, 이미 분석한 방의250ms 서버 선택 계획과 다음 방의 준비/추론을 겹칠 수 있습니다.",
     "기본 parallel은 A/B 각각 독립 슬롯을 사용해 준비·추론을 함께 처리하고, 이후 서버250ms 선택 계획도 독립적으로 재생합니다. 기존 FIFO는 실행기에 --inference-mode serial을 명시한 비교/복구 모드에서만 사용합니다."),
    ("이번 작업 검토: 2026-11-05 전체 본문을 재검토하고 공개 사이트 HTTP 확인", "이전 작업 검토(11/05 서버 기동): 2026-11-05 전체 본문을 재검토하고 공개 사이트 HTTP 확인"),
])
with (ROOT / "README.md").open("a", encoding="utf-8") as file:
    file.write("\n이번 작업 검토(병렬 운영): 2026-11-05 전체 본문을 재독하고 기본 parallel2슬롯/2CUDA스트림·가중치 한 번 공유·작업 상태 분리·명시적 serial 복구를 반영했다. 업데이트 재시작 후 새 A/B 방을 한 번 연결하며 이후 참가자 교체는 같은 방이다. 모델/임계값·250ms·학교/40%/ONNX/Pi 상태는 유지한다. 실제 GPU 겹침/출력/속도·공개 두 방 검사·새 가동과 문서 점검은 STATUS/CHANGELOG를 따른다.\n")

update("docs/README.md", [
    ("현재 재개 작업은 사진 사전 디코딩/3역할 준비 후 출발과 통신/시계/프로토콜 복구다.", "현재 작업은 사용자 병렬 요청에 따른 A/B 독립 슬롯2개·CUDA2스트림 운영 적용이다. 사진 사전 디코딩/3역할 준비 후 출발과 공통 시계·프로토콜3은 유지한다."),
    ("이번 작업 검토: 2026-11-05 색인과 전체 본문을 다시 대조하고 공개 사이트", "이전 작업 검토(11/05 서버 기동): 2026-11-05 색인과 전체 본문을 다시 대조하고 공개 사이트"),
])
with (ROOT / "docs/README.md").open("a", encoding="utf-8") as file:
    file.write("\n이번 작업 검토(병렬 운영): 2026-11-05 색인과 전체 본문을 재독하고 관리13개에 기본 parallel/명시적 serial·CPU/CUDA/공개 HTTP의 구분을 반영했다. 새 Markdown은 없다. 실제 가동·검증·미완료는 STATUS, 기술은 ARCHITECTURE/INTEGRATION, 재연결은 SETUP, 전체 검토 목록/점검 결과는 CHANGELOG가 정본이다.\n")
