# 광고 적용: 운영자가 해야 할 일

아래 항목은 계정/심사/도메인 소유권처럼 운영자만 할 수 있는 작업입니다.
코드 쪽(광고 슬롯, 런타임 스위치, 로더, 환경변수 연결)은 이미 반영되어 있습니다.

## 1) 광고사 선택
- `Google AdSense` 또는 `Kakao AdFit` 중 하나를 먼저 선택하세요.
- 초기 권장: AdSense 먼저 승인/안정화 후 AdFit 비교.

## 2) 계정/사이트 등록 및 심사
1. 광고사 콘솔에서 사이트를 등록합니다.
2. 서비스 도메인(실서비스 URL) 소유권 검증을 완료합니다.
3. 광고 심사를 통과할 때까지 대기합니다.

## 3) 광고 단위(슬롯) 발급
광고사 콘솔에서 아래 3개 슬롯에 대응하는 단위를 만드세요.
1. `top` : 상단 배너
2. `mid` : 중단 배너
3. `sticky` : 모바일 하단 고정

## 4) `.env` 값 입력
프로젝트 루트 `.env`에 아래처럼 입력하세요.

### AdSense 예시
```env
AD_PROVIDER=adsense
AD_ENABLED=true
AD_TEST_MODE=false
AD_STICKY_MOBILE_ONLY=true

ADSENSE_CLIENT_ID=ca-pub-xxxxxxxxxxxxxxxx
ADSENSE_SLOT_TOP=1234567890
ADSENSE_SLOT_MID=2345678901
ADSENSE_SLOT_STICKY=3456789012
```

### AdFit 예시
```env
AD_PROVIDER=adfit
AD_ENABLED=true
AD_TEST_MODE=false
AD_STICKY_MOBILE_ONLY=true

ADFIT_UNIT_TOP=DAN-xxxxxxxxxx
ADFIT_UNIT_MID=DAN-yyyyyyyyyy
ADFIT_UNIT_STICKY=DAN-zzzzzzzzzz
ADFIT_WIDTH_TOP=728
ADFIT_HEIGHT_TOP=90
ADFIT_WIDTH_MID=728
ADFIT_HEIGHT_MID=90
ADFIT_WIDTH_STICKY=320
ADFIT_HEIGHT_STICKY=100
```

## 5) `ads.txt` 배치 (중요)
1. `ads.txt`는 **도메인 루트**에서 접근 가능해야 합니다.
2. 예: `https://your-domain.com/ads.txt`
3. `/lotto/ads.txt`만 올리면 대부분 인증에 실패합니다.

## 6) 개인정보/광고 고지
1. 개인정보처리방침 페이지에 광고/쿠키/제3자 스크립트 내용을 명시하세요.
2. 필요 시 동의 배너(CMP)를 적용하세요.

## 7) 재배포
```bash
./rebuild_restart.sh
```

## 8) 확인 체크리스트
1. `GET /meta` 응답에서 `ads.enabled=true`와 공급사/슬롯 값이 보이는지 확인
2. 실제 페이지에서 상단/중단/모바일 하단 슬롯 노출 확인
3. 브라우저 콘솔에 광고 스크립트 오류가 없는지 확인
4. 광고사 콘솔에서 요청/노출 집계가 들어오는지 확인

## 9) 문제 발생 시 빠른 점검
1. `.env` 값 오탈자 (`ca-pub-`, `DAN-`) 확인
2. `docker compose` 환경변수 전달 여부 확인
3. 광고 심사 상태(승인/제한) 확인
4. 도메인 루트 `ads.txt` 접근 가능 여부 확인
