"""HWP / HWPX / PDF 新聞稿 → 純文字（只需 olefile、pypdf）
HWP 5.0：OLE 複合檔，BodyText/SectionN 串流（通常 zlib raw deflate 壓縮），
內含一連串紀錄；HWPTAG_PARA_TEXT（tag 67）是 UTF-16LE 段落文字。表格每個儲存格也是段落，
所以表格會依「列 → 儲存格」順序變成一段一段的文字。
"""
import io, re, zlib, zipfile

PARA_TEXT = 67
# 段落文字中的控制字元：1～31。其中下列 inline / extended 控制碼後面還帶 7 個 WCHAR（共佔 8 個字元）
EXT = {1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 12, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23}


def _para(b):
    out, i, n = [], 0, len(b) // 2
    while i < n:
        c = b[2 * i] | (b[2 * i + 1] << 8)
        if c < 32:
            if c in EXT:
                i += 8
                continue
            if c in (10, 13):
                out.append("\n")
            elif c == 24:
                out.append("-")
            elif c in (30, 31):
                out.append(" ")
            i += 1
            continue
        out.append(chr(c))
        i += 1
    return "".join(out)


def hwp_text(data):
    import olefile
    ole = olefile.OleFileIO(io.BytesIO(data))
    hdr = ole.openstream("FileHeader").read()
    compressed = bool(hdr[36] & 1)
    secs = sorted((s for s in ole.listdir() if s[0] == "BodyText"), key=lambda s: int(re.sub(r"\D", "", s[1]) or 0))
    paras = []
    for s in secs:
        raw = ole.openstream(s).read()
        if compressed:
            raw = zlib.decompress(raw, -15)
        i = 0
        while i + 4 <= len(raw):
            h = int.from_bytes(raw[i:i + 4], "little")
            tag, size = h & 0x3FF, (h >> 20) & 0xFFF
            i += 4
            if size == 0xFFF:
                size = int.from_bytes(raw[i:i + 4], "little")
                i += 4
            if tag == PARA_TEXT:
                paras.append(_para(raw[i:i + size]))
            i += size
    return "\n".join(paras)


def hwpx_text(data):
    z = zipfile.ZipFile(io.BytesIO(data))
    secs = sorted((n for n in z.namelist() if re.match(r"Contents/section\d+\.xml$", n)),
                  key=lambda n: int(re.sub(r"\D", "", n)))
    paras = []
    for n in secs:
        xml = z.read(n).decode("utf-8", "replace")
        for p in re.findall(r"<hp:p\b.*?</hp:p>", xml, re.S):
            t = "".join(re.findall(r"<hp:t[^>]*>(.*?)</hp:t>", p, re.S))
            t = re.sub(r"<[^>]+>", "", t)
            paras.append(t.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&"))
    return "\n".join(paras)


def pdf_text(data):
    from pypdf import PdfReader
    return "\n".join((p.extract_text() or "") for p in PdfReader(io.BytesIO(data)).pages)


def any_text(data, name=""):
    name = name.lower()
    if data[:4] == b"%PDF":
        return pdf_text(data)
    if data[:2] == b"PK":
        return hwpx_text(data)
    if data[:8] == bytes.fromhex("d0cf11e0a1b11ae1"):
        return hwp_text(data)
    raise ValueError(f"不支援的檔案格式：{name} {data[:8].hex()}")
