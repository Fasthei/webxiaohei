# LISG 网站文章

网站：https://www.xiaohei.co

## 写文章 → 推送 GitHub → 网站自动更新

1. 在 `posts/` 文件夹创建 Markdown 文件，例如 `posts/2026-10-20-my-note.md`。
2. 写好文章，推送或在 GitHub 网页提交到 `main` 分支。
3. GitHub Actions 中的 **Publish Markdown articles** 自动生成文章列表。
4. 工作流成功后，刷新网站即可看到文章。GitHub 的队列和缓存可能带来几分钟延迟。

**不用手工编辑 JSON，不用重新部署网站，不用提供 Token，不用电脑一直运行。**

你可以在 GitHub 网页点击 `posts` → `Add file` → `Create new file` 或 `Upload files`。

## 最简单的文章

文件名建议带日期，如 `posts/2026-10-20-my-note.md`：

```markdown
# 我的安全研究笔记

这里写正文。

## 背景

继续写内容。

- 第一点
- 第二点
```

标题取第一个一级标题，日期取文件名中的日期；没有日期前缀时，使用这篇文件首次提交的日期。中文文件名也支持，会生成稳定的文章 ID。

## 可选的文章信息

可复制 `examples/article.md` 到 `posts/`，修改内容并将 `draft: true` 改为 `draft: false`。

```markdown
---
title: 我的安全研究笔记
date: 2026-10-20
slug: my-security-note
category: 安全研究
summary: 这里是文章摘要。
draft: false
---

# 我的安全研究笔记

这里写正文。
```

文件头使用简单的 `key: value` 格式；`slug` 只允许小写英文、数字和连字符，且不可重复。省略 `draft` 默认发布。修改已发布文章后再次推送会更新正文；删除对应文件会从列表移除。文件头可省略。

现有自我介绍已放到 `posts/hello-lisg.md`，可以直接编辑它。

## 当前 Markdown 支持

支持段落、标题、代码围栏、简单有序/无序列表和引用。文章按原文展示，中英文切换不会自动翻译文章。目前复杂表格、嵌套列表、图片、行内链接/粗体等不会解析成对应富文本，HTML 也不会执行。Word/PDF 不会自动转成文章。

## 维护与排错

- 看 [Actions](https://github.com/Fasthei/webxiaohei/actions) 确认工作流是绿色成功状态。
- 工作流失败时保留之前的文章列表，可打开失败日志查看具体文件名或格式错误。
- `content/site.json` 的 `posts` 由工作流生成，不要手工维护；其他字段仍控制现有首页和关于页文字及联系邮箱。
- 网站访问时从 GitHub 公开 API 读取文章，不是把完整网站迁移到 GitHub Pages。原 Sites 托管和域名绑定保留。
- GitHub 接口不可用或被限流时，网站会显示随 Sites 版本发布的备用内容；备用内容不会实时跟随以后每篇文章更新。
- 仓库须保持公开；不要上传密码、Token 或未公开资料。
- 搜索引擎或不执行 JavaScript 的客户端可能只看到静态备用内容。
- 网站布局及样式修改仍需要 Sites 发布。

本地检查：`python3 -m unittest discover -s tests -v`；生成内容：`python3 scripts/build_posts.py`。

## Azure Static Web Apps

`site/` 保存网站页面与资源。Azure 工作流在每次推送到 main 时运行文章测试并从 `posts/` 生成内容，再将最新 `content/site.json` 复制到 `site/content/site.json` 并部署整个 `site/`。Azure 网站从同域读取文章，不依赖浏览器访问 GitHub API。

`app_location: site`、`skip_app_build: true`、`output_location: ""` 用于直接发布静态文件。部署凭据继续使用现有 GitHub Actions Secret。

### English articles

为 `posts/name.md` 添加 `posts/name.en.md` 可提供英文标题、摘要、分类及正文。两份文章应使用相同的段落、标题和列表结构；代码块保持一致。生成器会校验结构并合并为同一篇双语文章，不会把英文稿作为第二篇文章发布。没有英文稿时保留原文。
