---
topic: identity
category: 身份与红队
---

# 人人皆红队：AI 红队的四年

*门槛坍塌、双重失控，与纪律的回归*

2022 年 11 月 30 日 ChatGPT 上线。到今天——2026 年 10 月 27 日——三年十个月零二十七天。

这个时间刻度我想写下来，因为它回答了一个我一直在回避的问题：AI 安全到底走到哪了。我的答案是：不到四年，大模型安全大致走完了传统网络安全十到十五年的部分历程。攻击发现、漏洞原理、横向移动、供应链攻击、零信任——传统安全花了很多年才形成的这些阶段，被压缩进了一条陡得多的曲线。

这个过程看起来不可量化，但其实可以量化一部分：可量化的是速度，不可量化的是成熟度。

## 一、被压缩的十五年：可量化的是速度

传统安全的演进是有机的：漏洞研究、攻击链、横向移动、供应链、零信任，每一段隔着若干年，隔着一代人的经验积累。AI 安全把这条曲线压陡了：提示注入与越狱（2023）→ 间接提示注入（2023）→ Agent 工具链滥用（2024）→ MCP / A2A 协议层攻击与记忆投毒（2025）→ 供应链（slopsquatting、恶意 MCP）与 Agent 权限体系零信任（2026）。传统安全的"五段论"在 AI 语境下几乎一一对应地出现了压缩版。

数据能证明这种"快"：

- **CVE 曲线**：2018 年全球公开约 1.8 万个 CVE，漏洞公开后平均约两个月才会被利用；到 2025 年已接近每年 5 万个，而平均漏洞在公开披露之前就已经被打——防御方彻底站到了时钟的错误一侧（[ProjectDiscovery](https://projectdiscovery.io/blog/the-vulnerability-curve-bent-with-the-ai-curve)）。Google 威胁情报同样确认，AI 正在实测层面改变漏洞发现、利用的速度和类型（[Google GTIG](https://cloud.google.com/blog/topics/threat-intelligence/vulnerability-discovery-and-exploitation-trends-in-the-ai-era)）。
- **Agent 攻击面**：2025 年 agentic AI 安全事件的攻击向量分布中，提示注入占 43%、记忆投毒 28%、工具滥用 19%、权限提升 10%；agentic 事件平均 23 天被发现，传统事件则是 207 天（[统计](https://www.linkedin.com/posts/evan-benjamin-a405824_for-anyone-keeping-track-of-agentic-ai-activity-7411280212304236544-wbVQ)）。发现得更快，是因为盯的人更多；但组合爆炸的速度提升得更快。
- **组织侧时间线**：微软 AI 红队早在 2018 年就已成立——比 ChatGPT 早四年；2023 年公开方法论（[Microsoft AI Red Team](https://www.microsoft.com/en-us/security/blog/2023/08/07/microsoft-ai-red-team-building-future-of-safer-ai/)）；2025 年 1 月发布《[Lessons from Red Teaming 100 Generative AI Products](https://arxiv.org/abs/2501.07238)》，把 100 个 GenAI 产品的红队经验沉淀成八条教训；2026 年 7 月，微软干脆在《[Rethinking security for the age of AI](https://blogs.microsoft.com/blog/2026/07/27/rethinking-security-for-the-age-of-ai/)》中宣布"网络安全的物理学正在改变"：自主系统可以持续推理、适应、行动，而攻击成本在下降。这条时间线本身，就是整个行业的缩影。

不可量化的部分是成熟度：检测覆盖率、应急响应、责任认定、法律边界——这些依赖组织与人的东西，没有跟着四年一起压缩。被压缩的是攻击技术，滞后的是防御体系。

## 二、门槛坍塌：人人都是红队

三年前我信誓旦旦地说：未来十年 AI 都替代不了红队。现在回看，这个判断的认知水平极其低下——错就错在，我把红队当成了"知识集合"。而知识，恰好是 AI 最擅长压缩和复刻的东西。

今天，只要会 Agent 开发，就能成为红队：AI 清楚传统红队的一切，甚至能举一反三——你给它一个目标，它能把攻击面枚举、payload 生成、规避、横向的全链路自动串起来。小声说一句：我一度觉得自己要失业了。

这不是预言，是正在发生的现实。今年 9 月底到 10 月初，韩国至少九家银行遭攻击，七家金融机构确认数据泄露，约 6.8 万名客户信息被窃——新韩银行约 2.5 万人、Yegaram 储蓄银行约 4 万人、KB 国民银行 119 人（[韩联社](https://cn.yna.co.kr/view/ACK20261004000800881)）。CrowdStrike 追踪显示，攻击者使用的是 AI 驱动渗透工具 ARTEX（[CrowdStrike](https://www.crowdstrike.com/en-us/blog/unknown-threat-actor-uses-artex-to-target-south-korean-finance/)）；该工具在韩国被与多起银行攻击关联后，开发方承认被"恶意行为者"滥用并停止开源（[RFI](https://www.rfi.fr/cn/%E4%B8%AD%E5%9B%BD/20261009-%E9%9F%A9%E5%9B%BD%E5%A4%9A%E5%AE%B6%E9%93%B6%E8%A1%8C%E9%81%AD%E9%BB%91%E5%AE%A2%E6%94%BB%E5%87%BB%E5%90%8E-%E4%B8%80%E6%AC%BE%E4%B8%AD%E5%9B%BDai%E5%B7%A5%E5%85%B7)）。攻击者还使用了 Claude Code 等 AI 工具，嫌疑人据报可能是一名 26 岁、身处中国的男子（[纽约时报中文网](https://cn.nytimes.com/asia-pacific/20261009/south-korea-bank-hack-china-us-ai/)）。

ARTEX 的故事，是"人人都是红队"最直白的注脚：一个不需要自己写 exploit 的人，借助 AI 在韩国金融体系上撕开了一道口子。银行守住了核心系统，失守的是生态——这恰恰是 AI 把攻击成本打到地板之后，所有人都要面对的现实。

同期，CSA 的研究记录显示，自主 AI 红队已从研究演示走向商业产品——能够在生产系统上独立发现并验证可利用漏洞，不再需要人类操作员逐步指挥（[CSA](https://labs.cloudsecurityalliance.org/research/csa-research-note-ai-autonomous-red-team-agent-findings-2026/)）。四年之间，红队从"手艺"变成了"水电"。

## 三、协作形态：从团队到 Agent

AI 红队对我最大的感受之一：往后不再以团队协作为中心，而是以 Agent 协作为中心。拼的不是十个人怎么配合，而是你在 AI 场景下的进攻设计，加上传统安全沉淀出来的判断力——哪里有信任边界、哪里会出权限问题。

但我同样清醒：这个窗口可能只有几年。传统安全经验正在被 AI 逐渐替代——人不可能和机器比。AI 越强，人越要往上游走：定义目标、定义伤害、定义停止条件，而不是比拼枚举速度。

## 四、双重不可控

AI 业务场景的暴露面比传统 Web 时代更广：模型、RAG、Agent、工具、记忆、编排协议，每一个都是新面。而且越来越难说"漏洞还是人能控制的东西"：传统软件漏洞是可枚举的点，AI 场景的漏洞是组合出来的面。无论是 CVE 漏洞库的增速，还是 AWS AgentCore 暴露出来的问题，都在往同一个方向恶化。

AWS AgentCore 的案例很典型：Unit 42 发现 AgentCore Harness 的默认工具配置允许一次间接提示注入升级为明文凭据窃取——内置工具以 root 运行，还与解密 vault 凭据的进程共享内存空间（[CSA / Unit 42](https://labs.cloudsecurityalliance.org/research/csa-research-note-aws-agentcore-credential-exfiltration-2026/)）。SDK 层也被发现存在可让攻击者在 AI 沙箱内执行命令、触达 AWS 凭据的缺陷（[Infosecurity Magazine](https://www.infosecurity-magazine.com/news/aws-agentcore-sdk-flaws-ai/)）。同期还有 agentjacking：通过 MCP 注入，劫持接入 Sentry 的 AI 编码 Agent（[Tenet Security / CSA](https://labs.cloudsecurityalliance.org/research/csa-research-note-agentjacking-mcp-sentry-injection-20260612/)）。

人会犯错，这一点几千年没变过；过去机器犯错是可控的——边界清楚、后果可预测。现在，机器的"错误"本身就是攻击面。当人和机器这两个不可控因素叠加：人写了一个疏忽的 prompt，agent 在无人监督下把它执行成供应链投毒——整条链上没有任何一环是"计划内的恶意"，但结果已经发生。这种爆炸半径，我很难想象要怎么估算。

## 五、铁律：红队的 AI 必须被关进笼子

所以就目前而言，AI 红队的第一专注点不是能力，是纪律。

能力上不需要怀疑：AI 的知识面一定比你强。正因如此，AI 红队使用的 AI 必须受控制、被监控、被限制，不能掉以轻心。如果传统 AI 应用的安全规则是十条，AI 红队的规则必须是 10+1——多出来的那一条，是对武器本身的管理：红队 AI 接触的是未公开漏洞、客户内网拓扑和真实凭据，它的每一次工具调用，破坏力都比普通应用大一个数量级。

第二，经验必须资产化。一定要针对性地收集每一次进攻的经验——prompt 怎么写的、链路怎么串的、被哪一层拦下的、怎么绕过去的。这些经验无论复用还是回溯，都是最宝贵的资产。AI 会换代、会幻觉，但沉淀下来的攻击语料和判断框架不会——微软能从 100 个产品里写出一本书，靠的正是这种资产化能力。

第三，武器管理。AI 红队的武器库，在 AI 场景下就是真的武器库：提示词、越狱模板、工具、payload、agent 编排。既要防泄漏——红队的 prompt 外流就是军火外流；也要防滥用——ARTEX 从红队工具变成犯罪工具，中间只隔了一个开源仓库的距离。工具没有立场，但管理工具的人必须有。

## 结语

回到三年前的我。那句"十年内 AI 替代不了红队"，错在把"人"和"知识"混为一谈。知识会被压缩，工具会民主化，门槛会坍塌；但定义伤害的能力、设定边界的权力、以及知道什么时候该停手的纪律，眼下还是人的活。

AI 的车轮碾过来时，红队这个职业不会消失，但它会被重写：从少数精英的手艺，变成人人可用的杠杆；再从杠杆，变成需要纪律约束的武器。越是在失控的边缘，越要有人记得——武器库的钥匙，得锁在笼子里。
