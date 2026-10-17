# 수학 개념 간 선수관계 — 원문 근거만(basis 원문). LLM 없음.
#   python3 pipeline/extract_concept_links.py data/kr corpus
# ① 해설·적용 시 고려 사항의 「(초등학교|중학교)에서 학습한 X …」 문장
#    출발 = 문장 주어부(「학습한 X」를 뺀 나머지)에 이름 낱말이 가장 많이 나오는 개념(해설이면 그 기준의 개념)
#    대상 = 그 학교급 개념 중 이름에 X 의 낱말이 가장 많이 든 것(「실수」→ 제곱근과 실수), 없으면 X 낱말을 가장 많이 담은 기준의 개념
#           X 가 「내용」이면 주제어(「은/는」 앞 명사구 — 「함수의 개념은」→ 함수)로
# ② 공통수학 「성격」의 「중학교 ‘영역’ 영역에서 학습한 A, B, C가 …」 → 이름에 같은 낱말이 든 고1 개념 ← 그 영역의 중학교 개념
# 제안(basis 제안) 간선은 data/kr/concept_proposals.json(Claude 제안 → Gemini 반박 심사 → 판정)에 따로 합친다 — 원문 간선과 섞지 않는다.
import json, os, re, sys

sys.path.insert(0, os.path.dirname(__file__))
LEARNED = re.compile(r"(초등학교|중학교)에서 (?:학습한|배운|다룬)\s*")
STOP = re.compile(r"\s*(와|과)?\s*(연계|토대|바탕|확장|이외|이 있음)|\s*(을|를|이|가)\s*(토대|바탕|확장)")
SCHOOL = {"초등학교": ("2", "4", "6"), "중학교": ("9",)}
JOSA = re.compile(r"(과|와|의|은|는|을|를|이|가|에|도|으로|로)$")
words = lambda t: [w for w in (JOSA.sub("", w) for w in re.split(r"[\s,⋅·]+", t)) if len(w) >= 2 and w not in ("내용", "개념", "학습", "이해", "다룬다", "하게", "한다")]

def score(name, text):
    return sum(len(w) for w in words(name) if w in text)

def main(data, corpus):
    stds = {s["id"]: s for s in json.load(open(os.path.join(data, "standards.json")))["standards"]}
    concepts = json.load(open(os.path.join(data, "concepts.json")))["concepts"]
    own = {c: x for x in concepts for c in x["standards"]}
    links, seen = [], set()

    def target(school, phrase):
        cand = [y for y in concepts if y["standards"] and y["standards"][0][0] in SCHOOL[school] and not y["course"]]
        df = lambda w: sum(w in y["name"] for y in cand) or 1  # 여러 이름에 흔한 낱말(성질)은 가볍게
        by_name = {y["id"]: sum(len(w) / df(w) for w in words(phrase) if w in y["name"]) for y in cand}
        top = max(by_name.values(), default=0)
        if top:
            return [i for i, k in by_name.items() if k == top]
        best = {}
        for c, s in stds.items():
            if c in own and c[0] in SCHOOL[school] and not c.startswith("10"):
                k = sum(len(w) for w in words(phrase) if w in s["text"])
                if k:
                    best[own[c]["id"]] = max(best.get(own[c]["id"], 0), k)
        top = max(best.values(), default=0)
        return [i for i, k in best.items() if k == top]

    def add(frm, to, ev, rule, matched):
        if (frm, to) not in seen and frm != to:
            seen.add((frm, to))
            links.append({"from": frm, "to": to, "relation": "prerequisite", "basis": "원문", "rule": rule, "matched": matched, "evidence": ev})

    for x in concepts:
        for c in x["standards"]:
            for kind, notes in (("해설", stds[c].get("notes", [])), ("고려", stds[c].get("unitNotes", []))):
                for n in notes:
                    for sent in re.split(r"(?<=다)\.\s*", n):
                        m = LEARNED.search(sent)
                        if not m:
                            continue
                        rest = sent[m.end():]
                        stop = STOP.search(rest)
                        phrase = JOSA.sub("", rest[:stop.start()] if stop else rest[:20]).strip()
                        subject = sent[:m.start()] + (rest[stop.end():] if stop else "")
                        if kind == "해설":
                            frm = [x]
                        else:  # 단원 메모는 영역 안 모든 기준에 붙어 있다 — 주어부로 출발 개념을 고른다
                            pool = [y for y in concepts if y["area"] == x["area"] and y["grade"] == x["grade"]]
                            sc = {y["id"]: score(y["name"], subject) for y in pool}
                            top = max(sc.values(), default=0)
                            frm = [y for y in pool if top and sc[y["id"]] == top]
                        head = re.match(r"^\s*(.+?)(?:은|는)\s", sent[:m.start()] + " ")
                        tos = target(m.group(1), phrase if words(phrase) else (head.group(1) if head else subject))
                        for f in frm:
                            for t in tos:
                                add(f["id"], t, sent.strip().rstrip(".") + ".", kind, f"{m.group(1)}에서 학습한 {phrase or '내용'}")

    # ② 공통수학 성격
    from extract_standards import hwp_lines
    src = next(s for s in json.load(open(os.path.join(data, "sources.json")))["sources"] if s["annex"] == 8)
    for _, para in hwp_lines(os.path.join(corpus, "hwp", f"{src['seq']}.hwp")):
        if not para.startswith("<공통수학1>은 중학교"):
            continue
        for sent in re.split(r"(?<=다)\.\s*", para):
            course = re.match(r"<(공통수학[12])>", sent)
            if not course:
                continue
            for m in re.finditer(r"[‘']([^’']+)[’']\s*영역에서 학습한\s*([^‘']+?)(?:이|가|을|를)\s", sent):
                area, names = m.group(1), re.split(r"\s*,\s*|과\s|와\s", m.group(2))
                for w in (JOSA.sub("", n) for n in names if n.strip()):
                    w = w.replace("의 개념", "")
                    frm = [y for y in concepts if y["course"] == course.group(1) and w in y["name"]]
                    tos = [y for y in concepts if y["band"] == "중1~3" and y["area"] == area and w in y["name"]]
                    for f in frm:
                        for t in tos:
                            add(f["id"], t["id"], sent.strip().rstrip(".") + ".", "성격", f"중학교 ‘{area}’ 영역에서 학습한 {w}")
    json.dump({"version": "v1", "rule": "원문 문장이 밝힌 선수관계만(basis 원문) — 제안 간선은 concept_proposals.json", "count": len(links), "links": links},
              open(os.path.join(data, "concept_links.json"), "w"), ensure_ascii=False, indent=1)
    print(f"원문 개념 간선 {len(links)}")
    for l in links:
        print(f"  {l['from']}  ←  {l['to']}   [{l['rule']}] {l['matched']}")

if __name__ == "__main__":
    main(*sys.argv[1:3])
