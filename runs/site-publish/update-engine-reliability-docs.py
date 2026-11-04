from pathlib import Path
import re

root = Path(__file__).resolve().parents[2]
common = """## 사진 준비 후 공통 출발과 PC 지연 수정 (2026-11-01)

현재 remote 출발 순서는 **인간 시작 요청 → GPU 예약 대기 → loading에서 인간 화면·AI 표시 화면·PC의 사진9장 준비 → 세 역할의 준비 확인 → 약2초 공통 카운트다운 → 실제 문제 판별**이다. loading의 질문·시작 시각은 비공개이고 타이머는0이다. 브라우저는 숨긴 동일9개 이미지 노드를 실제로 디코딩하고 PC는9개 RGB를 최대3개 병렬로 받아 준비한다. 사진 URL은 loading부터 불투명 라운드 경로로 사용할 수 있지만 정답·원본 파일명·실제 정답 수는 제공하지 않는다. 시작 때 같은 브라우저 이미지와 PC의 같은 RGB 캐시를 재사용하고 실제 문제의 ML 판별은 playing 뒤에만 수행한다. 이전의 begin 즉시2초 출발·출발 후 사진 다운로드 설명은 아래에 남은 당시 이력이다.

`imageLoad`의 공통 준비 번호와 humanReady/botReady/engineReady를 사용한다. PC의 `images_ready`는 roundId·roundNumber·requestId·imageLoadId에 묶인다. 시작 전 페이지를 새로 열거나 새로고침하면 준비 번호와 세 플래그를 다시 확인하며, 이미 디코딩한 동일 라운드/동일 순서의 RGB는 재사용한다. 준비 번호가 달라진 옛 ACK나 다음 판 사진에는 캐시를 전용하지 않는다. 준비 ACK가 유실되고 재전송 때 이미 출발한 경우는 새 서버 조회에서 같은 라운드·요청·준비 번호와 세 플래그의 완료를 증명한 때만 복구한다. 경기 시작 뒤의 새로고침은 이미 시작한 타이머를 되돌리지 않으므로 참가자 교체에는 새로고침 대신 같은 방의 다음 참가자 준비를 사용한다.

사진 준비60초·GPU 대기120초·경기90초는 운영 가안이다. 준비 실패·취소·만료는 대기실로 복귀하고 인간이 다시 시작한다. 기존15초 엔진 생존 검사는 유지한다. 단순 viewer 참가나 모델 로드만으로 사진 로딩 완료를 표시하지 않는다. 새 서버에는 protocol3가 필요하고 과거 v11처럼 사진 준비 지원 필드가 없는 서버만 protocol2로 협상한다. 새 서버가 지원false를 알리는 경우는 준비 전 상태이므로 배리어를 우회하지 않는다. 대기실에서 새 서버 배포를 관측하면 같은 엔진 토큰으로 다음 생존 알림을3으로 올리며 이미 진행 중인 구형 판은 기존 계약으로 끝낸다.

PC는 방 연결을 허용하기 전에 합성 회색 RGB9장으로 존재·사람·나무 세 고정 모델을 예열한다. 실제 문제·학교 사진·정답은 예열에 사용하지 않고 startup에 모델 로드/예열/전체 시간을 나눠 기록한다. 건물·연못에는 기존 존재 모델만, 사람 문제에는 기존 사람 검출 모델만 실행해 질문과 무관한 연산을 생략한다. 가중치·전처리·임계값·NMS·계수·타일 선택 규칙은 유지하며 미실행 항목은 None으로 남긴다. 전체 예측 API는 보존하고 같은 공개 RGB9장에서 전체 실행과 대상별 점수/계수·선택 동등성을 별도 검사한다.

Python 기본 통신은 origin에 묶인 표준 http.client의 HTTP/1.1 연결을 호출 스레드별로 재사용한다. 리다이렉트·관리 API·외부 호스트는 허용하지 않으며 엔진 토큰은 방 API에만 전달한다. 읽기 GET은 일시 연결 오류에 한 번만 재시도한다. begin·사진 준비·불변 plan·개별 sequence는 기존 멱등 본문을 그대로 제한 재전송하며 일반 POST를 무조건 재전송하지 않는다. 새 배리어+plan 경로의 추론/선택 stage 표시는 주기 heartbeat로 전송해 경기 안의 동기 왕복을 줄인다. GPU 예약/사진 준비의 서버 확인과 모델 직전 상태 확인, 서버의 계획/승패 검증은 유지한다. 사진3개 worker와 연결은 종료 시 정리한다.

검증 스크립트 `scripts/verify_continuous_booth.py`는 실제 PC 모델을 한 번 로드해 A두판+B한판을 진행하고, 인간/봇 역할도 각각9개 공개 RGB를 실제 다운로드·PIL 디코딩한 뒤 준비를 알린다. A첫판 인간 준비를3초 보류해 PC/봇 준비 뒤에도 타이머0·사전 추론0인지 검사한다. 이 보류는 시험 조건이며 운영 지연 설정이 아니다. HTTP/PIL 시험은 실제 브라우저 렌더링 시험과 별개다. 같은 RGB의 출력 동등성과 준비/모델/HTTP 시간, 경기 중 사진 다운로드0을 기록하며 독립 정확도·목표40% 달성이나 지연0을 주장하지 않는다. 실제 게시/실측·현장 기기/네트워크의 미확인 범위는 STATUS가 정본이다.

"""

for name in ('SETUP', 'ARCHITECTURE', 'INTEGRATION'):
    path = root / 'docs' / (name + '.md')
    text = path.read_text(encoding='utf-8-sig')
    text = re.sub(r'최종 검토: \d{4}-\d{2}-\d{2}', '최종 검토: 2026-11-01', text, count=1)
    text = text.replace('최신 운영 정책(2026-10-27)', '선택 간격 정책(2026-10-27, 현재 유지)')
    text = text.replace('이번 작업 검토:', '이전 작업 검토(선택 계획):')
    # New, complete protocol description precedes the retained implementation history.
    marker = text.find('\n## ')
    text = text[:marker] + '\n' + common + text[marker:]
    text += ('\n이번 작업 검토: 2026-11-01에 전체 본문을 다시 읽고 사진3역할 준비·프로토콜2/3 협상/배포 중 업그레이드·동일 RGB 재사용·출발 전 문제 추론 금지·ACK 유실 복구를 반영했다. '
             '스레드별 HTTP 연결 재사용/제한 재시도·경기 안 동기 stage 왕복 축소·세 모델 합성 예열·질문별 불필요 모델 실행 생략과 출력 동등성 검증을 대조했다. '
             '실제 검사/게시/PC 가동 정본은 STATUS이며 이전 수치/정책은 이력으로 보존한다. 학교 사진 미사용·고정 모델/임계값·임의 오답0·40%/ONNX/Pi/legacy OS 입력 및 현장 리허설의 미완료 경계를 유지한다.\n')
    # All current reproduction commands should validate this review date.
    text = text.replace('scripts/check_docs.py --date 2026-10-27', 'scripts/check_docs.py --date 2026-11-01')
    path.write_text(text, encoding='utf-8')

path = root / 'docs/SETUP.md'
text = path.read_text(encoding='utf-8')
text = text.replace('PC는 공개 후9사진을 **최대3개 병렬 다운로드**하고', 'PC는 loading에서9사진을 **최대3개 병렬 다운로드**하고')
text = text.replace('GPU 예약을 확보한 뒤 인간/AI가 공통 출발하고 추론 함수가 반환하면 먼저 GPU를 해제한다.', 'GPU 예약 뒤 세 역할의9사진 준비를 확인하고 인간/AI가 공통 출발한다. 캐시 RGB의 추론 함수가 반환하면 먼저 GPU를 해제한다.')
text = text.replace('PC가 자원을 확보한 뒤 서버가 **2초 뒤 공통 startAt**을 양쪽에 동일하게 제공합니다.', 'PC가 자원을 확보하면 세 역할의9사진 준비를 기다리고, 모두 완료한 뒤 서버가 **2초 뒤 공통 startAt**을 양쪽에 동일하게 제공합니다.')
text = text.replace('대기 중에는 질문·사진이 없고 타이머는0입니다.', 'GPU 대기에는 질문·사진이 없고 타이머는0이며, loading에는 사진만 숨겨 미리 받고 질문·타이머는 공개하지 않습니다.')
text = text.replace('시작 전 사진은 숨기며 대기실 만료·사진 비활성화 후 URL을 사용할 수 없습니다.', '시작 전 사진은 화면에서 숨기되 loading부터 준비용 바이트 요청을 허용하며 대기실 만료·사진 비활성화 후 URL을 사용할 수 없습니다.')
text = text.replace('프로토콜2도 필수다', '새 출발에는 프로토콜3도 필수다')
text = text.replace('protocolVersion:2', 'protocolVersion:3')
text = text.replace('`protocolVersion:2`', '`protocolVersion:3`')
text = text.replace('GPU 대기 동안 타이머0으로 기다리고 자원 차례에 약2초 공통 카운트다운 뒤 시작합니다.', 'GPU 대기와 세 역할의 사진9장 준비 동안 타이머0으로 기다리고 모두 준비되면 약2초 공통 카운트다운 뒤 시작합니다. 인간/AI 두 화면을 앞에 두어 숨겨진 탭 때문에 준비가 보류되지 않는지 확인합니다.')
text = text.replace('존재·사람·나무 모델3개 로드가 끝나 콘솔의', '존재·사람·나무 모델3개 로드와 합성 RGB 예열이 끝나 콘솔의')
text = text.replace('begin 후inferencing/selecting/submitted', 'begin 후loading_images/images_ready, 출발 후inferencing/selecting/submitted')
text = text.replace('Python의 urllib 경로는 HTTP/1.1을 TLS/TCP로 전송하며', '이전 urllib 읽기 검사에서는 HTTP/1.1을 확인했고 현재 PC는 표준 http.client의 HTTP/1.1 연결을 재사용하며')
path.write_text(text, encoding='utf-8')

path = root / 'docs/ARCHITECTURE.md'
text = path.read_text(encoding='utf-8')
text = text.replace('countdown에는 질문/타일도 숨기고 사진 endpoint도 시작 전 접근을 차단한다.', 'loading/countdown에는 화면의 질문/타일을 숨긴다. 준비용 preloadTiles는 loading부터, 공개 조건 preloadTopic은 countdown부터 제공하며 클라이언트가 같은 공통 startAt에 숨김을 해제한다. 사진 endpoint는 현재 라운드의 loading부터 디코딩을 허용한다.')
text = text.replace('새 GPU 시작에는 protocol2도 필수다.', '새 사진 준비 출발에는 protocol3도 필수다.')
text = text.replace('새 heartbeat는 protocolVersion2와', '새 heartbeat는 protocolVersion3와')
text = text.replace('begin 뒤 inferencing/selecting/submitted', 'begin 뒤 loading_images/images_ready·공통출발 뒤 inferencing/selecting/submitted')
text = text.replace('봇 viewer의 준비·선택·HTTP 제출은 금지되며', '봇 viewer는 사진 준비 ACK만 할 수 있고 엔진 준비·선택·HTTP 제출은 금지되며')
text = text.replace('Python의 urllib 경로는 HTTP/1.1을 TLS/TCP로 전송하며', '이전 urllib 읽기 검사는 HTTP/1.1이었고 현재 Python은 표준 http.client로 HTTP/1.1 연결을 재사용하며')
path.write_text(text, encoding='utf-8')

path = root / 'docs/INTEGRATION.md'
text = path.read_text(encoding='utf-8')
text = text.replace('PC begin→약2초 공통 카운트다운', 'PC begin→세 역할9사진 준비→약2초 공통 카운트다운')
text = text.replace('현재 queued만 취소하고 lobby·ready0.', '현재 queued/loading/출발 전 countdown을 취소하고 lobby·ready0.')
text = text.replace('| `GET /api/photos/:id` | 시작된 라운드의 불투명 타일 ID |', '| `POST /api/rooms/:id/images-ready` | 인간/봇 표시, `{roundId,requestId,imageLoadId,ready,failed?}` | 현재 라운드 준비 번호에만 등록/디코딩 ACK. 봇의 답안 선택 권한은 없음 |\n| `GET /api/photos/:id` | 현재 라운드의 loading 이후 불투명 타일 ID |')
text = text.replace('`lobby/queued/countdown/playing/result`', '`lobby/queued/loading/countdown/playing/result`')
text = text.replace('질문/사진은 공통 시작 이후에만 공개하고 정답·라벨·원본 경로는 숨긴다.', 'loading부터 준비용 preloadTiles, countdown부터 preloadTopic을 제공하되 화면에서는 공통 시작까지 숨긴다. 정답·라벨·원본 경로는 계속 숨긴다.')
text = text.replace('protocolVersion:2', 'protocolVersion:3')
text = text.replace('생존/준비/protocol2를 CAS해 round N+1과2초 뒤 startAt 생성.', '생존/준비/protocol3를 CAS해 round N+1의 loading을 생성. 세 역할의 사진 준비 뒤2초 공통 startAt 생성.')
text = text.replace('| `plan` |', '| `images_ready` | `{action:"images_ready",roundId,roundNumber,requestId,imageLoadId}` | PC의9RGB 디코딩 후 같은 라운드/요청/준비 번호만 ACK. 인간/봇 표시와 함께 세 플래그 완료 뒤 공통 출발 |\n| `plan` |', 1)
text = text.replace('Python urllib 요청은 HTTP/1.1을 TLS/TCP로 전송한다.', '이전 urllib 조회는 HTTP/1.1이었고 현재 PC는 표준 http.client로 HTTP/1.1 연결을 스레드별 재사용한다.')
path.write_text(text, encoding='utf-8')
print('Updated 3 owned documents after full text review; validation/deployment evidence remains in STATUS.')
