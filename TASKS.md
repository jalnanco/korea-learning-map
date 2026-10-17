# TASKS — korea-learning-map (구 science-taxonomy-kr)

- [x] 참고 데이터 라이선스 판정(Marble ODbL 제외 · 프랑스판 MIT · 한국 초등 MCP MIT)
- [x] 과학과 원문 PDF 수집·성취기준 실측(약 480)
- [x] 설계 v0.1(과학) → v0.2(전 교과·상식·다시 배우기·무료 배포)
- [ ] 결정: 레포 이름·계정 · 첫 목표 10개 (DESIGN §9)
- [x] v0 원문층 (2026-10-18)
  - [x] NCIC 스캔 → `sources.json`(2022-33호 별책 21개, 별책별 최신 게시본)
  - [x] 원문 = HWP 본문 직접 파싱(`hwp_text.py` — PDF 는 낱말 중간 줄바꿈으로 「탐 색한다」) · 쪽 번호·대조 = PDF
  - [x] 수식 개체 복원(EQEDIT → `text` 읽기용 기호 + `math` 원본) · 표 칸 깊이로 단원 메모 거르기 · 과목명·과목 구분·학년군
  - [x] 원문 오기 보정 `exceptions.json`(코드만 · 문장은 손대지 않음)
  - [x] 관문 `check_v0.py` PASS — 성취기준 3,844 · 해설 2,404 · 단원 메모 3,825 · 수식 18 · PDF 대조 불일치 0 · 정규식 밖 코드 꼴 0
  - [x] 초등 MCP 정답지 620 대조: 완전일치 493 · 공백만 다름 32(정답지 쪽 오류) · 표 섞임 82 · 해설 오인 4 · 없음 9(2026 개정 `2건` — 고정판 밖)
- [x] v0 MCP `mcp/`: stdio `search_topic`·`get_topic` · `node test.js` PASS · 패키지 801kB
- [x] GitHub 공개 jalnanco/korea-learning-map · npm korea-learning-map-mcp@0.0.1 (2026-10-18)
- [x] 총론 범교과 학습 주제 10개 원문 확인 → `cross_curricular.json` (성취기준 단위 언급은 적다 — 대부분 교과 「교수·학습」 절에 있음)
- [ ] 범교과 주제 ↔ 교과·과목 연결(교수·학습 절 원문 언급) — v1
- [ ] 결정: 2026 일부개정(초1~2 「건강」 등) 반영 여부 — 고정 시점(pin) 문제
- [ ] 문해교육 교육과정 라이선스 확인
- [ ] 과목 「성격」 문단의 과목 간 연계 문장(예: 지구시스템과학 ↔ 행성우주과학) 추출 — 과목 단위 선수관계 근거
- [x] 단원 노드 `units.json`(824 · 필수 285) + 원문 연계 `links.json`(490 · 선수 191 · 후속 127 · 관련 172 · 못 푼 이름 0) — 관문에 배치·간선·근거 검사 추가
- [x] MCP 0.0.2: `prerequisites`(대상별 묶음·근거 배열) · `relearn_path`(BFS, 기본 depth 2, `via`) · `common_sense` · 테스트 추가 PASS
- [ ] npm 0.0.2 publish(사용자 터미널 — 2FA)
- [ ] docs 교과 문서에 선수·후속 단원 링크
- [x] 학습 목록 docs/ — 필수 공통 목차(1,386) · 전체 지도 · 교과 17쪽 (2026-10-18)
- [ ] v1 과학 초3~중3 개념층 시범(중1-3 운동과 에너지 1묶음 → 틀 문구 관문)

## 메모
- 「생태전환 교육」은 범교과 10개 목록에 없지만 교과 원문에 125회 — 상식 층 후보로 따로 볼 것.
- 창체(별책 40)는 성취기준 코드가 없어 HWP 미수집.
- 재현: `python3 pipeline/extract_standards.py data/kr/sources.json corpus data/kr/standards.json > corpus/extract-report.json && python3 pipeline/check_v0.py data/kr/sources.json corpus data/kr/standards.json corpus/extract-report.json`
