from pathlib import Path
import json

root=Path(__file__).resolve().parents[2]
def review(text, label, note):
    head,tail=text.rsplit('\n이번 작업 검토:',1)
    return (head+'\n이전 작업 검토('+label+'):'+tail).rstrip()+'\n\n이번 작업 검토: '+note+'\n'

path=root/'AGENTS.md'; text=path.read_text(encoding='utf-8')
head,tail=text.split('## 제한 학습 v1 보존 원칙',1)
head=head.replace('| 학교 사진 | 문제·고정 후 최종 평가 전용. 학습·개발 검증·튜닝에 사용하지 않음 |','| 학교 사진 | 최신 사용자 결정으로 이번 행사에 사용하지 않음. 촬영·문제·학교 최종 평가는 현재 범위에서 제외. 개발 사용 차단은 유지 |')
head=head.replace('첫 클릭·제출 적용은 미정이다.', 'remote 선택 계획은 서버 접수 후500ms 표시 여유를 두고250ms 간격 재생·마지막 선택 시 제출한다. legacy/구형 개별 선택의 첫 대기0·제출 간격 제외는 운영 가안이다.')
head=head.replace('화면은 경기 중 remote 봇125ms·그 외500ms 폴링과 네트워크 지연 뒤','화면은 계획 수신 후500ms 상태 조회와50ms 시계 갱신(계획 없는 진행 중 봇만125ms 폴링), 네트워크 지연 뒤')
head=head.replace('**90초 시간초과·첫 클릭 대기0초·제출 버튼의선택간격 제외·GPU 대기120초 상한은 운영 가안**', '**90초 시간초과·legacy/구형 경로 첫 대기0·제출 간격 제외·GPU 대기120초 상한은 운영 가안**')
head=head.replace('선택 sequence 멱등 ACK와 최소250ms 간격, 제출 시 선택 snapshot CAS 및 첫 완벽 정답 즉시 종료를 검사한다.', '최신 PC의 고정 ML 선택 목록을 round별 한 번 수락해500ms 뒤부터250ms 서버 일정으로 재생·제출한다. 같은 목록 재전송은 같은 ACK, 다른 목록/개별 API 혼용은 거부한다. 구형 개별 선택의 sequence 멱등 ACK·최소250ms·snapshot CAS는 유지한다. 서버 예정 제출이 도래하면 정산하며 인간 제출과 같은 트랜잭션/SQL 보호로 단일 승자를 확정한다.')
head=head.replace('표시 갱신은 경기 중 remote 봇125ms·그 외500ms 폴링과 네트워크 지연을 포함한다.', '표시는 유효 계획 수신 후500ms 상태 조회와50ms 시계로 재생하고 계획 없는 진행 중 봇만125ms 폴링한다.')
old='- 로컬 Kaggle 데모34장은 공개하지 않는다.'
start=head.index(old); end=head.index('\n',start)
head=head[:start]+'- 로컬 Kaggle 데모34장은 공개하지 않는다. 공개 사진은 기존 Commons24장과 새 CC0/PD22장으로 총46장·12,362,595bytes다. 새22장은 실제 RGB/원문 권리·그룹/해시·두 AI 교차검토를 거쳐22/22 업로드했고 운영46파일의 SHA/디코딩·4종 출제를 확인했다. 독립 사람 검수·추가 학습/튜닝0이며 정확도 표본이 아니다. 정본은 data/booth/public-web-v1/bank.json과 public-web-v2/bank.json, 운영 적용은 STATUS다.'+head[end:]
head += '\n선택 계획은 서버 수락 뒤 PC가 끊겨도 이미 받은 고정 모델 결과로 완료한다. 인간이 먼저 이기면 서버 종료 시각으로 선택을 자른다. 미래 모델 선택 일정은 봇 표시 화면에만 주고 인간/모델 입력에 정답·계획의 서버 정오답을 노출하지 않는다. PC는 타일별 select/submit HTTP를 보내지 않고 계획 한 번과 생존/상태 확인만 수행한다. 공개 RGB9장은 최대3개 병렬로 내려받되 원래 순서를 보존한다. 서버 일정·논리 제출·실제 HTTP/브라우저/OS 입력 시간을 구분한다.\n\n'
text=head+'## 제한 학습 v1 보존 원칙'+tail
old='학교 사진은 문제·모델 고정 후 최종 평가 전용이다. 학교 원본·크롭·증강본은 학습·미세조정·개발 검증·모델 선택·조기 종료·임계값/전처리 튜닝에서 제외한다. 개발용 train/val/test는 Kaggle 자료만으로 구성한다.\n기존 초기 프롬프트의 학교 추가 학습 지시는 폐기 상태를 유지한다. 학교 문제 결과나 본선 승패에 맞춰 모델·학습 제한을 다시 조절하지 않는다.'
new='최신 사용자 결정으로 학교 사진을 이번 행사에서 사용하지 않는다. 학교 촬영·문제 등록·학교 최종 평가는 현재 실행 계획에서 제외하고 인터넷의 명확한 공개 사용 가능 사진을 운영 문제로 쓴다. 학교 원본·크롭·증강본의 학습·미세조정·개발 검증·모델 선택·조기 종료·임계값/전처리 튜닝 금지는 미래 유입 방지용으로 유지한다. 개발용 train/val/test는 기존 Kaggle 자료다. 초기 학교 추가 학습 지시는 계속 폐기하며 본선 승패에 맞춰 모델을 다시 조절하지 않는다.'
assert old in text; text=text.replace(old,new,1)
text=review(text,'0.25초 제한','통신 지연 후속 요청으로 고정 ML 선택 계획1회·500ms 표시 버퍼/250ms 서버 일정·서버 단일 승자·최대3사진 병렬을 구현했다. 학교 사진과 학교 최종 평가는 이번 행사에서 제외하고 명확한 Commons22장을 추가해 운영46장을 확인했다. 새 모델 학습/임계값 조절·임의 오답0이며 예정 시각과 실제 화면/OS 실측을 구분한다. 관리13개 전수 검토·게시/검사/가동 정본은 STATUS다.')
path.write_text(text,encoding='utf-8')

path=root/'README.md'; text=path.read_text(encoding='utf-8'); head,tail=text.split('이전 작업 검토(실행 진단):',1)
head=head.replace('웹에서 확보한 공개 테스트사진24장을 등록해 지금 사진 출제를 시험할 수 있습니다.', '공개 사진46장(기존24장+새22장)을 등록해 지금 사진 출제를 시험할 수 있습니다.')
head=head.replace('Commons 원문의 CC0/Public domain 근거·RGB 라벨·24개 원본그룹과 해시를 확인했습니다.', 'Commons 원문의 CC0/Public domain 근거·RGB 라벨·원본 그룹과 해시를 확인했습니다. 새22장은 사람이 직접 셀 수 있는 단체 사진·여러 나무·건물 외관·정원 연못 위주이며 두 AI가 교차 검토했습니다. 독립 사람 검수는 아직입니다.')
head=head.replace('**학교 사진은 문제·모델 고정 후 최종 평가 전용**이며 학습·개발 검증·모델 선택·튜닝에 쓰지 않습니다.', '**학교 사진은 이번 행사에서 사용하지 않습니다.** 학교 촬영·문제 등록·학교 최종 평가를 현재 계획에서 제외합니다. 미래 학교 자료의 개발 학습/튜닝 차단은 유지합니다.')
head=head.replace('RGB 판별→최소0.25초 간격 선택 전송→AI 화면 체크→한 번 제출합니다. 표시는 경기 중 AI 화면125ms, 그 외500ms 폴링과 네트워크 지연을 포함합니다. 250ms는 최소 선택 간격이며 실제 표시 간격을 보장하지 않습니다.', '공개 RGB 최대3개 병렬 수신→ML 판별→고정 선택 목록 한 번 전송을 수행합니다. 서버는 접수 후0.5초 표시 여유를 두고250ms 간격으로 재생해 마지막 선택 시 한 번 제출합니다. AI 화면은 계획을 받으면50ms 시계로 표시하고 상태는500ms 조회합니다(계획 없는 구형 진행 중 화면만125ms). 통신/브라우저 지연으로 정확한250ms 표시를 보장하지는 않습니다.')
head=head.replace('이미 분석한 방의 최소0.25초 간격 선택/제출과 다음 방의 준비/추론을 겹칠 수 있습니다.', '이미 분석한 방의250ms 서버 선택 계획과 다음 방의 준비/추론을 겹칠 수 있습니다.')
head=head.replace('현재 모델은 각 라운드마다 예측을 한 번 하고 그 선택만 제출합니다.', '현재 모델은 각 라운드마다 예측을 한 번 하고 그 선택 목록만 서버에 한 번 보냅니다. 서버가 이미 수락한 계획은 PC가 끊겨도 완료하며, 인간이 먼저 맞히면 종료 시각에서 남은 선택을 중단합니다. 미래 선택 목록은 AI 표시 화면에만 제공하고 사람에게 정답/모델 계획을 미리 주지 않습니다.')
text=head+'이전 작업 검토(실행 진단):'+tail
text=review(text,'0.25초 제한','선택마다의 GET/POST 왕복을 고정 ML 계획 한 번으로 바꾸고500ms 표시 버퍼·250ms 서버 일정·3사진 병렬 다운로드를 현재 운영에 반영했다. Commons22장 추가/운영46장과 학교 사진·학교 최종 평가의 행사 제외를 기록했다. 예정 간격과 실제 표시 실측, 새 사진 기능 검사와 정확도를 구분하며 기존 모델/40%/ONNX/Pi 경계를 유지한다. 최종 검증·배포·PC 가동은 STATUS를 따른다.')
path.write_text(text,encoding='utf-8')

path=root/'docs/README.md'; text=path.read_text(encoding='utf-8')
text=text.replace('기존134장·로컬34장·별도공개24장·라벨/관계 그룹·학교 최종 전용','기존134장·로컬34장·공개24+22장·라벨/그룹·학교 행사 미사용')
text=text.replace('목표40%는 미달성이고 학교/Pi/OS 입력도 실제 검증을 구분합니다.', '목표40%는 미달성이고 Pi/OS 입력은 실제 검증을 구분합니다. 학교 사진·학교 최종 평가는 이번 행사 범위에서 제외합니다.')
text=review(text,'0.25초 제한','관리13개 색인과 본문을 선택 계획1회/500ms 버퍼/250ms 서버 재생·최대3사진 병렬·Commons22장 추가/총46장·학교 행사 비사용으로 대조했다. 새 Markdown은 없고 이전 실측/학교 최종전용은 이력이다. 실제 적용·QA·운영 프로세스와 미측정 시각은 STATUS/CHANGELOG가 정본이다.')
path.write_text(text,encoding='utf-8')

status='''## 최신 작업: 선택 통신 최적화·공개 사진22장 추가·버전11 (2026-10-27)

**현재 운영 사진은46장이고 학교 사진은 이번 행사에서 사용하지 않는다.** 학교 촬영·문제·학교 최종 평가는 현재 범위에서 제외했다. 기존 모델/전처리/임계값·학교 자료의 개발 학습 차단·40% 미달성·ONNX/Pi/legacy OS 미검증은 유지한다.

### 통신과 서버 일정

- 기존에는 각 타일마다 상태 GET→선택 POST→ACK후250ms가 필요했다. 최신 PC는 공개 RGB를 ML에 넣어 한 번 정한 목록을 `plan {roundId,selectedIndices}` 한 요청으로 보낸다. 타일별 select/submit HTTP는0이며 서버 생존/상태 조회는 계속한다. 공개 RGB9장은 최대3개 병렬 다운로드하며 `map`으로 타일 순서를 보존하고 실패 시 작업을 정리한다.
- 서버는 같은 round의 목록을 한 번만 수락한다. 같은 순서의 재전송은 동일 ACK, 다른 목록/기존 개별 선택과 혼용은 거부한다. **접수 후500ms 표시 버퍼→250ms 서버 일정→마지막 선택 시 제출**이다.0개 선택도500ms 뒤 그대로 제출하며 9개이면 버퍼 포함2.5초 일정이다. 선택 수/정답 수를 강제로 맞추거나 임의 오답을 넣지 않는다.
- 원격 계획 수락 뒤에는 PC가 끊겨도 이미 받은 결과로 재생을 완료한다. 인간 선승이면 정해진 종료 시각으로 남은 선택을 자른다. 미래 선택은 bot 표시 역할에만 주고 human/모델 입력에 노출하지 않는다. 예정 정오답은 서버 전용이다. due 정산과 인간 채점의 D1 batch/SQL 보호로 한 승자를 유지하며 예정 제출 시각과 같은 시각의 인간 요청은 이미 도래한 bot 제출이 우선한다.
- 계획을 받은 봇 표시는 기존50ms 시계로 체크하고 상태 조회는500ms다. 계획 없는 진행 중 봇 fallback만125ms이며 인간·대기·결과도500ms다. 늦게 받은 화면은 진행 시각까지 따라잡는다. **서버 일정250ms와 실제 화면/OS 클릭 간격은 다른 지표**이며 실제250ms 렌더링을 측정했다고 주장하지 않는다.
- migration `0003_colorful_cassandra_nova.sql`은 round의 nullable 계획4컬럼만 추가했다. 로컬4명령을 한번 적용했고 기존0000~0002는 변경하지 않았다. 구형 개별 API와 GPU 예약 출발/같은 방 next/프로토콜2는 유지한다.

### 새 공개 사진과 학교 범위

- [새 은행 정본](../data/booth/public-web-v2/bank.json)은 **22장·6,299,046bytes·CC0 15/PD7**이다. 사람 단체·명확한 나무 줄기/군락·건물 외관·돌 경계 정원/잉어 연못을 선정했다. 강/호수처럼 보이는 수면·눈녹은 웅덩이 같은 후보·같은 날 근접 촬영 가능 숲·조형물/그림/합성·사진권리 혼합은 제외하고 모르는 조건은 null로 남겼다. 선별에 모델 예측을 사용하지 않았다.
- 두 AI가 실제 RGB를 대조하고 일부 인원수는 큰 원본으로 다시 셌다. 파일별 Commons 원문 revision/권리·원본 SHA1·전송 SHA256·그룹을 보존했다. 독립 사람 검수는 미완료다. 기존 은행과 원본ID/SHA1·사진 바이트 중복0 및 dHash거리≤4 의심쌍0은 중복 검사 근거이지 세상 모든 유사 촬영이 없다는 증명은 아니다.
- importer dry-run22/22 뒤 운영 **22/22 신규 업로드·기존중복0**을 확인했다([업로드 기록](../runs/site-publish/public-bank-v2-upload.json)). 기존24장과 합쳐 **46장·12,362,595bytes(CC0 26/PD20)**다. 새 사진은 운영 문제용으로만 사용하며 추가 학습·개발val/audit 편입·승률 튜닝0이다.
- 운영46개 파일의 해시·디코딩이 두 로컬 은행과 일치했고 네 유형 각9독립그룹/사진·같은 인간/봇 배열과 출발·정답수 범위·정답 비노출을 검사했다. 그 중 신규 사진12개를 실제 공개 타일로 관측했다. 관리자 권한의 별도 SERVER 사진 검사이며 ML 풀이기와 분리하고 선택/제출하지 않았다([공개은행 검증](../runs/site-publish/expanded-photo-bank-verification.json)).

| 운영46장 조건 | 양성 그룹 | 음성 그룹 | 미확인 | 출제 준비 |
|---|---:|---:|---:|---|
| 사람≥3 |14|24|8|ready|
| 나무≥3 |16|22|8|ready|
| 건물 |13|25|8|ready|
| 연못 |11|34|1|ready|

### 실제 검사

| 검사 | 관측 결과 |
|---|---|
| Python 전체 |165개 통과14.515초; 계획 ACK/호환/목록·측정 분리·3다운로드 순서/실패 포함 |
| Node 서버/UI |89개 통과1.217초(서버65/UI24); 계획13·UI3 추가 |
| TypeScript·대상 ESLint·컴파일·diff |통과 |
| 실제 localhost HTTP |5종 통과: 기존채점6.340초·지속방9.065초·GPU대기18.186초·원격20.487초·계획13.005초; runner20.659초 |
| 실제 공개 PC CUDA |A같은방2판+B1판, 모델1회로드8.844초·18검사 passed=true·생존216샘플·준비후끊김 관측0 |
| 로컬 브라우저 |격리된 고정API계획으로9이미지 로드·4체크·전부읽기전용·가로넘침0을 DOM으로 확인. 실제ML/물리OS/정확한250ms렌더링 검사는 아님 |

공개 CUDA의 사람 문제 A1은 `[0,8]` 두 선택으로 정답 종료, A2 연못/B1 나무는 `[]` 그대로 오답 제출 뒤90초 timeout이었다. **세 판 재사용 기능검사를 정확도1/3이나40% 달성으로 해석하지 않는다.** [실제 CUDA 보고서](../runs/scheduled-booth-public-v1/verification.json)에 예측1회·논리제출1회·서버 제출 관측3·모델/표시 일치·경기중GPU대기0·계획 이전GPU해제와 같은 방/코드/권한 유지가 있다. 관리 정답/학교/OS입력/튜닝 접근0이다.

세 계획의 실제 업로드→ACK는 **0.360/0.375/0.469초**,9사진 다운로드는 **1.500/2.797/1.937초**였다. 서버 예정 간격 표본은 A1의250ms 1개이며 실제 타일별 HTTP 간격 표본은0이다. 고정API UI 시연의4체크는 별도이며 이를 실제 모델 클릭 속도로 바꾸지 않는다. 과거v10의762~957ms 실제 API 간격과 새 서버 예정250ms는 다른 측정이다. 같은 사진·네트워크로 짝지은 전체 경기 속도 비교를 수행한 것은 아니다.

브라우저 첫 고정 하네스가 이전 heartbeat와 출발 전환의409를 치명 오류로 처리해 종료했다. 서버의 옛 요청 거부는 정상이었고 하네스를 상태 재조회로 고친 새 QA방에서 queued→countdown→playing→계획 수락/표시→result를 확인했다. DOM 감시 생성자는 read-only 검사 범위에서 지원되지 않아 정확한 렌더링 간격을 측정하지 못했다. 영역 스크린샷은 캡처 좌표가 잘리지 않아 연결 코드를 포함한 임시 파일을 즉시 제거했으며 부정확한 이미지를 증거로 보존하지 않았다. 실제 DOM 관측과 서버 일정을 근거로 삼는다.

### 배포와 재현

버전11 production build/source push/package/save/publish **succeeded**, commit `8755f3c852c555ac2637c47a85bd4e3cedac8d0e`, saved `appgprj_6ade37995018819184a42c88bb0fde7c~appgver_0ef517f5604c8191b1e96654ef95eea5`, deployment `appgdep_6ae065686ac88191a8ea3c01f755ce6a`, 환경revision4다. 사진 등록용 기존 관리자 비밀값은 조회 시 가려져 같은 권한으로 갱신했고 메모리/stdin/서버 비밀 환경만 사용했다. owner·도메인·공개범위·기존사진/모델은 유지했다. 운영 엔진·최종 HTTPS/문서 점검 결과는 아래 확정 기록에 추가한다.

```powershell
.\\.venv\\Scripts\\python.exe -m unittest discover -s tests
.\\.venv\\Scripts\\python.exe scripts/verify_continuous_booth.py --base-url https://bot.marulee.dev --device cuda --execute --output runs/scheduled-booth-public-new
.\\.venv\\Scripts\\python.exe scripts/import_public_booth_bank.py --bank data/booth/public-web-v2/bank.json --base-url https://human.marulee.dev --output runs/site-publish/public-bank-v2-dry-new.json
.\\.venv\\Scripts\\python.exe scripts/check_docs.py --date 2026-10-27
.\\.venv\\Scripts\\python.exe runs/site-publish/audit_docs.py
```

웹 단위검사는 기존8파일에 `server/selection-plan.test.mjs`를 추가한다. 실제 localhost5종은 새 migration 후5186 미리보기·숨김stdin QA키와 `run-local-audits.mjs`로 실행한다. 관리자 사진 검증은 `with_booth_secret.mjs`의 숨김stdin으로 `verify_expanded_photo_bank.py`를 실행했으며 ML 경로에 키/라벨을 넘기지 않았다. 새 실행 출력 경로를 써서 과거 기록을 보존한다. 실제 물리부스 배치/장시간 네트워크·독립 품질·40%·ONNX/Pi/legacy OS 입력은 미완료이며 학교 최종 평가는 현재 행사 범위에서 제외했다.

이후 절은 이전 버전 이력이며 옛 학교 최종평가 계획/타일별 ACK 지연/PID는 현재 운영을 뜻하지 않는다.

'''
marker='최종 검토: 2026-10-27 (Asia/Pyongyang)\n'
path=root/'docs/STATUS.md';text=path.read_text(encoding='utf-8').replace('## 최신 작업: 선택 간격0.25초','## 이전 작업: 선택 간격0.25초',1)
text=text.replace(marker,marker+'\n'+status,1)
text=review(text,'0.25초 제한','고정 ML 계획1회·서버500ms/250ms 일정·이미지3병렬·신규22/운영46·학교행사제외를 실제배포/HTTP/CUDA/공개사진/DOM 관측과 대조했다. 예정 시각을 실제 HTTP/화면/OS 시간으로 바꾸지 않고 새 정확도를 주장하지 않는다. 관리13개 재독·갱신과 최종 문서/가동 결과를 기록한다.')
path.write_text(text,encoding='utf-8')

inventory=['AGENTS.md','README.md','docs/README.md','docs/SETUP.md','docs/ARCHITECTURE.md','docs/DATASET.md','docs/DATASET_CANDIDATES.md','docs/EXECUTION_PLAN.md','docs/INTEGRATION.md','docs/ROADMAP.md','docs/STATUS.md','docs/CHANGELOG.md','web/alpha-arena/README.md']
log='''## 2026-10-27 통신 왕복 제거·공개 사진 확대·학교 미사용·버전11

- 사용자 요청으로 타일별 상태GET/선택POST/ACK대기를 고정 ML 선택 계획1회 업로드로 대체했다. 서버500ms표시 버퍼·250ms일정·마지막 선택시 논리제출이며 같은 목록멱등/다른목록거부·human선승중단·due봇과human원자채점·timeout/같은방next/구형API호환을 구현했다. 수락후PC끊김에도서버재생이완료되며 미래정오답은서버만보유한다. 계획받은viewer는50ms시계+500ms상태조회,계획없는진행중bot만125ms다.
- RGB9장최대3병렬/map순서/실패정리를추가했다. 모델·전처리·임계값·학습/고의오답 변경0이다. 새 nullable4컬럼 migration0003생성·로컬한번4명령적용,기존0000~0002불변이다.
- Commons77후보에서명확한22장(6,299,046bytes·CC0 15/PD7)을시각/권리/원본그룹/해시와두AI교차검토후선정했다. 애매한수면/눈웅덩이·동일근접촬영숲·혼합권리·그림/조형물/합성은제외하고카누수면연못조건은null로뒀다. 독립사람검수는미완료다. 사진선정에모델예측을사용하지않았다.
- 신규22/22업로드·기존중복0으로운영46장/12,362,595bytes(CC0 26/PD20)이다. 공개46파일SHA/디코딩·4유형9독립사진·정답수범위·양역할배열/출발동일·비공개답안보호를검사했고신규12개공개타일을관측했다. 관리자SERVER사진검사와실제ML풀이를분리했다. 학교는이번행사촬영/문제/최종평가범위에서제외하며미래개발유입차단은유지한다.
- Python165개14.515초·Node89개1.217초·tsc/대상ESLint/컴파일/diff통과,실제localhostHTTP5종도통과(runner20.659초,계획검사13.005초)다. 실제공개CUDA A2판+B1판은18검사passed=true·모델1회로드8.844초·생존216샘플·준비후끊김관측0·각예측1/계획1/서버제출관측1을확인했다. A1사람[0,8]정답1판·A2연못[]/B1나무[]오답timeout2판은재사용기능검사이며정확도1/3이나40%달성아니다.
- 실제계획ACK0.360/0.375/0.469초,사진9장다운로드1.500/2.797/1.937초다. 예정250ms간격1표본·실제타일HTTP0표본을구분했고과거API762~957ms와예정시각을직접성능비교하지않는다. 로컬고정API브라우저9사진로드/4체크/읽기전용/넘침0은실제ML·OS·250ms렌더링검사가아니다. 첫하네스409회차경합을고친새QA방에서정상완료했으며불완전영역캡처파일은제거했다.
- 버전11 commit `8755f3c852c555ac2637c47a85bd4e3cedac8d0e`, saved `appgprj_6ade37995018819184a42c88bb0fde7c~appgver_0ef517f5604c8191b1e96654ef95eea5`, deployment `appgdep_6ae065686ac88191a8ea3c01f755ce6a`, 환경revision4로게시succeeded다. 관리자키만동일권한갱신·메모리/stdin전용,owner/도메인/공개범위/기존사진/모델을유지했다. 최종HTTPS·PC가동·문서점검확정은STATUS를따른다.
- 다음은실제운영컴퓨터배치/네트워크/장시간반복리허설·충분한독립품질/40%·ONNX/Pi/legacy OS다. 현재학교최종평가계획은제외했다. 아래13개전체본문을분담재독·갱신하고내용변경없는문서에도검토를기록했다. 과거수치와당시정책은이력으로보존하며새Markdown은없다.

### 이번에 읽고 갱신한 전체 Markdown (13개)

'''+''.join('- '+item+'\n' for item in inventory)+'\n'
path=root/'docs/CHANGELOG.md';text=path.read_text(encoding='utf-8').replace(marker,marker+'\n'+log,1)
text=review(text,'0.25초 제한','통신최적화의일정/측정·사진22추가/46운영·학교행사제외·v11배포/실제CUDA/서버사진검사를구분해기록했다. 관리13개전체본문을재독갱신했으며모델/정답률조작0과미완료실기기/품질경계를유지한다. 최종문서명령과운영PC가동은STATUS정본이다.')
path.write_text(text,encoding='utf-8')
print('Updated five root-managed documents for scheduled selections and public bank expansion.')
