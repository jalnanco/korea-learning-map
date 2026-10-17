#!/usr/bin/env node
// stdio MCP — 2022 개정 교육과정 성취기준 원문(v0). 요약(search_topic) → 상세(get_topic) 2단으로 토큰을 아낀다.
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";
import { search, get, GRADES, standards, prerequisites, relearnPath, commonSense } from "./search.js";

const server = new McpServer({ name: "korea-learning-map", version: "0.0.2" });
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
  "common_sense",
  {
    description: "모두가 배우는 것 — 초1~고1 필수 공통 교육과정(한문·중학교 선택·고2~3 선택 제외)의 단원 목록. 「상식으로 무엇을 배우나」의 원문 기준.",
    inputSchema: { grade: z.enum(GRADES).optional().describe("학년군으로 좁히기"), subject: z.string().optional().describe("교과·과목 이름 일부. 예: '과학', '통합사회'") },
  },
  async ({ grade, subject }) => json(commonSense({ grade, subject })),
);

await server.connect(new StdioServerTransport());
