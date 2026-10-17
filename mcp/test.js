// 검색·조회 회귀 + stdio 왕복 1회. node test.js
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { search, get } from "./search.js";

const r = search("광합성");
assert.ok(r.total > 0 && r.items.some((s) => s.subject.includes("과학")), "광합성은 과학에서 나와야 한다");
assert.ok(search("탐색 한다", { grade: "초3~4" }).items.every((s) => s.grade === "초3~4"), "학년군 필터");
assert.equal(search("없는낱말쀍").total, 0);
const g = get("[10공수2-01-07]");
assert.match(g.text, /x축, y축, 직선 y=x/, "수식이 본문에 복원돼야 한다");
assert.ok(g.source.url.startsWith("https://ncic.re.kr/") && g.source.page > 0);
assert.equal(get("9과01–01").id, "9과01-01", "엔대시 코드도 받는다");
assert.equal(get("없음-00"), null);

const p = spawn(process.execPath, [new URL("./index.js", import.meta.url).pathname]);
const send = (m) => p.stdin.write(JSON.stringify({ jsonrpc: "2.0", ...m }) + "\n");
let buf = "";
const replies = new Promise((res) => p.stdout.on("data", (d) => { buf += d; if (buf.split("\n").filter(Boolean).length >= 3) res(buf.split("\n").filter(Boolean).map(JSON.parse)); }));
send({ id: 1, method: "initialize", params: { protocolVersion: "2025-06-18", capabilities: {}, clientInfo: { name: "test", version: "0" } } });
send({ method: "notifications/initialized" });
send({ id: 2, method: "tools/list" });
send({ id: 3, method: "tools/call", params: { name: "search_topic", arguments: { q: "금융", grade: "고2~3", limit: 3 } } });
const [, list, call] = await replies;
p.kill();
assert.deepEqual(list.result.tools.map((t) => t.name).sort(), ["get_topic", "search_topic"]);
const found = JSON.parse(call.result.content[0].text);
assert.ok(found.total > 0, "고교 금융 성취기준");
console.log("PASS", { 광합성: r.total, 금융_고2_3: found.total, 첫결과: found.items[0].id + " " + found.items[0].text.slice(0, 40) });
