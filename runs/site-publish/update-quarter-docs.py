from pathlib import Path

root = Path(__file__).resolve().parents[2]

def review(text, label, latest):
    head, tail = text.rsplit('\n이번 작업 검토:', 1)
    return (head+'\n이전 작업 검토('+label+'):'+tail).rstrip()+'\n\n이번 작업 검토: '+latest+'\n'

path = root/'AGENTS.md'
text = path.read_text(encoding='utf-8')
head, tail = text.split('## 제한 학습 v1 보존 원칙', 1)
head = head.replace('타일 클릭을 1초에 한 번씩. 연속 실제 타일 클릭 간격 최소 1.0초', '타일 선택·클릭 기본 및 최소 간격0.25초(250ms). 이전1초 제한을 사용자 후속 요청으로 대체')
head = head.replace('속도는 **타일 클릭을 1초에 한 번**이다.', '속도는 최신 후속 요청으로 **타일 선택·클릭 최소0.25초**이며 이전1초 제한을 대체한다.')
head = head.replace('PC/Pi 모두 최소 1초', 'PC/Pi 모두 최소0.25초')
head = head.replace('제출 버튼의1초 제외', '제출 버튼의선택간격 제외')
head = head.replace('최소1000ms 간격', '최소250ms 간격')
head = head.replace('최소 1초 간격의 콜백', '최소0.25초 간격의 콜백')
head = head.replace('최소1초 클릭', '최소0.25초 클릭')
head = head.replace('dry-run의 0/1/2초', 'dry-run의 0/0.25/0.5초')
head = head.replace('화면은 약500ms 폴링과 네트워크 지연 뒤', '화면은 경기 중 remote 봇125ms·그 외500ms 폴링과 네트워크 지연 뒤')
head = head.replace('표시 갱신은 약500ms 폴링과 네트워크 지연을 포함한다.', '표시 갱신은 경기 중 remote 봇125ms·그 외500ms 폴링과 네트워크 지연을 포함한다. 중복 요청을 막으며 정확250ms 표시를 보장하지 않는다.')
old = '- 사용자 요청의 수정 적용을 위해 기존 운영용 체인을 검증한 뒤 재시작했다.'
start = head.index(old)
end = head.index('\n', start)
head = head[:start]+'- 사용자 요청의 수정 적용에 필요한 운영 엔진 재시작은 경로·부모 관계를 검증한 체인에만 수행한다. 최신 PID·모델 로드·생존·코드 입력 여부는 STATUS가 정본이다. 업데이트 재시작은 메모리 토큰을 잃어 최초 새 방 연결이 한 번 필요하고, 정상 참가자 교체에는 같은 방을 유지한다.'+head[end:]
text = head+'## 제한 학습 v1 보존 원칙'+tail
text = review(text, 'GPU 예약 출발', '사용자 최신 요청으로 이전1초 선택 제한을0.25초/250ms로 대체했다. 서버 CAS·PC ACK후 대기·legacy 스케줄러·PC/Pi 예시·현재 문서를 함께 수정하고 과거1초 측정값은 이력으로 보존했다. 경기 중 봇 표시125ms 폴링과 실제 통신 지연을 구분한다. GPU 예약 출발·학교/고정 모델/40%/Pi 경계를 유지하며 검사·게시·가동 정본은 STATUS다.')
path.write_text(text, encoding='utf-8')

path = root/'README.md'
text = path.read_text(encoding='utf-8')
head, tail = text.split('이전 작업 검토(실행 진단):', 1)
head = head.replace('최소1초', '최소0.25초')
head = head.replace('표시는 약0.5초 폴링과 네트워크 지연을 포함합니다.', '표시는 경기 중 AI 화면125ms, 그 외500ms 폴링과 네트워크 지연을 포함합니다. 250ms는 최소 선택 간격이며 실제 표시 간격을 보장하지 않습니다.')
text = head+'이전 작업 검토(실행 진단):'+tail
text = review(text, 'GPU 예약 출발', '사용자 승인으로 선택·클릭 기본/최소 간격을0.25초로 변경하고 서버250ms·PC ACK후 대기·봇 표시125ms/그 외500ms를 반영했다. 과거1초 기록은 이력이며 새로운 정확도 측정이 아니다. GPU 예약 출발·같은 방 참가자 교체와 학교/모델/40%/Pi 경계를 유지한다. 배포·재시작·실제 검사 결과는 STATUS에 기록한다.')
path.write_text(text, encoding='utf-8')

path = root/'docs/README.md'
text = path.read_text(encoding='utf-8')
text = text.replace('현재4종·가변 정답수·나무 계수의 정확도 보증이 아닙니다.', '현재4종·가변 정답수·나무 계수의 정확도 보증이 아닙니다. 최신 선택 간격은0.25초(서버250ms)이며 과거1초 기록은 이력입니다.', 1)
text = review(text, 'GPU 예약 출발', '관리13개 본문·색인을0.25초 선택 제한에 맞춰 다시 대조했다. 서버/PC/legacy/Pi 예시와125ms 진행중 봇 표시/그 외500ms의 위치를 확인했다. 새 Markdown은 없으며 실제 검사·배포·운영 엔진·미검증 범위는 STATUS/CHANGELOG가 정본이다. 학교/모델/40%/실기기 경계는 유지한다.')
path.write_text(text, encoding='utf-8')

inventory = '''- AGENTS.md
- README.md
- docs/README.md
- docs/SETUP.md
- docs/ARCHITECTURE.md
- docs/DATASET.md
- docs/DATASET_CANDIDATES.md
- docs/EXECUTION_PLAN.md
- docs/INTEGRATION.md
- docs/ROADMAP.md
- docs/STATUS.md
- docs/CHANGELOG.md
- web/alpha-arena/README.md'''

status = '''## 최신 작업: 선택 간격0.25초 (2026-10-27)

사용자 후속 요청으로 이전1초 제한을 **기본·최소0.25초(250ms)**로 변경했다. GPU 예약을 확보한 뒤 인간/AI가 공통 출발하는 버전9의 흐름은 유지한다. 새 제한은 타일 사이 대기이며 모델 정확도·추론 시간 변경이 아니다.

- Python `MIN_TILE_INTERVAL_SECONDS=0.25`를 remote ACK후 대기·legacy 콜백/설정 검증·CLI·보정기·PC/Pi 예시·저장 이미지 계획에 함께 사용한다. 부동소수점 반올림으로 짧아지지 않도록 다음 표현값으로 올린다. 첫 선택 대기0·제출 간격 제외는 기존 운영 가안이다.
- 서버 `TILE_INTERVAL_MS=250`를 사전 검사와 SQL CAS에 함께 사용한다. 249ms는 거부하고250ms는 허용하며 sequence 재전송 ACK·중복 타일/옛 회차 거부·단일 승자 조건을 유지한다.
- remote AI 표시의 playing 상태만125ms로 조회하고 인간/대기/결과는500ms다. 요청 중복을 막는다. 실제 간격에는 선택/상태 HTTP 왕복과 렌더링이 더해지며 정확히 초당4개 표시를 보장하지 않는다.

| 새 검증 | 실제 결과 |
|---|---|
| Python 전체 |155개 통과,11.072초;0.25 허용·0.249 거부·명시적 느린1.0 설정·ACK후 대기 경계 |
| Node 서버/UI |73개 통과,1.270초(서버52/UI21);249/250ms SQL·순서·상태·폴링 회귀 |
| TypeScript·대상 ESLint·Python 변경 파일 컴파일·diff |통과 |
| 실제 localhost HTTP |4종 통과: 기존채점5.402초·지속방8.004초·GPU대기17.730초·원격권한/250ms선택20.037초; runner20.192초 |

새 배포·공개 간격·운영 엔진 가동 결과는 아래 확정 기록에 추가한다. 이 문장만으로 게시/운영 재시작 완료를 주장하지 않는다.

### 재현 명령

```powershell
.\\.venv\\Scripts\\python.exe -m unittest discover -s tests
.\\.venv\\Scripts\\python.exe scripts/check_docs.py --date 2026-10-27
.\\.venv\\Scripts\\python.exe runs/site-publish/audit_docs.py
```

웹 폴더에서 `node --test server/logic.test.mjs server/storage.test.mjs server/authorization.test.mjs server/remote.test.mjs server/state-projection.test.mjs server/gpu-start.test.mjs components/arena-state.test.mjs components/engine-status.test.mjs`와 `npx tsc --noEmit`을 실행한다. 실제 HTTP4종은 로컬5186 미리보기에만 `run-local-audits.mjs`의 숨김 stdin으로 QA키를 넘겨 실행했다. 키·토큰·방코드는 파일/로그에 쓰지 않았다.

모델/임계값/학교 사용·새 학습은 변경0이다. 이번 선택 제한 수정으로40% 달성·학교 성능·ONNX/Pi·기존 OS 실클릭을 확인한 것은 아니다. 실제 브라우저의125ms 갱신과 물리 부스 기기/네트워크 리허설은 미검증이다.

## 구현 완료 이력: GPU 예약 후 공통 출발·버전9 (2026-10-27)

이 절은 이번 선택 간격 변경 직전에 완료한 버전9 기록이다. **여기의1초 정책과 측정은 당시 이력이며 현재 제한은 위0.25초가 우선한다.**

- 시작 요청은 `queued` 티켓으로 전환하고 round/질문/사진/startAt을 공개하지 않으며 타이머0이다. PC가 관측 등록순 FIFO로 공유 GPU 예약을 얻은 뒤 `begin`이 약2초 뒤 공통 출발을 확정한다. 추론 함수가 반환하면 선택/제출 전에 예약을 해제해 다음 방 준비와 겹친다. 단일 실행기의 등록순이며 서버 전역 공정성이나 모든 지연의 동일함을 보장하지 않는다.
- requestId·roundId·roundNumber 프로토콜2 heartbeat와 revision/티켓 CAS를 구현했다. 취소·오류·15초 생존 만료·120초 대기 상한은 lobby로 되돌리고 수동 재시작한다. 첫 신규 엔진의 명시적 지원false lobby만 부트스트랩하고 첫2 heartbeat로 지원을 확정한다. 구형 엔진은 기존 판을 마칠 수 있지만 새 예약 출발은 거부한다.
- `0002_mysterious_ravenous.sql`5개 컬럼을 추가하고 기존0000/0001을 유지했다. 로컬0002는한번 적용했고 운영 API와 실제 CUDA로 새 schema를 확인했다. Python154개·Node72개·localhost HTTP4종·타입/구문 검사가 통과했다.
- 실제 CUDA의 로컬/공개 각각A두판+B한판은 모두17항목 passed=true다. 대기 중 무문제/타이머0·경기중 GPU 대기0·추론후 예약해제·같은 방/코드/표시 권한·새 참가자 재준비·라운드별 예측/제출1회·표시/모델 일치를 확인했다. 로컬 모델1회 로드14.922초·생존866샘플, 공개18.047초·351샘플이며 준비후 끊김 관측0이다.
- 공개B1은 예약 대기13.250초(상태 HTTP10.843초 포함), 요청→공통 시작19.663초(공통2초 포함), 모델 함수0.907초였다. schema2는 모델 함수와 상태HTTP를 분리하며 기존v8 지표와 속도를 직접 비교하지 않는다. 대기를 타이머 앞으로 옮긴 결과이며 부스 전체 대기 단축 보장이 아니다.
- 로컬/공개 각3판 모두오답·90초 timeout으로 정상 종료했다. 이24사진 재사용 기능검사를 일반 정확도0%로 해석하지 않는다. 로컬1선택·공개2선택으로 연속 선택 간격 표본0이며 이 실행으로1초 실측을 주장하지 않는다.
- [로컬 CUDA 보고서](../runs/gpu-start-local-v1/verification.json), [공개 CUDA 보고서](../runs/gpu-start-public-v1/verification.json), [버전9 배포 기록](../runs/site-publish/gpu-start-release.json), [두 호스트 HTTPS 검사](../runs/site-publish/gpu-start-release-http.json)가 근거다. v9 commit `774cf6edfc54469253f2fbb343176fdf2d123581`, deployment `appgdep_6ae02fab01508191ba469fa974db7b53`, 환경revision3, succeeded다.
- 당시 운영 엔진49404→52164→51904는 CUDA 로드11.812초에 완료했다. 이PID는 과거 기록이며 재사용될 수 있어 현재 생존 근거로 쓰지 않는다. 운영 엔진은 아래 최신 가동 기록을 따른다. 재시작은 메모리 토큰을 잃으므로 업데이트 때 새 방으로 한 번 연결하고 정상 참가자 교체는 같은 방을 유지한다.
- queued UI의 실제 렌더링/취소는 브라우저 도구 연결 종료로 확인하지 못했다. 다른 입력도구로 우회하지 않았다. 서버 취소·UI 논리 테스트와 실제 화면 검증을 구분한다.

이후 절은 이전 작업 이력이다. 버전·미구현 제안·1초 정책·기기/PID 설명은 해당 당시를 기준으로 읽는다.

'''

path = root/'docs/STATUS.md'
text = path.read_text(encoding='utf-8')
text = text.replace('## 이번 검토: 공유 GPU 대기와 대결 공정성', '## 이전 상담: 공유 GPU 대기와 대결 공정성', 1)
marker = '최종 검토: 2026-10-27 (Asia/Pyongyang)\n'
text = text.replace(marker, marker+'\n'+status, 1)
text = review(text, 'GPU 공정성 상담', 'GPU 예약 출발의 구현/버전9·실제CUDA와 최신0.25초 수정의 테스트/게시/가동을 구분해 정리했다. 이전1초/미구현 제안/PID는 역사 기록으로 표시했다. 관리13개 전수 검토와 새 검증 명령을 반영하고 학교/모델/40%/ONNX/Pi·실제화면 미검증 경계를 유지한다.')
path.write_text(text, encoding='utf-8')

changelog = '''## 2026-10-27 선택 간격0.25초 변경

- 사용자 최신 요청으로 이전1초 제한을0.25초/250ms로 대체했다. Python 공유 하한·ACK후 대기·legacy 스케줄러/검증·CLI·보정기·PC/Pi 예시, 서버 사전 검사/SQL CAS와 UI 안내를 함께 교정했다. HTTP재시도1초와 GPU 예약/학습 정책은 유지한다.
- 경기 중 remote AI 표시는125ms 폴링, 그 외500ms이며 중복 요청을 막는다. 통신/렌더링을 포함한 실제250ms 표시 보장으로 설명하지 않는다.
- Python155개11.072초·Node73개1.270초·타입/대상lint/컴파일/diff 통과. 실제 localhost HTTP4종도 모두 통과(runner20.192초)했다. 249ms 거부/250ms 허용과 기존 순서/CAS/생존/참가자 교체/공통 출발을 확인했다.
- 최종 공개 배포·간격 검증·PC 재시작·문서 점검의 확정 결과는 STATUS의 최신 절과 아래 배포 기록으로 남긴다. 실제OS/Pi/브라우저 표시 간격·학교/40%·행사장 리허설은 미완료다.
- 아래13개 전체 본문을 이번 제한 변경과 기존 GPU 예약 구현에 맞춰 분담 재검토·갱신했다. 변경 없는 데이터 정책도 검토 결과를 남기고 과거1초 측정값은 보존했다. 새 Markdown은 없다.

### 이번에 읽고 갱신한 전체 Markdown (13개)

'''+inventory+'''

## 2026-10-27 GPU 예약 출발 구현·버전9 (직전 작업 확정)

- 사용자 승인으로 queued 무문제/타이머0→PC FIFO예약→begin 공통약2초 출발→모델 반환후 예약해제→방별 선택을 구현했다. 프로토콜2·취소/만료/오류 복구·begin 멱등/옛티켓 거부와 구버전 출발 거부를 추가했다. migration0002는5컬럼 추가이며 기존0000/0001은 유지했다.
- Python154개·Node72개·실제 HTTP4종이 통과했다. 실제 로컬/공개 CUDA 각각A두판+B한판은17검사 통과, 경기중 GPU대기0·선택전해제·같은방/코드/표시·예측/제출1회를 확인했다. 각3판 모두오답timeout은 재사용24사진 기능검사이며 정확도/40% 달성 근거가 아니다. 연속선택 간격 표본은0이다.
- 버전9은 build/source push/package/save/publish succeeded다. commit `774cf6edfc54469253f2fbb343176fdf2d123581`, saved `appgprj_6ade37995018819184a42c88bb0fde7c~appgver_9987abc16e84819187520a57980c38b3`, deployment `appgdep_6ae02fab01508191ba469fa974db7b53`, 환경revision3이다. 도메인·공개범위·기존사진·키를 유지했다. 두호스트HTTPS200 확인, 운영엔진 당시11.812초 로드/가동. 최신0.25초가 이 당시1초 정책을 대체한다.
- schema2는 모델함수/상태HTTP를 분리하지만 예약대기는 상태HTTP를 포함한다. 기존v8 순수GPU 성능과 직접 비교하지 않는다. 실제 queued 렌더링은 브라우저 연결 종료로 미검증이며 입력도구 우회0이다. 학교/모델/40%/ONNX/Pi·부스물리 리허설 경계를 유지했다.
- 다음 작업은 최신사이트·PC 갱신 후 행사 컴퓨터 배치에서 최초연결/공통출발/같은방 다음참가자 반복, 독립 품질평가·학교최종평가·ONNX/Pi다.

'''

path = root/'docs/CHANGELOG.md'
text = path.read_text(encoding='utf-8')
text = text.replace(marker, marker+'\n'+changelog, 1)
text = review(text, 'GPU 공정성 상담', '누락된 직전 GPU 예약 구현의 실제v9 게시/CUDA 결과와 최신0.25초 선택 요청을 별도 이력으로 기록했다. 관리13개 전체 본문을 재검토했고 이전1초 실측은 보존했다. 최신 검사/배포/가동 정본은 STATUS이며 학교/모델/40%/실기기 한계를 유지한다.')
path.write_text(text, encoding='utf-8')
print('Updated root five Markdown documents; release results will be finalized after measurement.')
