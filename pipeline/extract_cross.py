# 총론의 범교과 학습 주제 10개(원문) + 각 주제를 언급하는 성취기준(해설·단원 메모의 원문 언급). LLM 없음.
#   python3 pipeline/extract_cross.py data/kr/sources.json corpus data/kr/standards.json data/kr/cross_curricular.json
import json, os, re, subprocess, sys

HERE = os.path.dirname(__file__)

def main(sources_path, corpus, std_path, out_path):
    s = next(x for x in json.load(open(sources_path))["sources"] if x["annex"] == 1)
    lines = subprocess.run([sys.executable, os.path.join(HERE, "hwp_text.py"), os.path.join(corpus, "hwp", f"{s['seq']}.hwp")], capture_output=True, text=True, check=True).stdout.split("\n")
    i = next(k for k, l in enumerate(lines) if l.startswith("자. 범교과 학습 주제"))
    topics = [t.strip() for t in lines[i + 1].split(",")]
    pages = subprocess.run(["pdftotext", "-layout", os.path.join(corpus, "pdf", f"{s['seq']}.pdf"), "-"], capture_output=True, text=True, check=True).stdout.split("\f")
    page = next(k + 1 for k, p in enumerate(pages) if re.sub(r"\s", "", topics[-1]) in re.sub(r"\s", "", p))
    stds = json.load(open(std_path))["standards"]
    out = []
    for t in topics:
        key = re.sub(r"[\s⋅·∙ㆍ]", "", t)  # 가운뎃점 표기가 문서마다 다르다
        hit = sorted(x["id"] for x in stds if key in re.sub(r"[\s⋅·∙ㆍ]", "", " ".join(x.get("notes", []) + x.get("unitNotes", []))))
        out.append({"name": t, "mentionedBy": hit})
    json.dump({"version": "v0", "ref": f"{s['ref']} Ⅱ.1.자", "page": page, "url": s["url"], "intro": lines[i].strip(), "topics": out},
              open(out_path, "w"), ensure_ascii=False, indent=1)
    for x in out:
        print(x["name"], len(x["mentionedBy"]))

if __name__ == "__main__":
    main(*sys.argv[1:5])
