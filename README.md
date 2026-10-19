# LISG 网站内容

网站：https://www.xiaohei.co

这个仓库维护网站文字和新增文章。现有域名及 Sites 托管不变。

## 修改已有内容

1. 打开 `content/site.json`，点击 GitHub 的编辑按钮。
2. 搜索你想修改的原文，编辑对应的 `zh`（中文）和 `en`（英文）文字。保留 `text_XX` 键名。
3. 提交到 `main` 分支，然后刷新网站。网站每次加载会读取该文件；GitHub 的缓存可能让更新延迟几分钟。已打开的页面需要刷新。

字段说明：

- `contactEmail`：全站联系邮箱，目前是 `xiaohei@xiaohei.co`。
- `pages.home`：首页文字。
- `pages.about`：关于页文字。
- `pages.hello`：原有介绍文章文字。
- `posts`：新增文章列表。
- `version`：内容格式版本，保持为 `1`。

## 新增文章

将下面的对象加入 `posts` 数组。已有多个对象时用逗号分隔。`id` 必须唯一，只使用小写英文字母、数字和连字符。

```json
{
  "id": "my-first-note",
  "date": "2026-10-19",
  "category": {"en": "Research", "zh": "研究笔记"},
  "title": {"en": "My first note", "zh": "我的第一篇笔记"},
  "summary": {"en": "A short introduction.", "zh": "简短摘要。"},
  "body": [
    {"en": "First paragraph.", "zh": "第一段正文。"},
    {"en": "Second paragraph.", "zh": "第二段正文。"}
  ]
}
```

提交后，文章会自动显示在首页的新增文章列表，链接为 `/post.html?id=my-first-note`。新增文章按日期倒序排列；原有介绍文章保留在前面。`body` 中每个对象是一段纯文本，不解释 HTML 或 Markdown。

## 更新范围与故障处理

- 这是浏览器访问时从 GitHub 读取内容，不是 GitHub Actions 自动部署；无需 Token，也不需要电脑保持运行。
- 更新 CSS、页面布局、证书列表结构或新增功能仍需要修改 Sites 源码并发布。此仓库不是完整网站源码仓库。
- GitHub API 读取失败、被限流、超时或 JSON 格式不符合要求时，网站显示随版本发布的备用内容。备用内容不会跟随 GitHub 自动刷新；故障期间新文章可能暂时无法读取。
- 仓库必须保持公开。不要把密码、Token 或未公开资料写进内容文件。
- 修改前可以在本地执行 `python3 -m json.tool content/site.json` 检查 JSON 语法。
- 搜索引擎或不执行 JavaScript 的客户端可能只读取到随版本发布的静态文字。

如需撤销内容修改，可在 GitHub 中恢复之前提交的 `content/site.json`。
