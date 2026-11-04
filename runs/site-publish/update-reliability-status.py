"""Write current evidence above preserved historical status and changelog."""
import json
from pathlib import Path
import re

root = Path(__file__).resolve().parents[2]
release = json.loads((root/'runs/site-publish/reliability-release.json').read_text(encoding='utf-8'))
date = '2026-11-01'
body = f'''## 최신 작업: 사진 준비 후 공통 출발·통신/복구 수정·버전12 ({date})

11/01 재개 요청으로 지난 행사에서 제보된 사진 로딩/출발 차이, 서버·PC 버전 오류, 선택 지연과 A/B·같은 방 반복을 우선 수정했다. 다음 행사 목표는11/07(토)다. 재개 시 실제 공개 버전은11이고10/28 사진 준비 코드는 로컬 부분 구현 상태였음을 확인했다. 현재는 아래 버전12 게시가 완료됐으며 과거 v11 지표는 새 버전 측정으로 재사용하지 않는다.

### 현재 동작과 수정

- **시작 요청→GPU FIFO 예약→loading→인간 화면/AI 표시/PC의9장 준비→약2초 공통 출발→보관 RGB 추론→GPU 해제→선택 계획1회**다. loading은 startAt/deadlineAt/topic=null·tiles=[]·타이머0이며 불투명 preloadTiles만 전달한다. 브라우저는 숨긴 실제9img의decode/크기를 확인하고 PC는RGB9장을 미리 받는다. 실제 문제 추론은 공통 출발 후에만 수행하고 경기 중 재다운로드하지 않는다.
- 브라우저는 같은key/img/src를 출발 때 공개하고 준비한 질문을 시계로 표시한다. 출발 직후 추가GET을 기다리지 않는다. 페이지가 숨겨지면 출발 전 준비를 철회하고 보이는 페이지에서만 다시 준비한다. **인간·AI 표시를 각각 보이는 창/모니터에 둔다.** 같은 브라우저의 숨은 두 탭으로 동시 운영하지 않는다.
- 프로토콜3·round/request/imageLoadId로 준비/회차를 확인한다. 출발 전 재로드는 준비epoch/3역할을 초기화하고 이전ACK를 거부한다. PC는같은회차/같은사진순서만재사용한다. 취소·사진실패·준비60초/엔진15초 만료는 같은 방 lobby로 돌아가 수동 시작한다. 출발 후 재로드는 경기를 소급 정지하지 않는다. GPU대기120초·사진60초·경기90초는 운영 가안이다.
- v11에imageBarrierSupported필드가 아예 없을 때만 PC가protocol2를 협상한다. 새 서버는protocol3 준비를 우회한 출발을 거부한다. lobby중 배포가 바뀌면 같은PC권한으로3을 다시 알린다. 준비ACK의응답이유실되어이미playing이면 같은round/request/epoch·3ready와RGB캐시를새상태에서확인한경우만복구한다. 임의바이패스/재추론은없다.
- 마지막준비ACK와새heartbeat가겹쳐SQLrelease가거부된경우, 저장된3ready/loading을다음상태조회에서원자적으로재정산한다. 재정산은기존countdown시각을바꾸지않는다. 합성SQLite에서HB+1ms→옛시계release0→freshretry1을재현했다([독립경합검사](../runs/image-barrier-audit-20261101/heartbeat-release-race.json)).
- 화면시계는performance.now/최저RTT표본을사용하며확정카운트다운에서는기준을고정한다. 늦은응답이출발선을흔들던문제를줄였다. 요청은10초제한으로무한hang을해제하고정상회차409를끊김으로표시하지않는다. 사람의로컬선택은상태조회실패/제출왕복동안에도편집할수있다. 서버만채점/단일승자를확정한다.
- PC는스레드별HTTPS연결과최대3사진다운로드pool을재사용한다. 새barrier+plan경로의추론/선택stage동기heartbeat2개와중복guard1개를제거하되주기heartbeat와실제모델전검사/서버plan검사를유지했다. 읽기GET만유한재시도하고같은선택계획은기존멱등재시도를사용한다. 오류·경합의원자성/정답비공개조건을유지한다.
- PC는ready전에합성RGB로3모델을예열한다. 실제질문은건물/연못이면기존존재모델,사람이면기존검출모델,나무이면기존나무모델만실행한다. 미실행출력은None이고가중치·임계값·전처리/후처리는동일하다. 원래full예측API는보존한다. 합성예열과실제문제의사전추론을구분한다.
- 500ms표시여유/250ms서버선택일정·계획1회·단일승자·같은방next는유지한다. 네트워크/브라우저/모델지연이0이라는주장이나실제250ms렌더링보장은하지않는다.

### 실제 자체 검사

| 검사 | 실제 결과 |
|---|---|
| Python 전체 |179개 통과7.846초; 연결재사용/프로토콜업그레이드/준비ACK유실/캐시·출발경계 포함 |
| Node 단위 |105개 통과0.915초; SQL/회차/3역할/시계/경합 회귀 포함 |
| TypeScript·diff·변경Python컴파일 |통과; production build/source push/package/save/publish 통과 |
| 실제 localhost HTTP |6종 모두 통과20.935초; 느린human2.5초 동안loading/시각null,epoch/reset/사진실패/같은방복구,기존권한/채점/선택/next 포함 |
| 마지막 heartbeat경합 수정 후 HTTP |배리어 재검사1개 통과3.614초(runner),case3.518초 |
| 공개 CUDA·역할별RGB 준비 |검증 진행 중. 완료 결과는 아래 공개검증 절에 기록 |
| 실제 브라우저 DOM/동시렌더 |미수행. CUA가browser access host unavailable을반환했고다른UI도구로우회하지않음 |

로컬HTTP의준비메시지는테스트클라이언트이며브라우저decode/실제ML검사가아니다. [로컬검증기록](../runs/site-publish/reliability-local-http-20261101.json)을보존한다. 전체문서의이전일정/성능수치를이번결과로바꾸지않는다.

운영사진46장·12,362,595bytes의로컬정본SHA/디코딩과v1두체크포인트의고정SHA일치를별도로확인했다([보존검사](../runs/image-barrier-audit-20261101/data-preservation.json)). 학교사진/새학습/임계값조절/임의오답주입/정답파일사용0이다. 이는공개R2전체재검사나사진품질/40%달성평가가아니다. 목표40%·ONNX/Pi·legacy OS 입력·현장컴퓨터/네트워크리허설은미완료다.

### 배포·공개검증·운영

버전12 게시 **{release['status']}**, commit `{release['commit_sha']}`, saved `{release['version_id']}`, deployment `{release['id']}`, 환경revision{release['env_set_revision']}다. 기존owner/공개범위/두도메인/비밀환경/D1/R2/사진은행은유지했다. archive해시는[배포기록](../runs/site-publish/reliability-release.json)에있다. migration0004_amazing_namora.sql은사진준비5열추가이며로컬5명령을한번적용했다. 기존0000~0003SQL불변,운영migration은Sites게시절차로적용됐다.

공개검증 결과: 자체 검사 진행 중. 공개주소/운영엔진최종확인뒤이문장을갱신한다.

```powershell
.\\.venv\\Scripts\\python.exe -m unittest discover -s tests
.\\.venv\\Scripts\\python.exe scripts/verify_continuous_booth.py --base-url https://bot.marulee.dev --device cuda --execute --output runs/reliability-public-new
.\\.venv\\Scripts\\python.exe runs/site-publish/verify_reliability_surface.py --output runs/site-publish/reliability-http-new.json
.\\.venv\\Scripts\\python.exe scripts/check_docs.py --date 2026-11-01
.\\.venv\\Scripts\\python.exe runs/site-publish/audit_docs.py --date 2026-11-01 --output runs/site-publish/reliability-document-audit-new.json
```

Node단위명령은웹폴더에서 `node --test server/logic.test.mjs server/storage.test.mjs server/authorization.test.mjs server/remote.test.mjs server/state-projection.test.mjs server/gpu-start.test.mjs server/selection-plan.test.mjs server/image-barrier.test.mjs components/arena-state.test.mjs components/engine-status.test.mjs components/server-clock.test.mjs`다. 실제localhost6종은미리보기5186에숨김stdin의로컬QA키로실행한다. 공개ML명령은새QA방과실제선택/제출을만들며비공개정답을읽지않는다. 기존기록을덮지않도록새출력경로를사용한다.

이후절은이전버전이력이다. 당시학교평가/출발/타일별통신/PID/날짜는현재정책을뜻하지않는다.
'''

def prepend(name, title, content):
    path=root/name
    old=path.read_text(encoding='utf-8-sig')
    old=re.sub(r'최종 검토: \d{4}-\d{2}-\d{2}',f'최종 검토: {date}',old,count=1)
    heading=f'# {title}\n\n최종 검토: {date} (Asia/Pyongyang)\n\n'
    prior=old.split('\n',4)[4]
    if name.endswith('STATUS.md'): prior=prior.replace('## 최신 작업: 선택 통신 최적화', '## 이전 작업: 선택 통신 최적화',1)
    path.write_text(heading+content+'\n\n'+prior,encoding='utf-8')

prepend('docs/STATUS.md','현재 진행 상황',body)
inventory=['AGENTS.md','README.md','docs/README.md','docs/SETUP.md','docs/ARCHITECTURE.md','docs/DATASET.md','docs/DATASET_CANDIDATES.md','docs/EXECUTION_PLAN.md','docs/INTEGRATION.md','docs/ROADMAP.md','docs/STATUS.md','docs/CHANGELOG.md','web/alpha-arena/README.md']
log=f'''## 2026-11-01 사진 준비 동기화·연결/지연 수정·버전12

- 10/28중단된부분구현과공개v11의불일치를확인하고3역할9장준비→공통출발을서버/화면/PC에완성했다. loading동안타이머0/질문숨김,동일DOM/RGB재사용,protocol3/epoch/CAS/숨김페이지철회/60초실패복구를구현했다. v11전용protocol2협상과배포중3업그레이드·ACK유실복구를추가했다.
- 느린HTTP시계변경·무한hang·정상409끊김오표시·사람로컬선택잠금을수정했다. 마지막준비ACK와HB의시각경합으로all3ready가loading에멈추는조건을독립검토에서발견해freshclock+상태조회재정산으로고쳤고재현회귀를추가했다. PC HTTPS/pool재사용·불필요HB/GET제거·합성예열·질문에필요한고정모델만실행하는경로를추가했다.
- Python179개7.846초·Node105개0.915초·tsc/컴파일/diff/productionbuild통과. 실제localhost6종20.935초통과,마지막경합수정후배리어1종3.614초통과다. 실제DOM도구연결은불가해우회0이며공개CUDA/HTTPS/운영가동확정결과는STATUS에계속기록한다.
- 버전12 commit `{release['commit_sha']}`, saved `{release['version_id']}`, deployment `{release['id']}`, 환경revision{release['env_set_revision']}게시succeeded다. schema-only0004사진준비5열추가·로컬한번적용·이전migration불변,기존공개범위/도메인/비밀환경/사진/모델을보존했다.
- 로컬공개46장/12,362,595bytesSHA·디코딩과v1두모델고정SHA를재검사했다. 학교/학습/튜닝/임의오답0이며독립품질·40%·Pi/ONNX/legacy OS·현장리허설완료를주장하지않는다.11/07행사전자체검증뒤사용자가실제컴퓨터에서한번더검증한다.

### 이번에 읽고 갱신한 전체 Markdown (13개)

'''+ '\n'.join('- '+p for p in inventory) + '\n\n이번 작업 검토: 관리13개 전체 본문을 분담 재독하고 최신 코드·실제 검사·배포와 과거 이력을 대조했다. 내용 변화 없는 데이터/평가 문서도 검토 결과를 기록했다. 새 Markdown은 없으며 문서점검 최종결과/공개CUDA/운영가동은 STATUS에 확정 기록한다.\n'
prepend('docs/CHANGELOG.md','작업 이력',log)
print('Current STATUS/CHANGELOG inserted; public CUDA and operator verification pending.')
