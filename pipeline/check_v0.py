# v0 원문층 관문 — 하나라도 어기면 exit 1.
#   python3 pipeline/check_v0.py data/kr/sources.json corpus data/kr/standards.json corpus/extract-report.json
# 1) 추출 보고: 누락·해설만 있는 코드·PDF 불일치·충돌·쪽 없음 = 0 (다른 교과 기준 인용은 전체 집합에 있으면 통과)
# 2) 레코드: id 유일 · text 비지 않음 · grade 있음 · sourceSeq 가 sources.json 에 있음
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
    print(f"성취기준 {len(ids)} · 해설 {sum('notes' in s for s in stds)} · 단원 메모 {sum('unitNotes' in s for s in stds)} · 수식 {sum('math' in s for s in stds)}")
    for x in fails:
        print("FAIL", x)
    print("PASS" if not fails else f"{len(fails)} FAIL")
    sys.exit(1 if fails else 0)

if __name__ == "__main__":
    main(*sys.argv[1:5])
