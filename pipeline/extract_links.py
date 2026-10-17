# 단원 노드(units.json) + 고시문이 밝힌 단원 간 연계(links.json). LLM 없음.
#   python3 pipeline/extract_links.py data/kr
# 근거 문장 = 단원 메모 중 「…와/과 연계된다.」 — 학년군 맥락 + ‘단원’ 또는 고등학교 ‘과목’의 단원구.
# 대상이 `학년|과목|*` 이면 과목 전체(단원구가 없거나 단원명과 안 맞음).
# 방향: 대상 학년군이 낮으면 prerequisite(선수), 높으면 followup(후속), 같으면 related.
import collections, json, os, re, sys
from names import SUBJECT, is_core, label

GRADES = ["초1~2", "초3~4", "초5~6", "중1~3", "고1", "고2~3"]
FORMAL = re.compile(r"(와|과)\s*연계된다\.?\s*$")
QUOTE = re.compile(r"[‘'“\"]([^’'”\"]+)[’'”\"]")
CTX = re.compile(r"(초등학교|중학교|고등학교)?\s*(\d)\s*[∼~\-]\s*(\d)\s*학년군|(고등학교)")
norm = lambda t: re.sub(r"[\s⋅·･∙ㆍ]", "", t or "")

def unit_nodes(stds, annex_of):
    nodes = collections.OrderedDict()
    for s in stds:
        annex = annex_of[s["sourceSeq"]]
        key = (s["grade"], label(s, annex), s["unit"] or "")  # 교과까지 넣어야 음악·미술 「감상」, 바른·슬기로운·즐거운 생활 단원이 안 합쳐진다
        n = nodes.setdefault(key, {"id": "|".join(key), "grade": s["grade"], "annex": annex, "subject": SUBJECT[annex], "course": label(s, annex), "unit": s["unit"], "core": is_core(s, annex), "standards": []})
        n["standards"].append(s["id"])
    return nodes

def main(data):
    src = json.load(open(os.path.join(data, "sources.json")))["sources"]
    annex_of = {s["seq"]: s["annex"] for s in src}
    stds = json.load(open(os.path.join(data, "standards.json")))["standards"]
    nodes = unit_nodes(stds, annex_of)
    by_unit = collections.defaultdict(list)    # (학년군, 단원명) → 노드
    by_course = collections.defaultdict(list)  # 과목명 → 노드들
    for n in nodes.values():
        by_unit[(n["grade"], norm(n["unit"]))].append(n)
        if n["grade"].startswith("고"):
            by_course[norm(n["course"])].append(n)
    node_of_std = {c: n for n in nodes.values() for c in n["standards"]}
    links, unresolved, seen = [], collections.Counter(), set()
    for s in stds:
        here = node_of_std[s["id"]]
        for note in s.get("unitNotes", []):
            if not FORMAL.search(note) or (here["id"], note) in seen:
                continue
            seen.add((here["id"], note))
            for target, phrase in resolve(note, here, by_unit, by_course, unresolved):
                if target["id"] == here["id"]:
                    continue
                d = GRADES.index(target["grade"]) - GRADES.index(here["grade"])
                links.append({"from": here["id"], "to": target["id"], "relation": "prerequisite" if d < 0 else "followup" if d > 0 else "related",
                              "matched": phrase, "evidence": note})
    uniq = {(l["from"], l["to"]): l for l in links}
    json.dump({"version": "v0", "count": len(nodes), "units": list(nodes.values())}, open(os.path.join(data, "units.json"), "w"), ensure_ascii=False, indent=1)
    json.dump({"version": "v0", "count": len(uniq), "rule": "고시문 단원 메모의 「…와 연계된다」 문장만 — 추정 없음", "links": list(uniq.values())},
              open(os.path.join(data, "links.json"), "w"), ensure_ascii=False, indent=1)
    rel = collections.Counter(l["relation"] for l in uniq.values())
    print(f"단원 {len(nodes)} · 연계 {len(uniq)} {dict(rel)} · 못 푼 이름 {sum(unresolved.values())}")
    for k, v in unresolved.most_common(15):
        print("  못 품:", k, v)

def resolve(note, here, by_unit, by_course, unresolved):
    """연계 문장 → [(대상 노드, 근거 구절)]. 따옴표 이름을 학년군 맥락 안의 단원으로, 고등학교면 과목(+단원구)으로 푼다."""
    out, school, grade = [], None, None
    pos = 0
    quotes = list(QUOTE.finditer(note))
    for i, q in enumerate(quotes):
        for c in CTX.finditer(note, pos, q.start()):  # 이 따옴표 앞의 학년군 맥락
            if c.group(4):
                school, grade = "고등학교", None
            else:
                school = c.group(1) or school
                grade = "중1~3" if school == "중학교" else {"1": "초1~2", "3": "초3~4", "5": "초5~6"}[c.group(2)]
        name = q.group(1)
        if school == "고등학교" or (grade is None and norm(name) in by_course):
            names = [name] if norm(name) in by_course else [re.sub(r"\d,\s*\d$", d, name) for d in re.findall(r"\d", name[-4:])]  # 「통합과학1, 2」
            tail = note[q.end():quotes[i + 1].start() if i + 1 < len(quotes) else len(note)]
            parts = [p for p in re.split(r"\s*,\s*|\s+및\s+", re.sub(FORMAL, "", re.sub(r"^\s*의\s*", "", tail))) if norm(p)] if tail.lstrip().startswith("의") else []
            for nm in names:
                course_nodes = by_course.get(norm(nm), [])
                if not course_nodes:
                    unresolved[nm] += 1; continue
                hit = [n for p in parts for n in course_nodes if n["unit"] and (norm(n["unit"]).startswith(norm(p)) or norm(p).startswith(norm(n["unit"])))]
                if hit:
                    out += [(n, f"고등학교 ‘{nm}’의 {n['unit']}") for n in {id(n): n for n in hit}.values()]
                else:  # 단원구가 없거나 단원명과 안 맞으면 과목 단위로 잇는다
                    c = course_nodes[0]
                    out.append(({"id": f"{c['grade']}|{c['course']}|*", "grade": c["grade"]}, f"고등학교 ‘{nm}’ (과목 전체)"))
        else:
            g = grade or here["grade"]
            cands = by_unit.get((g, norm(name)), [])
            if not cands and re.search(r"[과와]\s", name):  # 「물질의 구성과 화학 반응의 규칙성」 = 단원 둘
                cands = [n for part in re.split(r"(?<=[가-힣])[과와]\s+", name) for n in by_unit.get((g, norm(part)), [])[:1]]
                if cands:
                    out += [(n, f"{g} ‘{n['unit']}’") for n in cands]; pos = q.end(); continue
            if not cands:  # 같은 이름이 다른 학년군에만 있으면 그쪽(맥락 생략 문장)
                cands = [n for (gg, u), ns in by_unit.items() if u == norm(name) for n in ns]
            same = [n for n in cands if n["annex"] == here["annex"]]
            if not cands:
                unresolved[name] += 1
            for n in (same or cands)[:1]:
                out.append((n, f"{g} ‘{name}’"))
        pos = q.end()
    return out

if __name__ == "__main__":
    main(sys.argv[1])
