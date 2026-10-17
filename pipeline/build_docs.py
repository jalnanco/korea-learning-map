# 원문층 → 사람이 읽는 학습 목록(docs/). LLM 없음 — standards.json 을 펼치기만 한다.
#   python3 pipeline/build_docs.py data/kr docs
# 필수(모두가 배우는 것) = 초·중 전 교과(한문·중학교 선택 교과 제외) + 고1 공통과목. 나머지는 선택.
import collections, json, os, re, shutil, sys
from urllib.parse import quote
from names import SUBJECT, course_of, is_core

GRADES = ["초1~2", "초3~4", "초5~6", "중1~3", "고1", "고2~3"]
LINK = re.compile(r"연계(된다|한다|하여|할 수)")

DATA = None

def main(data, out):
    global DATA
    DATA = data
    src = {x["seq"]: x for x in json.load(open(os.path.join(data, "sources.json")))["sources"]}
    stds = json.load(open(os.path.join(data, "standards.json")))["standards"]
    for s in stds:
        s["annex"] = src[s["sourceSeq"]]["annex"]
        s["core"] = is_core(s, s["annex"])
        s["courseName"] = course_of(s)
        s["url"] = src[s["sourceSeq"]]["url"]
    if os.path.isdir(out):
        shutil.rmtree(out)
    os.makedirs(os.path.join(out, "교과"))
    by_annex = collections.defaultdict(list)
    for s in stds:
        by_annex[s["annex"]].append(s)
    rel = relations(data)
    for annex, ss in by_annex.items():
        open(os.path.join(out, "교과", f"{SUBJECT[annex]}.md"), "w").write(subject_page(annex, ss, rel))
    open(os.path.join(out, "필수-공통.md"), "w").write(core_page(stds))
    open(os.path.join(out, "README.md"), "w").write(index_page(stds, by_annex))
    print(f"교과 {len(by_annex)}쪽 · 성취기준 {len(stds)} · 필수 {sum(s['core'] for s in stds)}")

def tree(ss):  # 학년군 → 과목 → 단원 (원문 순서 유지)
    t = {}
    kinds = ["공통과목", "일반선택과목", "진로선택과목", "융합선택과목"]
    for s in sorted(ss, key=lambda s: (GRADES.index(s["grade"]), kinds.index(s["courseType"]) if s.get("courseType") in kinds else 0)):
        t.setdefault(s["grade"], {}).setdefault(s["courseName"], {}).setdefault(s["unit"], []).append(s)
    return t

def relations(data):  # 단원 id → {선수·후속·관련: [대상 id]} — links.json 양방향(추출 전이면 빈 것)
    path = os.path.join(data, "links.json")
    if not os.path.exists(path):
        return {}, {}
    annex_of = {u["id"]: u["annex"] for u in json.load(open(os.path.join(data, "units.json")))["units"]}
    flip = {"prerequisite": "followup", "followup": "prerequisite", "related": "related"}
    rel = collections.defaultdict(lambda: collections.defaultdict(list))
    for l in json.load(open(path))["links"]:
        for a, b, r in ((l["from"], l["to"], l["relation"]), (l["to"], l["from"], flip[l["relation"]])):
            if b not in rel[a][r]:
                rel[a][r].append(b)
    return rel, annex_of

def unit_link(target, here_annex, annex_of):  # 다른 교과 문서면 그 파일로, 과목 전체(`|*`)면 과목 머리로
    g, c, u = target.split("|")
    annex = annex_of.get(target) or next((a for t, a in annex_of.items() if t.startswith(f"{g}|{c}|")), here_annex)
    page = "" if annex == here_annex else f"{quote(SUBJECT[annex])}.md"
    text = f"{g} {c}" + (f" · {u}" if u and u != "*" else (" (과목 전체)" if u == "*" else ""))
    return f"[{text}]({page}#{anchor(g, c, u if u != '*' else '')})"

def nav_lines(rel, uid, annex, who=""):  # 「⬅️ 먼저 / ➡️ 이어서 / ↔️ 함께」 — 고시문이 밝힌 연계만
    r = rel[0].get(uid, {})
    nav = [f"> {who}{tag} " + " · ".join(unit_link(t, annex, rel[1]) for t in r[k]) + "  " for k, tag in (("prerequisite", "⬅️ 먼저"), ("followup", "➡️ 이어서"), ("related", "↔️ 함께")) if r.get(k)]
    return nav + [""] if nav else []

def anchor(*parts):
    return "-".join(re.sub(r"[^\w가-힣]+", "-", p or "").strip("-") for p in parts if p)

def subject_page(annex, ss, rel=({}, {})):
    name = SUBJECT[annex]
    o = [f"# {name}", "", f"원문: {ss[0]['ref']} · [고시문 PDF]({ss[0]['url']}) · 성취기준 {len(ss)}개 (필수 {sum(s['core'] for s in ss)})", "",
         "> 🟢 필수 = 모두가 배우는 것 · ⚪ 선택. 문장은 고시문 원문 그대로다. 「연계」는 고시문이 밝힌 학년·단원 간 연결이다.", ""]
    t = tree(ss)
    o.append("## 차례")
    for g, courses in t.items():
        o.append(f"- **{g}**: " + " · ".join(f"[{c or name}](#{anchor(g, c or name)}) ({sum(len(v) for v in units.values())})" for c, units in courses.items()))
    o.append("")
    for g, courses in t.items():
        for c, units in courses.items():
            first = next(iter(units.values()))[0]
            mark = "🟢 필수" if first["core"] else "⚪ 선택"
            kind = f" · {first['courseType']}" if first.get("courseType") else ""
            o += [f'<a id="{anchor(g, c or name)}"></a>', f"## {g} · {c or name}", "", f"{mark}{kind}", ""]
            o += nav_lines(rel, f"{g}|{c or name}|*", annex, "과목 ")
            for u, items in units.items():
                if u:  # 단원 구분이 없는 과목(국어·영어 선택 일부)은 기준을 바로 늘어놓는다
                    o += [f'<a id="{anchor(g, c or name, u)}"></a>', f"### {u}", ""]
                for s in items:
                    o.append(f"- **[{s['id']}]** {s['text']} <sub>p.{s['page']}</sub>")
                    if s.get("notes"):
                        o.append(f"  <details><summary>해설</summary>\n\n  " + "\n\n  ".join(s["notes"]) + "\n  </details>")
                links = [n for n in items[0].get("unitNotes", []) if LINK.search(n)]
                if links:
                    o += [""] + [f"> 🔗 {n}" for n in links]
                nav = nav_lines(rel, f"{g}|{c or name}|{u or ''}", annex)
                if nav:
                    o += [""] + nav[:-1]
                o.append("")
    return "\n".join(o)

def core_page(stds):
    core = [s for s in stds if s["core"]]
    o = ["# 모두가 배우는 것 — 필수 공통 교육과정 목차", "",
         f"초등학교 1학년부터 고등학교 1학년까지 **모든 학생이 배우는** 성취기준 {len(core)}개를 학년군·교과·단원으로 줄였다. "
         "「상식으로 무엇을 아는가」의 원문 기준이며, 다시 배울 때 어디까지 내려가면 되는지 보는 지도다.", "",
         "- 제외: 한문·중학교 선택 교과(보건·환경·진로와 직업)·고2~3 선택 과목 → [전체 지도](README.md)",
         "- 고1 기본수학·기본영어는 공통수학·공통영어 대신 들을 수 있는 과목이라 함께 싣는다.", ""]
    cross_path = os.path.join(DATA, "cross_curricular.json")
    if os.path.exists(cross_path):
        c = json.load(open(cross_path))
        o += ["## 교과를 가로질러 — 범교과 학습 주제", "", f"총론({c['ref']}, [p.{c['page']}]({c['url']}))은 교과 밖에서도 다음 10개 주제를 모든 교육 활동에 걸쳐 다루게 한다. "
              "숫자는 성취기준 해설·적용 시 고려 사항이 주제 이름을 그대로 언급한 기준 수다.", "",
              " · ".join(f"{t['name']} ({len(t['mentionedBy'])})" for t in c["topics"]), ""]
    for g in GRADES:
        gs = [s for s in core if s["grade"] == g]
        if not gs:
            continue
        o += [f"## {g} ({len(gs)})", ""]
        by_subj = collections.OrderedDict()
        for s in sorted(gs, key=lambda s: s["annex"]):
            by_subj.setdefault((SUBJECT[s["annex"]], s["courseName"]), collections.OrderedDict()).setdefault(s["unit"], []).append(s["id"])
        for (subj, c), units in by_subj.items():
            label = f"{subj} · {c}" if c else subj
            o.append(f"- **[{label}](교과/{quote(subj)}.md#{anchor(g, c or subj)})** — " + " · ".join(f"{u or '성취기준'} ({len(ids)})" for u, ids in units.items()))
        o.append("")
    return "\n".join(o)

def index_page(stds, by_annex):
    o = ["# 배울 것 전체 지도", "", f"2022 개정 교육과정 성취기준 {len(stds)}개 — 교과 × 학년군. 숫자를 누르면 그 교과 문서로 간다. "
         f"모두가 배우는 것만 보려면 → **[필수 공통 목차](필수-공통.md)** ({sum(s['core'] for s in stds)}개)", "",
         "| 교과 | " + " | ".join(GRADES) + " | 합계 |", "|---|" + "---:|" * (len(GRADES) + 1)]
    for annex in sorted(by_annex):
        ss = by_annex[annex]
        c = collections.Counter(s["grade"] for s in ss)
        cells = [str(c[g]) if c[g] else "" for g in GRADES]
        o.append(f"| [{SUBJECT[annex]}](교과/{quote(SUBJECT[annex])}.md) | " + " | ".join(cells) + f" | {len(ss)} |")
    c = collections.Counter(s["grade"] for s in stds)
    o.append("| **합계** | " + " | ".join(f"**{c[g]}**" for g in GRADES) + f" | **{len(stds)}** |")
    o += ["", "고2~3 열은 모두 선택 과목이다(학생마다 고른다). 원문 출처·라이선스는 [NOTICE](../NOTICE.md)."]
    return "\n".join(o)

if __name__ == "__main__":
    main(*sys.argv[1:3])
