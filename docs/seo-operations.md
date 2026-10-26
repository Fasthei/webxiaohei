# TR Notes：SEO 执行与推广方案

## 已接入站内构建

- 为五个学习方向生成固定专题 URL：`/topics/ai/`、`/topics/agents/`、`/topics/cloud/`、`/topics/identity/`、`/topics/notes/`，中文对应 `/zh/topics/.../`。
- 文章通过分类面包屑、相关阅读链接与专题相连；无文章的专题不加入 sitemap，设置 noindex。
- 英文 `/feed.xml` 与中文 `/zh/feed.xml` 提供 RSS，便于读者与内容渠道订阅。
- Azure 正式部署成功后执行 IndexNow：先验证两个域名上的公开所有权文件，再发送对应域名的 sitemap URL。GitHub Actions Summary 记录收到、验证待定或失败，不把提交等同于收录。
- `config/marketing.json` 保留 Google、Bing、Ahrefs 的公开验证字符串，以及两个语言站的 Ahrefs Analytics 项目 data-key。未配置时不加载第三方统计脚本。
- 配置真实统计项目后，追踪 `contact_click`、`github_click`、`engaged_read`；后者表示停留至少 30 秒并到达正文约 75% 位置，是阅读参与信号，并非求职转化本身。已接入用户提供的 Ahrefs 项目 data-key；实际数据接收与账号中的安装验证仍需上线后核对。

## 账号接入

推荐 Ahrefs Free（https://ahrefs.com/free），配合 Google Search Console 与 Bing Webmaster Tools。先验证自有站，再配置免费审计与统计，不需要先购买套餐。

需要账号提供的都是公开站点安装值：验证 meta 字符串和 Analytics data-key；不要提交登录密码、OAuth token、服务账号私钥。各值填入 config/marketing.json，随后推送即可由自动构建写入对应语言页面。账号建立、验证完成和统计生效目前不能仅凭代码判断。

## 第一轮付费投放草案（尚未购买或启动）

- 建议测试上限：人民币 1,000～3,000 元/月，实际支出须另行确定预算与付款账户。
- 英文目标：有 AI 安全、Agent 安全与云安全需求的技术负责人；中文目标：相关研究人员、招聘负责人及技术同行。
- 落地页：优先选择加密推理实测、多云路由研究、云身份系列。广告标题必须准确描述文章内容；不承诺入侵结果、职位或认证验证。
- 分组：AI/Agent 安全、云身份与混合云；一次先测一组，排除与实际内容不符的泛流量。
- 评估：来源、有效阅读、联系点击与实际联系质量；不以刷出的访问量或外链数量验收。
- 付款前服务交付清单：渠道及版位、目标受众、UTM 标签、预算上限、投放时段、报告与停止条件。未确定这些项，不购买“包排名”或批量外链。

## 衡量与待确认

30 天为第一轮观察窗口，不作排名保证。先检查域名抓取、收录与查询词，再对有展示的文章调整标题与内链。两个域名此前从检查环境返回 403；这不证明普通用户或搜索爬虫一定被拦。IndexNow 会独立记录其运行环境能否访问所有权文件，不能替代 Search Console URL 检查。
