# Lotto Strategy Simulation Service

## 기능
- 로또 6/45 과거 회차 데이터 SQLite 적재/갱신
- 매주 크론(스케줄러) 기반 자동 동기화
- 전략 기반 게임 생성
  - `low_overlap_random` (기본): 가능한 한 중복을 줄인 랜덤 조합
  - `uniform_random`: 단순 무작위 조합
- 각 게임별 과거 회차 당첨 통계(1~5등) 계산 및 저장
- FastAPI 기반 API 제공
- Docker 구성(웹포트: 8645)

## 프로젝트 구조
- `app/main.py` : FastAPI 앱 및 API 라우트
- `app/services/crawler.py` : 동행복권 결과 페이지 파싱 및 엑셀 다운로드
- `app/services/excel_parser.py` : 엑셀 파싱
- `app/services/sync_service.py` : 주간 동기화 오케스트레이션
- `app/services/strategies.py` : 번호 생성 전략
- `app/services/evaluator.py` : 회차별 등수 계산
- `app/db.py` : SQLite 저장소 관리
- `app/cli.py` : 동기화 CLI
- `app/scheduler.py` : 매주 일요일 09:00 Asia/Seoul 주기 동기화

## 데이터 동기화 규칙
- 매 실행시 최신 회차를 확인
- 항상 엑셀(`lt645/excelDown.do`)로 1회차~최신회차 구간을 내려받아 파싱 시도
- 엑셀 파싱 실패 시 같은 구간을 API로 보조 조회
- DB에 존재하지 않는 회차는 Insert, 값이 변경된 경우 Update, 동일값은 Skip

## 실행 방법 (Docker)

### 1) 환경 구성
```bash
cp .env.example .env  # 없으면 환경변수 직접 사용
```

### 2) 빌드
```bash
docker compose build
```

### 3) 실행
```bash
docker compose up -d
```

- 웹 API: `http://localhost:8645`
- 헬스체크: `http://localhost:8645/health`
- API 스펙(자동 생성) 참고: `/docs`

### 수동 동기화
```bash
docker compose exec web python -m app.cli sync
```

### 게임 생성 예시
```bash
curl -X POST http://localhost:8645/api/games \
  -H 'Content-Type: application/json' \
  -d '{"game_count":5,"strategy":"low_overlap_random","seed":42}'
```

## 엔드포인트
- `POST /api/sync` : 동기화 실행
- `GET /api/draws` : 회차 조회 (`start_no`, `end_no` 쿼리 지원)
- `POST /api/games` : 게임 생성 및 평가
- `GET /api/games` : 게임 실행 이력
- `GET /api/games/{id}` : 게임 상세(추가 파라미터 `include_hits=true` 가능)
- `GET /api/sync/runs` : 동기화 이력

## 주의
- 웹사이트 파싱 정책에 따라 엑셀 구조가 변경되면 파서 튜닝 필요
- 사이트 과도 호출을 방지하기 위해 배치 주기(일주일 1회)를 권장
