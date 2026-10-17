# v0 원문층 관문 — 하나라도 어기면 exit 1.
#   python3 pipeline/check_v0.py data/kr/sources.json corpus data/kr/standards.json corpus/extract-report.json
# 1) 추출 보고: 누락·해설만 있는 코드·PDF 불일치·충돌·쪽 없음 = 0 (다른 교과 기준 인용은 전체 집합에 있으면 통과)
# 2) 레코드: id 유일 · text 비지 않음 · grade 있음 · sourceSeq 가 sources.json 에 있음
# 4) 단원·연계(units.json·links.json 이 있으면): 모든 기준이 단원 하나에 · 간선 양끝이 노드(또는 `학년|과목|*`) · 근거 문장이 원문 단원 메모에 있음(성격 간선은 원문 PDF 에 그대로 있음) · 자기 간선 0
# 5) 수학 개념층(concepts.json 이 있으면): 개념 이름·원문 간선 근거가 수학 고시문(별책 8)에 그대로 있음 · 개념마다 기준 ≥ 1 ·
#    간선(원문 + 제안) 양끝이 개념 · 선수 학년 ≤ 출발 학년 · 순환 0
# 3) 느슨한 코드 꼴: `[숫자…-숫자…]` 인데 CODE 정규식에 안 맞는 것 = 0 (알려진 비기준 꼴 제외)
#    — 추출과 검사가 같은 정규식을 쓰면 정규식 구멍(로마 숫자·괄호 과목명)을 못 본다. 2026-10-18 실측 296줄 누락이 그랬다.
import json, os, re, subprocess, sys

HERE = os.path.dirname(__file__)
sys.path.insert(0, HERE)
import extract_standards as E

LOOSE = re.compile(r"\[\d{1,2}[가-힣A-Za-zⅠ-Ⅻ·()]+\d{0,2}[-–][^\]\s\[]{1,10}\]")
KNOWN = [re.compile(p) for p in (r"[∼~,/]", r"자율-\d\]$", r"-\d\]$", r"-\d{2}-\d\]$")]  # 범위 인용 · 학교자율시간 예시 · 끝자리 한 자리 오기 인용

def main(sources_path, corpus, std_path, report_path):
    fails = []
    stds = json.load(open(std_path))["standards"]
    ids = [s["id"] for s in stds]
    have = set(ids)
    for r in json.load(open(report_path)):
        if "skipped" in r:
            continue
        for k in ("orphanNotes", "notInPdf", "noPage", "conflict"):
            if r.get(k):
                fails.append(f"별책{r['annex']} {k}: {r[k][:5]}")
        if (miss := [c for c in r["missing"] if c not in have]):
            fails.append(f"별책{r['annex']} missing: {miss[:5]}")
    if len(ids) != len(have):
        fails.append(f"id 중복 {len(ids) - len(have)}건")
    seqs = {s["seq"] for s in json.load(open(sources_path))["sources"]}
    for s in stds:
        if not s.get("text") or not s.get("grade") or s.get("sourceSeq") not in seqs:
            fails.append(f"레코드 불완전: {s['id']}")
    for f in sorted(os.listdir(os.path.join(corpus, "hwp"))):
        t = subprocess.run([sys.executable, os.path.join(HERE, "hwp_text.py"), os.path.join(corpus, "hwp", f)], capture_output=True, text=True, check=True).stdout
        for a, b in E.EXC["codeFix"].items():
            t = t.replace(a, b["to"])
        odd = sorted({m.group(0) for m in LOOSE.finditer(t) if not re.fullmatch(E.CODE, m.group(0)) and not any(k.search(m.group(0)) for k in KNOWN)})
        if odd:
            fails.append(f"{f} 정규식 밖 코드 꼴: {odd[:5]}")
    udir = os.path.dirname(std_path)
    if os.path.exists(os.path.join(udir, "links.json")):
        units = json.load(open(os.path.join(udir, "units.json")))["units"]
        uid = {u["id"] for u in units} | {f"{u['grade']}|{u['course']}|*" for u in units}
        placed = [c for u in units for c in u["standards"]]
        if sorted(placed) != sorted(ids):
            fails.append(f"단원 배치 불일치: 기준 {len(ids)} · 배치 {len(placed)}")
        notes = {n for s in stds for n in s.get("unitNotes", [])}
        pdf = "".join(E.squash("".join(E.pdf_pages(os.path.join(corpus, "pdf", f)))) for f in sorted(os.listdir(os.path.join(corpus, "pdf"))))
        for l in json.load(open(os.path.join(udir, "links.json")))["links"]:
            grounded = l["evidence"] in notes if l["rule"] == "단원 메모" else re.sub(r"[⋅·]", "", E.squash(l["evidence"])) in re.sub(r"[⋅·]", "", pdf)
            if l["from"] not in uid or l["to"] not in uid or l["from"] == l["to"] or not grounded:
                fails.append(f"간선 이상: {l['from']} → {l['to']}")
    if os.path.exists(os.path.join(udir, "concepts.json")):
        fails += check_concepts(udir, corpus)
    print(f"성취기준 {len(ids)} · 해설 {sum('notes' in s for s in stds)} · 단원 메모 {sum('unitNotes' in s for s in stds)} · 수식 {sum('math' in s for s in stds)}")
    for x in fails:
        print("FAIL", x)
    print("PASS" if not fails else f"{len(fails)} FAIL")
    sys.exit(1 if fails else 0)

CGRADES = ["초1~2", "초3~4", "초5~6", "중1", "중2", "중3", "고1"]

def check_concepts(udir, corpus):
    out = []
    concepts = {c["id"]: c for c in json.load(open(os.path.join(udir, "concepts.json")))["concepts"]}
    src = next(s for s in json.load(open(os.path.join(udir, "sources.json")))["sources"] if s["annex"] == 8)
    flat = lambda t: re.sub(r"[\s⋅·]", "", t)
    hwp = flat(subprocess.run([sys.executable, os.path.join(HERE, "hwp_text.py"), os.path.join(corpus, "hwp", f"{src['seq']}.hwp")], capture_output=True, text=True, check=True).stdout)
    for c in concepts.values():
        if flat(c["name"]) not in hwp or not c["standards"]:
            out.append(f"개념 이상: {c['id']}")
    edges = [(l, "원문") for l in json.load(open(os.path.join(udir, "concept_links.json")))["links"]]
    prop = os.path.join(udir, "concept_proposals.json")
    if os.path.exists(prop):
        edges += [(l, "제안") for l in json.load(open(prop))["proposals"]]
    graph = {}
    for l, kind in edges:
        a, b = concepts.get(l["from"]), concepts.get(l["to"])
        if not a or not b or a is b or CGRADES.index(b["grade"]) > CGRADES.index(a["grade"]) or (kind == "원문" and flat(l["evidence"]) not in hwp):
            out.append(f"개념 간선 이상({kind}): {l['from']} ← {l['to']}")
        graph.setdefault(l["from"], set()).add(l["to"])
    state = {}
    def visit(n, path):  # 0 방문 중 · 1 끝
        if state.get(n) == 0:
            out.append("개념 순환: " + " ← ".join(path[path.index(n):] + [n])); return
        if n in state:
            return
        state[n] = 0
        for m in graph.get(n, ()):
            visit(m, path + [n])
        state[n] = 1
    for n in list(graph):
        visit(n, [])
    print(f"개념 {len(concepts)} · 개념 간선 원문 {sum(k == '원문' for _, k in edges)} · 제안 {sum(k == '제안' for _, k in edges)}")
    return out

if __name__ == "__main__":
    main(*sys.argv[1:5])
