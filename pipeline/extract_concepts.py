# 수학 개념층(v1) — 고시문 「내용 체계」 지식⋅이해 칸 = 개념 노드. LLM 없음.
#   python3 pipeline/extract_concepts.py data/kr corpus
# 초1~중3: 개념 = 성취기준 절의 지식⋅이해 제목(󰊱 네 자리 이하의 수) — 기준을 그 아래에 묶어 두므로 개념 → 기준이 원문 그대로다.
#          학년군은 기준 코드, 중1·중2·중3 은 내용 체계 표(중학교 1~3학년 칸이 다시 세 칸)에서 같은 이름의 칸으로 찾는다.
# 고1(공통수학1·2): 표의 칸이 영역(다항식 …)이고 기준도 영역으로 묶여 있어, 영역 안에서 개념 낱말이 겹치는 기준에 잇는다.
# 원문 근거: 「초⋅중학교의 지식⋅이해 범주는 학년(군)에 따라 위계성을 가지며, 영역 간에도 위계성을 고려하여 구성하였다.」
import json, os, re, subprocess, sys

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
    json.dump({"version": "v1", "subject": "수학", "source": f"{src['ref']} 내용 체계 지식⋅이해", "count": len(concepts), "concepts": concepts},
              open(os.path.join(data, "concepts.json"), "w"), ensure_ascii=False, indent=1)
    placed = {c for x in concepts for c in x["standards"]}
    math = [k for k in stds if re.match(r"(\d+수\d|10공수)", k)]
    print(f"개념 {len(concepts)} · 학년/기준 못 정함 {len(miss)} {miss[:10]} · 수학 기준(초1~고1 공통) {len(math)} 중 개념에 놓인 것 {len(placed & set(math))} · 빠진 것 {sorted(set(math) - placed)[:12]}")

if __name__ == "__main__":
    main(*sys.argv[1:3])
