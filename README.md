# Markdown 转换工具（Markdown 转 PDF）

本地运行的 Markdown 转换小工具：自带**中文操作页面**，左输入 / 中实时预览 / 右选择格式并下载。
当前支持 **PDF**（排版美观、支持中文），Word / JPG / PNG 已在界面预留、后续扩展。

## 特性

- **左中右三板块中文界面**
  - 左：粘贴 / 上传 .md，输入框固定高度（不随内容变高），文本过多时内部滚动条显示
  - 中：实时预览，排版与 PDF 输出**完全一致**（所见即所得）；内容多时面板内部滚动，整页不拉长
  - 右：选择输出格式（PDF 可用，Word/JPG/PNG 敬请期待）+ 一键下载
- **PDF 排版**：微软雅黑字体、段落首行缩进、层级标题、表格隔行变色、代码块灰底圆角、
  引用块蓝边浅底、代码块/表格避免跨页断裂
- 纯本地运行，数据不出本机；用本机 Microsoft Edge 无头渲染，无需额外下载浏览器

## 安装

```bash
pip install -r requirements.txt
```

> 需要本机已装 Microsoft Edge。没有 Edge 时会自动回退到 Playwright Chromium：
> `playwright install chromium`

## 运行

```bash
uvicorn main:app --host 127.0.0.1 --port 8000
```

浏览器打开 **http://127.0.0.1:8000**：粘贴 Markdown → 点「下载 PDF」即可。

## 本地验证

```bash
python verify.py
```

一次跑 13 项检查（PDF 渲染核心 + 三板块页面 + 全部 API 接口）。

## 目录结构

```
main.py          # FastAPI 服务: 页面 + /api/* 接口
renderer.py      # 渲染核心: PDF 已实现, Word/JPG/PNG 预留
web/index.html   # 中文三板块页面(左输入/中预览/右格式+下载)
verify.py        # 一键验证脚本
sample.md        # 示例 Markdown
requirements.txt # 依赖
```

## API 一览

| 方法 | 路径 | 说明 |
| ---- | ---- | ---- |
| GET  | `/` | 中文操作页面 |
| POST | `/api/convert` | 表单 `md` + `format` → 下载文件 |
| GET  | `/api/html-preview` | 中栏实时预览用 |
| GET  | `/api/formats` | 可用/规划中格式 |
| GET  | `/api/sample` | 示例 Markdown |
| GET  | `/health` | 健康检查 |
