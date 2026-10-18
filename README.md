# korea-learning-map

한국 초·중·고 교육과정(2022 개정, 교육부 고시 제2022-33호)의 **전 교과 성취기준 3,844개를 원문 그대로** 구조화한 공개 데이터와, AI 가 이를 찾아 읽게 하는 로컬 MCP 서버.

목표는 「살면서 무엇을 상식으로 배우는가」와 「다시 배우려면 어디서부터 하나」를 누구나 원문 근거로 답할 수 있게 하는 것이다. 지금은 바탕인 **원문층**, 고시문이 직접 밝힌 **단원·과목 간 연계**, 그리고 **수학 초1~고1 · 과학 초3~중3 개념 지도**(개념 293개, 개념마다 셀프 체크)까지 있다([DESIGN.md](DESIGN.md)).

## 이렇게 묻는다

MCP 를 붙인 AI 에게 그냥 물으면, 아래 같은 원문 근거 답이 돌아온다(실제 도구 출력을 줄인 것).

**「분수 나눗셈이 헷갈려. 어디부터 다시 봐야 해?」** → `concept_path("분수 나눗셈")`

```text
목표  초5~6 분수의 곱셈과 나눗셈 (6수01-09 …)
1단계 초5~6 분수의 덧셈과 뺄셈   [제안] 분수 계산의 다음 단계
      초5~6 약수와 배수          [제안] 약분에 공약수를 쓴다
2단계 초3~4 분수의 덧셈과 뺄셈   [제안] 분모가 같은 경우에서 다른 경우로
      초3~4 세 자리 수 범위의 나눗셈 [제안] 나누어떨어짐으로 약수를 정한다
      … depth 3 이상에 더 있다(초1~2 자릿값까지)
```

**「고등학교 인수분해, 중학교 무엇과 이어져?」** → `concept_path("인수분해", proposals=false)` — 원문 간선만

```text
고1 인수분해 ← 중3 다항식의 곱셈과 인수분해   [원문]
  「다항식의 곱셈과 인수분해는 중학교에서 학습한 내용을 토대로 고등학교에서 추가된 내용을 이해하게 하고, …」
```

**「중학교 ‘기체의 성질’ 전에 뭘 배워?」** → `prerequisites("9과06-01")`

```text
선수  초3~4 과학 「여러 가지 기체」
  근거 「초등학교 3∼4학년군 ‘물체와 물질’, 중학교 1∼3학년군 ‘기체의 성질’과 연계된다.」 (고시 별책 9)
```

**「옴의 법칙이 이해가 안 돼. 전기 회로랑 대전은 알아.」** → `concept_path("옴의 법칙", known=["전기 회로","대전"])`

```text
목표  중1~3 옴의 법칙
  □ 전기 회로에서 전류를 모형으로 설명하고, 실험을 통해 저항, 전류, 전압 사이의 관계를 이끌어낼 수 있나요?
먼저  초5~6 전지의 직렬연결 → 중1~3 전압      [제안] 전지를 직렬로 이으면 전압이 커진다
      중1~3 전류                               [제안] 전압과 전류의 관계
      수학 중1 좌표평면과 그래프               [제안] 전압-전류 그래프가 정비례
      … 수학 쪽 사슬(정수와 유리수 · 대응 관계 등) 5개 더
      (전기 회로·대전은 known 이라 거기서 멈춘다)
```

[원문]은 고시문 문장이 직접 밝힌 연결이다. [제안]은 원문에 없는 개념 사이 화살표로, Claude 가 제안하고 Gemini 가 반박 심사한 뒤 판정한 것이다(심사 기록: `data/kr/concept_proposals.json`). 둘은 섞지 않고, `proposals=false` 로 원문만 볼 수 있다.

## 바로 보기

- **[모두가 배우는 것 — 필수 공통 목차](docs/필수-공통.md)**: 초1~고1 모든 학생이 배우는 성취기준 1,386개를 학년군·교과·단원으로
- **[수학 개념 지도](docs/수학-개념-지도.md)** · **[과학 개념 지도](docs/과학-개념-지도.md)**: 수학 99 · 과학 194 개념과 선수관계(원문 27 · 제안 385, 교과 간 5 포함)를 영역별 그림과 셀프 체크로
- **[배울 것 전체 지도](docs/README.md)**: 교과 × 학년군 3,844개, 교과별 문서로 원문·해설·학년 간 연계까지

## 들어 있는 것

| 파일 | 내용 |
|---|---|
| `data/kr/standards.json` | 성취기준 3,844개 — 코드·원문·학년군·교과·과목·단원·성취기준 해설·적용 시 고려 사항(학년 간 연계 문장 포함)·고시 별책·쪽 |
| `data/kr/units.json` | 단원 824개(필수 285) — 학년군·교과·과목·단원과 소속 성취기준 |
| `data/kr/links.json` | 연계 672개 — 단원 간 490(단원 메모 「…와 연계된다」) + 과목 간 182(고교 과목 「성격」 문단 「…를 심화⋅확장한 과목」 등). 선수·후속·관련과 근거 원문 문장, 추정 없음 |
| `data/kr/concepts.json` | 개념 293개 — 수학 99(초1~고1) · 과학 194(초3~중3, 범주 포함). 고시문 「내용 체계」 지식⋅이해 항목 이름 그대로, 개념마다 소속 성취기준 |
| `data/kr/concept_links.json` · `concept_proposals.json` | 개념 선수관계 — 원문 27(수학 해설·고려 사항·성격 문장 「중학교에서 학습한 …」) · 제안 385(수학 144 · 과학 241, 이유·Gemini 심사·판정 기록) |
| `data/kr/sources.json` | 원문 고시문 21개 별책의 NCIC 다운로드 주소와 sha256 |
| `data/kr/cross_curricular.json` | 총론의 범교과 학습 주제 10개 |
| `mcp/` | stdio MCP 서버 — `search_topic`(낱말 검색) · `get_topic`(원문·해설·출처) · `prerequisites`(선수·후속 단원) · `relearn_path`(다시 배우는 순서) · `concept_path`(수학·과학 개념 단위 경로 + 셀프 체크) · `common_sense`(필수 공통 단원) |
| `docs/` | 위 JSON 을 펼친 학습 목록 — `python3 pipeline/build_docs.py data/kr docs` 로 다시 만든다 |
| `pipeline/` | 고시문 HWP/PDF → JSON 추출기와 검증 관문(LLM 미사용) |

레코드 예:

```json
{ "id": "9과01-01", "grade": "중1~3", "unit": "과학과 인류의 지속가능한 삶",
  "text": "과학적 탐구 방법을 이해하고, 일상생활의 문제에 대한 과학적 해결 방안을 제안할 수 있다.",
  "notes": ["…"], "unitNotes": ["…와 연계된다.", "…"],
  "ref": "교육부 고시 제2022-33호 [별책 9]", "page": 46 }
```

## MCP 로 쓰기

```bash
claude mcp add korea-learning-map -- npx -y korea-learning-map-mcp
```

다른 MCP 클라이언트(Claude Desktop 등)는 설정에 다음을 넣는다.

```json
{ "mcpServers": { "korea-learning-map": { "command": "npx", "args": ["-y", "korea-learning-map-mcp"] } } }
```

「중학교에서 금융을 어디서 배워?」「분수 나눗셈은 몇 학년이야?」처럼 물으면 원문 성취기준과 출처 쪽수로 답한다. 「광합성을 다시 배우려면 어디부터?」는 `relearn_path` 가 고시문이 밝힌 선수 단원을 학년군 낮은 순으로 돌려준다. 수학·과학은 `concept_path` 가 개념 단위로 더 촘촘하게, 셀프 체크 물음과 함께 돌려준다. 네트워크·서버·API 키가 필요 없다.

## 다시 만들기

```bash
python3 pipeline/scan_ncic.py 2022 10003530 10003830 > corpus/ncic-2022-scan.tsv   # 게시본 목록
# sources.json 의 url·hwpUrl 로 corpus/pdf/<seq>.pdf · corpus/hwp/<seq>.hwp 를 받는다
python3 pipeline/extract_standards.py data/kr/sources.json corpus data/kr/standards.json > corpus/extract-report.json
python3 pipeline/extract_links.py data/kr corpus                                    # units.json · links.json
python3 pipeline/check_v0.py data/kr/sources.json corpus data/kr/standards.json corpus/extract-report.json   # PASS 여야 한다
python3 pipeline/build_docs.py data/kr docs
```

원문 텍스트는 HWP 본문을 직접 읽는다(PDF 는 낱말 중간 줄바꿈 때문에 띄어쓰기를 되살릴 수 없어 쪽 번호·대조용으로만 쓴다). 관문은 모든 문장이 같은 별책 PDF 에 그대로 있는지, 코드 꼴이 빠짐없이 잡혔는지를 검사한다. 원문 자체의 코드 오기는 `pipeline/exceptions.json` 에서 코드만 보정하고 문장은 고치지 않는다.

## 라이선스

- 코드: MIT ([LICENSE](LICENSE))
- 데이터: 교육과정 고시문은 공공저작물(저작권법 제24조의2)이다. 출처 — 교육부, 국가교육과정정보센터(NCIC). 자세한 것은 [NOTICE.md](NOTICE.md).
- share-alike(ODbL·CC BY-SA)나 비영리(NC) 조건의 자료는 섞지 않는다. 교과서·해설서 문장도 넣지 않는다.

## 기여

원문과 다른 곳을 찾으면 이슈로 코드와 별책·쪽을 알려 주세요. 데이터는 손으로 고치지 않고 추출기·`exceptions.json` 을 고쳐 다시 만든다.
