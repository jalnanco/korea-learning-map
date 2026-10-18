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

// 모두가 배우는 것(필수) 단원 목록 + 총론이 모든 교육 활동에 걸쳐 다루라는 범교과 학습 주제 10개
const cross = read("cross_curricular.json");
export function commonSense({ grade, subject } = {}) {
  const us = units.filter((u) => u.core && (!grade || u.grade === grade) && (!subject || squash(`${u.subject} ${u.course}`).includes(squash(subject))));
  return {
    total: us.length, standards: us.reduce((n, u) => n + u.standards.length, 0),
    units: us.map((u) => ({ unit: u.id, grade: u.grade, subject: u.subject, course: u.course, name: u.unit || u.course, count: u.standards.length })),
    crossCurricular: {
      source: `${cross.ref} p.${cross.page}`, rule: cross.intro,
      topics: cross.topics.map((t) => ({ name: t.name, mentionedBy: t.mentionedBy })),
      note: "mentionedBy = 해설·단원 메모가 주제 이름을 그대로 언급한 성취기준. 주제 낱말이 들어간 기준을 더 찾으려면 search_topic('통일') 처럼 쓴다(뜻이 다른 낱말도 섞인다)",
    },
  };
}

// ── 개념층(v2) — 전 교과 초1~고2~3. 개념 = 고시문 「내용 체계」 지식⋅이해 항목. 간선은 basis 로 나눈다: 원문(고시문 문장) · 제안(Claude 제안 → Gemini 반박 심사 → 판정)
//    · 구조(내용 체계 같은 범주 행의 앞 학년 칸) · 단원(고시문 단원 연계 위의 개념 쌍) — 구조·단원은 규칙으로 뽑아 Gemini 가 반박 심사해 「타당」만 ──
const CRANK = { "초1~2": 0, "초3~4": 1, "초5~6": 2, "중1": 3, "중1~3": 3, "중2": 4, "중3": 5, "고1": 6, "고2~3": 7 };
const concepts = read("concepts.json").concepts;
export const conceptSubjects = [...new Set(concepts.map((c) => c.subject))];
export const conceptCount = concepts.length;
const conceptById = new Map(concepts.map((c) => [c.id, c]));
const conceptOfStd = new Map(concepts.flatMap((c) => c.standards.map((s) => [s, c])));
const proposals = read("concept_proposals.json").proposals;
const conceptPre = new Map();
for (const l of [...read("concept_links.json").links, ...proposals, ...read("concept_structure.json").links]) {
  if (!conceptPre.has(l.from)) conceptPre.set(l.from, []);
  conceptPre.get(l.from).push(l);
}

// 셀프 체크 = 그 개념 성취기준 문장의 끝맺음만 물음으로(「…할 수 있다.」→「…할 수 있나요?」) — 원문 밖 문장을 만들지 않는다
const ASK = [[/있다\.$/, "있나요?"], [/이해한다\.$/, "이해하고 있나요?"], [/안다\.$/, "알고 있나요?"], [/기른다\.$/, "기르고 있나요?"], [/(갖는다|가진다)\.$/, "갖고 있나요?"]];
const ask = (t) => { const r = ASK.find(([re]) => re.test(t)); return r ? t.replace(r[0], r[1]) : t; };
const selfCheck = (c) => c.standards.map((id) => ({ id, q: ask(byId.get(id).text) }));
const conceptView = (c) => ({ concept: c.id, subject: c.subject, grade: c.grade, area: c.area, strand: c.strand || undefined, name: c.name, course: c.course || undefined,
  units: [...new Set(c.standards.map((s) => unitOfStd.get(s)?.id).filter(Boolean))], selfCheck: selfCheck(c) });

// 개념 id · 성취기준 코드 · 개념 이름(낱말이 모두 든 것 중 가장 짧은 이름, 같으면 높은 학년) · 그래도 없으면 성취기준 검색
export function conceptOf(ref, { subject } = {}) {
  if (conceptById.has(ref)) return conceptById.get(ref);
  const code = ref.replace(/^\[|\]$/g, "").replace(/[–—]/g, "-");
  if (conceptOfStd.has(code)) return conceptOfStd.get(code);
  const pool = concepts.filter((c) => !subject || c.subject === subject);
  const words = ref.split(/\s+/).map(squash).filter(Boolean);
  const named = pool.filter((c) => words.every((w) => squash(c.name).includes(w)));
  if (named.length) return named.sort((a, b) => (squash(a.name) === squash(ref) ? 0 : 1) - (squash(b.name) === squash(ref) ? 0 : 1) || a.name.length - b.name.length || CRANK[b.grade] - CRANK[a.grade])[0];
  const hit = search(ref, { limit: 20, subject }).items.find((s) => conceptOfStd.has(s.id));
  return hit ? conceptOfStd.get(hit.id) : null;
}

// known = 이미 아는 개념(이름·코드·id) — 그 개념에서 더 거슬러 가지 않는다
export function conceptPath(ref, { depth: max = 3, proposals: withProposals = true, known = [], subject } = {}) {
  const c = conceptOf(ref, { subject });
  if (!c) return null;
  const knownIds = new Set(known.map((k) => conceptOf(k)?.id).filter(Boolean));
  const seen = new Map([[c.id, null]]);
  let frontier = [c.id];
  for (let d = 1; d <= max && frontier.length; d++) {
    const next = [];
    for (const id of frontier) {
      for (const l of conceptPre.get(id) || []) {
        if (seen.has(l.to) || knownIds.has(l.to) || (!withProposals && l.basis !== "원문")) continue;
        seen.set(l.to, { ...conceptView(conceptById.get(l.to)), depth: d, via: id, basis: l.basis, because: l.basis === "원문" ? l.evidence : l.reason });
        next.push(l.to);
      }
    }
    frontier = next;
  }
  seen.delete(c.id);
  const steps = [...seen.values()].sort((a, b) => CRANK[a.grade] - CRANK[b.grade] || b.depth - a.depth);
  const more = frontier.some((id) => (conceptPre.get(id) || []).some((l) => !seen.has(l.to) && !knownIds.has(l.to) && (withProposals || l.basis === "원문")));
  return {
    goal: conceptView(c), depth: max, known: knownIds.size ? [...knownIds] : undefined, steps, more: more || undefined,
    note: "basis 원문 = 고시문 문장이 밝힌 선수관계(because = 그 문장) · basis 제안 = 원문에 없는 직접 선수관계를 Claude 가 제안하고 Gemini 가 반박 심사한 것(because = 이유)"
      + " · basis 구조 = 내용 체계 표 같은 범주 행의 바로 앞 학년 칸 · basis 단원 = 고시문이 밝힌 단원 연계 안의 개념 쌍(둘 다 규칙으로 뽑고 Gemini 가 「타당」이라 한 것만)"
      + " · selfCheck = 성취기준 문장을 물음으로 바꾼 것 — 「예」인 개념은 known 에 넣고 다시 부르면 경로가 줄어든다"
      + " · units = 단원 id(prerequisites·relearn_path 로 고시문 단원 연계를 볼 수 있다)"
      + (more ? ` · depth ${max + 1} 이상에 더 있다` : ""),
  };
}
