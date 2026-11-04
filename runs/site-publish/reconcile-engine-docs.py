from pathlib import Path

fixes = {
    'SETUP': [
        ('`gpuReservationSupported`는 엔진 protocol2 보고 여부이며 물리 자원 검증이나 화면9장 로딩의 보증이 아닙니다.', '`gpuReservationSupported`와 `imageBarrierSupported`는 지원 규약 보고이며 물리 자원 검증이나 화면9장 로딩의 보증이 아닙니다. 새 출발은 protocol3와 세 역할의 실제 사진 준비가 필요합니다.'),
        ('자원 차례에 공통 카운트다운→사람·AI 동시 시작→공개 RGB 추론→GPU 해제', '자원 차례에 세 역할9사진 준비→공통 카운트다운→사람·AI 동시 시작→캐시 RGB 추론→GPU 해제'),
        ('PC의 Python urllib 요청 경로는 HTTP/1.1을 TLS/TCP로 전송하지만', '이전 urllib 읽기 확인은 HTTP/1.1이었으며 현재 PC는 표준 http.client의 HTTP/1.1 연결을 재사용하지만'),
    ],
    'ARCHITECTURE': [
        ('D1 batch에서 딱 한 round와2초 뒤 공통 startAt을 만든다.', 'D1 batch에서 딱 한 round의 loading을 만들고 세 역할의 사진 준비를 확인한 뒤2초 공통 startAt을 확정한다.'),
    ],
    'INTEGRATION': [
        ('새 queue에는 protocol2 지원도 필요하다.', '새 queue에는 protocol3 사진 준비 지원도 필요하다.'),
        ('봇 브라우저는 선택·준비·제출·next 권한이 없다.', '봇 브라우저는 자기 사진 준비 ACK만 할 수 있고 엔진 준비·선택·제출·next 권한이 없다.'),
        ('PC 원격 실행기의3모델 로드와 숨김 입력 대기를 확인한 뒤', 'PC 원격 실행기의3모델 로드·합성 RGB 예열과 숨김 입력 대기를 확인한 뒤'),
        ('경기 전 GPU 예약 대기→자원 차례의 공통 카운트다운→사람·AI 동시 시작→공개 RGB 추론 후 GPU 해제', '경기 전 GPU 예약 대기→자원 차례에 세 역할9사진 준비→공통 카운트다운→사람·AI 동시 시작→캐시 RGB 추론 후 GPU 해제'),
    ],
}
root = Path(__file__).resolve().parents[2]
for name, pairs in fixes.items():
    path = root / 'docs' / (name + '.md')
    text = path.read_text(encoding='utf-8')
    for old, new in pairs:
        text = text.replace(old, new)
    if '같은 창의 배경 탭은 준비 완료를 보류한다.' not in text:
        text = text.replace('브라우저는 숨긴 동일9개 이미지 노드를 실제로 디코딩하고 PC는9개 RGB를 최대3개 병렬로 받아 준비한다.',
                            '브라우저는 숨긴 동일9개 이미지 노드를 실제로 디코딩하고 PC는9개 RGB를 최대3개 병렬로 받아 준비한다. 인간과 AI 표시 창은 공통 출발까지 둘 다 앞에 보이는 상태로 두며, 같은 창의 배경 탭은 준비 완료를 보류한다.')
    if '0004_amazing_namora.sql' not in text:
        text = text.replace('검증 스크립트 `scripts/verify_continuous_booth.py`는',
                            '사진 준비에는 추가 migration `0004_amazing_namora.sql`이 round의 준비 번호/만료 시각/세 역할 준비 플래그5열을 더한다. 기존0000~0003은 변경하거나 다시 적용하지 않는다. 실제 로컬/운영 적용은 STATUS를 확인한다.\n\n검증 스크립트 `scripts/verify_continuous_booth.py`는', 1)
    path.write_text(text, encoding='utf-8')
print('Reconciled 3 current protocol/visibility descriptions.')
