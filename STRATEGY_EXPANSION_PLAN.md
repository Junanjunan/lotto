# Lotto 확장 기획 v2

작성일: 2026-03-04  
데이터 기준: `draws` 1~1213회차 (`2002-12-07` ~ `2026-02-28`)  
코드 기준: 현재 `main` 브랜치

## 0) 핵심 결론

1. 현재 서비스는 생성 엔진 자체는 안정적이지만, 유저가 체감하는 선택지가 부족하다.
2. 유저가 실제로 좋아하는 방향은 "복잡한 수학"보다 "쉽게 이해되는 룰 + 비교 + 저장/재사용"이다.
3. 바로 효과가 큰 우선순위는 아래 4개다.
   - `balanced_quickpick`(기본 전략)
   - 전략 비교 모드(동시 실행/동시 비교)
   - 통계 탭(번호/구간/합계/간격)
   - 프리셋/북마크(재사용)

## 1) 조사 방법

### 1.1 코드/구조 조사
- 전략 엔진: `app/services/strategies.py`
- 평가 엔진: `app/services/evaluator.py`
- API: `app/main.py`
- 스키마: `app/schemas.py`
- UI: `app/static/index.html`

### 1.2 데이터 조사
- 로컬 DB(`data/lotto.db`) 실측 통계 사용
- 확인 테이블:
  - `draws`: 1213건
  - `games`: 28건
  - `game_sets`: 345건
  - `game_hits`: 31,774건
  - `sync_runs`: 6건

### 1.3 사용자 관점 조사 프레임
- 로또 유저가 선호하는 UX 패턴을 다음 3축으로 정리
  - 이해 가능성: 왜 이런 번호가 나왔는지 설명 가능해야 함
  - 통제감: 룰을 켜고 끌 수 있어야 함
  - 재사용성: 저장/복제/비교가 쉬워야 함

## 2) 데이터 인사이트 (실측)

### 2.1 분포 핵심

| 항목 | 결과 |
|---|---|
| 회차 수 | 1213 |
| 번호합 평균 | 138.25 |
| 번호합 중앙값 | 138 |
| 번호합 p10 / p90 | 98 / 177 |
| 스팬(`max-min`) 평균 | 32.70 |
| 연속수 1쌍 이상 비율 | 51.69% |
| 홀짝 2:4~4:2 비율 | 82.44% |
| 고저(23 기준) 2:4~4:2 비율 | 80.38% |
| 끝수 쏠림 방지(`max<=2`) 비율 | 91.67% |

### 2.2 빈도 인사이트

- 메인 번호 최다 출현 Top 5: `34(181)`, `27(179)`, `12(177)`, `13(174)`, `33(172)`
- 메인 번호 하위 Top 5: `9(133)`, `22(141)`, `32(141)`, `23(146)`, `41(147)`
- 현재 미출현 회차 긴 번호 Top 5: `14(29회)`, `19(20회)`, `13(19회)`, `34(18회)`, `15(17회)`

### 2.3 제약 조합 난이도 인사이트

아래 비율은 과거 회차에서 동시에 성립한 비율이다.

| 제약 묶음 | 성립 비율 |
|---|---|
| `balanced_odd_even + balanced_high_low + sum(105~175) + last_digit_max<=2 + span(22~42) + consecutive_pairs<=2` | 49.55% |
| 위 조건 + `zone_coverage >= 4` | 36.27% |
| 위 조건 + `high(32~45) >= 2` | 25.47% |

해석:
- 기본 추천 전략은 성립 비율이 30~55% 사이여야 생성 실패율이 낮다.
- 20%대 제약 묶음은 재시도/완화 로직이 반드시 필요하다.

## 3) 유저가 좋아할 전략 카탈로그 (상세)

## 3.1 우선 도입 전략 8개

| 전략 ID | UI 라벨(제안) | 유저 가치 | 구현 난이도 | 우선순위 |
|---|---|---|---|---|
| `balanced_quickpick` | 균형 퀵픽 | 기본으로 쓰기 쉬움 | 낮음 | P0 |
| `zone_spread` | 구간 분산 | 번호대 쏠림 방지 | 낮음 | P0 |
| `pair_tuner` | 연속수 튜너 | 연속수 취향 반영 | 낮음 | P0 |
| `sum_span_guard` | 합/스팬 가드 | 극단 조합 방지 | 낮음 | P0 |
| `hot_focus` | 최근 강세 중심 | 최근 출현 중심 선택 | 중간 | P1 |
| `cold_focus` | 미출현 중심 | 오래 안 나온 번호 중심 | 중간 | P1 |
| `hot_cold_mix` | 강세+미출현 혼합 | 편향 완화 + 재미 | 중간 | P1 |
| `portfolio_diversify_v2` | 중복 최소 강화 | 여러 게임 포트폴리오 최적화 | 중간 | P1 |

## 3.2 전략별 상세 설계

### A) `balanced_quickpick` (새 기본값)
- 의도: 설명 가능한 기본 전략 제공
- 기본 룰:
  - 홀짝 2~4
  - 고저(23 기준) 2~4
  - 합 105~175
  - 스팬 22~42
  - 끝수 최대 2개
  - 연속쌍 최대 2쌍
- 기대 효과:
  - 과거 성립률 기준 약 49.55%라 생성 안정성 높음
- 적용:
  - `app/services/strategies.py`에 별도 전략 함수 추가
  - 기존 옵션 조합을 내부 default로 캡슐화

### B) `zone_spread`
- 의도: 숫자 구간 분산 강화
- 기본 룰:
  - 5개 구간(1~10, 11~20, 21~30, 31~40, 41~45)
  - 최소 4개 구간 커버
- 데이터 근거:
  - 과거 회차에서 구간 커버 4 이상 비율: 64.14%
- 적용:
  - 신규 옵션 `zone_coverage_min` (`0~5`)
  - UI는 슬라이더 또는 단계 버튼

### C) `pair_tuner`
- 의도: 연속수 취향 반영
- 모드:
  - `none` (연속쌍 0)
  - `one_or_two` (1~2쌍)
  - `any` (제약 없음)
- 데이터 근거:
  - `none`: 48.31%
  - `one_or_two`: 49.96%
- 적용:
  - 옵션 bool 대신 enum으로 확장

### D) `sum_span_guard`
- 의도: 너무 좁거나 너무 극단적인 조합 배제
- 기본 파라미터:
  - `sum_min=105`, `sum_max=175`
  - `span_min=22`, `span_max=42`
- 적용:
  - 기존 `sum_band_100_170`를 일반화하여 범위형 옵션으로 전환

### E) `hot_focus`
- 의도: 최근 `N`회차 자주 나온 번호 가중
- 권장 파라미터:
  - `window=30`
  - `weight_alpha=1.4`
- 구현:
  - `app/services/strategy_stats.py`에서 최근 빈도 캐시
  - weighted sample로 번호 선택

### F) `cold_focus`
- 의도: 최근 `N`회차 덜 나온 번호 가중
- 권장 파라미터:
  - `window=30`
  - `weight_alpha=1.4`
- 구현:
  - `hot_focus`와 동일 인프라 재사용
  - 가중치만 반대로 적용

### G) `hot_cold_mix`
- 의도: 과도한 편향 완화
- 권장 파라미터:
  - `mix_ratio_hot=0.5`, `mix_ratio_cold=0.5`
- 적용:
  - `hot`/`cold` 풀에서 교차 샘플링

### H) `portfolio_diversify_v2`
- 의도: 여러 게임 생성 시 내부 중복 최소화
- 기본 룰:
  - 게임간 번호 overlap 페널티 강화
  - 특정 번호 과사용 soft cap 적용
- 적용:
  - 기존 `usage` 점수 함수 개선

## 4) 전략 외에 추가하면 좋은 기능 (상세)

## 4.1 즉시 체감 기능

1. 전략 비교 실험실 (`Strategy Lab`)
- 한 번에 3개 전략 동시 실행
- 비교 항목:
  - 총 히트
  - 등수 분포
  - 전략 다양성 점수(게임간 중복률)
- 구현:
  - 신규 `POST /api/games/compare`
  - UI에 비교 테이블 + 카드

2. 통계 대시보드 탭
- 항목:
  - 번호 빈도 Top/Bottom
  - 구간 점유율
  - 합계/스팬 분포
  - 미출현 회차 랭킹
- 구현:
  - 신규 `GET /api/stats/lottery`
  - UI 히스토그램/배지 렌더링

3. 프리셋/북마크
- 전략/옵션 조합 저장
- 생성 결과의 특정 게임 북마크 후 재실행
- 구현:
  - 1차는 `localStorage`
  - 2차는 서버 저장 API 확장

## 4.2 다음 단계 기능

1. 회차 알림 + 결과 자동 확인
- 다음 추첨 후 저장된 북마크 조합 자동 대조
- 알림 방식: 인앱 배지, 추후 이메일/푸시 확장

2. 예산/구매 계획 도우미
- 주당 구매 게임 수 설정
- 전략별 배분 추천(예: 균형 50%, 실험 50%)

3. 설명 품질 표준화
- 각 전략에 공통 카드 제공:
  - "이 전략이 하는 일"
  - "이 전략이 보장하지 않는 것"
  - "추천 사용자"

## 5) 적용 설계 (파일 단위)

## 5.1 백엔드

### A. 스키마 확장 (`app/schemas.py`)
- `StrategyOptions` 신규 키 추가(초기)
  - `zone_coverage_min: int | None`
  - `consecutive_pair_mode: str` (`any|none|one_or_two`)
  - `sum_min: int | None`, `sum_max: int | None`
  - `span_min: int | None`, `span_max: int | None`
  - `hot_cold_window: int | None`
  - `hot_cold_alpha: float | None`
- 하위 호환:
  - 기존 bool 키는 유지
  - 신규 키 미입력 시 기존 동작 보장

### B. 통계 서비스 신규 (`app/services/strategy_stats.py`)
- 책임:
  - 최근 N회차 빈도
  - 미출현 길이(miss streak)
  - 구간/합계 분포 계산
- 캐시:
  - 프로세스 메모리 캐시 + draws max_no 기준 무효화

### C. 전략 엔진 확장 (`app/services/strategies.py`)
- `STRATEGIES` 확장
- enum/range 옵션 normalize 추가
- 제약 실패 시 fallback 정책:
  - 최대 재시도 초과 시 제약 완화 단계 적용

### D. API 확장 (`app/main.py`)
- `/meta`에 전략 카탈로그/옵션 스키마 추가
- `POST /api/games/compare` 추가
- `GET /api/stats/lottery` 추가

## 5.2 프론트엔드 (`app/static/index.html`)

1. 하드코딩 제거
- 전략/옵션 렌더링을 `/meta` 동적 기반으로 전환

2. 탭 구조 확장
- `전략 게임 생성`
- `전략 비교 실험실` (신규)
- `통계 대시보드` (신규)
- `번호 6개 직접 검증` (기존 유지)

3. 프리셋/북마크 UX
- `프리셋 저장`, `프리셋 불러오기`
- 결과 카드의 `북마크` 버튼

## 6) API 제안 스펙 (상세)

### 6.1 `GET /meta` 확장

```json
{
  "strategy_catalog": [
    {
      "id": "balanced_quickpick",
      "label": "균형 퀵픽",
      "description": "분포형 제약을 기본 적용한 설명 가능한 기본 전략",
      "difficulty": "easy"
    }
  ],
  "strategy_option_schema": {
    "zone_coverage_min": {"type":"int","min":0,"max":5,"default":0},
    "consecutive_pair_mode": {"type":"enum","values":["any","none","one_or_two"],"default":"any"},
    "sum_min": {"type":"int","min":21,"max":260,"default":105},
    "sum_max": {"type":"int","min":21,"max":260,"default":175}
  }
}
```

### 6.2 `POST /api/games/compare` (신규)

```json
{
  "game_count": 5,
  "seed": 42,
  "strategies": [
    {"strategy":"balanced_quickpick","options":{}},
    {"strategy":"hot_focus","options":{"hot_cold_window":30}},
    {"strategy":"portfolio_diversify_v2","options":{}}
  ]
}
```

### 6.3 `GET /api/stats/lottery` (신규)

```json
{
  "evaluated_until": 1213,
  "number_frequency": [{"number":34,"count":181}],
  "zone_share_pct": {"1-10":21.67,"11-20":23.15,"21-30":21.50,"31-40":22.78,"41-45":10.90},
  "sum_stats": {"p10":98,"median":138,"p90":177},
  "miss_streak_top": [{"number":14,"miss_draws":29}]
}
```

## 7) 테스트/품질 계획

1. 단위 테스트 (`tests/test_strategies.py`)
- 신규 전략별:
  - 개수/중복/범위 검증
  - 제약 충족 검증
  - seed 고정 재현성 검증

2. 통계 테스트 (`tests/test_stats.py` 신규)
- 빈도/구간/미출현 계산 검증
- draws 변경 시 캐시 무효화 검증

3. API 테스트
- `/meta` 스키마 회귀 검증
- `/api/games/compare` 정상/오류 케이스 검증
- `/api/stats/lottery` 응답 필드 검증

4. 성능 기준
- `game_count=5`, 전략 1개 생성 p95 < 400ms 목표
- 비교모드 3전략 p95 < 1.2s 목표

## 8) 단계별 실행 로드맵 (더 상세)

### Phase 1 (1~2일): P0 전략 + 메타 구조
- `balanced_quickpick`, `zone_spread`, `pair_tuner`, `sum_span_guard` 구현
- `/meta` 스키마 확장
- DoD:
  - 기존 API 완전 호환
  - 신규 전략 4개 생성 성공
  - 테스트 통과

### Phase 2 (2~3일): P1 전략 + 통계 API
- `hot_focus`, `cold_focus`, `hot_cold_mix`, `portfolio_diversify_v2`
- `strategy_stats.py` + `/api/stats/lottery`
- DoD:
  - window/alpha 파라미터 정상 반영
  - 통계 탭 API 준비 완료

### Phase 3 (2~3일): 비교 모드 + 프리셋
- `/api/games/compare`
- UI 비교 탭 + `localStorage` 프리셋
- DoD:
  - 3전략 동시 비교 가능
  - 프리셋 저장/복구 동작

### Phase 4 (선택): 북마크 서버 저장 + 알림
- 조합 북마크 서버 저장 API
- 추첨 후 자동 대조 배치

## 9) 리스크와 대응

1. 과도 제약으로 생성 실패
- 대응:
  - 제약 충족 실패 시 단계별 완화
  - UI에 실패 사유 명시

2. "예측력" 오해
- 대응:
  - 모든 전략 카드에 비보장 문구 표시
  - 과장 표현 금지

3. 성능 저하
- 대응:
  - 통계 캐시
  - 비교모드 병렬 실행

## 10) 지금 바로 착수 추천

1. `balanced_quickpick` + `zone_spread` 먼저 구현
2. `/meta`를 동적 스키마 기반으로 정리
3. `GET /api/stats/lottery` 최소 버전 추가
4. UI에 `통계` 탭과 `전략 비교` 탭 순차 추가

---

요약: 이번 v2 계획은 단순 전략 개수 증가가 아니라, "유저가 이해하고 반복 사용하게 만드는 구조"를 목표로 한다.  
핵심은 `설명 가능한 기본 전략 + 비교 + 통계 + 재사용`이며, 현재 코드 구조에서 부작용을 최소화하고 단계적으로 확장 가능하다.
