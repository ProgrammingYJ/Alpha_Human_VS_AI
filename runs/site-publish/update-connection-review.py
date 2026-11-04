"""Document a read-only protocol/capacity explanation; no runtime changes."""
from pathlib import Path

root = Path(__file__).resolve().parents[2]
reviews = {
    "AGENTS.md": "통신/TCP와 두 세션 문의에 맞춰 전체 본문을 재검토했다. 현재 원격은 Cloudflare HTTPS API/폴링이며 Python urllib 응답 HTTP/1.1을 읽기 전용으로 확인했다. 브라우저 실제 협상 버전은 미측정이다. 모델1회 공유·GPU추론 직렬·A/B독립 및 기존 공개 동시실행 근거를 확인했으며 장시간/모든 조합 성능을 보장하지 않는다. 새 코드·배포·ML성능측정·운영 프로세스 조작0, 학교/모델/40%/Pi 경계는 유지한다.",
    "README.md": "통신 방식과 PC 두 세션 문의에 맞춰 본문을 다시 읽고 HTTPS API/폴링·단일 모델 공유/GPU차례처리·A/B독립을 확인했다. 기존 공개 A/B 검증은 실행 가능성의 근거이며 새 부하/장시간 성능 측정은 아니다. 현재 Python HTTPS 응답은 HTTP/1.1이고 브라우저 HTTP버전은 미측정이다. 이번은 문서/읽기전용 확인만으로 실행기·사이트·학교·모델·40%·Pi 상태를 바꾸지 않았다.",
    "docs/README.md": "통신과 두 세션 문의에 맞춰 관리13개 색인·본문을 다시 대조했다. 구조 설명은 ARCHITECTURE/INTEGRATION, 단일 실행기 A/B 운영은 SETUP, 실제 HTTP/1.1 조회와 과거 동시 실행 수치/한계는 STATUS에 기록했다. 새 Markdown·코드·배포·ML성능측정은 없고 기존 학교/평가/실기기 미완료 경계를 유지한다."
}
for name, review in reviews.items():
    path = root / name
    text = path.read_text(encoding="utf-8")
    if "\n이번 작업 검토:" in text:
        head, tail = text.rsplit("\n이번 작업 검토:", 1)
        text = head + "\n이전 작업 검토(컴퓨터 운영·생존 수정):" + tail
    text = text.rstrip() + "\n\n이번 작업 검토: " + review + "\n"
    path.write_text(text, encoding="utf-8")

path = root / "README.md"
text = path.read_text(encoding="utf-8")
anchor = "현재 모델은 각 라운드마다 예측을 한 번 하고 그 선택만 제출합니다."
addition = "통신은 각 브라우저·모델 PC가 Cloudflare 서버에 보내는 **HTTPS API 요청과 폴링**입니다. PC끼리 전용 TCP 소켓을 직접 연결하는 구조는 아닙니다. 현재 Python 봇과 같은 urllib 경로의 읽기 전용 요청에서 HTTP/1.1(TLS/TCP)을 확인했고 브라우저의 실제 HTTP버전은 미측정입니다. 모델은 실행기 하나에 한 번 올려 공유하며 A/B는 독립적으로 진행하고 GPU 추론만 차례로 처리합니다. 따라서 실행기를 두 개 켜지 말고 한 콘솔에 A와 B를 연결합니다. 기존 공개 두 세션 검사는 통과했으나 겹친 추론의 대기와 행사 장시간 운용은 구분합니다.\n\n"
assert anchor in text
path.write_text(text.replace(anchor, addition + anchor, 1), encoding="utf-8")

path = root / "docs/STATUS.md"
text = path.read_text(encoding="utf-8")
anchor = "## 현재 결론 (2026-10-27, 버전8)"
entry = """## 이번 확인: HTTPS 통신과 두 세션 용량 문의 (2026-10-27)

- 이번은 설명·문서 갱신과 읽기 전용 HTTPS 확인이다. 사이트/코드/모델/추론/배포·운영 프로세스 조작은0이며 아래 버전8 검사 수치를 새 측정이라고 쓰지 않는다.
- 실제 구조는 브라우저 및 PC 엔진→Cloudflare Worker의 HTTPS API와 상태 폴링이다. PC끼리 raw TCP 소켓으로 직접 연결하거나 WebSocket을 상시 여는 코드는 없다. 웹 폴링 기본500ms·엔진 heartbeat3초·유효15초는 유지된다.
- 같은 프로젝트 Python의 urllib로 `https://bot.marulee.dev/?lane=A`를 읽기 전용 조회해 HTTPS200·response.version=11(HTTP/1.1)을 확인했다. Python 경로는 TLS/TCP다. 브라우저의 실제 HTTP버전·도메인의 HTTP/3 협상은 측정하지 않았다. Cloudflare가 HTTP/3/QUIC을 지원한다는 사실만으로 이 사이트의 모든 브라우저가 HTTP/3이라고 단정하지 않는다. [공식 HTTP/3 안내](https://developers.cloudflare.com/speed/optimization/protocol/http3/).
- 같은 엔진은 모델3개를 한 번 로드해 공유하고 A/B 작업을 독립 관리한다. GPU 추론만 단일 잠금으로 직렬화해 모델을 방마다 중복 적재하지 않는다. 다운로드·선택/제출·생존 알림은 방별로 진행한다. 실행기는 하나만 켜고 A/B를 그 콘솔에 연결한다.
- 기존 공개 버전8의 동시 A1/B1 결과가 현재 PC의 두 세션 실행 근거다. A1 GPU대기0.391초/순수추론1.547초, B1 대기2.250초/추론0.844초였다. 시작~제출은12.156/15.977초로 네트워크·타일 대기를 포함한다. 겹친 추론은 기다릴 수 있으며 모든 유형 조합·현장 장시간 부하/온도·네트워크 성능 보장은 미완료다.

이번 작업 검토: 관리13개를 분담 재독·갱신하고 HTTPS/폴링과 TCP 계층을 구분했다. Python 응답 버전만 새로 확인했으며 기존 모델 공유·동시 실행 기록으로 용량 질문을 설명했다. 학교/가중치/임계값·40%·Pi/ONNX·기존 OS 입력 상태는 그대로다. 문서 점검은 이번 갱신 후 실제 명령 결과로 기록한다.

"""
assert anchor in text
path.write_text(text.replace(anchor, entry + anchor, 1), encoding="utf-8")

path = root / "docs/CHANGELOG.md"
text = path.read_text(encoding="utf-8")
anchor = "## 2026-10-27 컴퓨터 화면 운영·초기 생존 상태 수정·버전8"
names = ["AGENTS.md", "README.md", "docs/README.md", "docs/SETUP.md", "docs/ARCHITECTURE.md", "docs/DATASET.md", "docs/DATASET_CANDIDATES.md", "docs/EXECUTION_PLAN.md", "docs/INTEGRATION.md", "docs/ROADMAP.md", "docs/STATUS.md", "docs/CHANGELOG.md", "web/alpha-arena/README.md"]
entry = """## 2026-10-27 통신 계층·A/B 두 세션 설명 확인

- 사용자의 TCP/두 세션 용량 문의에 코드와 기존 보고서를 읽어 답했다. 원격은 Cloudflare HTTPS API/폴링이며 PC간 raw TCP 직결·전용 WebSocket이 아니다. 같은 urllib 경로의 공개 읽기 전용 GET에서 HTTPS200/HTTP1.1을 확인했고 브라우저 HTTP2/3 협상은 미측정으로 남겼다.
- 모델1회 로드 공유·단일 GPU 추론 잠금·독립 A/B를 재확인했다. 과거 버전8 A1/B1의 대기0.391/2.250초·추론1.547/0.844초와 동시 실행 검증을 근거로 삼되 새 성능 측정/장시간 보장으로 쓰지 않았다. 운영 실행기 하나에 A/B를 연결하도록 설명했다.
- 이번 변경은 관리 문서뿐이며 코드·배포·ML추론/성능측정·학교/모델/임계값·운영 프로세스 조작0이다. 버전8을 유지한다. 현장 컴퓨터/네트워크·장시간/유형별 동시 부하·40%·학교 최종 평가·Pi/ONNX·OS 입력 미완료는 유지한다.
- 관리13개 전체를 분담 재독·갱신했다. 최종 문서 점검 결과는 실제 실행 후 반영한다.

### 이번에 읽고 갱신한 전체 Markdown (13개)

""" + "\n".join("- " + name for name in names) + """

이번 작업 검토: 설명 요청에 맞춰 통신·공유 모델·두 세션 실행 근거와 한계를 갱신했다. 새 HTTP 응답 확인과 과거 GPU 측정을 구분하고 관리13개 전체 검토와 문서 점검 의무를 유지한다.

"""
assert anchor in text
path.write_text(text.replace(anchor, entry + anchor, 1), encoding="utf-8")
print("Updated root-owned review records and protocol/capacity explanation.")
