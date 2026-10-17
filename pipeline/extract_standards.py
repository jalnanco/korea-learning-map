# 고시문 → 성취기준 원문(L0). LLM 없음.
#   python3 pipeline/extract_standards.py data/kr/sources.json corpus data/kr/standards.json
# 원문 텍스트 = HWP(문단당 한 줄 — PDF 는 낱말 중간에서 줄을 바꿔 「탐 색한다」가 된다) · 쪽 번호·대조 = PDF.
# 규칙: 문단 첫머리 `[코드] 문장` = 성취기준 · `(가) 성취기준 해설` 의 `[코드] …` = 그 기준의 해설
#       · `(나) 성취기준 적용 시 고려 사항` 의 문단 = 단원 메모(단원 안 모든 기준에 연결) · 단원 = `(1) 제목`
# 관문: 모든 성취기준 문장(공백 제거, 수식 제외 조각)이 같은 별책 PDF 텍스트(공백 제거)의 부분 문자열이어야 한다.
import hashlib, json, os, re, subprocess, sys

HERE = os.path.dirname(__file__)
DASH = r"[-–—‐−]"
CODE = r"\[(\d{1,2})([가-힣A-Za-z·Ⅰ-Ⅻ]+?(?:\([가-힣]+\))?[Ⅰ-Ⅻ]?)(\d{0,2})" + DASH + r"(\d{2})(?:" + DASH + r"(\d{2}))?\]"
STD = re.compile(r"^\s*\[?" + CODE[2:] + r"\s*(.*)$")  # 여는 괄호가 빠진 원문(`12연몸02-04]`)도 받는다
BULLET = re.compile(r"^\s*•\s*")
HEADING = re.compile(r"^\s*(\d|[가-하])\.\s")  # 장·절 제목(「3. 교수·학습 및 평가」「나. 성취기준」) — 해설·고려 절이 끝난다
UNIT = re.compile(r"^\s*\((\d{1,2})\)\s+(\S.*)$")
SECTION = re.compile(r"^\s*\((가|나|다)\)\s*(.*)$")
BAND = re.compile(r"^\s*\[(초등학교|중학교|고등학교)\s*([0-9∼~\-]+학년(?:군)?)?\]\s*$")
COURSE = re.compile(r"^\s*[\[<〈]([^\]>〉\d][^\]>〉]{0,24})[\]>〉]\s*$")  # 고교 과목 머리(「[공통수학2]」「<통합과학2>」)
COURSE_TYPE = re.compile(r"^\s*-\s*(.+?과목)\s*-\s*$")  # 「- 일반 선택 과목 -」
GRADE = {"2": "초1~2", "4": "초3~4", "6": "초5~6", "9": "중1~3", "10": "고1", "12": "고2~3"}  # 코드 앞자리 = 학년군(고1 공통 10 · 고교 선택 12)
EXC = json.load(open(os.path.join(HERE, "exceptions.json")))

def code_of(m):
    g = m.groups()
    return f"{g[0]}{g[1]}{g[2]}-{g[3]}" + (f"-{g[4]}" if g[4] else "")

def alias(c):
    return EXC["noteAlias"].get(c, {}).get("to", c)

def hwp_lines(path):
    out = subprocess.run([sys.executable, os.path.join(HERE, "hwp_text.py"), path], capture_output=True, text=True, check=True).stdout
    return [(len(l) - len(l.lstrip("\t")), re.sub(r"\s+", " ", l).strip()) for l in out.split("\n") if l.strip()]  # (표 중첩 깊이, 문단)

def pdf_pages(path):
    out = subprocess.run(["pdftotext", "-layout", path, "-"], capture_output=True, text=True, check=True).stdout
    return out.split("\f")

MATH = re.compile(r"⟦(.*?)⟧")
SYM = [(r"\{([^{}]*)\}\s*over\s*\{([^{}]*)\}", r"(\1)/(\2)"), (r"(\S+)\s+over\s+(\S+)", r"\1/\2"), (r"sqrt\s*\{([^{}]*)\}", r"√(\1)"),
       (r"(?i)\btimes\b", "×"), (r"\bdiv\b", "÷"), (r"SMALLSUM", "Σ"), (r"[`~{}]", ""), (r"\s+", "")]

def readable(script):  # HWP 수식 문법 → 읽기용 한 줄 (원본은 math 에 남긴다)
    for a, b in SYM:
        script = re.sub(a, b, script)
    return re.sub(r"\((\w)\)", r"\1", script)

squash = lambda t: re.sub(r"\s+", "", t).replace("–", "-")

def extract(lines, src):
    stds, unit, band, course, ctype, section = {}, None, None, None, None, None
    prev = (0, "")
    unit_codes, unit_notes = {}, {}
    for depth, l in lines:
        for a, b in EXC["codeFix"].items():
            l = l.replace(a, b["to"])
        last, prev = prev, (depth, l)
        if (m := COURSE_TYPE.match(l)):
            ctype = m.group(1).replace(" ", ""); continue
        if re.match(r"^(1\.\s*성격|교육과정 설계의 개요$)", l) and last[0] > 0 and len(last[1]) <= 25:  # 고교 과목 첫 장 — 바로 앞 짧은 중첩 줄이 과목명
            course, unit, section = re.sub(r"^.*?과목\s*-\s*", "", last[1]), None, None; continue
        if (m := BAND.match(l)):
            band = (m.group(1) + " " + (m.group(2) or "")).strip(); course = None; section = None; continue
        if (m := COURSE.match(l)) and depth == 0:
            course = m.group(1).strip(); section = None; continue
        if (m := UNIT.match(l)):
            unit = m.group(2).strip(); section = None; continue
        if HEADING.match(l):
            section = None; continue
        if (m := SECTION.match(l)):
            section = "해설" if "해설" in m.group(2) else ("고려" if "고려" in m.group(2) else m.group(2)); continue
        l = BULLET.sub("", l)  # HWP 는 글머리표가 문단 서식이라 「•」가 없다 — 있으면 떼고 같은 규칙으로 본다
        m = STD.match(l)
        if section == "해설":
            if m:
                last = alias(code_of(m)); stds.setdefault(last, {}).setdefault("notes", []).append(m.groups()[-1].strip())
            continue
        if section == "고려":
            if not m:
                if (unit or course) and depth == 0 and l != "없음":  # 「없음」 = 해당 없음 · 깊이 1 이상 = 고려 절 안 표의 칸(「운동」「건강」 같은 머리 글자)
                    unit_notes.setdefault((band, course, unit), []).append(l)
                continue
            section = None  # 단원 제목 없이 이어지는 다음 성취기준 묶음
        if m:
            code = code_of(m)
            if "text" in stds.get(code, {}) and f"{code}#2" in EXC["duplicateRemap"]:
                code = EXC["duplicateRemap"][f"{code}#2"]["to"]
            rec = stds.setdefault(code, {})
            if "text" not in rec:
                raw = m.groups()[-1].strip()
                if (eqs := MATH.findall(raw)):
                    rec["math"] = eqs
                rec.update({"id": code, "grade": GRADE[m.group(1)], "text": MATH.sub(lambda e: readable(e.group(1)), raw), "_raw": raw, "band": band, "course": course, "courseType": ctype, "unit": unit, "ref": src["ref"], "sourceSeq": src["seq"]})
                unit_codes.setdefault((band, course, unit), []).append(code)
    for key, codes in unit_codes.items():
        for c in codes:
            if unit_notes.get(key):
                stds[c]["unitNotes"] = unit_notes[key]
    return stds

def main(sources_path, corpus, out_path):
    src = json.load(open(sources_path))
    allstd, report = {}, []
    for s in src["sources"]:
        if s["role"] != "subject":
            continue
        pdf, hwp = os.path.join(corpus, "pdf", f"{s['seq']}.pdf"), os.path.join(corpus, "hwp", f"{s['seq']}.hwp")
        if not os.path.exists(hwp):
            report.append({"annex": s["annex"], "title": s["title"], "skipped": "HWP 없음"}); continue
        s["sha256"] = hashlib.sha256(open(pdf, "rb").read()).hexdigest()
        s["hwpSha256"] = hashlib.sha256(open(hwp, "rb").read()).hexdigest()
        lines = hwp_lines(hwp)
        stds = extract(lines, s)
        pages = [squash(p) for p in pdf_pages(pdf)]
        whole = "".join(pages)
        got = {c for c, r in stds.items() if "text" in r}
        unverified = []
        for c in got:
            pieces = [squash(x) for x in MATH.split(stds[c].pop("_raw"))[::2] if squash(x)]  # 수식은 PDF 에서 세로 분수 등으로 그려져 대조 밖
            stds[c]["page"] = next((i + 1 for i, p in enumerate(pages) if squash(f"{c}]") in p.replace("–", "-")), None)
            if not all(x in whole for x in pieces):
                unverified.append(c)
        mentioned = {alias(code_of(m)) for _, l in lines for m in re.finditer(CODE, l)}
        report.append({"annex": s["annex"], "title": s["title"], "standards": len(got), "mentioned": len(mentioned),
                       "missing": sorted(mentioned - got)[:20], "orphanNotes": sorted(c for c, r in stds.items() if "text" not in r)[:20],
                       "notInPdf": sorted(unverified)[:20], "notInPdfCount": len(unverified),
                       "noPage": sorted(c for c in got if not stds[c]["page"])[:10]})
        for c in got:
            if c in allstd and allstd[c]["text"] != stds[c]["text"]:
                report[-1].setdefault("conflict", []).append(c)
            allstd.setdefault(c, stds[c])
    json.dump(src, open(sources_path, "w"), ensure_ascii=False, indent=1)
    json.dump({"version": "v0", "count": len(allstd), "standards": [allstd[k] for k in sorted(allstd)]}, open(out_path, "w"), ensure_ascii=False, indent=1)
    json.dump(report, sys.stdout, ensure_ascii=False, indent=1)

if __name__ == "__main__":
    main(*sys.argv[1:4])
