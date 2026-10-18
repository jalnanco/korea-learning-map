#!/usr/bin/env node
// stdio MCP — 2022 개정 교육과정 성취기준 원문(v0). 요약(search_topic) → 상세(get_topic) 2단으로 토큰을 아낀다.
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";
import { search, get, GRADES, standards, prerequisites, relearnPath, commonSense, conceptPath, conceptSubjects, conceptCount } from "./search.js";

const server = new McpServer({ name: "korea-learning-map", version: "0.3.0" });
const json = (v) => ({ content: [{ type: "text", text: JSON.stringify(v, null, 1) }] });

server.registerTool(
  "search_topic",
  {
    description: `한국 초·중·고 교육과정(2022 개정) 성취기준 ${standards.length}개를 낱말로 찾는다. 「무엇을 배우나」「몇 학년에 배우나」를 원문으로 답할 때 쓴다. 결과는 요약 — 해설·출처는 get_topic.`,
    inputSchema: {
      q: z.string().describe("찾을 낱말(공백으로 여러 개 = 모두 포함). 예: '광합성', '금융 소비자', '분수 나눗셈'"),
      grade: z.enum(GRADES).optional().describe("학년군으로 좁히기"),
      subject: z.string().optional().describe("교과·과목·단원 이름 일부로 좁히기. 예: '과학', '통합사회'"),
      limit: z.number().int().min(1).max(50).optional().describe("최대 개수(기본 10)"),
    },
  },
  async ({ q, grade, subject, limit }) => json(search(q, { grade, subject, limit })),
);

server.registerTool(
  "get_topic",
  {
    description: "성취기준 코드 하나의 원문·해설(notes)·단원 메모(unitNotes — 학년 간 연계 문장 포함)·출처(고시 별책·쪽·원문 URL)를 돌려준다.",
    inputSchema: { id: z.string().describe("성취기준 코드. 예: '9과01-01', '[10통과1-01-01]'") },
  },
  async ({ id }) => {
    const s = get(id);
    return s ? json(s) : { isError: true, content: [{ type: "text", text: `없는 코드: ${id} — search_topic 으로 먼저 찾는다` }] };
  },
);

const ref = z.string().describe("성취기준 코드('9과03-01'), 단원 id('중1~3|과학|힘의 작용'), 또는 낱말('광합성')");
const notFound = (r) => ({ isError: true, content: [{ type: "text", text: `못 찾음: ${r} — search_topic 으로 먼저 찾는다` }] });

server.registerTool(
  "prerequisites",
  { description: "단원 하나의 선수(prerequisite)·후속(followup)·관련(related) 단원을 고시문 근거 문장과 함께 돌려준다. 고시문이 「…와 연계된다」고 밝힌 것만 — 추정 없음.", inputSchema: { ref } },
  async ({ ref }) => { const r = prerequisites(ref); return r ? json(r) : notFound(ref); },
);

server.registerTool(
  "relearn_path",
  {
    description: "어떤 내용을 다시 배우려 할 때 거슬러 올라가 먼저 볼 단원들을 학년군 낮은 순으로 돌려준다(고시문 연계만 따라감). 「이걸 이해하려면 어디부터 다시 봐야 해?」에 쓴다.",
    inputSchema: { ref, depth: z.number().int().min(1).max(6).optional().describe("몇 단계까지 거슬러 갈지(기본 2 — 1 = 바로 앞 단원만)") },
  },
  async ({ ref, depth }) => { const r = relearnPath(ref, { depth }); return r ? json(r) : notFound(ref); },
);

server.registerTool(
  "concept_path",
  {
    description: `개념 하나를 다시 배우려 할 때 먼저 알아야 할 개념들을 학년 낮은 순으로, 개념마다 셀프 체크 물음과 함께 돌려준다. 개념 = 고시문 「내용 체계」 지식⋅이해 항목 — 전 교과 초1~고2~3 ${conceptCount}개(예: '분수의 곱셈과 나눗셈', '옴의 법칙', '생각이나 감정이 함축적으로 제시된 글', '표준 환원 전위와 화학 전지의 전위차'). 간선마다 basis — 원문(고시문 문장) · 제안(Claude 제안 → Gemini 반박 심사, 수학·과학) · 구조(내용 체계 같은 범주 행의 앞 학년 칸) · 단원(고시문 단원 연계 안의 개념 쌍) — 구조·단원도 Gemini 가 「타당」이라 한 것만. 학습자가 「안다」고 답한 개념은 known 에 넣어 다시 부르면 경로가 줄어든다. 간선이 없는 개념은 units 로 relearn_path(단원 단위)를 쓴다.`,
    inputSchema: {
      ref: z.string().describe("개념 이름 낱말('분수 나눗셈', '옴의 법칙'), 성취기준 코드('6수01-10'), 또는 개념 id('수학|중3|이차방정식', '과학|고2~3|화학|분자의 구조')"),
      depth: z.number().int().min(1).max(8).optional().describe("몇 단계까지 거슬러 갈지(기본 3)"),
      proposals: z.boolean().optional().describe("false 면 원문 간선만(기본 true — 원문 간선은 수학 고1 ← 중학교에 주로 있다)"),
      known: z.array(z.string()).optional().describe("이미 아는 개념들(이름·코드·id) — 거기서 멈춘다"),
      subject: z.enum(conceptSubjects).optional().describe("이름이 여러 교과에 걸칠 때 좁히기"),
    },
  },
  async ({ ref, depth, proposals, known, subject }) => { const r = conceptPath(ref, { depth, proposals, known, subject }); return r ? json(r) : notFound(ref); },
);

server.registerTool(
  "common_sense",
  {
    description: "모두가 배우는 것 — 초1~고1 필수 공통 교육과정(한문·중학교 선택·고2~3 선택 제외)의 단원 목록과 총론의 범교과 학습 주제 10개(안전·건강, 인성, 진로, 민주시민, 인권, 다문화, 통일, 독도, 경제·금융, 환경·지속가능발전). 「상식으로 무엇을 배우나」의 원문 기준.",
    inputSchema: { grade: z.enum(GRADES).optional().describe("학년군으로 좁히기"), subject: z.string().optional().describe("교과·과목 이름 일부. 예: '과학', '통합사회'") },
  },
  async ({ grade, subject }) => json(commonSense({ grade, subject })),
);

await server.connect(new StdioServerTransport());
