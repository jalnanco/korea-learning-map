# 개념 간선 — 구조·단원(basis 구조 / 단원). 규칙으로 후보를 뽑고 Gemini 반박 심사에서 「타당」인 것만 links, 나머지는 rejected.
#   python3 pipeline/extract_concept_structure.py data/kr [review.json]
# 구조: 같은 교과·영역·범주 행(내용 체계 표의 한 줄)에서 바로 앞 학년 칸의 요소 — 이름 낱말이 겹칠 때(IDF 합 ≥ 4, 같은 이름은 +5)
#       원문 근거: 각 교과 「내용 체계」는 범주를 학년(군)에 따라 위계적으로 배열한다. 수학(제목 개념)은 원문·제안 간선이 따로 있어 뺀다.
# 단원: links.json 의 원문 단원 연계(선수·후속) 안에서 양쪽 단원의 개념 쌍 — 이름 낱말 IDF 합 ≥ 6
# 심사: 후보를 Gemini Flash 에 1턴 JSON 으로 — 타당 / 약함 / 틀림. 결과는 (from, to) 로 캐시해 두고(이 파일의 links·rejected), 새 후보만 심사가 필요하다.
import collections, json, math, os, re, sys

RANK = {"초1~2": 0, "초3~4": 1, "초5~6": 2, "중1": 3, "중2": 4, "중3": 5, "중1~3": 3, "고1": 6, "고2~3": 7}
JOSA = re.compile(r"(과|와|의|에서|에|을|를|은|는|이|가|으로|로|하기|하는|한)$")
STOP = {"다양한", "활용하여", "이해", "의미", "특징", "방법", "사용하여", "제시한", "관련", "기초", "등", "내용", "글", "원리", "개념", "종류", "표현", "과정", "작품"}
words = lambda t: {w for w in (JOSA.sub("", w) for w in re.split(r"[\s,⋅·?.()\-]+", t)) if len(w) >= 2 and w not in STOP}

def candidates(data):
    C = json.load(open(os.path.join(data, "concepts.json")))["concepts"]
    units = json.load(open(os.path.join(data, "units.json")))["units"]
    df = collections.Counter(w for c in C for w in words(c["name"]))
    ov = lambda a, b: sum(math.log(len(C) / df[w]) for w in words(a["name"]) & words(b["name"]))
    cands = {}
    def add(a, b, basis, reason, score):
        if a["id"] != b["id"] and RANK[b["grade"]] <= RANK[a["grade"]] and ((a["id"], b["id"]) not in cands or cands[(a["id"], b["id"])]["score"] < score):
            cands[(a["id"], b["id"])] = {"from": a["id"], "to": b["id"], "relation": "prerequisite", "basis": basis, "reason": reason, "score": round(score, 2)}
    rows = collections.defaultdict(list)
    for c in C:
        if not c["course"] and c["standardsBy"] != "제목":
            rows[(c["subject"], c["area"], c["strand"])].append(c)
    for (subj, area, strand), cs in rows.items():
        gs = sorted({RANK[c["grade"]] for c in cs})
        for a in cs:
            lower = [g for g in gs if g < RANK[a["grade"]]]
            for b in cs:
                if lower and RANK[b["grade"]] == lower[-1] and (s := ov(a, b) + (5 if a["name"] == b["name"] else 0)) >= 4:
                    add(a, b, "구조", f"내용 체계 같은 범주 행({strand or area})의 바로 앞 학년 칸", s)
    uof = {s: u["id"] for u in units for s in u["standards"]}
    by_unit = collections.defaultdict(list)
    for c in C:
        for u in {uof.get(s) for s in c["standards"]} - {None}:
            by_unit[u].append(c)
    whole = collections.defaultdict(list)  # 「고1|통합과학1|*」 = 과목 전체
    for u in units:
        whole[f"{u['grade']}|{u['course'] or u['subject']}|*"].append(u["id"])
    for l in json.load(open(os.path.join(data, "links.json")))["links"]:
        if l["relation"] not in ("prerequisite", "followup"):
            continue
        f, t = (l["from"], l["to"]) if l["relation"] == "prerequisite" else (l["to"], l["from"])
        for x in whole.get(f, [f]) if f.endswith("*") else [f]:
            for y in whole.get(t, [t]) if t.endswith("*") else [t]:
                for a in by_unit.get(x, []):
                    for b in by_unit.get(y, []):
                        if (s := ov(a, b)) >= 6:
                            add(a, b, "단원", f"고시문 단원 연계 — {l['evidence']}", s)
    return sorted(cands.values(), key=lambda x: -x["score"])

def main(data, review=None):
    path = os.path.join(data, "concept_structure.json")
    old = json.load(open(path)) if os.path.exists(path) else {"links": [], "rejected": []}
    cache = {(l["from"], l["to"]): l["review"] for l in old["links"] + old["rejected"]}
    cands = candidates(data)
    if review:  # 심사 결과 파일 {후보 번호: {v, why}} — 번호는 이 스크립트가 낸 후보 순서
        for i, r in json.load(open(review)).items():
            cache[(cands[int(i)]["from"], cands[int(i)]["to"])] = {"model": "gemini-3.8-flash-high", "verdict": r["v"], "why": r["why"]}
    links, rejected, todo = [], [], []
    for c in cands:
        r = cache.get((c["from"], c["to"]))
        if not r:
            todo.append(c); continue
        (links if r["verdict"] == "타당" else rejected).append({**c, "review": r})
    json.dump({"version": "v2", "rule": "basis 구조(내용 체계 같은 범주 행의 앞 학년 칸) · 단원(고시문 단원 연계 안의 개념 쌍) — 규칙 후보를 Gemini 가 반박 심사해 「타당」만 links",
               "count": len(links), "links": links, "rejected": rejected}, open(path, "w"), ensure_ascii=False, indent=1)
    print(f"후보 {len(cands)} · 채택 {len(links)} {dict(collections.Counter(l['basis'] for l in links))} · 뺌 {len(rejected)} · 심사 안 됨 {len(todo)}")

if __name__ == "__main__":
    main(*sys.argv[1:3])
