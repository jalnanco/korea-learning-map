# 교과·과목 이름 규칙 — 학습 목록(build_docs)과 단원 노드(extract_links)가 같이 쓴다.
import re

SUBJECT = {5: "국어", 6: "도덕", 7: "사회", 8: "수학", 9: "과학", 10: "실과·기술가정·정보", 11: "체육", 12: "음악", 13: "미술", 14: "영어",
           15: "통합교과(초1~2)", 17: "한문", 18: "중학교 선택", 19: "고등학교 교양", 20: "과학 계열 선택", 21: "체육 계열 선택", 22: "예술 계열 선택"}
ELECTIVE_ANNEX = {17, 18}  # 한문 · 중학교 선택(보건·환경·진로와 직업)
ABBR = {"바": "바른 생활", "슬": "슬기로운 생활", "즐": "즐거운 생활"}

def course_of(s):  # 초·중은 코드 약칭으로(과목명 필드가 없는 교과가 많다), 고교는 과목명
    if s.get("course"):
        return re.sub(r"\s+(\d)$", r"\1", s["course"].strip())  # 「통합사회 1」 → 「통합사회1」
    ab = re.match(r"\d+(\D+?)\d*-", s["id"]).group(1)
    return ABBR.get(ab)

def label(s, annex):  # 노드·목록에 보이는 과목 이름 — 과목명이 없으면 교과명
    return course_of(s) or SUBJECT[annex]

def is_core(s, annex):  # 필수 = 모두가 배우는 것: 초·중 전 교과(한문·중학교 선택 제외) + 고1 공통과목
    if s["grade"] == "고1":
        return s.get("courseType") == "공통과목"
    return not s["grade"].startswith("고") and annex not in ELECTIVE_ANNEX
