"""一键验证: 逐步覆盖各板块。

运行: python verify.py

第 1 步  PDF 渲染核心(排版/字体/有效性)
第 2 步  三板块中文页面 + 后端 API(用 TestClient, 不发真实 HTTP)
后续步骤会在此追加。
"""

import re
from pathlib import Path
from urllib.parse import unquote

from renderer import (
    build_html_doc,
    extract_title,
    markdown_to_jpg,
    markdown_to_pdf,
    markdown_to_png,
    markdown_to_pptx,
    markdown_to_word,
)

BASE = Path(__file__).parent


def step1_pdf_core() -> None:
    md_text = (BASE / "sample.md").read_text(encoding="utf-8")
    pdf, filename = markdown_to_pdf(md_text)
    assert pdf.startswith(b"%PDF") and b"%%EOF" in pdf, "PDF 无效"
    out = BASE / "output" / "sample.pdf"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(pdf)
    print(f"[OK] 1. PDF 有效: {out} ({len(pdf)} 字节)")
    assert filename == "Markdown 转 PDF 排版测试.pdf", f"文件名异常: {filename!r}"
    print("[OK] 2. 文件名取自一级标题")
    doc = build_html_doc(md_text)
    for kw in ["text-indent: 2em", "Microsoft YaHei", "border-left: 5px solid #2f6feb",
               "tr:nth-child(even) td", "page-break-inside: avoid"]:
        assert kw in doc, f"排版缺失: {kw}"
    print("[OK] 3. 排版要素齐全(缩进/中文字体/标题竖条/隔行/避免跨页)")
    assert extract_title(md_text) == "Markdown 转 PDF 排版测试"
    print("[OK] 4. extract_title 正常")


def step1b_word_core() -> None:
    import io
    import zipfile
    md_text = (BASE / "sample.md").read_text(encoding="utf-8")
    data, filename = markdown_to_word(md_text)
    assert data.startswith(b"PK"), "docx 不是有效的 zip"
    zf = zipfile.ZipFile(io.BytesIO(data))
    assert "word/document.xml" in zf.namelist(), "缺少 document.xml"
    xml = zf.read("word/document.xml").decode("utf-8")
    assert "排版测试" in xml, "标题中文缺失"
    assert "Microsoft YaHei" in xml, "未设置中文字体"
    out = BASE / "output" / "sample.docx"
    out.write_bytes(data)
    print(f"[OK] 5. Word 有效: {out} ({len(data)} 字节, 中文字体已设)")
    assert filename == "Markdown 转 PDF 排版测试.docx"
    print("[OK] 6. Word 文件名取自一级标题")


def step1c_image_core() -> None:
    md_text = (BASE / "sample.md").read_text(encoding="utf-8")
    png, pn = markdown_to_png(md_text)
    assert png.startswith(b"\x89PNG"), "PNG 头无效"
    (BASE / "output" / "sample.png").write_bytes(png)
    print(f"[OK] 7. PNG 有效: {pn} ({len(png)} 字节)")
    jpg, jn = markdown_to_jpg(md_text)
    assert jpg.startswith(b"\xff\xd8\xff"), "JPG 头无效"
    (BASE / "output" / "sample.jpg").write_bytes(jpg)
    print(f"[OK] 8. JPG 有效: {jn} ({len(jpg)} 字节)")


def step1d_ppt_core() -> None:
    import io
    import zipfile
    from pptx import Presentation
    md_text = (BASE / "sample.md").read_text(encoding="utf-8")
    data, filename = markdown_to_pptx(md_text)
    assert data.startswith(b"PK"), "pptx 不是有效的 zip"
    out = BASE / "output" / "sample.pptx"
    out.write_bytes(data)
    print(f"[OK] 9. PPT 有效: {out} ({len(data)} 字节)")
    assert filename == "Markdown 转 PDF 排版测试.pptx"
    print("[OK] 10. PPT 文件名取自一级标题")
    # 读回校验: 页数/封面标题/页码/中文字体
    prs = Presentation(io.BytesIO(data))
    slides = list(prs.slides)
    assert len(slides) >= 2, "PPT 页数过少"
    def texts(s):
        for sh in s.shapes:
            if sh.has_text_frame:
                for p in sh.text_frame.paragraphs:
                    t = "".join(r.text for r in p.runs)
                    if t.strip():
                        yield t
    assert any("排版测试" in t for t in texts(slides[0])), "封面缺主标题"
    for idx, s in enumerate(slides, start=1):
        if idx == 1:
            continue
        assert str(idx) in list(texts(s)), f"第{idx}页缺页码"
    xml = b"".join(zf.read(n) for zf in [zipfile.ZipFile(io.BytesIO(data))]
                   for n in zf.namelist() if n.startswith("ppt/slides/slide"))
    assert b"a:ea" in xml and "Microsoft YaHei".encode() in xml, "未写中文字体"
    # 封面文字自动换行(长标题/介绍不溢出): 封面所有文本框都开 word_wrap
    cover_txt = [sh for sh in slides[0].shapes if sh.has_text_frame and sh.text_frame.text.strip()]
    assert cover_txt, "封面无文本框"
    assert all(sh.text_frame.word_wrap for sh in cover_txt), "封面文本框未全部开启换行"
    # 背景图已嵌入 + 文字区半透明面板(叠字可读)
    zf = zipfile.ZipFile(io.BytesIO(data))
    assert any(n.startswith("ppt/media/") for n in zf.namelist()), "未嵌入背景图"
    assert b"a:blip" in xml, "幻灯片未引用背景图"
    assert b"a:alpha" in xml, "文字区面板未设不透明度"
    print(f"[OK] 11. PPT 结构正确({len(slides)}页, 封面/页码/中文字体/背景图/文字区面板齐全)")


def step2_page_and_api() -> None:
    from fastapi.testclient import TestClient
    import main

    client = TestClient(main.app)

    # 首页三板块结构(中文界面)
    r = client.get("/")
    assert r.status_code == 200
    for label in ["输入区", "实时预览", "输出格式", "加载示例", "下载"]:
        assert label in r.text, f"页面缺少板块: {label}"
    print("[OK] 12. 三板块中文页面(输入区/实时预览/输出格式/下载按钮齐全)")

    # 输入框固定高度 + 内部滚动(不再自动增高), 内容多时用滚动条
    page_css = r.text
    assert "autoResize" not in page_css, "仍残留 autoResize(应为固定高度+滚动)"
    assert "min-height: 240px" in page_css, "输入框缺少固定最小高度"
    assert re.search(r"#md-input\s*\{[^}]*overflow:\s*auto", page_css), "输入框应 overflow:auto"
    # 整页锁死一屏, 三板块内部滚动: body 100vh + board 单行 + panel 锁高
    assert "height: 100vh" in page_css, "整页未锁定为单屏(100vh)"
    assert "grid-template-rows: 1fr" in page_css, "三板块未等高锁定"
    assert "min-height: 0; overflow: hidden" in page_css, "板块未锁定高度(内容应在板块内滚动)"
    # 中栏 panel-body 可滚动
    assert re.search(r"\.panel-body\s*\{[^}]*overflow:\s*auto", page_css), "中栏未启用内部滚动"
    print("[OK] 13. 输入框固定高度+内部滚动, 整页锁定单屏, 中栏内部滚动")

    # /api/formats (五种格式全部可用)
    d = client.get("/api/formats").json()
    for fmt in ("pdf", "word", "pptx", "png", "jpg"):
        assert fmt in d["available"], f"{fmt} 未加入可用格式"
    print(f"[OK] 14. /api/formats 可用格式: {d['available']}")

    # /api/html-preview
    r = client.get("/api/html-preview", params={"md": "# 标题\n\n正文"})
    data = r.json()
    html = data["html"]
    assert "<h1" in html and "标题" in html and "正文" in html, f"预览内容异常: {html!r}"
    # 预览必须带与 PDF 一致的排版样式, 且已作用域化(#preview), 不污染页面其他区域
    pcss = data.get("css", "")
    assert "text-indent: 2em" in pcss, "预览缺少排版样式, 与 PDF 不一致"
    assert "#preview" in pcss, "预览样式未作用域化"
    assert "@page" not in pcss, "预览样式不应包含 @page"
    assert "\nbody" not in pcss and "body {" not in pcss, "预览样式漏出裸 body 选择器"
    print("[OK] 15. /api/html-preview 返回渲染 HTML + 作用域化(#preview)排版样式")

    # /api/sample
    assert "Markdown 转 PDF 排版测试" in client.get("/api/sample").json()["md"]
    print("[OK] 16. /api/sample 返回示例文档")

    # /api/convert 文本转 PDF(含中文文件名 RFC5987)
    r = client.post("/api/convert", data={"md": "# 产品说明书\n\n正文", "format": "pdf"})
    assert r.status_code == 200 and r.content.startswith(b"%PDF")
    cd = r.headers.get("content-disposition", "")
    m = re.search(r"filename\*=UTF-8''(.+?)(?:;|$)", cd, re.I)
    assert m and unquote(m.group(1)) == "产品说明书.pdf", f"文件名编码异常: {cd}"
    print("[OK] 17. /api/convert 文本转 PDF, 中文文件名编码正确")

    # /api/convert 文本转 Word(中文文件名 + 合法 docx)
    r = client.post("/api/convert", data={"md": "# 产品说明书\n\n正文", "format": "word"})
    assert r.status_code == 200 and r.content.startswith(b"PK"), "Word 转换失败"
    cd = r.headers.get("content-disposition", "")
    m = re.search(r"filename\*=UTF-8''(.+?)(?:;|$)", cd, re.I)
    assert m and unquote(m.group(1)) == "产品说明书.docx", f"Word 文件名异常: {cd}"
    assert r.headers["content-type"].startswith("application/vnd.openxmlformats"), "Word MIME 错误"
    print("[OK] 18. /api/convert 文本转 Word(.docx), 中文文件名与 MIME 正确")

    # /api/convert 文本转 PPT(合法 pptx + MIME + 中文字体)
    r = client.post("/api/convert", data={"md": "# 产品说明书\n\n- 要点A\n- 要点B", "format": "pptx"})
    assert r.status_code == 200 and r.content.startswith(b"PK"), "PPT 接口失败"
    cd = r.headers.get("content-disposition", "")
    m = re.search(r"filename\*=UTF-8''(.+?)(?:;|$)", cd, re.I)
    assert m and unquote(m.group(1)) == "产品说明书.pptx", f"PPT 文件名异常: {cd}"
    assert r.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.presentationml"), "PPT MIME 错误"
    import io as _io, zipfile as _zip
    _xml = b"".join(_zf.read(n) for _zf in [_zip.ZipFile(_io.BytesIO(r.content))]
                    for n in _zf.namelist() if n.startswith("ppt/slides/slide"))
    assert b"a:ea" in _xml, "PPT 未写中文字体"
    print("[OK] 19. /api/convert 文本转 PPT(.pptx), 文件名/MIME/中文字体正确")

    # /api/convert 转 PNG / JPG(文件头 + MIME)
    r = client.post("/api/convert", data={"md": "# 产品说明书\n\n正文", "format": "png"})
    assert r.status_code == 200 and r.content.startswith(b"\x89PNG"), "PNG 接口失败"
    assert r.headers["content-type"] == "image/png"
    print("[OK] 20. /api/convert 文本转 PNG, 文件头与 MIME 正确")
    r = client.post("/api/convert", data={"md": "# 产品说明书\n\n正文", "format": "jpg"})
    assert r.status_code == 200 and r.content.startswith(b"\xff\xd8\xff"), "JPG 接口失败"
    assert r.headers["content-type"] == "image/jpeg"
    print("[OK] 21. /api/convert 文本转 JPG, 文件头与 MIME 正确")

    # /api/convert 空内容 400
    assert client.post("/api/convert", data={"md": "   ", "format": "pdf"}).status_code == 400
    print("[OK] 22. 空内容返回 400")

    # /api/convert 非法格式
    r = client.post("/api/convert", data={"md": "# t", "format": "gif"})
    assert r.status_code == 400
    print(f"[OK] 23. 非法格式(gif)返回 {r.status_code}")

    # /health
    assert client.get("/health").json()["status"] == "ok"
    print("[OK] 24. /health 正常")

    # /api/ppt-templates: 6 款模板 + 默认值
    d = client.get("/api/ppt-templates").json()
    assert len(d["templates"]) == 6, f"PPT 模板应 6 款, 实际 {len(d['templates'])}"
    assert d["default"] in [t["key"] for t in d["templates"]]
    assert all(k for t in d["templates"] for k in ("key", "name", "bg", "accent"))
    print(f"[OK] 25. /api/ppt-templates 返回 {len(d['templates'])} 款模板, 默认 {d['default']}")

    # 页面含 PPT 模板区(仅选 PPT 时显示) + 下载带 template 字段
    page_css = client.get("/").text
    assert 'id="tpl-zone"' in page_css and "tpl-grid" in page_css, "页面缺 PPT 模板区"
    assert "toggleTplZone" in page_css, "缺模板区显隐逻辑"
    assert 'form.append("template"' in page_css, "下载未携带 template 字段"
    print("[OK] 26. 页面含 PPT 模板区, 选中 PPT 时显示, 下载携带 template")


def step_mermaid_core() -> None:
    """mermaid 图表: 含 ```mermaid 块的 Markdown, 离线内嵌本地 mermaid.js 渲染成 SVG。"""
    md = "# 图\n\n```mermaid\ngraph LR\nA --> B\n```\n"
    # 1) 含 mermaid -> 内嵌本地 mermaid.js(内联, 不引外部 CDN 的 <script src>)
    doc = build_html_doc(md)
    assert "mermaid.initialize" in doc, "含 mermaid 块未内嵌渲染脚本"
    assert "<script src=" not in doc, "不应引用外部 <script src>(需离线, 数据不出本机)"
    print("[OK] 27. 含 mermaid 块时离线内嵌本地 mermaid.js(无外部脚本引用)")
    # 2) 不含 mermaid -> 不注入(零额外体积)
    doc2 = build_html_doc("# 纯文本\n\n正文")
    assert "mermaid.initialize" not in doc2, "无 mermaid 块不应注入 mermaid.js"
    print("[OK] 28. 无 mermaid 块时不注入 mermaid.js(零额外体积)")
    # 3) PNG 长图渲染出图: 含 SVG 图形的 PNG 一定比纯文本版大
    png_plain, _ = markdown_to_png("# t\n\n正文")
    png_mermaid, _ = markdown_to_png(md)
    assert len(png_mermaid) > len(png_plain), "mermaid 图未渲染进长图(体积未增长)"
    print(f"[OK] 29. mermaid 图渲染进 PNG 长图({len(png_mermaid)} vs {len(png_plain)} 字节)")
    # 4) 预览接口返回 mermaid 标记 + /assets/js 静态路由可达
    from fastapi.testclient import TestClient
    import main
    client = TestClient(main.app)
    assert client.get("/api/html-preview", params={"md": md}).json().get("mermaid") is True
    assert client.get("/api/html-preview", params={"md": "# x\n\ny"}).json().get("mermaid") is False
    r = client.get("/assets/js/mermaid.min.js")
    assert r.status_code == 200 and len(r.content) > 100000, "/assets/js 静态路由不可达"
    print("[OK] 30. 预览接口返回 mermaid 标记, /assets/js 静态路由可达")
    # 5) PPT 方案 B: 内容页 mermaid 渲染成透明 PNG 并嵌入(图文混排, 非文本降级)
    import io as _io
    import zipfile as _zip
    import re as _re
    multi = (BASE / "test_sample.md").read_text(encoding="utf-8")
    assert multi.count("mermaid") >= 2, "test_sample.md 应含多张 mermaid 图"
    pp_data, _ = markdown_to_pptx(multi)
    zf = _zip.ZipFile(_io.BytesIO(pp_data))
    media = [n for n in zf.namelist() if n.startswith("ppt/media/")]
    slide_blips = sum(len(_re.findall(r"<a:blip", zf.read(n).decode()))
                      for n in zf.namelist()
                      if n.startswith("ppt/slides/slide") and n.endswith(".xml"))
    assert len(media) >= 2 and slide_blips >= 2, \
        f"PPT 未嵌入 mermaid 图(仅 {len(media)} 媒体, {slide_blips} 引用)"
    (BASE / "output" / "sample_mermaid.pptx").write_bytes(pp_data)
    print(f"[OK] 31. PPT 方案B: mermaid 渲染成透明 PNG 并嵌入({len(media)} 张媒体, 图文混排)")
    # 6) DOM 级强断言: 后端渲染管线确确实实出 <svg>(而非静默出错误块)
    #    取代 #29「PNG 变大」的弱判断 —— 渲染失败(错误块文字)同样会让 PNG 变大,
    #    只有直接数 DOM 里 .mermaid-diagram svg 数量才算真正成功。
    #    复用进程级共享浏览器(走 renderer.dom_mermaid_stats 的整页任务),
    #    不在本线程另起 sync_playwright(与常驻 driver 冲突)。
    import renderer
    dom = renderer.dom_mermaid_stats(md)
    assert dom["svg"] >= 1 and dom["err"] == 0, f"mermaid 后端未真正渲染出 SVG: {dom}"
    print(f"[OK] 32. 后端渲染管线 DOM 级确认出 SVG({dom['svg']} 个, 0 错误块)")
    # 7) Word 方案: 内容页 ```mermaid 渲染成透明 PNG 并 add_picture 嵌入(非文本降级)
    import io as _io2
    import zipfile as _zip2
    word_data, _ = markdown_to_word(multi)
    wzf = _zip2.ZipFile(_io2.BytesIO(word_data))
    wmedia = [n for n in wzf.namelist() if n.startswith("word/media/")]
    assert len(wmedia) >= 5, f"Word 未嵌入 mermaid 图(仅 {len(wmedia)} 张媒体)"
    (BASE / "output" / "sample_mermaid.docx").write_bytes(word_data)
    print(f"[OK] 33. Word: mermaid 渲染成 PNG 并 add_picture 嵌入({len(wmedia)} 张, 非文本降级)")


def main() -> int:
    step1_pdf_core()
    step1b_word_core()
    step1c_image_core()
    step1d_ppt_core()
    step2_page_and_api()
    step_mermaid_core()
    print("\n全部验证通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
