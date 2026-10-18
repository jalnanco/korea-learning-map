# 수학 개념층(v1) — 고시문 「내용 체계」 지식⋅이해 칸 = 개념 노드. LLM 없음.
#   python3 pipeline/extract_concepts.py data/kr corpus
# 초1~중3: 개념 = 성취기준 절의 지식⋅이해 제목(󰊱 네 자리 이하의 수) — 기준을 그 아래에 묶어 두므로 개념 → 기준이 원문 그대로다.
#          학년군은 기준 코드, 중1·중2·중3 은 내용 체계 표(중학교 1~3학년 칸이 다시 세 칸)에서 같은 이름의 칸으로 찾는다.
# 고1(공통수학1·2): 표의 칸이 영역(다항식 …)이고 기준도 영역으로 묶여 있어, 영역 안에서 개념 낱말이 겹치는 기준에 잇는다.
# 원문 근거: 「초⋅중학교의 지식⋅이해 범주는 학년(군)에 따라 위계성을 가지며, 영역 간에도 위계성을 고려하여 구성하였다.」
# 과학(초3~중3): 내용 체계 = 영역 → 범주(힘과 에너지 …) × 학년군 칸의 내용 요소(⋅밀기와 당기기  ⋅무게). 개념 = 내용 요소 하나.
#   성취기준은 단원으로 묶여 있어 개념 → 기준은 같은 학년군 기준 문장(+단원명)에 요소 낱말이 가장 많이 든 것(standardsBy 낱말).
import collections, json, os, re, subprocess, sys

sys.path.insert(0, os.path.dirname(__file__))
from names import SUBJECT

HERE = os.path.dirname(__file__)
ITEM = re.compile(r"^\s*⋅\s*(.+?)\s*$")
CELL = re.compile(r"^\s*⟪칸 (\d+) (\d+) (\d+) (\d+)⟫$")
TITLE = re.compile(r"^\s*[\U000F0000-\U000FFFFD]?\s*(.+?)\s*$")  # 성취기준 절의 지식⋅이해 제목 — 원문자 글리프가 붙거나(󰊱) 추출에서 빠진다(⑩ 이후)
STD = re.compile(r"^\s*\[(\d+수\d{2}-\d{2}|10공수[12]-\d{2}-\d{2})\]")
AREA = re.compile(r"^\s*\((\d)\)\s+(수와 연산|변화와 관계|도형과 측정|자료와 가능성|다항식|방정식과 부등식|경우의 수|행렬|도형의 방정식|집합과 명제|함수와 그래프)\s*$")
COLS = {"1~2학년": ["초1~2"], "3~4학년": ["초3~4"], "5~6학년": ["초5~6"], "1~3학년": ["중1", "중2", "중3"]}
BAND = {"초1~2": "초1~2", "초3~4": "초3~4", "초5~6": "초5~6", "중1": "중1~3", "중2": "중1~3", "중3": "중1~3", "고1": "고1"}
norm = lambda t: re.sub(r"[\s⋅·,]", "", t)

def lines(hwp):
    out = subprocess.run([sys.executable, os.path.join(HERE, "hwp_text.py"), hwp, "--cells"], capture_output=True, text=True, check=True).stdout
    return [l.rstrip() for l in out.split("\n") if l.strip()]

def tables(ls):
    """내용 체계 표들 → [(영역 또는 과목, 개념 이름, 학년, 표 안 영역)] — 지식⋅이해 행만."""
    out, area, course, i = [], None, None, 0
    while i < len(ls):
        l = ls[i].strip()
        if (m := re.match(r"^\[(공통수학[12]|기본수학[12])\]$", l)):
            course = m.group(1) if course != "skip" and m.group(1).startswith("공통") else "skip"  # 기본수학(대체 이수)부터 뒤의 선택 과목은 범위 밖
        if (m := AREA.match(l)):
            area = m.group(2)
        if l.startswith("가. 내용 체계"):
            j, cells, cur = i + 1, {}, None
            while j < len(ls) and not ls[j].strip().startswith("나. 성취기준"):
                if (m := CELL.match(ls[j])):
                    cur = tuple(map(int, m.groups())); cells[cur] = []
                elif cur:
                    cells[cur].append(ls[j].strip())
                elif (m := AREA.match(ls[j].strip())):
                    cells.setdefault(("영역", m.group(2)), [])
                j += 1
            if course != "skip":
                out += read_tables(ls[i + 1:j], course)
            i = j; continue
        i += 1
    return out

def read_tables(block, course):
    # 블록 안에 표가 여럿(영역마다 하나) — 「⟪칸 0 0 …⟫」가 새 표의 시작
    out, area, cells, cur, t_area = [], None, None, None, None
    def flush():
        if cells is None:
            return
        cols = {}
        for (r, c, rs, cs), txt in cells.items():
            if txt and txt[0] in COLS:
                for k, g in enumerate(COLS[txt[0]]):
                    cols[c + k] = g
        know = next(((r, rs) for (r, c, rs, cs), txt in cells.items() if c == 0 and txt and txt[0] == "지식⋅이해"), None)
        if not know:
            return
        r0, rs0 = know
        sub = {}  # 고1: 같은 행의 1열 = 표 안 영역
        for (r, c, rs, cs), txt in sorted(cells.items()):
            if not r0 <= r < r0 + rs0 or c == 0:
                continue
            items = [m.group(1) for t in txt if (m := ITEM.match(t))]
            if course and not items and txt:
                sub[r] = txt[0]; continue
            for it in items:
                out.append({"area": sub.get(r, t_area), "name": it, "grade": "고1" if course else cols[c], "course": course})
    for l in block:
        if (m := AREA.match(l)):
            area = m.group(2); continue
        if (m := CELL.match(l)):
            key = tuple(map(int, m.groups()))
            if key[:2] == (0, 0):
                flush(); cells = {}; t_area = area
            cur = key; cells[cur] = []
        elif cur is not None:
            cells[cur].append(l.strip())
    flush()
    return out

def standards_by_title(ls):
    """성취기준 절: 지식⋅이해 제목 → 그 아래 기준 코드들. 고1 은 영역 제목 → 기준."""
    out, title, area, in_std = {}, None, None, False
    for k, l in enumerate(ls):
        s = l.strip()
        depth = len(l) - len(l.lstrip("\t"))
        if s.startswith("나. 성취기준"):
            in_std = True; continue
        if re.match(r"^\d\.\s", s) and not s.startswith("2."):
            in_std = False
        if not in_std:
            continue
        if (m := AREA.match(s)):
            area, title = m.group(2), None
        elif depth and len(s) <= 30 and not STD.match(s) and not s.endswith("다.") and k + 1 < len(ls) and STD.match(ls[k + 1].strip()):
            title = (area, TITLE.match(s).group(1))  # 기준 상자 안, 기준 바로 앞의 짧은 줄
        elif (m := STD.match(s)) and depth:  # 깊이 0 = 해설·고려 사항 줄의 코드 인용
            out.setdefault(("영역", area) if m.group(1).startswith("10") or not title else title, []).append(m.group(1))  # 고1 은 영역 묶음
    return out

# 전 교과(수학 초1~고1 제외): 「가. 내용 체계」 블록마다 표 → 지식⋅이해 칸(「지식⋅ 이해」「[지식⋅이해]」 — 한글만 비교)의 내용 요소 = 개념.
#   열: 학년군 머리(「3∼4학년」「5-6학년군」「중학교」) → 초·중 / 머리 없는 한 열 표 → 고교 과목(뒤따르는 성취기준 절의 과목·학년) / 통합교과는 열 = 과목.
#   기준: 그 블록 성취기준 중 같은 학년군(고교는 같은 과목) 문장(+단원명)에 요소 낱말이 가장 많이 든 것(standardsBy 낱말), 0 점이면 같은 칸 이웃(이웃).
GRADE_HEAD = {("1", "2"): "초1~2", ("3", "4"): "초3~4", ("5", "6"): "초5~6", ("1", "3"): "중1~3"}
COURSE = re.compile(r"^\s*[\[<〈]([^\]>〉\d][^\]>〉]{0,24})[\]>〉]\s*$")  # 표 앞 과목 머리(「[한국사1]」) — extract_standards 와 같은 꼴
ABBR = {"바른 생활": "바", "슬기로운 생활": "슬", "즐거운 생활": "즐"}
JOSA = re.compile(r"(과|와|의|에서|에|을|를|은|는|이|가)$")
ko = lambda t: re.sub(r"[^가-힣]", "", t)
nm = lambda x: re.sub(r"\s", "", x or "")
words = lambda t: [w for w in (JOSA.sub("", w) for w in re.split(r"[\s,⋅·]+", t)) if len(w) >= 2]

def blocks(ls, stds):
    """「가. 내용 체계」 블록 → (표 줄들, 뒤따르는 「나. 성취기준」 절의 기준 코드들 — 상자 안(들여쓴) 줄만, 해설의 인용 제외)"""
    i = 0
    while i < len(ls):
        if ls[i].strip().startswith("가. 내용 체계"):
            j = next((j for j in range(i + 1, len(ls)) if ls[j].strip().startswith("나. 성취기준")), len(ls))
            k = next((k for k in range(j, len(ls)) if ls[k].strip().startswith("가. 내용 체계")), len(ls))
            yield ls[i + 1:j], list(dict.fromkeys(c for l in ls[j:k] if l.startswith("\t") for c in re.findall(r"\[([^\[\]\s]{3,24})\]", l) if c in stds))
            i = k; continue
        i += 1

def content_tables(block):
    """블록 → [(영역, 과목 머리, 칸들)] — 「⟪칸 0 0 …⟫」가 새 표. 들여쓰지 않은 줄은 표 밖(「(1) 듣기⋅말하기」 영역 머리)."""
    out, area, head, cells, cur = [], None, None, None, None
    for l in block:
        if not l.startswith("\t"):
            cur = None
            if (m := re.match(r"^\s*\(\d+\)\s+(.+?)\s*$", l)):
                area = m.group(1)
            elif (m := COURSE.match(l)):
                head = m.group(1)
            continue
        if (m := CELL.match(l)):
            key = tuple(map(int, m.groups()))
            if key[:2] == (0, 0):
                cells = {}; out.append((area, head, cells))
            cur = key; cells[cur] = []
        elif cur is not None:
            cells[cur].append(l.strip())
    return out

def knowledge(cells):
    """표 하나 → [(영역 칸 또는 None, 범주, 이름, 열 값들 또는 None)] — 열 값 = 학년군 또는 통합교과 과목, None = 한 열 표."""
    cols = {}
    for (r, c, rs, cs), t in cells.items():
        h = re.sub(r"\s", "", "".join(t))
        if (m := re.match(r"^([1-6])[~∼-]([1-6])학년(군)?$", h)) and m.groups()[:2] in GRADE_HEAD:
            cols.update({x: GRADE_HEAD[m.groups()[:2]] for x in range(c, c + cs)})  # 수학 「1~3학년」 아래 1·2·3학년 세 칸
        elif h == "중학교":  # 도덕
            cols.update({x: "중1~3" for x in range(c, c + cs)})
        elif " ".join(t) in ABBR:
            cols[c] = " ".join(t)
    out = []
    for know in [k for k, t in sorted(cells.items()) if ko(" ".join(t)) == "지식이해"]:  # 통합교과는 영역마다 지식⋅이해 칸
        r0, c0, rs0, _ = know
        rows = [(k, t) for k, t in sorted(cells.items()) if r0 <= k[0] < r0 + rs0 and k != know and t]
        first = min(cols) if cols else max(k[1] for k, _ in rows)
        strands = [(k, re.sub(r"\s+", " ", " ".join(t)).replace("⋅ ", "⋅").strip()) for k, t in rows if c0 < k[1] < first]  # 두 줄 칸(생물의 / 구조와 에너지)
        area = next((re.sub(r"\s+", " ", " ".join(t)) for (r, c, rs, cs), t in cells.items() if c == 0 < c0 and r <= r0 < r + rs and t), None)
        for (r, c, rs, cs), t in rows:
            vals = [cols[x] for x in range(c, c + cs) if x in cols] if cols else None  # 두 학년 칸에 걸친 칸 = 두 학년 모두
            if c < first or vals == []:
                continue
            strand = next((s for (sr, sc, srs, _), s in strands if sr <= r < sr + srs), None)
            for line in t:
                for it in re.split(r"(?:^|\s+)[⋅∙•]", line.strip()):  # 글머리는 줄 처음이나 빈칸 뒤 — 「재해⋅재난」의 가운뎃점은 이름 안
                    if ko(it) or re.search(r"[A-Za-z0-9]", it):  # 빈 칸 표시 「-」 제외
                        out.append((area, strand, it.strip(), vals))
    return out

def annex_concepts(data, corpus, stds, annex):
    src = next(s for s in json.load(open(os.path.join(data, "sources.json")))["sources"] if s["annex"] == annex)
    subject = re.sub(r"\(.*\)", "", SUBJECT[annex])
    out = []
    for block, codes in blocks(lines(os.path.join(corpus, "hwp", f"{src['seq']}.hwp")), stds):
        courses = list(dict.fromkeys(stds[c]["course"] for c in codes))
        tabs = content_tables(block)
        by_area = sum(nm(stds[c].get("unit")) in {nm(a) for a, _, _ in tabs} for c in codes) * 2 > len(codes)
        for ti, (t_area, head, cells) in enumerate(tabs):
            # 한 열 표의 과목: 표 앞 과목 머리 → 블록 과목 수 = 표 수면 순서대로(한국사 1·2) → 가장 많은 과목
            course = next((c for c in courses if head and nm(c) == nm(head)), None) or (courses[ti] if len(courses) == len(tabs) > 1 else
                     collections.Counter(stds[c]["course"] for c in codes).most_common(1)[0][0] if codes else None)
            tab = []
            for area, strand, name, vals in knowledge(cells):
                if vals is None:
                    g = collections.Counter(stds[c]["grade"] for c in codes if stds[c]["course"] == course).most_common(1)[0][0]
                    targets = [(g, course, [c for c in codes if stds[c]["course"] == course])]
                elif vals[0] in ABBR:  # 통합교과 표는 첫 과목(바른 생활) 블록에만 있다 — 기준은 그 과목 전체에서
                    targets = [("초1~2", v, [c for c in stds if c.startswith("2" + ABBR[v])]) for v in vals]
                else:  # 초·중은 학년군만 — 사회 「지리 영역」, 실과 「초등학교 실과」 같은 과목 칸은 보지 않는다
                    targets = [(g, None, [c for c in codes if stds[c]["grade"] == g]) for g in vals]
                for g, crs, pool in targets:
                    if any((x["course"], x["grade"], x["name"]) == (crs, g, name) for x in out):
                        continue
                    if by_area:  # 단원명 = 영역명인 교과(국어 「읽기」)는 그 영역 기준 안에서 — 과학은 단원이 영역 아래 따로라(9과19 「운동과 에너지」 하나만 같다) 그대로
                        pool = [c for c in pool if nm(stds[c].get("unit")) in (nm(area), nm(t_area))] or pool
                    ws = words(name) or [name]
                    sc = {c: sum(len(w) for w in ws if w in stds[c]["text"] + " " + (stds[c].get("unit") or "")) for c in pool}
                    top = max(sc.values(), default=0)
                    x = {"id": "|".join(p for p in (subject, g, crs, name) if p), "subject": subject, "area": area or t_area, "strand": strand, "name": name, "grade": g,
                         "band": g, "course": crs, "standards": [c for c, v in sc.items() if top and v == top], "standardsBy": "낱말"}
                    out.append(x); tab.append((x, pool))
            for k, (c, pool) in enumerate(tab):  # 요소 낱말이 기준 문장에 없으면(대전 · 옴의 법칙) 같은 칸의 앞(첫 요소면 뒤) 요소의 기준 — 칸 안 순서가 기준 순서를 따른다
                if not c["standards"]:
                    cell = [x for x, _ in tab if (x["area"], x["strand"], x["grade"], x["course"]) == (c["area"], c["strand"], c["grade"], c["course"]) and x["standardsBy"] == "낱말" and x["standards"]]
                    near = [x for x in cell if out.index(x) < out.index(c)][-1:] or [x for x in cell if out.index(x) > out.index(c)][:1]
                    if near:
                        c["standards"], c["standardsBy"] = near[0]["standards"], "이웃"
                    else:  # 칸 전체가 0 점 — 범주 이름 낱말로(듣기⋅말하기 맥락), 그것도 0 점이면 비워 둔다(서정⋅서사⋅극⋅교술 · 수와 생활경제) — 억지로 잇지 않는다
                        sc = {s: sum(len(w) for w in words(c["strand"] or "") if w in stds[s]["text"] + " " + (stds[s].get("unit") or "")) for s in pool}
                        top = max(sc.values(), default=0)
                        c["standards"], c["standardsBy"] = [s for s, v in sc.items() if top and v == top], "범주" if top else "없음"
                        if not top and by_area and pool and len(pool) < len([x for x in codes if stds[x]["grade"] == c["grade"]]):  # 영역 안으로 좁혀진 경우만 — 그 학년 영역 기준 전체
                            c["standards"], c["standardsBy"] = pool, "영역"
    return out

def main(data, corpus):
    src = next(s for s in json.load(open(os.path.join(data, "sources.json")))["sources"] if s["annex"] == 8)
    stds = {s["id"]: s for s in json.load(open(os.path.join(data, "standards.json")))["standards"]}
    ls = lines(os.path.join(corpus, "hwp", f"{src['seq']}.hwp"))
    items = tables(ls)
    by_title = standards_by_title(ls)
    year = {norm(it["name"]): it["grade"] for it in items if not it["course"]}  # 중1·중2·중3
    concepts, miss = [], []
    split = []  # 같은 제목이 학년군마다 따로 있다(초1~2 길이 · 초3~4 길이)
    for key, codes in by_title.items():
        if key[0] != "영역":
            for b in dict.fromkeys(c[0] for c in codes):
                split.append((key, [c for c in codes if c[0] == b]))
    for key, codes in split:
        area, name = key
        band = {"2": "초1~2", "4": "초3~4", "6": "초5~6", "9": "중1~3"}[codes[0][0]]
        grade = year.get(norm(name), band) if band == "중1~3" else band
        if grade == "중1~3":
            miss.append(name)
        concepts.append({"id": f"수학|{grade}|{name}", "subject": "수학", "area": area, "name": name, "grade": grade, "band": band, "course": None,
                         "standards": codes, "standardsBy": "제목"})
    high = [x for x in items if x["course"]]
    own = {}  # 기준 하나 → 낱말 점수가 가장 높은 개념 하나(0 점이면 원문 순서상 앞 기준의 개념, 첫 기준이면 영역 첫 개념)
    for (kind, area), pool in by_title.items():
        if kind != "영역":
            continue
        cands = [x for x in high if x["area"] == area]
        prev = cands[0]["name"] if cands else None
        for c in pool:
            def score(x):  # (맞은 글자 수, 개념 이름 중 맞은 비율) — 한 글자 낱말(원)은 낱말 경계에서만
                ws = [re.sub(r"(과|와|의)$", "", w) for w in re.split(r"[\s,]+", x["name"])]
                hit = sum(len(w) for w in ws if (w in stds[c]["text"] if len(w) >= 2 else re.search(r"(^|[\s,])" + w + r"(의|과|와|을|이|\s)", stds[c]["text"])))
                return (hit, hit / sum(map(len, ws)))
            best = max(cands, key=score) if cands else None
            own[c] = best["name"] if best and score(best)[0] else prev
            prev = own[c]
    for it in high:
        hit = [c for c, n in own.items() if n == it["name"] and c.startswith("10공수" + it["course"][-1])]
        if not hit:
            miss.append(it["name"])
        concepts.append({"id": f"수학|고1|{it['name']}", "subject": "수학", "area": it["area"], "name": it["name"], "grade": "고1", "band": "고1",
                         "course": it["course"], "standards": hit, "standardsBy": "낱말"})
    for annex in sorted(SUBJECT):
        if annex == 16:
            continue
        got = annex_concepts(data, corpus, stds, annex)
        if annex == 8:  # 수학 초1~고1 은 위(성취기준 절 제목) — 여기서는 공통수학 밖 과목만(기본수학 · 고2~3)
            got = [c for c in got if c["course"] and not c["course"].startswith("공통수학")]
        print(f"{SUBJECT[annex]} 개념 {len(got)} · 기준 못 정함 {[c['name'] for c in got if not c['standards']][:8]}")
        concepts += got
    subjects = list(dict.fromkeys(c["subject"] for c in concepts))
    json.dump({"version": "v2", "subjects": subjects, "source": "교육부 고시 제2022-33호 [별책 5~22] 교과별 내용 체계 지식⋅이해", "count": len(concepts), "concepts": concepts},
              open(os.path.join(data, "concepts.json"), "w"), ensure_ascii=False, indent=1)
    placed = {c for x in concepts for c in x["standards"]}
    math = [k for k in stds if re.match(r"(\d+수\d|10공수)", k)]
    print(f"개념 {len(concepts)} · 학년/기준 못 정함 {len(miss)} {miss[:10]} · 수학 기준(초1~고1 공통) {len(math)} 중 개념에 놓인 것 {len(placed & set(math))} · 빠진 것 {sorted(set(math) - placed)[:12]}")

if __name__ == "__main__":
    main(*sys.argv[1:3])
