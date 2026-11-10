"""一键验证: 逐步覆盖各板块。

运行: python verify.py

第 1 步  PDF 渲染核心(排版/字体/有效性)
第 2 步  三板块中文页面 + 后端 API(用 TestClient, 不发真实 HTTP)
后续步骤会在此追加。
"""

import re
from pathlib import Path
from urllib.parse import unquote

from renderer import build_html_doc, extract_title, markdown_to_pdf

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


def step2_page_and_api() -> None:
    from fastapi.testclient import TestClient
    import main

    client = TestClient(main.app)

    # 首页三板块结构(中文界面)
    r = client.get("/")
    assert r.status_code == 200
    for label in ["输入区", "实时预览", "输出格式", "加载示例", "下载"]:
        assert label in r.text, f"页面缺少板块: {label}"
    print("[OK] 5. 三板块中文页面(输入区/实时预览/输出格式/下载按钮齐全)")

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
    print("[OK] 6. 输入框固定高度+内部滚动, 整页锁定单屏, 中栏内部滚动")

    # /api/formats
    d = client.get("/api/formats").json()
    assert "pdf" in d["available"]
    print(f"[OK] 7. /api/formats 可用格式: {d['available']}")

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
    print("[OK] 8. /api/html-preview 返回渲染 HTML + 作用域化(#preview)排版样式")

    # /api/sample
    assert "Markdown 转 PDF 排版测试" in client.get("/api/sample").json()["md"]
    print("[OK] 9. /api/sample 返回示例文档")

    # /api/convert 文本转 PDF(含中文文件名 RFC5987)
    r = client.post("/api/convert", data={"md": "# 产品说明书\n\n正文", "format": "pdf"})
    assert r.status_code == 200 and r.content.startswith(b"%PDF")
    cd = r.headers.get("content-disposition", "")
    m = re.search(r"filename\*=UTF-8''(.+?)(?:;|$)", cd, re.I)
    assert m and unquote(m.group(1)) == "产品说明书.pdf", f"文件名编码异常: {cd}"
    print("[OK] 10. /api/convert 文本转 PDF, 中文文件名编码正确")

    # /api/convert 空内容 400
    assert client.post("/api/convert", data={"md": "   ", "format": "pdf"}).status_code == 400
    print("[OK] 11. 空内容返回 400")

    # /api/convert 不支持的格式
    r = client.post("/api/convert", data={"md": "# t", "format": "word"})
    assert r.status_code in (400, 501)
    print(f"[OK] 12. 未实现格式(word)返回 {r.status_code}")

    # /health
    assert client.get("/health").json()["status"] == "ok"
    print("[OK] 13. /health 正常")


def main() -> int:
    step1_pdf_core()
    step2_page_and_api()
    print("\n全部验证通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
