#!/usr/bin/env node
// stdio MCP — 2022 개정 교육과정 성취기준 원문(v0). 요약(search_topic) → 상세(get_topic) 2단으로 토큰을 아낀다.
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";
import { search, get, GRADES, standards } from "./search.js";

const server = new McpServer({ name: "korea-learning-map", version: "0.0.1" });
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

await server.connect(new StdioServerTransport());
