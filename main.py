"""FastAPI 服务: Markdown 转换工具。

启动:
    uvicorn main:app --host 127.0.0.1 --port 8000
    浏览器打开 http://127.0.0.1:8000

接口:
    GET  /                 中文操作页面(左输入 / 中预览 / 右格式+下载)
    GET  /api/html-preview 返回渲染后的 HTML 片段(中栏预览用)
    POST /api/convert      表单 md + format(pdf/word/pptx/png/jpg) [+ template 仅 PPT] -> 下载对应文件
    GET  /api/formats      返回可用格式列表
    GET  /api/ppt-templates 返回 PPT 可选配色模板列表
    GET  /api/sample       返回示例 Markdown(左栏「加载示例」)
    GET  /health           健康检查
"""

from pathlib import Path
from urllib.parse import quote

from fastapi import FastAPI, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
import json

import renderer

app = FastAPI(title="Markdown 转换工具", version="1.0.0")

WEB_DIR = Path(__file__).parent / "web"
app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")

# 当前可用格式(后端已实现的), 页面右栏据此渲染按钮
AVAILABLE_FORMATS = ["pdf", "word", "png", "jpg", "pptx"]


@app.get("/", response_class=HTMLResponse)
def index():
    return (WEB_DIR / "index.html").read_text(encoding="utf-8")


@app.get("/api/formats")
def formats():
    return {"available": AVAILABLE_FORMATS, "planned": []}


@app.get("/api/sample")
def sample():
    return {"md": (WEB_DIR.parent / "sample.md").read_text(encoding="utf-8")}


@app.get("/api/html-preview")
def html_preview(md: str = ""):
    """中栏实时预览: 返回渲染后的 HTML 片段 + 排版样式(与 PDF 一致)。"""
    if not md.strip():
        return {"html": "<p style='color:#888'>暂无内容</p>", "css": ""}
    return {
        "html": renderer.markdown_to_html_body(md),
        "css": renderer.preview_css(),
    }


@app.get("/api/ppt-templates")
def ppt_templates():
    """PPT 可选模板列表(供页面渲染模板卡片)。"""
    return {"templates": [
        {"key": k, "name": v["name"], "bg": v["bg"], "accent": v["accent"]}
        for k, v in renderer.PPT_TEMPLATES.items()
    ], "default": renderer.PPT_DEFAULT_TEMPLATE}


@app.post("/api/convert")
def convert(md: str = Form(...), format: str = Form("pdf"), template: str = Form("")):
    """右栏「下载」按钮: 按格式转换并返回文件。同步端点(线程池), 避免
    Playwright 同步 API 与 asyncio 冲突。template 仅 PPT 生效(配色模板)。"""
    if not md.strip():
        raise HTTPException(400, "Markdown 内容为空")
    if format not in AVAILABLE_FORMATS:
        raise HTTPException(400, f"暂不支持的格式: {format}")
    if format not in renderer.FORMATS:
        raise HTTPException(501, "该格式尚未实现")
    try:
        if format == "pptx":
            data, filename = renderer.markdown_to_pptx(md, template or renderer.PPT_DEFAULT_TEMPLATE)
        else:
            data, filename = renderer.FORMATS[format](md)
    except NotImplementedError as e:
        raise HTTPException(501, str(e))
    except Exception as e:
        raise HTTPException(500, f"转换失败: {e}")
    encoded = quote(filename)
    media = {
        "pdf": "application/pdf",
        "word": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "jpg": "image/jpeg",
        "png": "image/png",
        "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    }.get(format, "application/octet-stream")
    return Response(
        content=data,
        media_type=media,
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded}"},
    )


@app.get("/health")
def health():
    return {"status": "ok", "formats": AVAILABLE_FORMATS}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
