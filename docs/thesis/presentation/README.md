# 第一阶段成果汇报

- `stage1_report.pptx`：可编辑 PowerPoint，中文为主，18 页主讲 + 3 页备份，主讲约 13.5 分钟。
- `stage1_speaker_notes.md`：逐页口播、时长、演示指示及追问口径；相同口播已写入 PPT 备注。
- `stage1_report.pdf`：从实际 PPTX 转换的预览版本。
- `build_presentation.py`：构建源，包含原生可编辑架构图、表格与源码节选。
- `build_audit.json`：页数、文本布局检查及使用材料的 SHA256。
- `stage1_overview.png`：全部页面总览；`preview/` 为实际 PDF 渲染的逐页检查图。

内容围绕核心设计、实现与英文论文前五章，保留现有平台与本课题新增边界。工程测试和真实模型实验来自 2026-10-20 归档，不代表本次重新执行。小样本中多角色未优于单角色，PPT 与讲稿不作相反宣称。

## 重新生成

从仓库根目录执行，不修改项目依赖或锁文件：

```bash
uv run --no-project --with python-pptx==1.0.2 --with Pillow==12.3.0 python docs/thesis/presentation/build_presentation.py
```

需要本机已有 Noto Sans CJK SC Regular / Bold 字体；字体路径在脚本顶部。源码与指标从仓库读取，归档案例若缺失则构建失败，不填充假数据。修改源脚本后重新生成会覆盖此目录的生成文稿与口播稿，因此直接在 PowerPoint 中修改后的版本应另存。

PDF 使用 LibreOffice Impress 的 `impress_pdf_Export` 转换；架构和代码在 PPTX 中仍是可编辑形状与文字，不是整页图片。封面不虚构姓名、学号或导师信息，可按实际情况补充。

转换后检查实际 PDF 文本完整性、越界、重叠、PPT 备注、逐页讲稿以及 17 个归档实现指纹：

```bash
uv run --no-project --with python-pptx==1.0.2 --with Pillow==12.3.0 --with pymupdf==2.0.0 python docs/thesis/presentation/audit_presentation.py
```

本次采用 LibreOffice Impress 7.3.7.2 转换。字体未内嵌至 PPTX，跨机展示若字体替换导致差异，可使用同时提供、已渲染检查的 PDF。
