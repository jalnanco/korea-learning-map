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
