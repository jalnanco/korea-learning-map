# 스캔 결과에서 v0 원문 목록(sources.json)을 만든다 — 2022-33호 [별책N] PDF, 별책마다 번호가 가장 큰(나중) 게시본.
#   python3 pipeline/build_sources.py corpus/ncic-2022-scan.tsv > data/kr/sources.json
import csv, json, re, sys

EXCLUDE = set(range(23, 40)) | {16}  # 전문교과·제2외국어는 v0 범위 밖
COMPILATION = {2, 3}                 # 학교급 합본 — 교과 별책과 내용이 겹쳐 대조용으로만
pick = {}
for seq, name, size, url in csv.reader(open(sys.argv[1]), delimiter="\t"):
    m = re.match(r"\[별책(\d+)\]\s*(.+)\.pdf$", name, re.I)
    if not m or int(m.group(1)) in EXCLUDE or "특수" in name or "기본 교육과정" in name or "유치원" in name:
        continue
    n = int(m.group(1))
    if n not in pick or int(seq) > int(pick[n]["seq"]):
        pick[n] = {"annex": n, "title": m.group(2), "seq": seq, "bytes": int(size), "url": url,
                   "ref": f"교육부 고시 제2022-33호 [별책 {n}]", "role": "compilation" if n in COMPILATION else "subject"}
json.dump({"pin": "교육부 고시 제2022-33호 — NCIC 게시본 중 별책별 최신 번호", "license": "공공저작물(저작권법 제24조의2) · 출처: 교육부, 국가교육과정정보센터(NCIC)",
           "sources": [pick[k] for k in sorted(pick)]}, sys.stdout, ensure_ascii=False, indent=1)
