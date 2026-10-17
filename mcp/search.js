// 원문층 적재·검색 — MCP 와 테스트가 같이 쓴다. 검색은 공백을 지운 부분 문자열 일치(한국어 띄어쓰기 차이를 흡수).
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const dataDir = [path.join(here, "data"), path.join(here, "..", "data", "kr")].find((d) => fs.existsSync(path.join(d, "standards.json")));
const read = (f) => JSON.parse(fs.readFileSync(path.join(dataDir, f), "utf8"));

const sources = Object.fromEntries(read("sources.json").sources.map((s) => [s.seq, s]));
export const standards = read("standards.json").standards.map((s) => ({ ...s, subject: sources[s.sourceSeq].title }));
const byId = new Map(standards.map((s) => [s.id, s]));
const squash = (t) => (t || "").replace(/\s+/g, "").toLowerCase();
const index = standards.map((s) => ({ s, text: squash(s.text), meta: squash([s.subject, s.course, s.unit].join(" ")), notes: squash((s.notes || []).join(" ")) }));

export const GRADES = ["초1~2", "초3~4", "초5~6", "중1~3", "고1", "고2~3"];

// 낱말마다: 성취기준 문장 3점 · 교과/과목/단원 2점 · 해설 1점. 모든 낱말이 어딘가에 있어야 한다.
export function search(q, { grade, subject, limit = 10 } = {}) {
  const words = q.split(/\s+/).map(squash).filter(Boolean);
  const hits = [];
  for (const it of index) {
    if (grade && it.s.grade !== grade) continue;
    if (subject && !it.meta.includes(squash(subject))) continue;
    let score = 0;
    for (const w of words) {
      const p = (it.text.includes(w) ? 3 : 0) + (it.meta.includes(w) ? 2 : 0) + (it.notes.includes(w) ? 1 : 0);
      if (!p) { score = 0; break; }
      score += p;
    }
    if (score) hits.push([score, it.s]);
  }
  hits.sort((a, b) => b[0] - a[0] || GRADES.indexOf(a[1].grade) - GRADES.indexOf(b[1].grade) || a[1].id.localeCompare(b[1].id));
  return { total: hits.length, items: hits.slice(0, limit).map(([, s]) => summary(s)) };
}

export const summary = (s) => ({ id: s.id, grade: s.grade, subject: s.subject, course: s.course || undefined, unit: s.unit, text: s.text });

export function get(id) {
  const s = byId.get(id.replace(/^\[|\]$/g, "").replace(/[–—]/g, "-"));
  if (!s) return null;
  const src = sources[s.sourceSeq];
  return {
    ...summary(s),
    courseType: s.courseType || undefined,
    math: s.math,
    notes: s.notes || [],
    unitNotes: s.unitNotes || [],
    source: { ref: s.ref, page: s.page, url: src.url, license: "공공저작물(저작권법 제24조의2) · 출처: 교육부, 국가교육과정정보센터(NCIC)" },
  };
}

// ── 단원·연계(고시문 「…와 연계된다」 문장만, 추정 없음) ──
const units = read("units.json").units;
const unitById = new Map(units.map((u) => [u.id, u]));
const unitOfStd = new Map(units.flatMap((u) => u.standards.map((c) => [c, u])));
const links = read("links.json").links;
const unitView = (u) => ({ unit: u.id, grade: u.grade, subject: u.subject, course: u.course, name: u.unit || u.course, core: u.core, standards: u.standards });
const node = (id) => unitById.get(id) ? unitView(unitById.get(id)) : { unit: id, course: id.split("|")[1], grade: id.split("|")[0], name: `${id.split("|")[1]} (과목 전체)` };

// 코드·단원 id·낱말 무엇을 받아도 단원 하나로
export function unitOf(ref) {
  const code = ref.replace(/^\[|\]$/g, "").replace(/[–—]/g, "-");
  if (unitOfStd.has(code)) return unitOfStd.get(code);
  if (unitById.has(ref)) return unitById.get(ref);
  const hit = search(ref, { limit: 1 }).items[0];
  return hit ? unitOfStd.get(hit.id) : null;
}

// 선수 = prerequisite 간선의 대상 + followup 간선을 거꾸로 본 출발점(B 가 A 의 후속이면 A 는 B 의 선수)
const prereqOf = new Map();
for (const l of links) {
  const [x, y] = l.relation === "prerequisite" ? [l.from, l.to] : l.relation === "followup" ? [l.to, l.from] : [null];
  if (!x) continue;
  if (!prereqOf.has(x)) prereqOf.set(x, new Map());
  if (!prereqOf.get(x).has(y)) prereqOf.get(x).set(y, []);
  if (!prereqOf.get(x).get(y).includes(l.evidence)) prereqOf.get(x).get(y).push(l.evidence);
}

// 단원 노드와 그 단원이 속한 과목 전체(`학년|과목|*` — 과목 「성격」 문단의 과목 간 관계)
const courseOf = (id) => (id.endsWith("|*") ? null : id.split("|").slice(0, 2).join("|") + "|*");
const withCourse = (id) => [id, courseOf(id)].filter(Boolean);

// 양쪽 단원 메모가 같은 쌍을 각자 밝히면 간선이 둘이다 — 대상 단원 하나로 묶고 근거 문장은 배열로
export function prerequisites(ref) {
  const u = unitOf(ref);
  if (!u) return null;
  const flip = { prerequisite: "followup", followup: "prerequisite", related: "related" };
  const out = { prerequisite: new Map(), followup: new Map(), related: new Map() };
  const mine = new Set(withCourse(u.id));
  for (const l of links) {
    if (!mine.has(l.from) && !mine.has(l.to)) continue;
    const [self, other, rel] = mine.has(l.from) ? [l.from, l.to, l.relation] : [l.to, l.from, flip[l.relation]];
    if (other === courseOf(u.id)) continue;
    if (!out[rel].has(other)) out[rel].set(other, { ...node(other), level: self === u.id ? "단원" : "과목", evidence: [] });
    const ev = out[rel].get(other).evidence;
    if (!ev.includes(l.evidence)) ev.push(l.evidence);
  }
  const list = (m) => [...m.values()].sort((a, b) => GRADES.indexOf(a.grade) - GRADES.indexOf(b.grade));
  return { ...unitView(u), prerequisite: list(out.prerequisite), followup: list(out.followup), related: list(out.related) };
}

// 거슬러 올라가며 선수 단원 — 가까운 것부터 depth 단계까지(멀리 가면 통합 단원을 타고 다른 영역으로 번진다), 학년군 낮은 것부터(= 다시 배우는 순서)
export function relearnPath(ref, { depth: max = 2 } = {}) {
  const u = unitOf(ref);
  if (!u) return null;
  const seen = new Map([[u.id, null]]);
  let frontier = [u.id];
  for (let d = 1; d <= max && frontier.length; d++) {
    const next = [];
    for (const id of frontier) {
      for (const [p, ev] of withCourse(id).flatMap((x) => [...(prereqOf.get(x) || [])])) {
        if (seen.has(p)) continue;
        seen.set(p, { ...node(p), depth: d, via: id, because: ev });
        next.push(p);
      }
    }
    frontier = next;
  }
  seen.delete(u.id);
  const steps = [...seen.values()].sort((a, b) => GRADES.indexOf(a.grade) - GRADES.indexOf(b.grade) || b.depth - a.depth);
  const more = frontier.some((id) => withCourse(id).some((x) => [...(prereqOf.get(x) || []).keys()].some((p) => !seen.has(p))));
  return {
    goal: unitView(u), depth: max, steps, more: more || undefined,
    note: steps.length ? "고시문이 밝힌 연계만 따라간 경로다 — 연계 문장이 없는 교과는 비어 있을 수 있다" + (more ? ` · depth ${max + 1} 이상에 더 있다` : "") : "고시문에 이 단원의 선수 연계 문장이 없다",
  };
}

// 모두가 배우는 것(필수) 단원 목록
export function commonSense({ grade, subject } = {}) {
  const us = units.filter((u) => u.core && (!grade || u.grade === grade) && (!subject || squash(`${u.subject} ${u.course}`).includes(squash(subject))));
  return { total: us.length, standards: us.reduce((n, u) => n + u.standards.length, 0), units: us.map((u) => ({ unit: u.id, grade: u.grade, subject: u.subject, course: u.course, name: u.unit || u.course, count: u.standards.length })) };
}
