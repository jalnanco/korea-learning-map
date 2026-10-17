# NCIC 고시문 다운로드 번호를 HEAD 로 훑어 파일명·크기를 모은다(본문은 받지 않음).
#   python3 pipeline/scan_ncic.py <year> <seq_from> <seq_to> > out.tsv
import re, sys, time, urllib.parse, urllib.request
year, a, b = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
for seq in range(a, b + 1):
    url = f"https://ncic.re.kr/inv/org/download.do?year={year}&seq={seq}&orgType=ogi4"
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            cd = r.headers.get("Content-Disposition", "")
            m = re.search(r'fileName="([^"]+)"', cd, re.I)
            if m:
                print(seq, urllib.parse.unquote(m.group(1)), r.headers.get("Content-Length", ""), url, sep="\t", flush=True)
    except Exception as e:
        print(f"# {seq} {e}", file=sys.stderr)
    time.sleep(0.1)
