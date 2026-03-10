# Notion 시각화 가이드 — 상세 참조 문서

## 📌 실전 Use Cases

---

### Use Case 1: 팀 스프린트 현황 칸반 보드

**상황:** 개발팀의 Notion 스프린트 DB를 칸반으로 시각화

**사용자 요청 예시:**
> "우리 팀 스프린트 DB 칸반으로 보여줘"
> "https://notion.so/... 이 DB 상태별로 정리해줘"

**Notion DB 구조 예시:**
```
DB 이름: Sprint Board
속성:
  - Name (title): 작업명
  - Status (select): 백로그 | 진행중 | 검토중 | 완료
  - Assignee (person): 담당자
  - Priority (select): 높음 | 중간 | 낮음
  - Due Date (date): 마감일
  - Story Points (number): 포인트
```

**Claude 처리 흐름:**
```
1. notion_query_database → 전체 항목 조회
2. Status 속성 값 추출 → 칸반 컬럼 생성
3. Priority → 배지 색상 매핑 (높음:빨강, 중간:노랑, 낮음:초록)
4. Due Date → D-day 계산 표시
5. React 칸반 컴포넌트 렌더링
```

**출력:** React `.jsx` 칸반 보드 (컬럼별 카드, 우선순위 배지, 담당자 표시)

---

### Use Case 2: 프로젝트 로드맵 Gantt 차트

**상황:** 분기별 프로젝트 일정을 Gantt 차트로 시각화

**사용자 요청 예시:**
> "Q1 로드맵 페이지 Gantt로 만들어줘"
> "프로젝트 일정 DB 타임라인으로 보여줘"

**Notion DB 구조 예시:**
```
DB 이름: Q1 Roadmap
속성:
  - Project (title): 프로젝트명
  - Phase (select): 기획 | 개발 | 테스트 | 배포
  - Start Date (date): 시작일
  - End Date (date): 종료일
  - Owner (person): 담당팀
  - Progress (number): 진행률 %
```

**Claude 처리 흐름:**
```
1. notion_query_database → 모든 프로젝트 조회
2. Phase 속성 → Gantt 섹션 그룹핑
3. Start/End Date → 기간 계산
4. Progress → 완료 표시 스타일
5. Mermaid gantt 차트 생성
```

**출력:** Mermaid `.mermaid` Gantt 차트

---

### Use Case 3: 회의록 페이지 마인드맵

**상황:** 브레인스토밍 회의록을 구조화된 마인드맵으로 변환

**사용자 요청 예시:**
> "어제 회의록 마인드맵으로 정리해줘"
> "이 페이지 아이디어들 마인드맵으로 보여줘"

**Notion 페이지 구조 예시:**
```
# 신제품 아이디어 회의 (2026.02.20)

## 타겟 시장
- B2B 소프트웨어
  - 중소기업
  - 스타트업
- B2C 앱
  - MZ세대

## 핵심 기능
- AI 자동화
  - 문서 처리
  - 데이터 분석
- 협업 도구
  - 실시간 편집
  - 알림 시스템

## 출시 전략
- MVP 우선 출시
- 베타 테스터 모집
```

**Claude 처리 흐름:**
```
1. notion_get_page + notion_get_block_children → 페이지 블록 조회
2. H1/H2/H3 → 마인드맵 계층 구조 파악
3. 글머리 기호 목록 → 말단 노드 변환
4. Mermaid mindmap 생성
```

**출력:** Mermaid `.mermaid` 마인드맵

---

### Use Case 4: 매출 데이터 통계 대시보드

**상황:** 월별 매출 DB를 차트 대시보드로 시각화

**사용자 요청 예시:**
> "매출 DB 차트로 만들어줘"
> "분기별 실적 시각화해줘"

**Notion DB 구조 예시:**
```
DB 이름: Monthly Revenue
속성:
  - Month (title): 월
  - Revenue (number): 매출액
  - Expenses (number): 지출액
  - Profit (formula): 수익
  - Channel (select): 온라인 | 오프라인 | 파트너
  - Growth Rate (number): 성장률 %
```

**출력:** React + Recharts 복합 대시보드
- Bar Chart: 월별 매출/지출 비교
- Line Chart: 성장률 추이
- Pie Chart: 채널별 매출 비율

---

### Use Case 5: 조직도 / 관계도

**상황:** 팀 구조 DB 또는 Relation 속성 시각화

**사용자 요청 예시:**
> "팀 구조 조직도로 보여줘"
> "이 DB 관계 다이어그램 그려줘"

**출력:** Mermaid graph 조직도 또는 관계 다이어그램

---

## 🎨 색상 팔레트 가이드

시각화 시 일관된 색상 체계 사용:

```css
/* 상태 색상 */
--color-todo:       #E8E8E8;  /* 회색 - 예정 */
--color-inprogress: #D3E5FF;  /* 파랑 - 진행중 */
--color-review:     #FFF3CC;  /* 노랑 - 검토중 */
--color-done:       #D4EDDA;  /* 초록 - 완료 */
--color-blocked:    #FFD5D5;  /* 빨강 - 블로킹 */

/* 우선순위 색상 */
--priority-high:    #FF4444;
--priority-medium:  #FF8C00;
--priority-low:     #44BB44;
```

---

## ⚡ 빠른 참조: Notion MCP 도구 목록

| MCP 도구 | 용도 | 필요 파라미터 |
|---------|------|------------|
| `notion_search` | 페이지/DB 검색 | query (키워드) |
| `notion_get_page` | 페이지 내용 조회 | page_id |
| `notion_query_database` | DB 항목 목록 조회 | database_id |
| `notion_get_block_children` | 하위 블록 조회 | block_id |

---

## 🔧 시각화 유형 빠른 선택 가이드

```
데이터 유형에 따른 추천:

"단계/순서가 있다"     → 플로우차트 (Mermaid flowchart)
"계층/분류가 있다"     → 마인드맵 (Mermaid mindmap)
"날짜가 있다"          → Gantt / 타임라인 (Mermaid gantt)
"상태(Status)가 있다"  → 칸반 보드 (React)
"숫자 데이터가 있다"   → 차트 (React + Recharts)
"관계(Relation)가 있다" → 관계도 (Mermaid graph)
"갤러리/목록이다"      → 카드 그리드 (HTML)
"복합 DB다"            → 대시보드 (React 복합)
```
