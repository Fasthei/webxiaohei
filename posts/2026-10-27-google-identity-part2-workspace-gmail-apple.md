---
title: "Google Workspace 身份管理与 Apple 联邦"
date: "2026-10-27"
slug: "google-identity-part2-workspace-gmail-apple"
category: "云安全研究"
summary: "本文梳理 Workspace 的域名与目录边界、组织单元、管理员角色、两步验证和联邦登录，并讨论 API 控制、域范围委派、冲突账户，以及 Workspace 与 Apple Business Manager 的联邦关系。"
---

# Google Workspace 身份管理与 Apple 联邦

Workspace（连同 Cloud Identity）在 Google 体系中最接近租户边界：它有域名、目录和管理控制台，也与自己的计费关系相连。其管理模型、与 Google Cloud 的授权关系，以及对外联邦方式都不同于 Entra。本文聚焦 Workspace 的认证与管理面，以及它与 Apple Business Manager 的联邦关系。

## 一、域名是身份根

Workspace 的骨架是一条主域名加一个目录。Directory API 的 customer ID 就是这个目录的编号——云侧组织节点的 owner 字段填的正是它，且不可更改。“租户”在谷歌体系里不是一个独立的云对象，而是邮箱侧目录在云侧的投影。

层级上，Workspace 提供两类入口：付费的 Google Workspace 各版本，和免费的 Cloud Identity。Cloud Identity 是纯身份与设备管理服务，Workspace 在其上叠加生产力套件。对企业边界来说两者等价：都是受管账号的世界，都能挂组织节点，都归 Admin console 管。

管理单元是组织单元（OU）：用户和设备按 OU 分层，服务开关与策略按 OU 生效。云侧 IAM 没有 OU 的对应物——OU 属于邮箱侧的裁决体系，云侧的资源策略只认资源层级。同一个员工，在邮箱侧属于某个 OU（受一套策略管），在云侧属于某个项目/组织的 IAM 主体集合（受另一套策略管），两个“位置”互不镜像。

Workspace 的管理员权限体系是预定义管理员角色，按功能域拆分，角色可以按 OU 收窄作用范围。这套体系与云侧 IAM 完全独立：Workspace 管理员角色在 Admin console 里看，云侧角色在 IAM 里看，名字相似，归属不同。

## 二、超级管理员：信任根是一条人

Super Admin 位于管理员体系的顶端，掌握四类关键能力。

第一，管理员世界的门钥匙：分配管理员角色、对管理员账号重置密码，只有超管能做——其他管理员角色不能重置管理员密码。

第二，恢复路径：域内至少需要一名超管，建议两名互为恢复；谷歌的恢复流程支持预先指定恢复用的辅助邮箱，而这个邮箱在域外——一个域外的强信任点。

第三，域名所有权的保人：超管是域名验证的责任人和找回联系人，因此默认拥有分配 IAM 角色的能力，其在云侧的主要动作是把 Organization Administrator 授予域内合适的人。

第四，通知的终点：至少一名超管被指定为 primary administrator，接收账单与谷歌发出的关键通知。

把四类能力合起来：谷歌体系的信任根不是一把钥匙，而是一条人。超管同时是域名找回、管理员恢复、云侧授权的交汇点。任何能到达“重置管理员密码”的路径——恢复流程、域外辅助邮箱、超管的会话与令牌——都直接暴露整个体系的根。

## 三、用户认证路径：2SV、联邦与上下文

普通用户的认证是密码加第二因子。管理员可以把 2SV 从用户自选推进到强制全员，并按 OU 和分组例外。第二因子的形态从短信、验证码到安全密钥不等，抗钓鱼能力差别很大：短信与电话验证码抗不掉 SIM 换卡，安全密钥才抗。管理员策略决定了整个域的认证下限。

第二层是联邦。Workspace 支持把第三方 IdP 放在登录路径上（SAML/OIDC），让企业已有目录成为谷歌账号的认证源；同时谷歌自己也对外做 IdP（苹果线是最大客户）。方向不同，信任模型相同：密码学的根从一个域搬到另一个域，会话的根始终在谷歌侧。联邦配置的两个固定检查点：退出联邦时锁死了谁；超管是否被联邦策略覆盖（必须保留不联邦的后门管理员，否则 IdP 故障等于全员锁死）。

第三层是上下文裁决：Workspace 的 Context-Aware Access（CAA）按设备、位置、IP 等条件给服务访问划线。关键细节在 API 控制侧：管理员可以给 OAuth 应用配置“豁免被 CAA 阻断的 API 访问”，但豁免不是单向开关——还要在 CAA 级别分配里同步豁免才生效。设备信任信号、认证强度、上下文条件共同构成邮箱侧的访问决策；它的裁决对象不只是浏览器会话，还包括 API 访问。

## 四、API 控制面：Work 高于 Cloud 的裁决点

Admin console 的 Security → Access and data control → API controls 是一张裁决表，对象是“应用”，粒度是 OAuth client ID（包括服务账号的 client ID）。裁决分四档：

- Trusted：应用可以访问全部 Google Workspace 服务（OAuth scopes），包括受限服务。
- Specific Google data：只能请求配置时指定的 scope。
- Limited：只能访问不受限服务。
- Blocked：不能访问任何 Google 数据。

三条结构性规则决定这张表的分量。

第一，谷歌自家应用默认站在高信任一侧：非 Workspace 类的 Google-owned 应用默认大多是 Trusted——云侧的服务账号再怎么折腾 OAuth，到了邮箱侧，默认裁决表里谷歌系应用是畅通的。

第二，Blocked 压倒设备 allowlist：设备面和 API 面冲突时，API 面赢。

第三，Trusted 应用可以在 CAA 收紧时维持 API 访问：把配置了 OAuth client ID 的应用加入 allowlist，即使相关服务部署了 CAA 策略作用于 API 访问，该应用仍保留 API 通路。

把三条放回多 BU 的坐标系，得到“Work 高于 Cloud”的精确含义：云侧 IAM 完全管不到邮箱数据，而邮箱侧的一张表就能裁决云侧身份（服务账号、第三方 OAuth 应用）能不能碰 Workspace。Cloud 给不出任何邮箱授权，Work 却能让云侧身份全有或全无——两棵树的权重不对称。评估一个“云侧权限不大”的服务账号时，必须跨到 Admin console 查它的 client ID 被裁成了什么。

> “Work 高于 Cloud”描述的是授权边界：云侧 IAM 不授予邮箱数据访问权，而 Workspace API 控制策略可以限制云侧身份访问 Workspace 数据。云团队和 Workspace 团队应交叉审查 Admin console 与 IAM 中的相关配置。

## 五、域范围委派：一枚服务账号的域级跃迁

域范围委派（domain-wide delegation，DWD）是邮箱侧最大的授予面。它允许超级管理员授予客户端应用访问全体 Workspace 用户数据的权限，且该授权不要求用户同意。

机制三步：必须由超级管理员操作；拿到应用的 client ID（服务账号的 client ID，或第三方 OAuth 应用的 client ID）；在 Manage Domain Wide Delegation 里把 client ID 与一串 OAuth scope 绑定到域。生效之后，该应用可以访问域内全体用户的数据。

在云侧，这只是一个普通服务账号——IAM 绑定可能小到只有跑任务的权限，日志里它只是它自己。在邮箱侧，它是一张覆盖全目录的通行证，授权记录不在云侧 IAM 里，在 Admin console 的 DWD 表里。两侧的审计视图没有任何一处同时显示“这个 client ID 的云侧角色 + 邮箱侧 scope”——授予是跨体系的，审计是分体系的。

> DWD 的审查重点在授权范围：持有有效凭据且获 DWD 授权的服务账号，其 Workspace 数据访问能力取决于 Admin console 中配置的 scope，而不只取决于云侧角色。应限制 scope、管理服务账号生命周期，并将 DWD 配置变更纳入域级审批。

## 六、冲突账户与影子身份

同一个邮箱地址，个人世界里是未受管账号，企业世界里是受管账号，登录框完全一样。两个账号不能共享同一个用户名；潜在冲突应在用户加入 Cloud Identity 之前审查并解决。

冲突账户会带来几类治理风险。用户可能混淆个人与受管身份；未受管账号创建的项目可能不在组织目录和云资源审计范围内；即使受管身份停用，个人账号及其登录记录、OAuth 授权和订阅关系仍可能存在。应通过账号发现、归属确认和数据迁移流程处理这些边界。

## 七、苹果联邦线：谷歌做企业的 IdP，苹果认设备

苹果的 Apple Business Manager（ABM）支持与 Google Workspace 的联邦认证：管理员在 ABM 里选择“Sign in with Google”，用 Workspace 管理员身份完成配置，之后 Managed Apple ID 的认证走谷歌凭据。方向明确：设备世界的用户身份，由 Workspace 域发牌。

谷歌侧的对应能力是公司自有 iOS 设备管理：管理员可以在 Google Admin console 里管理公司所有的 iPhone 和 iPad，前提是把 Apple Business Manager 或 Apple School Manager 与 Workspace 或 Cloud Identity 订阅关联。这条集成 2020 年上线（当时 ABM 还叫 Device Enrollment Program），让 iOS 设备管理出现在 Admin console 的统一设备视图里。

这条联邦线的信任结构分三段：Workspace 认证人（联邦 IdP 是谷歌），ABM/ASM 认证设备的归属（设备进不进企业的注册池，是苹果侧的裁决），MDM 回填设备合规信号。三个平面各管一段：谁是人、设备是谁的、设备可不可信。

> 三个平面的策略需分别治理。Workspace 用户状态变化会影响 Managed Apple ID 登录；设备注册池由 ABM 配置；MDM 再将设备管理状态反馈给组织。应分别审查身份停用流程、ABM 管理权限和设备合规策略，并确认联邦登录的审计记录覆盖各环节。

## 关键边界

1. Workspace/Cloud Identity 是谷歌体系里最像租户的对象：域名是身份根，customer ID 是云侧组织的 owner。
2. OU 是邮箱侧管理单元，与云侧资源层级互不镜像；两根柱子中间只有少数横线。
3. 信任根是一条人：超管独占管理员分配与管理员密码重置，同时是域名找回联系人与云侧 IAM 授予能力的持有者。
4. 2SV 形态决定全域认证下限；联邦方向不同但会话根始终在谷歌侧；超管必须保留不联邦的恢复路径。
5. API 控制四档：Trusted/Specific Google data/Limited/Blocked，粒度是 OAuth client ID（含服务账号）。
6. 谷歌自家应用默认 Trusted；Blocked 压倒设备 allowlist；Trusted 应用可在 CAA 收紧时维持 API 访问。
7. “Work 高于 Cloud”是裁决拓扑：Cloud 给不出邮箱授权，Work 一张表裁决云侧身份的全有或全无。
8. DWD：超管把 client ID + scopes 绑到域，应用不经用户同意访问全体用户数据——跨体系授予、分体系审计。
9. 一枚被 DWD 授权的服务账号是域级身份，其价值由 Admin console 的 scope 决定，与云侧角色无关。
10. 冲突账户：同一邮箱可能对应个人与受管身份；未受管账号及其项目需要纳入资产发现和数据治理。
11. 苹果线三平面：Workspace 负责身份认证，ABM 管理设备归属，MDM 提供设备合规状态；三者的策略与审计应保持一致。

## 参考

Google Workspace 帮助中心：Prebuilt administrator roles — https://support.google.com/a/answer/2405986

Google Workspace 帮助中心：Deploy 2-Step Verification — https://support.google.com/a/answer/9176657

Google Workspace 帮助中心：Control which apps access Google Workspace data — https://support.google.com/a/answer/7281227

Google Workspace 帮助中心：Control API access with domain-wide delegation — https://support.google.com/a/answer/162106

Google Workspace 帮助中心：Domain-wide delegation best practices — https://support.google.com/admin/apps/domain-wide-delegation-best-practices

Google Cloud 文档：Create Cloud Identity user accounts（冲突账户） — https://docs.cloud.google.com/identity/docs/how-to/create-cloud-identity-user-accounts

Google Cloud 文档：Cloud Platform resource hierarchy（超管与组织） — https://cloud.google.com/resource-manager/docs/cloud-platform-resource-hierarchy

Google Workspace 帮助中心：Set up management of company-owned iOS devices — https://support.google.com/a/answer/9904735

Apple 支持：Use federated authentication with Google Workspace in Apple Business Manager — https://support.apple.com/guide/apple-business-manager/axmaef1a0154/web

Google Workspace Updates：Simplify management of company-owned iOS devices with new Apple Business Manager integration — https://workspaceupdates.googleblog.com/2020/07/ios-device-management-google-endpoint-apple.html
