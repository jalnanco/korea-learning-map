# 단원 노드(units.json) + 고시문이 밝힌 단원 간 연계(links.json). LLM 없음.
#   python3 pipeline/extract_links.py data/kr
# 근거 문장 = 단원 메모 중 「…와/과 연계된다.」 — 학년군 맥락 + ‘단원’ 또는 고등학교 ‘과목’의 단원구.
# 대상이 `학년|과목|*` 이면 과목 전체(단원구가 없거나 단원명과 안 맞음).
# 방향: 대상 학년군이 낮으면 prerequisite(선수), 높으면 followup(후속), 같으면 related.
# corpus 를 주면 고교 과목 「1. 성격」 문단의 과목 간 관계도 잇는다 — 「‘문학’은 … ‘국어’와 … ‘공통국어1, 공통국어2’의 문학 영역을 심화⋅확장한 과목」
#   → 과목 전체(`학년|과목|*`) 사이 간선(rule 성격). 같은 학년군이면 따옴표 묶음 바로 뒤가 「…에서 학습한」「…를 통해 익힌」
#   「…와 연계된 (…의) 심화」「…를 토대로」「…의 … 를 (…) 확장⋅심화」일 때만 선수, 아니면 관련(「긴밀히 연계된다」는 방향이 없다).
#   python3 pipeline/extract_links.py data/kr corpus
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

def main(data, corpus=None):
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
    for l in links:
        l["rule"] = "단원 메모"
    if corpus:
        links += nature_links(src, corpus, nodes)
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

LEAD_COURSE = re.compile(r"^(?:또한\s*)?(?:고등학교\s*)?[‘']([^’']+)[’']\s*(?:과목에서는|과목은|은|는)")
PRE = re.compile(r"^\s*(까지|에서|를\s*통해|을\s*통해)?\s*(학습한|배운|다룬|익힌)|^\s*(와|과)\s*연계된[^‘]{0,15}?심화|^\s*(을|를)\s*(토대|바탕|기초)로|^\s*의\s[^‘]{0,60}?(을|를)[^‘]{0,15}?(심화|확장)")

def after_run(sent, quotes, i):  # i 번째 따옴표가 속한 묶음(쉼표·「와」·「고등학교 진로 선택」 같은 짧은 이음말로 이어진 따옴표들) 뒤 구절
    for j in range(i, len(quotes)):
        seg = sent[quotes[j].end():quotes[j + 1].start() if j + 1 < len(quotes) else len(sent)]
        if PRE.search(seg) or len(norm(seg)) > 15 or "다" in seg or j + 1 == len(quotes):
            return seg
    return ""
SCHOOL = re.compile(r"초등학교|중학교|고등학교")
cname = lambda t: norm(re.sub(r"\(.*?\)", "", t)).replace("II", "Ⅱ").replace("I", "Ⅰ")

def nature_links(src, corpus, nodes):
    """고교 과목 「1. 성격」 문단에서 그 과목이 주어인 문장 → 따옴표 안 다른 과목들(학교급 맥락 안에서 이름 풀이)."""
    sys.path.insert(0, os.path.dirname(__file__))
    from extract_standards import hwp_lines
    courses = collections.OrderedDict()  # (학년군, 과목 이름) → 노드 하나(과목 단위 간선에 학년군만 쓴다)
    for n in nodes.values():
        courses.setdefault((n["grade"], n["course"]), n)
    band = {"초등학교": ("초1~2", "초3~4", "초5~6"), "중학교": ("중1~3",), "고등학교": ("고1", "고2~3")}

    def find(name, schools):  # 학교급마다 가장 높은 학년군의 그 과목 하나(초등 국어 = 초5~6 국어)
        out = []
        for sc in schools:
            hit = [(g, c) for (g, c) in courses if g in band[sc] and (cname(c) == cname(name) or re.fullmatch(re.escape(cname(name)) + r"\d", cname(c))
                   or (sc != "고등학교" and cname(name) in cname(c)))]
            for g in band[sc][::-1]:
                same = [k for k in hit if k[0] == g]
                if same:
                    out += same; break
        return out

    links = []
    for s in src:
        hwp = os.path.join(corpus, "hwp", f"{s['seq']}.hwp")
        if s["role"] != "subject" or not os.path.exists(hwp):
            continue
        inside = False
        for depth, para in hwp_lines(hwp):
            if re.match(r"^1\.\s*성격", para):
                inside = True; continue
            if re.match(r"^[2-9]\.\s", para):
                inside = False
            if not inside or depth:
                continue
            for sent in re.split(r"(?<=다)\.\s+", para):
                m = LEAD_COURSE.match(sent)
                me = m and [k for k in courses if k[0].startswith("고") and cname(k[1]) == cname(m.group(1))]
                if not me or not re.search(r"심화|확장|토대|기초로|계승|연계", sent):
                    continue
                g0, c0 = me[0]
                school = None
                quotes = list(QUOTE.finditer(sent, m.end()))
                for qi, q in enumerate(quotes):
                    pre = bool(PRE.search(after_run(sent, quotes, qi)))
                    for sc in SCHOOL.finditer(sent, 0, q.start()):
                        school = sc.group(0)
                    schools = ["초등학교", "중학교"] if re.search(r"초(등학교\s*및\s*|\s*[⋅·]?\s*)중학교", sent[:q.start()]) and school == "중학교" else [school or "고등학교"]
                    names = re.split(r"\s*,\s*", q.group(1))
                    names = [re.sub(r"\d$", n, names[0]) if n.isdigit() else n for n in names]  # 「통합과학1, 2」
                    for name in names:
                        for g, c in find(name, schools) or (find(name, ["고등학교"]) if "고등학교" not in schools else []):  # 「중학교 ‘도덕’ … ‘통합사회’」 — 맥락이 이어져도 그 학교급에 없으면 고교 과목
                            if (g, c) == (g0, c0):
                                continue
                            d = GRADES.index(g) - GRADES.index(g0)
                            rel = "prerequisite" if d < 0 or (d == 0 and pre) else "followup" if d > 0 else "related"
                            links.append({"from": f"{g0}|{c0}|*", "to": f"{g}|{c}|*", "relation": rel, "matched": f"{g} ‘{name}’", "evidence": sent.rstrip(".") + ".", "rule": "성격"})
    return links

if __name__ == "__main__":
    main(*sys.argv[1:3])
