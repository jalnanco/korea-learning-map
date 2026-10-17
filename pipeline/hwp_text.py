# HWP 5.x 본문 → 문단당 한 줄 텍스트. 줄바꿈으로 낱말이 갈리지 않는 원문을 얻기 위한 것(PDF 는 쪽 번호용).
# pyhwp 는 DocInfo 의 글꼴 이름 디코딩에서 멈춰서(UnicodeDecodeError) 본문 스트림만 직접 읽는다.
#   python3 pipeline/hwp_text.py <file.hwp>  > out.txt
#   --cells: 표 칸마다 `⟪칸 행 열 행병합 열병합⟫` 줄을 앞에 낸다(내용 체계 표의 학년 칸을 되살릴 때)
import struct, sys, zlib
import olefile

PARA_HEADER, PARA_TEXT, LIST_HEADER, EQEDIT = 66, 67, 72, 88
EQ = "\ue000"  # 본문 안 수식 자리 — 같은 문단에 딸린 EQEDIT 스크립트로 채운다(「x축」의 x 가 수식 개체다)
# 컨트롤 문자: 1글자짜리(char) vs 8글자(16바이트)짜리(inline/extended)
CHAR_CTRL = {0, 10, 13, 24, 25, 26, 27, 28, 29, 30, 31}

def records(data):
    i = 0
    while i + 4 <= len(data):
        h = struct.unpack_from("<I", data, i)[0]; i += 4
        tag, level, size = h & 0x3FF, (h >> 10) & 0x3FF, (h >> 20) & 0xFFF
        if size == 0xFFF:
            size = struct.unpack_from("<I", data, i)[0]; i += 4
        yield tag, level, data[i:i + size]; i += size

def para_text(b):
    out, i = [], 0
    while i + 2 <= len(b):
        c = struct.unpack_from("<H", b, i)[0]
        if c < 32:
            if c in CHAR_CTRL:
                if c in (10, 13): out.append("\n")
                elif c == 24: out.append("-")   # 하이픈
                elif c in (30, 31): out.append(" ")  # 묶음 빈칸·고정폭 빈칸
                i += 2
            else:
                if b[i + 2:i + 6] == b"deqe":    # 수식(ctrl id 'eqed', 거꾸로 저장)
                    out.append(EQ)
                i += 16                          # 표·그림 등 확장 컨트롤 — 본문은 아래 문단 레코드로 따로 나온다
            continue
        out.append(chr(c)); i += 2
    return "".join(out).encode("utf-16-le", "surrogatepass").decode("utf-16-le", "replace")  # BMP 밖 글자(서로게이트 쌍) 복원

def main(path, cells=False):
    ole = olefile.OleFileIO(path)
    compressed = struct.unpack_from("<I", ole.openstream("FileHeader").read(), 36)[0] & 1
    sections = sorted((s for s in ole.listdir() if s[0] == "BodyText"), key=lambda s: int(s[1].replace("Section", "")))
    for s in sections:
        data = ole.openstream(s).read()
        if compressed:
            data = zlib.decompress(data, -15)
        paras, open_at = [], {}  # 문단 = [텍스트, 수식 스크립트들] · 표 안 문단이 끼어도 나온 순서대로 낸다
        for tag, level, body in records(data):
            if tag == PARA_HEADER:
                open_at = {k: v for k, v in open_at.items() if k < level}
            elif tag == PARA_TEXT:
                paras.append([para_text(body), [], (level - 1) // 2]); open_at[level - 1] = paras[-1]
            elif tag == LIST_HEADER and cells and len(body) >= 16:  # 표 칸: 문단 수·속성 다음 열·행·열병합·행병합
                col, row, cspan, rspan = struct.unpack_from("<4H", body, 8)
                paras.append([f"⟪칸 {row} {col} {rspan} {cspan}⟫", [], level // 2])
            elif tag == EQEDIT and level - 2 in open_at:
                n = struct.unpack_from("<H", body, 4)[0]
                open_at[level - 2][1].append(body[6:6 + 2 * n].decode("utf-16-le", "replace").strip())
        for t, eqs, depth in paras:
            for e in eqs:
                t = t.replace(EQ, f"⟦{e}⟧", 1)  # 추출기가 읽기용 기호로 바꾸고 원본은 따로 보존한다
            t = t.replace(EQ, "").rstrip("\n")
            if t.strip():
                print("\t" * depth + t.replace("\n", " "))  # 탭 수 = 표 칸 중첩 깊이

if __name__ == "__main__":
    main(sys.argv[1], "--cells" in sys.argv[2:])
