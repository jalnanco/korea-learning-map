// 검색·조회 회귀 + stdio 왕복 1회. node test.js
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { search, get, prerequisites, relearnPath, commonSense, conceptPath } from "./search.js";

const r = search("광합성");
assert.ok(r.total > 0 && r.items.some((s) => s.subject.includes("과학")), "광합성은 과학에서 나와야 한다");
assert.ok(search("탐색 한다", { grade: "초3~4" }).items.every((s) => s.grade === "초3~4"), "학년군 필터");
assert.equal(search("없는낱말쀍").total, 0);
const g = get("[10공수2-01-07]");
assert.match(g.text, /x축, y축, 직선 y=x/, "수식이 본문에 복원돼야 한다");
assert.ok(g.source.url.startsWith("https://ncic.re.kr/") && g.source.page > 0);
assert.equal(get("9과01–01").id, "9과01-01", "엔대시 코드도 받는다");
assert.equal(get("없음-00"), null);

// 단원 연계 — 같은 대상 단원은 한 번만, 근거는 배열
const pr = prerequisites("중1~3|과학|힘의 작용");
for (const k of ["prerequisite", "followup", "related"]) {
  const ids = pr[k].map((x) => x.unit);
  assert.equal(new Set(ids).size, ids.length, `${k} 중복 없음`);
  assert.ok(pr[k].every((x) => x.evidence.length > 0 && (x.level === "과목" || x.evidence.every((e) => /연계된다/.test(e)))), `${k} 근거는 고시문 연계 문장`);
}
assert.ok(pr.prerequisite.some((x) => x.unit === "초3~4|과학|힘과 우리 생활"), "힘의 작용 ← 힘과 우리 생활");
assert.equal(prerequisites("9과06-01").unit, "중1~3|과학|기체의 성질", "코드로도 단원을 찾는다");
const rp = relearnPath("9과06-01");
assert.ok(rp.steps.some((s) => s.unit === "초3~4|과학|여러 가지 기체"), "기체의 성질 → 여러 가지 기체");
const ph = relearnPath("광합성"), ph1 = relearnPath("광합성", { depth: 1 });
assert.ok(ph.steps.every((s) => s.depth <= 2) && ph1.steps.every((s) => s.depth === 1) && ph1.steps.length <= ph.steps.length, "깊이 제한");
assert.ok(ph.steps.every((s, i, a) => !i || ["초1~2", "초3~4", "초5~6", "중1~3", "고1", "고2~3"].indexOf(a[i - 1].grade) <= ["초1~2", "초3~4", "초5~6", "중1~3", "고1", "고2~3"].indexOf(s.grade)), "학년군 낮은 순");
// 과목 「성격」 문단의 과목 간 관계 — 선택 과목에서 공통 과목으로 거슬러 간다
const lit = prerequisites("12문학01-01");
assert.ok(lit.prerequisite.some((x) => x.level === "과목" && x.unit === "고1|공통국어1|*"), "문학 ← 공통국어1 (성격)");
assert.ok(relearnPath("12문학01-01").steps.some((s) => s.unit === "중1~3|국어|*"), "문학 다시 배우기 → 중학교 국어");
const cs = commonSense({ grade: "중1~3", subject: "과학" });
assert.ok(cs.total > 10 && cs.units.every((u) => u.grade === "중1~3"), "필수 단원");
assert.equal(commonSense({ grade: "고2~3" }).total, 0, "고2~3 은 전부 선택");
assert.equal(cs.crossCurricular.topics.length, 10, "범교과 학습 주제 10개");

// 수학 개념층 — 낱말·코드로 개념 찾기, 학년 낮은 순, 원문만 보기
const fr = conceptPath("분수 나눗셈", { depth: 8 });
assert.equal(fr.goal.concept, "수학|초5~6|분수의 곱셈과 나눗셈", "낱말로 개념 찾기");
assert.equal(conceptPath("6수01-10").goal.concept, fr.goal.concept, "코드로 개념 찾기");
assert.ok(fr.steps.some((s) => s.name === "약수와 배수") && fr.steps[0].grade === "초1~2", "분수 계산 → 약수와 배수 · 초1~2 부터");
const G = ["초1~2", "초3~4", "초5~6", "중1", "중2", "중3", "고1"];
assert.ok(fr.steps.every((s, i) => !i || G.indexOf(fr.steps[i - 1].grade) <= G.indexOf(s.grade)), "학년 낮은 순");
const fac = conceptPath("인수분해", { proposals: false });
assert.deepEqual(fac.steps.map((s) => [s.name, s.basis]), [["다항식의 곱셈과 인수분해", "원문"]], "원문만 = 고1 인수분해 ← 중3");
assert.ok(fac.steps[0].because.includes("중학교에서 학습한"), "원문 근거 문장");

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
assert.deepEqual(list.result.tools.map((t) => t.name).sort(), ["common_sense", "concept_path", "get_topic", "prerequisites", "relearn_path", "search_topic"]);
const found = JSON.parse(call.result.content[0].text);
assert.ok(found.total > 0, "고교 금융 성취기준");
console.log("PASS", { 광합성: r.total, 광합성_경로: ph.steps.length, 힘의작용_선수: pr.prerequisite.length, 금융_고2_3: found.total, 분수나눗셈_개념경로: fr.steps.length, 첫결과: found.items[0].id + " " + found.items[0].text.slice(0, 40) });
