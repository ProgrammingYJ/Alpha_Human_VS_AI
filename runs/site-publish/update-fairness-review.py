"""Record fairness analysis only; the proposed start reservation is unimplemented."""
from pathlib import Path

root = Path(__file__).resolve().parents[2]
reviews = {
    "AGENTS.md": "공유 GPU 순차 처리의 공정성 문의에 전체 본문을 재검토했다. 현재 공통 시작 후 대기 때문에 방별 AI 응답 차이가 생길 수 있으며 두 세션 동작 검사를 공정성 보장과 구분했다. GPU 예약 대기 후 해당 인간/봇 공통 출발은 미구현 제안이고 코드·규칙·운영 프로세스·추가 측정 변경0이다. 기존 시간 지표의 상태조회 HTTP 포함 한계를 교정했으며 학교/모델/40%/Pi 경계는 유지한다.",
    "README.md": "전체 본문을 다시 읽고 경기 중 GPU 대기가 방별 인간/AI 대결 조건에 미치는 영향을 검토했다. 시작 요청을 GPU 예약 대기 뒤 공통 출발로 바꾸는 방안은 미구현이며 현재 직렬 추론과 규칙은 그대로다. 과거 대기/추론 수치는 상태 확인 왕복도 포함해 순수 GPU/ML 시간으로 해석하지 않는다. 코드·배포·추론·새 측정 없이 문서만 갱신하고 학교/모델/40%/실기기 경계를 유지한다.",
    "docs/README.md": "관리13개 색인과 본문을 공정성 문의에 맞춰 대조했다. 현재 경기 중 공유 GPU 대기와 시작 전 예약 제안을 구분하는 문서 위치를 확인했다. 제안은 미구현이고 새 Markdown·코드·규칙·배포·성능 측정은 없다. 시간 구간의 HTTP 포함 한계와 학교/모델/40%/Pi/현장 리허설 상태는 STATUS를 따른다."
}
for name, review in reviews.items():
    path = root / name
    text = path.read_text(encoding="utf-8")
    head, tail = text.rsplit("\n이번 작업 검토:", 1)
    text = head + "\n이전 작업 검토(통신·두 세션):" + tail
    path.write_text(text.rstrip() + "\n\n이번 작업 검토: " + review + "\n", encoding="utf-8")

path = root / "README.md"
text = path.read_text(encoding="utf-8")
anchor = "현재 모델은 각 라운드마다 예측을 한 번 하고 그 선택만 제출합니다."
note = "현재는 타이머가 시작된 뒤 GPU 차례를 기다리므로 겹친 추론이 한 방의 AI를 늦춰 그 방 참가자가 상대적으로 유리해질 수 있습니다. 두 세션 동작 검증이 동일 응답시간/공정성 검증은 아닙니다. **시작 요청→GPU 예약 대기→해당 인간/AI 공통 출발→추론 후 GPU 해제**로 자원 대기를 경기 전으로 옮기는 방안은 아직 미구현 제안입니다. 실제 코드·타이머 규칙은 그대로이며 GPU 대기를 사후 시간 보정하거나 문제 공개 전에 미리 추론하지 않습니다.\n\n"
assert anchor in text
path.write_text(text.replace(anchor, note + anchor, 1), encoding="utf-8")

path = root / "docs/STATUS.md"
text = path.read_text(encoding="utf-8")
text = text.replace("A1 GPU대기0.391초/순수추론1.547초, B1 대기2.250초/추론0.844초였다.", "A1의 기록된 대기 구간0.391초/추론 구간1.547초, B1 대기 구간2.250초/추론 구간0.844초였다. 두 지표는 잠금 안의 서버 상태 확인 HTTP도 포함하며 순수 GPU 대기/ML 계산 시간은 아니다.")
anchor = "## 이번 확인: HTTPS 통신과 두 세션 용량 문의 (2026-10-27)"
entry = """## 이번 검토: 공유 GPU 대기와 대결 공정성 (2026-10-27)

- 사용자의 지적은 현재 구조에서 타당하다. `run_one_room`은 playing과 공통 startAt 이후9사진을 받아 `SharedModels.infer`의 단일 잠금을 기다린다. 따라서 한 방 AI의 자원 대기가 그 방 타이머에 포함된다. 그 방 인간은 상대 AI가 늦어지는 이점을 받을 수 있다. A/B 동시 동작 통과를 동일 응답시간/공정성 보장으로 해석하지 않는다.
- 과거 공개v8 A1/B1의 gpu_queue_seconds는0.391/2.250초였다. 단, 타이머는 잠금 획득 후 active() HTTP까지 포함하고 inference_seconds도 predict 뒤 active() HTTP를 포함한다. 정확한 순수 잠금 대기/ML 계산을 분리 측정한 값은 아니며 이번에는 새 측정0이다. 이후 분리 측정이 필요하면 잠금 획득 직후·모델 반환 직후·상태 확인을 각각 기록해야 한다.
- 미구현 제안: 인간의 시작 요청→GPU 예약 대기 표시→차례가 오면 해당 방의 인간/AI에 공통 카운트다운/시작 시각 확정→공개 후 사진 추론→GPU 해제다. 기존 방의1초 간격 선택/제출과 다음 방의 준비/추론은 독립적으로 겹칠 수 있다. GPU 경합 대기를 타이머 전에 옮기는 방안이며 현장 전체 지연을 같게 보장하는 것은 아니다.
- 이 제안은 구현·배포·검증하지 않았다. 현재 버전8의 타이머/시작/API/잠금은 그대로다. 미리 답을 추론하거나 사후에 경기 시간을 고쳐 공정성을 주장하지 않는다. 학교·가중치·임계값·1초·40%·Pi 정책도 바꾸지 않는다.

읽기 전용 재현은 `SharedModels.infer`의 잠금/시간 기록과 `run_one_room`의 playing 이후 호출 순서를 대조한다. 과거 실행 근거는 runs/desktop-liveness-public-v1의 lane-A-game-1.json/lane-B-game-1.json이다. 이번 코드·새 추론/성능시험·배포·운영 프로세스 조작은0이다.

이번 작업 검토: 관리13개 전체를 분담 재독·갱신해 실행 가능성과 공정성 한계를 구분했다. 미구현 GPU 예약 출발과 현재 버전8 동작·과거 측정 구간의 HTTP 포함을 명확히 기록했다. 문서 최종 점검 결과는 실제 명령 실행 후 반영한다.

"""
assert anchor in text
path.write_text(text.replace(anchor, entry + anchor, 1), encoding="utf-8")

path = root / "docs/CHANGELOG.md"
text = path.read_text(encoding="utf-8")
text = text.replace("대기0.391/2.250초·추론1.547/0.844초와 동시 실행 검증", "대기 구간0.391/2.250초·추론 구간1.547/0.844초(상태 확인 HTTP 포함)와 동시 실행 검증")
anchor = "## 2026-10-27 통신 계층·A/B 두 세션 설명 확인"
names = ["AGENTS.md", "README.md", "docs/README.md", "docs/SETUP.md", "docs/ARCHITECTURE.md", "docs/DATASET.md", "docs/DATASET_CANDIDATES.md", "docs/EXECUTION_PLAN.md", "docs/INTEGRATION.md", "docs/ROADMAP.md", "docs/STATUS.md", "docs/CHANGELOG.md", "web/alpha-arena/README.md"]
entry = """## 2026-10-27 GPU 순차 대기의 공정성 검토

- 사용자 지적에 현재 공유 GPU 대기가 타이머 시작 후 발생하며 한쪽 AI 지연이 그 방 인간에게 유리할 수 있음을 확인했다. 기존 동시2세션 실행 성공은 동일 반응시간/공정성 검증이 아니다.
- 시작 요청을 GPU 예약 대기로 받은 뒤 자원 차례에 해당 인간/AI의 공통 출발을 확정하고 추론 후 GPU를 해제하는 방안을 미구현 제안으로 기록했다. 선택/제출은 기존처럼 방별 독립 진행이다. 사전 정답 추론·사후 시간 보정을 하지 않는다.
- 보고서 gpu_queue_seconds/inference_seconds의 active() 상태조회 HTTP 포함을 확인해 ‘순수 GPU 대기/순수 추론’이라는 이전 설명을 교정했다. 기존 측정값은 보존하고 새 순수 측정으로 바꾸지 않았다.
- 이번은 문서 검토만으로 코드·타이머 규칙·추론/성능시험·배포·운영 프로세스 조작0이다. 학교/모델/임계값·1초·40%·Pi/ONNX·현장 리허설 경계를 유지한다. 다음 구현은 별도 작업이며 아직 완료하지 않았다.
- 관리13개 전체를 분담 재독·갱신했다. 최종 문서 점검은 실제 명령 결과로 기록한다.

### 이번에 읽고 갱신한 전체 Markdown (13개)

""" + "\n".join("- " + name for name in names) + """

이번 작업 검토: GPU 경합의 참가자 조건 차이와 보고서 시간 구간을 재검토했다. 현재 구현·과거 측정·미구현 예약 출발 제안을 나눠 기록하고 관리13개 문서를 갱신했다.

"""
assert anchor in text
path.write_text(text.replace(anchor, entry + anchor, 1), encoding="utf-8")
print("Updated fairness analysis and clarified recorded timing boundaries; runtime unchanged.")
