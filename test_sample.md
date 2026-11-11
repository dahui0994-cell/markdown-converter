# 二次开发验收测试文档

这是**加粗**、*斜体*、`行内代码`，以及一张 [示例链接](https://example.com)。

## 一、基础排版

- 列表项 A
- 列表项 B
  - 子项 B1
  - 子项 B2

1. 有序一
2. 有序二

| 格式 | 文件 | mermaid |
| ---- | ---- | ------- |
| PDF  | .pdf | ✅ 矢量 |
| Word | .docx | ✅ 插图 |
| PPT  | .pptx | ✅ 图文混排 |

> 这是一段引用，验证左蓝边浅底。

```python
def hello():
    print("Hello, 中文世界!")
```

## 二、mermaid：已闭合围栏（正常写法）

```mermaid
flowchart LR
    A[开发小工具] --> B[上传GitHub]
    B --> C[积累Star & 用户]
    C --> D[开通Sponsors赞助]
    C --> E[接外包/悬赏]
    D --> F[获得收益]
    E --> F
```

## 三、mermaid：时序图（sequenceDiagram）

```mermaid
sequenceDiagram
    用户->>页面: 粘贴 Markdown
    页面->>后端: /api/convert
    后端->>用户: 返回文件下载
```

## 四、mermaid：甘特图（gantt）

```mermaid
gantt
    title 二次开发排期
    section 渲染
    Mermaid 支持    :done, a1, 2026-11-11, 2d
    自动补围栏      :done, a2, after a1, 1d
    section 验证
    33 项自检       :active, b1, after a2, 1d
```

## 五、mermaid：饼图（pie）

```mermaid
pie showData
    title 导出格式占比
    "PDF" : 40
    "Word" : 25
    "PPT" : 20
    "长图" : 15
```

## 六、mermaid：未闭合围栏（故意漏写结尾 ```，验证自动修复）

```mermaid
graph TD
    S[开始] --> P{自动补围栏}
    P -->|是| OK[正常渲染]
    P -->|否| ERR[显示错误块]
