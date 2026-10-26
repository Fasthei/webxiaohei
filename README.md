# TR · 安全学习知识库

网站：https://www.xiaohei.co

默认英文，可切换中文。首页提供全文搜索、分类筛选与时间排序；分类目录列出各方向的文章；正文根据二至四级标题自动生成章节导航。作者简介、专业认证和联系方式保留在“关于”页。

## 发布文章

1. 在 `posts/` 新建或上传 Markdown 文件，可以放入子目录。
2. 填写标题、日期、`slug` 和 `topic`，然后提交到 `main`。
3. GitHub Actions 自动生成文章索引并部署 Azure 网站；Sites 镜像从 GitHub 读取最新文章索引。
4. 等 **Publish Markdown articles** 和 **Azure Static Web Apps CI/CD** 成功后刷新网站。

无需手动修改 JSON。部署存在队列和执行时间，提交成功不代表页面已经完成部署。

## 文章模板

复制 `examples/article.md` 到 `posts/`，修改内容，并将 `draft: true` 改为 `draft: false`。

```markdown
---
title: 我的实验笔记
date: 2026-10-26
slug: my-experiment
topic: ai
category: AI 安全研究
summary: 一两句话说明本文的问题、方法和收获。
draft: false
---

# 我的实验笔记

## 问题与背景

这里写正文。

## 实验过程

记录关键步骤、代码与观察。

## 结论与待验证项

区分实验结果和进一步推测。
```

`slug` 使用小写英文、数字和连字符，是文章永久链接的一部分。发布后尽量不要修改。日期格式为 `YYYY-MM-DD`。

## 分类目录

| topic | 分类 | 适合内容 |
|---|---|---|
| ai | AI 与大模型 | 模型、推理状态、模型基础设施、围栏 |
| agents | Agent 与 RAG | 智能体、工具、MCP、A2A、检索、知识库 |
| cloud | 云与混合云 | AWS、Azure、GCP、混合环境 |
| identity | 身份与红队 | AD、域控、身份、信任关系、红队实践 |
| notes | 学习笔记 | 学习方法、复盘、个人记录 |

`topic` 决定归档目录，`category` 是可自由填写的文章主题文字。未填 `topic` 的旧文章按 `category` 关键词归类，无法识别的进入“学习笔记”。推荐明确填写 `topic`，避免跨领域文章归类歧义。

## 中英文文章

中文稿：`posts/my-experiment.md`。
英文稿：`posts/my-experiment.en.md`。

两份使用相同的 `slug`、日期、`topic` 和段落结构。标题、摘要、分类文字和正文可以翻译；标题层级、列表项数量、表格行列数和代码块数量必须一致。构建会校验结构，将它们合并为同一篇文章。没有英文稿时，两种界面都显示原文，不会自动生成翻译。

## 支持的排版

- 标题、段落、列表、引用、分隔线。
- 带语言标记的代码块、行内代码、加粗和斜体。
- Markdown 表格与 HTTP/HTTPS 链接。
- 根据正文标题自动生成目录；切换语言时章节链接保持稳定。
- HTML 作为普通文本显示，不执行脚本。

## 自动化与部署

`scripts/build_posts.py` 生成 `content/site.json`，按日期由新到旧排列并跳过 `draft: true`。Azure 工作流会在部署前重新生成索引并复制到 `site/content/site.json`，将 `site/` 部署到网站。

只更新文章时，现有工作流即可处理。修改页面样式或交互后，Azure 自动部署；Sites 镜像的静态页面需要同步发布。GitHub 公开仓库中的内容会被 Sites 客户端读取，因此不要提交密钥或其他秘密。

## 本地检查

```bash
python -m unittest discover -s tests -v
python scripts/build_posts.py
cp content/site.json site/content/site.json
node --test tests/content.test.cjs
```
