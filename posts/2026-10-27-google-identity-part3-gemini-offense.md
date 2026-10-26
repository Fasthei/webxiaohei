---
title: "Google Workspace 中的 Gemini：数据访问边界与安全评估"
date: "2026-10-27"
slug: "google-identity-part3-gemini-offense"
category: "云安全研究"
summary: "本文区分 Gemini App、Workspace 内嵌功能与 Gemini Enterprise，梳理各自的数据访问范围、管理控制与审计边界，并以公开披露且已修复的 GeminiJack 历史案例讨论间接提示注入风险。"
---

# Google Workspace 中的 Gemini：数据访问边界与安全评估

Gemini 的访问行为受到身份、Workspace 管理设置、协作内容权限与 API 控制策略共同约束。本文区分主要产品形态，说明其数据访问与审计边界，并以公开研究案例讨论提示注入等风险。

## 一、Gemini 的三张面孔

“Gemini”涵盖多个产品形态，访问范围与管理方式并不相同，评估时应分别核对。

第一张是 Gemini App 及其连接应用（Connected Apps / Workspace 扩展）。Gemini App 作为核心服务包含在 Workspace 商业与企业版本及全部教育版本里；用户在提示里 @ 一个应用（Gmail、Drive、Calendar），让它取数或代办事。

第二张是嵌在 Gmail、Docs、Sheets 侧栏里的 Gemini（Gemini in Workspace）。它不出应用边界，直接在工作负载内读写用户正在处理的文件内容，隐私规则由 Workspace 的 Generative AI Privacy Hub 统一约束。

第三张是 Gemini Enterprise。它提供企业搜索、AI 助手和 agent 能力，可通过连接器接入 Confluence、Jira、SharePoint、ServiceNow 等系统，并按配置对内容权限进行感知。连接器、索引和 agent 的组合扩大了治理范围，因此需逐项确认访问身份与授权边界。

治理三张面孔的是 Admin console 里的 AI control center，统一管理 AI 安全与合规。谷歌把 AI 治理明确放在 Workspace 管理面而不是云侧，这个位置本身就是“Work 高于 Cloud”的延续。

```text
                 Admin console（治理根）
                     │  AI control center
   ┌─────────────────┼──────────────────┐
   ▼                 ▼                  ▼
Gemini App       Gemini in          Gemini Enterprise
+连接应用         Workspace          +连接器 +自定义 agent
（@Gmail/@Drive）  （侧栏读写）        （企业检索与 agent）
   └──────── 以用户身份取数 ──────────┘
```

## 二、取数边界：谁的身份在读，开关在谁手里

评估时需要区分以下五个方面。

第一，Gemini 不是新的权限主体。它以用户的身份、用户的授权取数——它拿到的任何东西都是用户本来就看得见的。风险不在于它多了一个权限，而在于它把用户既有的读取面变成了一个会总结、会执行指令的检索器。

第二，开关在管理员。工作或学校账号使用连接应用必须由 Workspace 管理员启用；启用之后，用户在提示里 @ 了应用就直接使用，不需要每次确认。个人谷歌账号没有这道闸。同一个 Gemini 界面，工作身份下多一层管理面裁决，个人身份下没有。

第三，会话有快照效应。应用在会话开始后被管理员停用，用户仍可查看并继续该会话；Gemini 只保留响应原始提示所必需的已获取信息，不再有新增访问。事后关闸不是完全的吊销。

第四，能力边界是官方逐项列出的：Gmail 里不能读评论与图片、不能创建草稿或删邮件；Drive 里不能访问图片和视频（文档、表格、演示文稿、PDF 之外的内容一律不可达）、不能建文件夹或移动内容；Classroom 不能录成绩、不能发作业公告。这份“不能”清单反着读就是可达面索引：文本、文档、日历、任务都是天然入口。

第五，隐私边界分三层。训练隔离：用户提示按 Cloud Data Processing Addendum 属于客户数据，Workspace 未经客户事先许可不用于训练模型。会话隔离：侧栏对话历史仅本人可见，即使共享文件里，其他协作者也看不到提示与回复。外部感知：文件对外部协作者开放或由域外创建时，侧栏显示 out-of-domain banner，提示提示词与生成内容可能被外部参与者看见；Fill with Gemini 这类功能对外部共享文档不使用内部 Workspace 上下文。

> Gemini 通常沿用用户及连接器所拥有的访问范围，但自然语言检索会改变内容被发现和汇总的方式。审查时应同时检查底层权限、连接器配置和日志覆盖，而不能只看模型本身的身份。

## 三、安全风险 A：间接提示注入

OWASP 将提示注入列为 LLM 应用的重要风险（LLM01:2025 Prompt Injection）。当模型处理的内容含有指令式文本时，系统需要区分用户意图与不可信数据。Workspace 场景中，相关输入可能来自共享内容：

- 输入天然来自他人。共享文档、日历邀请、邮件正文，都是别人写的内容被拉进提示上下文。
- 检索会纳入用户可访问的共享内容，因此文档、邮件和日历邀请都可能成为需要审查的数据来源。
- 输出通道多样化。总结、草稿、下一步动作建议，都是把不可信内容转化为用户会信任的形态。

公开披露的 GeminiJack 研究曾展示 Gemini Enterprise 检索流程中的间接提示注入风险：不可信共享内容可能影响检索结果及其后续呈现。GeminiJack 是已公开披露并已修复的历史案例，不应被描述为目前仍可利用的问题；本文不推定或补写修复日期。它仍可用于讨论一个更一般的设计问题：输入来自数据面，而部分防护和治理位于身份与管理面，两者需要共同审查。

> 提示注入的风险在于，不可信内容可能影响模型如何解释请求或组织响应。对检索式 AI 系统而言，外部可见内容应纳入输入面审查；实际影响取决于产品能力、权限与防护配置，不能仅由内容可读性推断。

## 四、安全风险 B：记忆与跨会话状态

Gemini 的部分功能支持跨会话记忆或自定义指令。公开研究展示了间接提示注入可能影响长期记忆内容。其影响取决于产品能力与用户设置，因此应将记忆视作独立于单次会话的状态，并明确管理、审查和清理机制。

会话隔离并不必然涵盖所有跨会话功能；数据保留与个性化行为应按对应产品的隐私说明和管理设置核对。

对治理而言，关键问题是记忆由谁创建、如何查看和删除，以及在人员离职或调岗时是否纳入数据生命周期流程。

## 五、安全风险 C：检索与内容聚合

即使不存在提示注入，自然语言检索也可能提高用户汇总既有授权内容的效率。

对组织而言，关注点包括用户一次检索涉及的范围、会话内容的可见性，以及管理设置变更后已有会话数据如何处理。自然语言交互可能使原本分散在多个位置的信息更容易被汇总，因此需要建立相应的审计基线。

域范围委派（DWD）可能授予应用访问 Workspace 数据的能力，其授权记录位于 Admin console，与 Google Cloud IAM 的视图分开。若此类身份被用于检索或分析集成，审计时应同时核对 DWD scope、应用凭据、数据源和下游服务。

Gemini Enterprise 的 agent 和连接器可能以不同身份访问数据，具体行为由产品类型和配置决定。权限感知并不能替代对高权限账号、连接所有者、数据源范围及操作授权的审查。

> AI 检索改变了内容访问的交互方式，但不会让传统权限、审计和 DLP 控制失去作用。应结合产品可提供的事件字段，评估检索范围、主体和会话上下文，并确认异常访问调查所需的数据能够保留。

## 六、安全风险 D：Workspace 管理控制面

API 控制表是 Workspace 应用访问治理的一部分，需与云侧 IAM 分开审查。

第一，Google 自有应用可能采用与第三方应用不同的默认信任设置；管理员应按当前控制台状态核对 Gemini 相关应用的访问范围。

第二，API 控制与 Context-Aware Access（CAA）可能共同影响应用访问。审查设备和上下文策略时，应同时核对应用豁免与服务范围。

第三，能够修改 API controls 或 AI 管理设置的管理员属于高价值管理主体。应限制相关角色的分配，启用适当的会话保护，并审计配置变化。Cloud IAM 无法替代 Workspace 管理面的审查。

## 七、防守侧清单

治理检查可按以下方面开展：

1. 裁决面收紧：API controls 里把默认 Trusted 的谷歌系应用逐个过一遍，Trusted 只留给确认需要的；受限服务上给 Google 应用做显式裁决而不是吃默认值。
2. DWD 治理：全量列出已授权的 client ID 与 scope，最小化并定期复核；任何新增 DWD 都按域级权限变更审批。
3. 记忆与自定义指令：纳入周期性审查与清理策略，离职与调岗流程包含记忆清理。
4. 共享面：外部共享（链接共享、域外协作者）是注入的入口带——out-of-domain banner 是产品给的信号，共享策略才是真正的闸。
5. 检索模式审计：为 AI 检索行为建立“谁在问、问的范围、会话上下文”的日志口径；异常的大范围检索比异常的导出更值得告警。
6. CAA 与 API 控制联动：收紧 CAA 时同步检查 API 侧的豁免名单，别让留门的手悄悄开着。
7. 管理面自身：超管与 Service Settings 管理员的会话保护（强制强 2SV 形态、上下文限制）与 Admin console 变更审计，是以上一切的地基。
8. 向用户说明组织账号与个人账号的管理差异、会话数据处理方式，以及如何报告异常的 AI 访问或输出。

## 要点

1. Gemini 三张面孔：App 连接应用、Workspace 内嵌侧栏、Enterprise（连接器 + agent）；治理统一在 Admin console 的 AI control center。
2. 它不是新权限主体，而是用户权限的放大器与归纳器：把“有权看但看不完”的语料变成“一段提示就能取回”的检索面。
3. 工作身份下开关在管理员；个人身份下没有这道闸——同一个产品，两种边界。
4. 会话有快照效应：事后关闸，已流入会话的内容继续可用。
5. 官方“不能做”清单反着读就是可达面索引：文本、文档、日历、任务是天然入口。
6. 隐私承诺三件套：不用于训练（CDPA 约束）、会话隔离（仅本人可见）、外部共享有 banner——但会话隔离不覆盖记忆。
7. 间接提示注入是检索式 AI 的输入风险；GeminiJack 是已公开披露并已修复的历史案例，不代表当前可利用性。
8. 跨会话记忆与自定义指令应纳入独立的数据生命周期和审计流程。
9. 检索与连接器可能提高既有授权内容的汇总效率；审查范围应覆盖用户、应用身份、DWD scope 和数据源。
10. Workspace API controls 与云侧 IAM 是不同的管理面，相关管理员和配置变更都应纳入审计。
11. AI 检索审计应结合主体、范围和会话上下文，并按产品实际提供的日志字段评估。

## 参考

Google Workspace 帮助中心：Control Gemini App access to Workspace services — https://support.google.com/a/answer/15293691

Google Gemini 帮助中心：Gemini Apps connected apps（@应用取数与能力边界） — https://support.google.com/gemini/answer/14959807

Google Workspace 帮助中心：Control which apps access Google Workspace data（API 控制四档） — https://support.google.com/a/answer/7281227

Google Workspace 帮助中心：Control API access with domain-wide delegation — https://support.google.com/a/answer/162106

Google Workspace 知识中心：Generative AI in Google Workspace Privacy Hub — https://knowledge.workspace.google.com/admin/generative-ai/generative-ai-in-google-workspace-privacy-hub

Google Workspace 知识中心：Explore the AI control center — https://knowledge.workspace.google.com/admin/generative-ai/explore-the-ai-control-center

Google Cloud 文档：What is Gemini Enterprise? — https://cloud.google.com/gemini-enterprise/docs/overview

Google Cloud 文档：Cloud Platform resource hierarchy（超管与组织信任桥） — https://cloud.google.com/resource-manager/docs/cloud-platform-resource-hierarchy

OWASP GenAI：LLM01:2025 Prompt Injection — https://genai.owasp.org/llmrisk/llm01-prompt-injection/

Expert Insights：GeminiJack Flaw Shows How A Single Poisoned Workspace File Could Hijack Enterprise AI Searches（公开研究报道） — https://expertinsights.com/news/geminijack-shows-how-a-poisoned-workspace-can-hijack-enterprise-ai-searches

Gigazine：An indirect prompt injection attack that hacks the long-term memory of Google's AI Gemini（公开研究报道） — https://gigazine.net/gsc_news/en/20250214-prompt-injection-gemini-long-term-memory/
