# korea-learning-map

한국 초·중·고 교육과정(2022 개정, 교육부 고시 제2022-33호)의 **전 교과 성취기준 3,844개를 원문 그대로** 구조화한 공개 데이터와, AI 가 이를 찾아 읽게 하는 로컬 MCP 서버.

목표는 「살면서 무엇을 상식으로 배우는가」와 「다시 배우려면 어디서부터 하나」를 누구나 원문 근거로 답할 수 있게 하는 것이다. 지금(v0)은 그 바탕인 **원문층**만 있다 — 개념·선수관계·다시 배우기 경로는 다음 판에서 쌓는다([DESIGN.md](DESIGN.md)).

## 들어 있는 것 (v0)

| 파일 | 내용 |
|---|---|
| `data/kr/standards.json` | 성취기준 3,844개 — 코드·원문·학년군·교과·과목·단원·성취기준 해설·적용 시 고려 사항(학년 간 연계 문장 포함)·고시 별책·쪽 |
| `data/kr/sources.json` | 원문 고시문 21개 별책의 NCIC 다운로드 주소와 sha256 |
| `data/kr/cross_curricular.json` | 총론의 범교과 학습 주제 10개 |
| `mcp/` | stdio MCP 서버 — `search_topic`(낱말 검색) · `get_topic`(원문·해설·출처) |
| `pipeline/` | 고시문 HWP/PDF → JSON 추출기와 검증 관문(LLM 미사용) |

레코드 예:

```json
{ "id": "9과01-01", "grade": "중1~3", "unit": "과학과 인류의 지속가능한 삶",
  "text": "과학적 탐구 방법을 이해하고, 일상생활의 문제에 대한 과학적 해결 방안을 제안할 수 있다.",
  "notes": ["…"], "unitNotes": ["…와 연계된다.", "…"],
  "ref": "교육부 고시 제2022-33호 [별책 9]", "page": 46 }
```

## MCP 로 쓰기

npm 공개 전까지는 로컬에서:

```bash
git clone https://github.com/jalnanco/korea-learning-map && cd korea-learning-map/mcp && npm install
claude mcp add korea-learning-map -- node "$PWD/index.js"
```

「중학교에서 금융을 어디서 배워?」「분수 나눗셈은 몇 학년이야?」처럼 물으면 원문 성취기준과 출처 쪽수로 답한다. 네트워크·서버·API 키가 필요 없다.

## 다시 만들기

```bash
python3 pipeline/scan_ncic.py 2022 10003530 10003830 > corpus/ncic-2022-scan.tsv   # 게시본 목록
# sources.json 의 url·hwpUrl 로 corpus/pdf/<seq>.pdf · corpus/hwp/<seq>.hwp 를 받는다
python3 pipeline/extract_standards.py data/kr/sources.json corpus data/kr/standards.json > corpus/extract-report.json
python3 pipeline/check_v0.py data/kr/sources.json corpus data/kr/standards.json corpus/extract-report.json   # PASS 여야 한다
```

원문 텍스트는 HWP 본문을 직접 읽는다(PDF 는 낱말 중간 줄바꿈 때문에 띄어쓰기를 되살릴 수 없어 쪽 번호·대조용으로만 쓴다). 관문은 모든 문장이 같은 별책 PDF 에 그대로 있는지, 코드 꼴이 빠짐없이 잡혔는지를 검사한다. 원문 자체의 코드 오기는 `pipeline/exceptions.json` 에서 코드만 보정하고 문장은 고치지 않는다.

## 라이선스

- 코드: MIT ([LICENSE](LICENSE))
- 데이터: 교육과정 고시문은 공공저작물(저작권법 제24조의2)이다. 출처 — 교육부, 국가교육과정정보센터(NCIC). 자세한 것은 [NOTICE.md](NOTICE.md).
- share-alike(ODbL·CC BY-SA)나 비영리(NC) 조건의 자료는 섞지 않는다. 교과서·해설서 문장도 넣지 않는다.

## 기여

원문과 다른 곳을 찾으면 이슈로 코드와 별책·쪽을 알려 주세요. 데이터는 손으로 고치지 않고 추출기·`exceptions.json` 을 고쳐 다시 만든다.
