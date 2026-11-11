# Markdown 转换工具（多格式导出）

本地运行的 Markdown 转换小工具：自带**中文操作页面**，左输入 / 中实时预览 / 右选择格式并下载。
支持 **PDF / Word / PPT / PNG / JPG** 五种导出，均支持中文。

## 特性

- **左中右三板块中文界面**
  - 左：粘贴 / 上传 .md，输入框固定高度（不随内容变高），文本过多时内部滚动条显示
  - 中：实时预览，排版与 PDF 输出**完全一致**（所见即所得）；内容多时面板内部滚动，整页不拉长
  - 右：选择输出格式（PDF / Word / PPT / PNG / JPG）+ 一键下载
- **PDF 排版**：微软雅黑字体、段落首行缩进、层级标题、表格隔行变色、代码块灰底圆角、
  引用块蓝边浅底、代码块/表格避免跨页断裂
- **Word (.docx)**：标题/列表/表格/代码块/引用结构化导出，中文统一微软雅黑，可再编辑
- **PPT (.pptx)**：大纲转幻灯片，`#` 作封面/分节、`##` 作内容页，自动分页 + 页码；
  内置 6 款配色模板（简约商务/科技深蓝/活力橙/清新绿/黑金尊享/创意紫），各带创意背景图
  （放射/透视网格/电路/太阳光芒/山峦/Art Deco/星轨等），文字区加半透明面板保证可读；
  选中 PPT 后在右栏挑模板再下载
- **PNG / JPG**：渲染为一张排版好的长图，适合分享
- 纯本地运行，数据不出本机；PDF/PNG/JPG 用本机 Microsoft Edge 无头渲染，无需额外下载浏览器

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

一次跑 26 项检查（PDF/Word/PPT/PNG/JPG 渲染核心 + 三板块页面 + 全部 API + PPT 模板选择）。

## 目录结构

```
main.py          # FastAPI 服务: 页面 + /api/* 接口
renderer.py      # 渲染核心: PDF / Word / PPT / PNG / JPG
make_backgrounds.py # 生成 6 款 PPT 背景图(assets/ppt_bg/*.png)
web/index.html   # 中文三板块页面(左输入/中预览/右格式+下载)
verify.py        # 一键验证脚本
sample.md        # 示例 Markdown
requirements.txt # 依赖
assets/ppt_bg/   # 6 款 PPT 背景图(PNG) + preview_grid.png
```

## 支持的导出格式

| 格式 | 文件 | 说明 |
| ---- | ---- | ---- |
| PDF  | `.pdf`   | 排版美观，A4 分页，适合打印/归档 |
| Word | `.docx`  | 结构化可再编辑，中文微软雅黑 |
| PPT  | `.pptx`  | 大纲转幻灯片，封面+分节+内容页，带页码，6 款配色模板 |
| PNG  | `.png`   | 长图，透明无损，适合分享 |
| JPG  | `.jpg`   | 长图，体积小，适合分享 |

## API 一览

| 方法 | 路径 | 说明 |
| ---- | ---- | ---- |
| GET  | `/` | 中文操作页面 |
| POST | `/api/convert` | 表单 `md` + `format`(pdf/word/pptx/png/jpg) [+ `template` 仅 PPT] → 下载文件 |
| GET  | `/api/html-preview` | 中栏实时预览用 |
| GET  | `/api/formats` | 可用格式列表 |
| GET  | `/api/ppt-templates` | PPT 可选配色模板列表 |
| GET  | `/api/sample` | 示例 Markdown |
| GET  | `/health` | 健康检查 |
