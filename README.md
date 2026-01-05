# WeChat Article HTML → Clean Markdown

A lightweight Python tool to extract the main text content from exported WeChat Official Account (mp.weixin.qq.com) article HTML files and convert it into **clean, structured Markdown** for AI/LLM ingestion.

一个轻量级 Python 工具，用于从「下载/导出的微信公众号文章 HTML」中提取正文内容，并转换为**干净、结构化的 Markdown**，方便做知识库/向量化/LLM 学习。

---

## Features / 功能特性

- ✅ Extracts title + main content (WeChat DOM-aware)  
  ✅ 提取文章标题 + 正文（针对公众号常见 DOM 结构做了适配）
- ✅ Preserves structure: headings / paragraphs / lists / blockquotes / code blocks / tables (best-effort)  
  ✅ 尽量保留结构：标题 / 段落 / 列表 / 引用 / 代码块 / 表格（尽力而为）
- ✅ **No images** (text-only output)  
  ✅ **不输出图片**（纯文本更适合训练/检索）
- ✅ Drops link `href` and strips attributes to reduce tracking/privacy risks  
  ✅ 移除链接 `href` 并清理标签属性，降低追踪参数/隐私泄露风险
- ✅ Simple function API + CLI usage  
  ✅ 提供函数接口 + 命令行用法

---

## Install / 安装

Python 3.9+ recommended.

```bash
pip install beautifulsoup4 lxml
````

---

## Usage / 用法

### 1) As a function / 作为函数调用

```python
from wechat_clean import wechat_html_to_markdown

wechat_html_to_markdown(
    src_html_path="input.html",
    out_md_path="output.md"
)
```

### 2) CLI / 命令行

```bash
python wechat_clean.py input.html output.md
```

---

## Output / 输出说明

* Output is a **clean Markdown** file:

  * Title is emitted as `# <title>`
  * Body is emitted as structured Markdown blocks
  * Images/media/scripts are removed
  * Links keep visible text only; tracking parameters are not preserved

输出为**干净的 Markdown**：

* 标题会以 `# <标题>` 形式输出
* 正文尽量保留结构化块
* 图片/媒体/脚本全部移除
* 链接仅保留可见文本，不保留追踪参数

---

## Privacy Notes / 隐私说明

Exported WeChat HTML may contain tokens, scene parameters, or other traceable attributes depending on the export method.
This tool **aggressively removes tag attributes** and **drops all link hrefs**, aiming to reduce accidental leakage when sharing or building datasets.

不同方式导出的公众号 HTML 可能包含 token、scene 等可追踪参数或属性。
本工具会**强力清理标签属性**并**移除所有链接 href**，尽量降低在分享文件/构建语料时的意外泄露风险。

> Still, always review outputs before publishing datasets.
> 仍建议在公开发布数据集前自行抽检输出内容。

---

## Limitations / 局限性

* Heading detection uses heuristics (bold/large font/short lines).
  标题识别使用启发式规则（加粗/字号/短行），可能需要按文章风格微调。
* Complex layouts may degrade structure fidelity.
  复杂排版可能会影响结构还原的准确度。
* Table output is simplified (TSV-like).
  表格输出为简化形式（类似 TSV）。

---

## Project Structure / 项目结构建议

```text
.
├─ wechat_clean.py        # main converter
├─ examples/              # optional sample inputs/outputs
└─ README.md
```

---

## License / 许可证

MIT License.

---

## Credits / 致谢

Inspired by practical needs of building privacy-conscious local knowledge bases from WeChat public articles.
源于将公众号公开文章安全地离线化、结构化用于本地知识库的实际需求。
