# LaTeX 编译与版面核对

日期：2026-10-23。范围仅为论文排版、辅助脚本和已有证据只读核对。
分支 `main`，HEAD `b90335dbe1e739b2092c846aec59983bfa15ce04`。
新增修复实现仍按未提交工作区指纹记录，不将 HEAD 视为该实现的提交。

## 交付物与来源

- [论文 PDF](../latex/build/main.pdf)：通用 A4 中文论文初稿，66 页，包含封面、摘要、目录、七章正文与参考文献。
- [LaTeX 源码包](../thesis-latex-source.zip)：Markdown、生成章节、主文件、书目与图件，以及 PDF 和检查报告。
- [构建报告](../latex/build/build-report.json)：9 个摘要及章节来源摘要、工具版本、PDF 摘要及元素计数。
- [自动检查报告](../latex/build/pdf-audit.json)：引用、编号、页面边界、日志与证据来源核验。
- [重建说明](../latex/README.md)：本机命令、工具要求及迁移方式。

使用 Pandoc 3.9、Mermaid CLI 12.0.0、Tectonic 0.17.0、Matplotlib 3.11.2 和 PyMuPDF 2.0.0。
工具安装在用户缓存或临时 uv 环境，没有添加项目产品依赖或修改锁文件。
常规 XeLaTeX 编译方式已提供说明，本次实际执行并验证的是 Tectonic。

## 实际执行与结果

在原仓库根目录运行：

```bash
uv run --no-project --with matplotlib==3.11.2 python docs/thesis/figures/plot_repair_results.py
uv run --no-project --with pypandoc_binary==1.17 --with pymupdf==2.0.0 python docs/thesis/latex/build.py
uv run --no-project --with pymupdf==2.0.0 python docs/thesis/latex/audit.py
uv run --no-sync ruff check docs/thesis/latex/build.py docs/thesis/latex/audit.py docs/thesis/figures/plot_repair_results.py
uv run --no-sync ruff format --check docs/thesis/latex/build.py docs/thesis/latex/audit.py docs/thesis/figures/plot_repair_results.py
```

本次执行通过：7 章、8 张图、24 张表、2 段算法、5 处显示公式和 9 条参考文献完整。
正文中 40 个不同交叉引用目标均能解析，最终 TeX 日志无缺字、溢出框、未定义引用或重复标签。
PDF 无空白页、文本越出纸张边界或替换字符；17 个实现文件指纹及修复实验原始数据摘要一致。
这些是本次排版检查结果；归档 160 passed 仍是历史执行证据，没有重新运行产品测试。

## 视觉检查与修正

逐页查看全稿页面缩略图，并放大检查封面、中英文摘要、目录、表格、架构图、角色时序图、
长流程图、伪代码、实验统计图及参考文献。修正内容包括：

- 行内代码中的中文占位符改用可回退中文字体的排版方式。
- 长表格恢复可伸缩的左右间距，消除全宽溢出提示。
- 关闭封面页码锚点，消除与正文页码重复的目标。
- 调整长流程图的标签宽度与纸面占比，增大结果图文字。
- 统计图字体由不兼容的 CFF/TrueType 嵌入改为 Type 3 字形轮廓；修复后重新查看源图和论文 PDF，
  中文、8/5/4 成功数及 31.12/64.54/60.17 千 token 标注显示正常。
- 缩小参考文献字号与行距，使 9 项书目排在同页，避免末项单独跨页。

最终日志仍有 1 处英文摘要段落的 Underfull 排版提示；没有因此缺失文字。
编译器还提示第三方 `lineno.sty` 注释中的编码、系统字体绝对路径及导入图件标签被忽略。
本机可编译不等于其他机器字节级复现，字体与 TeX 环境要求见重建说明。

## 仍待确认

当前使用通用 `ctexrep` 版式和 `gbt7714-numerical` 参考文献样式。学校模板、作者、学号、
学院专业、导师和提交日期尚未提供；封面只放真实题目及“论文排版初稿”，未编造个人事实。
致谢、原创性声明、学校专用页及正式格式审定仍需按真实要求补充。
本轮未新增模型实验、运行 Docker、修改业务代码、提交或推送。
