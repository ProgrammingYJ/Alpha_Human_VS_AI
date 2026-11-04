from pathlib import Path
path = Path(__file__).resolve().parents[2]/'web/alpha-arena/README.md'
text = path.read_text(encoding='utf-8')
text = text.replace('최신 속도 정책(2026-10-27):', '직전 속도 정책(2026-10-27):', 1)
marker = '최종 검토: 2026-10-27 (Asia/Pyongyang)\n'
note = '''
최신 통신 경로(2026-10-27): 기본 remote는 PC가 공개RGB에 실제 ML 추론을 한 번 끝낸 뒤 고정 타일 번호 전체를 `plan` 요청 한 번으로 보낸다. 서버가 수락한 시각 뒤500ms 표시 버퍼를 두고 첫 선택부터 **250ms 간격**으로 재생하고 마지막 선택 시각에 한 번 제출한다. 0개 예측도 바꾸지 않고 버퍼 종료 시0개를 제출한다. 매 타일의 상태GET·선택POST/ACK 왕복을 기다리지 않는다. GPU 예약은 이 요청 전에 이미 해제한다. 구형 서버는 기존 개별 선택/제출 경로를 유지한다.

봇 표시만 미래 ML 선택 일정(정답 정보 없음)을 받고 기존50ms 서버시계 tick으로 진행을 보간한다. 계획을 받은 진행중 봇 화면은500ms로 상태를 확인하고, 아직 계획 없는 진행중 봇만125ms로 조회한다. 인간/다른 단계는500ms다. 계획 수신이 늦으면 도래한 선택으로 따라잡고 서버 승리/종료 시각 이후 선택은 잘라낸다. 정확250ms 렌더링·네트워크 무지연을 보장하지 않으며 승패를 클라이언트가 추정하지 않는다. 수락한 계획은 PC가 끊겨도 서버에서 계속 진행하지만 생존 표시는 실제 상태를 보존한다.

최신 사진 정책: 사용자 결정으로 송내고등학교 사진은 이번 부스에 사용하지 않는다. 인터넷 사진 중 출처/공개 사용 조건과 명확한 조건 라벨을 검토한 문제은행을 사용한다. 기존24장과 이번 추가분의 실제 등록 수·검증은 상위 STATUS가 정본이다. 모델 예측에 맞춰 사진을 고르거나 사진에 맞춰 모델을 재튜닝하지 않는다.
'''
text = text.replace(marker, marker+'\n'+note, 1)
text = text.replace('진행 중 remote AI 표시만125ms 폴링하고 인간 화면·대기/결과 등은500ms를 유지한다.', '계획 없는 진행 중 remote AI 표시만125ms 폴링하고 계획 수신 후·인간 화면·대기/결과 등은500ms를 유지한다.', 1)
text = text.replace('진행 중 remote AI 표시만125ms, 인간 화면과 그 외 단계는500ms 폴링하며 진행 중 요청은 겹쳐 보내지 않는다.', '계획 없는 진행 중 remote AI 표시만125ms, 계획 수신 뒤와 인간 화면/그 외 단계는500ms 폴링하며 진행 중 요청은 겹쳐 보내지 않는다.', 1)
text = text.replace('PC가 HTTPS로 보낸 선택을 서버가 최소0.25초 간격으로 수락하고 AI 표시 화면이 진행 중125ms·그 외500ms 폴링 및 네트워크 지연 후 표시한다.', 'PC가 HTTPS로 고정 예측을 한 번 보내면 서버 일정으로 최소0.25초 간격의 선택과 한 번 제출을 처리하고 AI 표시 화면은 이를 서버시계로 보간한다. 구형 서버의 개별 선택 전송은 호환 경로로 남는다.', 1)
text = text.replace('학교 사진은 문제·고정 후 최종 평가 전용이고 학습·튜닝에 사용하지 않는다. 현재 실제 학교 사진은 없다.', '사용자 최신 결정으로 학교 사진은 이번 부스 문제·학습·튜닝·평가에 사용하지 않는다.', 1)
text = text.replace('실제 적용·배포 결과는 상위 STATUS가 정본이고 실행 형식은 docs/SETUP.md를 따른다.', '고정 선택 계획에는 `drizzle/0003_colorful_cassandra_nova.sql`의 round nullable4열(indices/start/submit/private correctness)도 필요하다. 실제 적용·배포 결과는 상위 STATUS가 정본이고 실행 형식은 docs/SETUP.md를 따른다.', 1)
text = text.replace('ONNX·Pi·학교 최종 평가는 미완료다.', 'ONNX·Pi 검증은 미완료이며 학교 사진 최종 평가는 최신 결정으로 이번 부스 범위에서 제외한다.', 1)
text = text.replace('진행 중 remote 봇 표시는125ms, 그 외 화면/단계는500ms 폴링한다.', '계획 없는 진행 중 remote 봇 표시는125ms, 계획 수신 뒤와 그 외 화면/단계는500ms 폴링한다.', 1)
section = '''
## 고정 ML 선택 계획 API

`POST /api/rooms/{id}/engine`의 `action:"plan"`은 engine만 `{roundId,selectedIndices:[0..8]}`로 요청한다. 중복 없는0~9개 타일을 순서 그대로 보존하며 실제 정답 개수를 채우지 않는다. 새 계획은 playing·현재 round·15초 이내 준비된 엔진·아직 선택/제출하지 않은 상태에서만 CAS로 수락한다. 응답은 `{plan:{roundId,selectedIndices,startAt,intervalMs:250,submitAt},serverNow}`이고 상태/정답/라벨은 포함하지 않는다. 같은 순서의 재전송은 결과 뒤에도 동일 일정으로 ACK하며 변경 계획은 `plan_conflict`로 거부한다. 계획이 있는 판의 개별 선택/제출은 `plan_active`다. 종료 시각 이전에 끝낼 수 없는 계획은 `plan_too_late`로 거부한다.

정답 여부는 서버만 계산해 round에 비공개로 저장한다. 조회 또는 인간 제출이 예정 제출을 정산하며, 인간 채점 트랜잭션과 SQL 자체가 이미 도래한 완벽한 봇 제출보다 늦은 인간 승리를 막는다. 같은 밀리초 경계에서는 예정 봇 제출이 우선한다. 도래 전 인간이 먼저 완벽하게 제출하면 인간이 이기고 나머지 재생은 중단한다. 오답 계획은 한 번의 제출 시각/오답만 기록하고 인간의 수정/재제출을 막지 않는다. 시간초과 경계의 봇 승리는 금지하며 다음 참가자의 새 round는 계획 없이 시작한다. 인간 응답에는 계획과 미래 선택을 제공하지 않는다. 이 서버 재생은 실제 PC 모델이 이미 낸 결과를 실행하는 결정적 어댑터다.

Node의 `server/selection-plan.test.mjs`는 경계·CAS·단일 승자·privacy·구형 입력과의 경합·다음 회차를 검증한다. `server/selection-plan.http.test.mjs`는 숨긴 관리자 키를 사용하는 localhost 전용 서버 채점 검사이며 실제 ML 엔진과 분리한다. 여기의 기대 정답은 이 테스트 프로세스에만 존재하고 모델/봇에 제공하지 않는다. 배포·실제 PC 및 브라우저 검증·사진 등록 결과는 STATUS를 따른다.
'''
text = text.replace('## 사진 준비', section+'\n## 사진 준비', 1)
head, old = text.rsplit('\n이번 작업 검토:', 1)
text = head+'\n이전 작업 검토(0.25초 제한):'+old
text = text.rstrip()+'\n\n이번 작업 검토: 전체 본문을 다시 읽고 사용자 통신 지연 개선 요청에 따라 고정 ML 선택 계획·500ms 버퍼/250ms 재생·최소 ACK·원자 승자/시간초과·미래 선택 비공개·계획 수신후500ms 폴링과 구형 경로를 반영했다. 학교 사진은 최신 결정으로 이번 부스에서 사용하지 않는다. 과거 실측은 보존하며 새 사진/게시/PC/브라우저의 실제 검증 정본은 STATUS다. 모델/임계값/40%/ONNX/Pi 경계를 유지한다.\n'
path.write_text(text, encoding='utf-8')
print('Reviewed and updated web README for server-timed fixed ML plans and no-school booth photos.')
