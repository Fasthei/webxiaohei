---
title: "AWS 身份与计费边界：Root、管理账户与跨账号信任"
date: "2026-10-26"
slug: "aws-identity-root-payer-trust"
category: "云安全研究"
summary: "AWS 将身份、凭证、信任与账单集中在账号边界内：root 是账号的身份原点，payer 是管理账户的经济角色，跨账号访问则依赖明确的信任与授权关系。"
---

# AWS 身份与计费边界：Root、管理账户与跨账号信任

AWS 与微软在身份与计费模型上存在结构性差异：微软将身份（租户）、资源（订阅）与账单（计费账户）拆分为三棵可独立转移的树；AWS 将三者收敛于同一个原语——账号。账号既是资源容器，也是身份容器（IAM 位于账号内部），同时是独立计费实体。我以账号边界为起点，分别梳理认证、凭证、信任与账单关系。

账号之上的组织层（AWS Organizations）由管理账户创建，成员账号按 OU 组织成一棵树，树顶是组织创建时自动生成、有且仅有的 root 容器。

```text
      账号（资源 + 身份 + 计费的三合一容器）     组织（治理 + 账单的上层容器）

   ┌────────────────────────────┐        ┌─────────────────────────────┐
   │ AWS account（12 位 ID）     │        │ Organization（唯一 root 容器）│
   │  ├── root user（注册邮箱）   │        │  ├── 管理账户 = payer         │
   │  ├── IAM 用户 / 组           │        │  ├── OU → 成员账号            │
   │  ├── IAM 角色（信任策略）     │        │  └── SCP / RCP 等组织策略      │
   │  └── 资源（region 内）       │        └─────────────────────────────┘
   └────────────────────────────┘
```

两种模型对照如下：

| 边界 | Azure 的落点 | AWS 的落点 |
| --- | --- | --- |
| 身份 | Entra 租户（目录） | 账号内部（root + IAM），账号之间彼此独立 |
| 资源 | 订阅 / 管理组 | 账号（按 region 部署） |
| 账单 | 计费账户 → 配置文件 → 发票区 | 组织（管理账户 = payer） |

两点推论：

- Azure 中“将订阅换绑目录”是一次属性变更，资源与账单可分别处理；AWS 中“跨账号”意味着跨越一整层容器——资源迁移、身份重建、信任显式声明。AWS 的账号边界较为明确：跨账号角色访问需要信任与权限配置；资源策略也可以直接授权外部主体，后文会单独说明这条路径。
- 组织不改变成员账号的独立性。无 SCP 等策略约束时，成员账号 owner 仍使用自己的凭证、独立完成授权；账单合并与权限合并是两个维度，payer 也不等于跨账号的全面控制权。

## 二、Root：账号的原点

root user 是创建账号时获得的唯一登录身份，对账号内全部服务与资源拥有完整访问权限；其凭证即注册账号所用的邮箱与密码。

三条衍生性质：

- **root 的身份载体是邮箱而非自然人。** 恢复通道是 root 邮箱的收件箱。对应的控制要求：root 使用组邮箱注册；密码与 MFA 由不同人员分持，登录需双人配合。
- **root 的权限上限即账号的上限。** IAM 身份策略无法约束 root；资源策略中的显式 Deny 对 root 依然生效——“删除拒绝所有 principal 的 S3 桶策略 / SQS 队列策略”正是 root 独占的恢复任务。root 不是权限更高的管理员，root 即账号本身。
- **root 的能力特征是“独占”而非“更大”。** 仅 root 可完成的任务包括：修改账号设置（root 邮箱、root 密码、root 访问密钥）、关闭与重开账号、恢复被锁死的 IAM 管理员权限、为 Billing 控制台激活 IAM 访问、部分账单与税务发票、S3 MFA Delete、KMS 特殊恢复、Reserved Instance 市场注册、GovCloud 注册。

凭证纪律：不为 root 创建长期访问密钥；确有交互式 CLI 需要时，可使用 `aws login` 基于控制台登录获取临时凭证。AWS 要求 root 用户启用 MFA；未配置的 root 用户需在首次登录后的 14 天宽限期内完成注册，该要求适用于各类 AWS 账号。

成员账号的 root 属于另一层治理：组织内新建的成员账号默认不生成任何 root 凭据；启用集中式 root 访问后，管理账户或委托管理员可删除成员账号的 root 密码、访问密钥、签名证书并停用 MFA，可代为执行需要 root 的特权任务，也可临时允许密码恢复。该机制将组织内 root 的可及性收拢到治理层，同时使“能执行 root 特权任务的委托管理员”具备接近 root 的价值。评估 root 目标时，其分量取决于账号层级：业务成员账号的 root 等于该账号的全部；管理账户的 root 等于组织治理面、资金面与 SCP 豁免的叠加。

## 三、Payer：组织内唯一承担支付的角色

### 3.1 payer 是管理账户的经济角色

组织由管理账户创建，该账号同时就是 payer：负责支付组织内全部账号累积的费用。Cost and Usage Report 的 `bill/PayerAccountId` 字段定义为付款账号 ID，在 AWS Organizations 中即管理账户。

因此准确的关系是：**同一账号，root 是其身份原点，payer 是其经济角色。** 一个组织只有一个管理账户，即只有一个 payer；更换付款人的实践路径是新建组织并迁移成员账号，而非在组织内修改字段（billing transfer 是另一条路径，见 3.3）。

### 3.2 root 账号与 payer 账户的关系

三条核心性质：

- **管理账户的 root 是组织的授权源。** 创建账号、邀请与管理成员、指定委托管理员、启用 all features 等组织级操作的授权均落在管理账户；组织唯一的 root 容器也位于管理账户。
- **管理账户受约束最少。** SCP 仅影响成员账号内的 IAM 用户与角色（含成员账号 root），对管理账户的用户与角色无效；挂在组织 root 上的 SCP 同样无法约束管理账户。管理账户的 root 与管理员因此是组织内最难被策略约束的主体。
- **管理账户 root 必须注册 MFA**；AWS 对所有类型的 root 用户实施 MFA 要求，未配置时适用首次登录后的 14 天注册宽限期。

```text
                 ┌────────────────────────────────┐
                 │ 管理账户（Organization 的创建者） │
                 │  ├── root（邮箱 + MFA，授权源）   │
                 │  ├── payer（支付所有成员的费用）  │
                 │  └── 组织治理（账号 / OUs / 策略）│
                 └───────────────┬────────────────┘
                                 │ 合并账单、折扣共享、SCP 下发、跨账号角色
                 ┌───────────────┴────────────────┐
                 │      成员账号 × N（各自独立）     │
                 │    IAM 主体、资源、独立凭证       │
                 └────────────────────────────────┘
```

三条性质叠加的含义：管理账户的 root 对应组织 owner——其失陷无需任何跨账号动作即可作用于全组织，被改变的是规则本身。

需要单独澄清一个常见的心智模型："root → admin → payer 从小到大"的权限阶梯并不存在，它混淆了两条坐标轴。root 与 admin（挂 `AdministratorAccess` 策略的 IAM 用户或角色）是账号内部的授权层级，只在单个账号内有意义；payer 是账号在组织中的角色。两条轴不可互比：成员账号的 root 或 admin 对管理账户默认没有任何权限，管理账户对成员账号的 IAM 权限同样默认为零。层级在影响面上成立，靠的是显式通道而非权限继承：

- **`OrganizationAccountAccessRole`**：组织内新建成员账号时自动创建的角色，授予 AdministratorAccess，信任方为管理账户——管理账户 assume 该角色即取得成员账号内的管理员权限；邀请加入的账号需手工创建同名角色。
- **委托管理员与 AssumeRoot**：集中式 root 访问启用后，管理账户或委托管理员可对成员账号执行 root 特权任务。
- **SCP 的不对称**：只约束成员账号，不约束管理账户。

### 3.3 payer 与支付的关系

- **每月一张合并账单。** AWS 每月向管理账户收取全部成员账号的费用；成员账号自身的账单仅作参考（informational purpose only），实际付款以管理账户为准。
- **折扣跨账号共享。** RI、Savings Plans 与容量折扣在组织内共享，这是多账号并入同一组织的主要经济动因。
- **付款方式归属管理账户。** 付款方式、账单联系人、发票均在 payer 侧配置；成员账号不存在独立于组织的付款流程（转售等特殊合同形态除外）。
- **账单可见性集中于 payer。** 管理账户可查看全部成员的合并成本与逐账号明细；成员退出组织后失去其在组织期间生成的 Cost Explorer 历史的访问权，数据保留于管理账户。
- **治理存在默认值。** 2026-07-10 之后经控制台创建的组织自动在组织 root 上挂载拒绝 `organizations:LeaveOrganization` 与 `account:CloseAccount` 的 SCP；此前创建的组织需自行添加。
- **账单管理权可外转。** billing transfer 允许将账单管理权转移给组织外的另一管理账户——“付钱与看账”和“管账号”可以分离。

防御侧基线：限制管理账户的访问范围；定期审查 root 邮箱、密码、MFA、电话的持有人，恢复流程不依赖特定个人；管理账户仅执行必须由其完成的操作，不部署工作负载；以 SCP 阻止成员账号擅自退出或关闭。

> 在治理审查中，我会优先关注管理账户的付款方式、账单可见性和账号生命周期控制。管理账户权限不会自动继承为成员账号 IAM 权限；进入成员资源仍依赖跨账号角色、委托管理员任务或服务集成等具体通道。账单角色与资源访问应分别核验。

## 四、认证的三层

我先把“认证”与“凭证”分开：认证是证明身份的过程，凭证是证明所用的材料。AWS 把人因认证集中在控制台与 Identity Center（密码 + MFA，联合场景以 SAML/OIDC 断言为材料），把机器认证完全交给签名与临时凭证。另一个常被含糊使用的词是“服务凭证”：AWS 没有独立的“服务账号”，服务以角色借权，服务的凭证就是它 assume 的角色的临时凭证——这是第五节“机器身份”的起点。

### 4.1 三个身份层次

- **root**：账号原点，邮箱 + 密码（+ MFA），独占任务集。
- **IAM 用户**：账号内长期身份，可持有控制台密码、访问密钥、MFA。经典形态，正被 IAM Identity Center 与临时凭证体系替代。
- **IAM 角色 / 联合身份**：临时身份。角色不持有密码与密钥，仅由信任策略与权限策略定义；主体经 STS `AssumeRole` 或身份联合（OIDC/SAML）换取临时凭证。IAM Identity Center 是推荐的中心化人因身份方案，权限集最终映射为目标账号中的角色。

### 4.2 控制台与 API 两个平面

控制台登录发生在账号自己的身份入口（root 邮箱或 IAM 用户密码，配 MFA），验证通过后控制台经 STS 为该主体签发会话——控制台里的操作同样是“临时凭证 + 签名”。API 平面的全部请求直接以 SigV4 签名发起。联合登录把认证材料换成身份提供商的断言（SAML/OIDC），STS 验证断言后签发临时凭证。登录入口本身也是枚举面：root 用账号 ID 或别名加邮箱登录，IAM 用户用别名或账号 ID 加用户名登录，账号别名一旦出现在页面或文档中即等价于账号 ID 的公开。MFA 作为独立因素与凭证分离注册——root、IAM 用户、Identity Center 的 MFA 各自独立，评估时不能按一个因子合并计算。红队拿到的凭证绝大多数属于 API 平面：控制台会话的痕迹在登录事件中，API 凭证的痕迹在每一条签名请求中。

### 4.3 SigV4：密钥不出现在网络上

签名过程：将方法、路径、查询串、请求头与负载摘要规范化为待签字符串，经 HMAC 派生链（`kSecret → kDate → kRegion → kService → kSigning`）计算签名，放入 `Authorization` 头，与访问密钥 ID 一并发送。

请求中始终不传输 SecretAccessKey：服务端以其保存的密钥材料重算签名并比对。凭证泄露的本质因此是 SecretAccessKey 泄露；访问密钥 ID 只是公开的身份指针。由此得到一条推论：临时凭证为三件套（访问密钥 ID + SecretAccessKey + SessionToken），三者缺一不可，SessionToken 同属秘密。

## 五、服务凭证：寿命决定攻击面

按“寿命 × 存放位置”分类：

| 类型 | 形态 | 寿命 | 主要兑换点 |
| --- | --- | --- | --- |
| root 访问密钥 | `AKIA…` + Secret | 永不过期，直到人工删除 | 人、脚本、配置文件（强烈不建议） |
| IAM 用户密钥 | `AKIA…` + Secret | 永不过期，直到人工轮换 | 本地配置、CI 变量、应用配置 |
| STS 临时凭证 | `ASIA…` + Secret + SessionToken | 默认 1 小时，可配置最长 12 小时 | `AssumeRole`、联合登录、Identity Center |
| EC2 实例身份 | 实例配置文件 → IMDS | 随会话自动轮换 | `169.254.169.254`（v2 需先 PUT 换 token） |
| 容器 / EKS | Task role、IRSA / Pod Identity | 随会话轮换 | 挂载的投射令牌、元数据端点 |
| CI/CD | OIDC 联合换临时凭证 | 随流水线 | GitHub Actions 等外部身份提供商 |
| 服务关联角色 | SLR，信任仅指向服务主体 | 随服务生命周期 | 服务代表账号执行操作 |

服务关联角色（SLR）是“服务凭证”的正统形态：信任策略只指向服务主体，用户不能直接 assume，服务以它在账号内执行操作。

两处容易漏掉的凭证形态。其一是服务级专用凭证：部分服务不经 STS 直接签发自己的凭证，如 ECR 的 docker login 令牌（约 12 小时有效）与 CodeCommit 的 Git 凭证，签发与轮换规则由各服务定义——枚举凭据时只看 IAM 会漏掉这一类。其二是凭证的本地存放形态：IAM 用户密钥常落在 `~/.aws/credentials`、环境变量、CI 变量与应用配置；Identity Center 的会话缓存在 `~/.aws/sso/cache`，其中含可续期的 refresh token；机器身份的凭证不落盘，由 IMDS 或投射令牌在进程内按需提供。长期密钥被窃取意味着持久化，会话缓存被窃取意味着时间窗口内的续期能力。

四条判定规则：

- 访问密钥前缀即指纹：`AKIA` 为长期凭证（IAM 用户或 root），`ASIA` 为 STS 临时凭证。取得密钥后由前缀直接确定处置思路——长期凭证按“轮换”评估，临时凭证按“有效期”评估。
- 角色链将会话时长强制压缩至 1 小时，与角色自身的最大会话时长配置无关：链式借权存在硬上限。
- 机器身份的本质是凭证兑换点：IMDS 以一次请求兑换一份完整身份；容器与 CI 联合会话同理。SSRF 与容器内代码执行在云上近似等价于身份失陷，IMDSv2 的 PUT token 握手正是针对该兑换路径的缓解措施。
- `get-caller-identity` 是取得任何密钥后的第一个动作：AWS 身份自描述，一次调用即可将“主体、账号、角色”变为可核对的事实。

> 我通常从存放位置、寿命和权限三个维度评估凭证风险。长期凭证越接近运行时代码，暴露窗口通常越大；IMDS 应作为运行时身份的重要边界进行保护。

## 六、信任关系：谁能变成谁

IAM 角色由两半构成：信任策略回答“谁能变成我”（Principal、条件、`sts:AssumeRole`），权限策略回答“变成我之后能做什么”。`AssumeRole` 的语义：主体切换至角色时放弃自身原有权限，仅保留所扮演角色的权限。

Principal 分三类，对应三种借权来源：

- **AWS 账号 / 用户 / 角色**：跨账号或同账号借权；
- **服务主体**（如 `ec2.amazonaws.com`）：服务代表资源执行操作时的借权；
- **联合身份**（SAML / OIDC）：外部身份提供商的用户或工作负载借权。

四条判定规则：

- **跨账号信任需要两侧同时允许。** 将账号加入角色信任策略只完成跨账号信任的一半；调用方账号内还需一条允许 `sts:AssumeRole` 的身份策略。信任与许可缺一不可。
- **信任整个账号即将授权决定权移交对方。** 信任策略写 `arn:aws:iam::账号ID:root` 时，“允许谁进入”由对方账号管理员决定。这是最易被低估的授权面。
- **confused deputy 有标准缓解。** 第三方多租户场景使用 ExternalId；更现代的收紧手段是以 `aws:PrincipalOrgID` 将信任限定于组织内，以 `aws:SourceAccount` / `aws:SourceArn` 限定服务主体的来源。
- **SCP 与信任是两个维度。** SCP 约束成员账号内主体的行为，对管理账户无效，对组织外账号的主体同样无效：A 账号挂载 SCP 后，组织外 B 账号的用户经桶策略访问 A 的资源时，该 SCP 不适用于 B 的用户。

跨账号访问存在两条并行通道。第一条是身份通道：角色 + 信任策略（上文）。第二条是资源通道：资源策略直接引用外部账号的 principal——S3 桶策略、KMS 密钥策略、SNS 主题策略等可以不经角色把权限直接交给外部账号或本账号主体。KMS 尤其特殊：密钥策略是密钥的授权根，IAM 策略只有在密钥策略放行后才生效。评估跨账号面时两条通道都要枚举，漏掉资源通道会系统性低估暴露面。

权限评估的骨架：显式 Deny 永远胜出；组织护栏（SCP）给出成员账号的最大可用权限；权限边界与会话策略把主体与会话压到上限之内；身份策略与资源策略决定实际放行；无一放行则默认拒绝。权限边界常被误读为“授权”——它只是上限，不产生权限。

> 权限策略回答“能做什么”，信任策略回答“谁能变成我”。审查信任关系时，我会分别核对本账号主体可承担的角色，以及信任策略允许进入本账号的外部主体，并重点检查 Principal 范围和条件是否符合业务需要。

## 七、角色链与传递性

- 信任不传递，委托可组合：A 信任 B、B 再将权限借给 C，链由此形成。每一跳都需要显式声明，但链的整体效果可超出任何单跳的授权意图。
- 角色链存在硬上限：链式会话时长固定为 1 小时，与角色配置无关。
- 每一跳都是一次权限换装，可能提权也可能降权。分析应将链表示为有向图，而非只记录最终角色——中间每一跳的信任策略与条件都是防御方可以设卡的位置。
- 服务主体的唯一性条件是另一半防线：`aws:SourceAccount` / `aws:SourceArn`（EC2 场景为实例 / 实例配置文件唯一 ID 条件）将“服务可借该角色”收紧为“该账号内的该资源可借”。

## 八、展开顺序与检测面

取得初始访问后，我的展开顺序固定为五步：

1. **身份**：`get-caller-identity` —— 主体、账号、角色；
2. **凭证**：长期或临时（前缀判定）、到期时间、来源兑换点；
3. **信任**：可 assume 的角色；被信任进入本账号的外部 principal（双向枚举）；
4. **组织**：账号在组织中的层级、payer 归属、委托管理员权限；
5. **账单**：用量在谁的账单上可见、能否影响付款与账号去留。

对应检测面：

- CloudTrail：`AssumeRole`、`UpdateAssumeRolePolicy`、`CreateAccessKey` / `CreateLoginProfile`、`ConsoleLogin`（含 MFA 标记）的来源与频率；
- IAM Access Analyzer：持续枚举跨账号信任与外部可访问资源，是信任面的官方审计面；
- GuardDuty：RootCredentialUsage 及凭据异常使用类发现；
- 组织与账单：新账号加入、成本异常、付款方式变更、billing transfer；
- 主机与网络：对 `169.254.169.254` 的异常访问。

防御侧镜像清单：root 锁死（MFA、无访问密钥、组邮箱、双人分持）、凭证短寿命化、信任面最小化（Principal 收窄 + 条件补齐）、payer 隔离与审计、账单告警、SCP 护栏。

## 九、关键边界

- 账号是资源、身份、计费三合一的容器；组织只是账号的容器，不改变成员账号的独立性。
- root 是注册邮箱 + 密码，账号内完整权限；IAM 身份策略无法约束它，资源策略的显式 Deny 可以拒绝它。
- payer 不是账号类型，是管理账户的经济角色；组织由管理账户创建，付款方式与账单集中于此。
- root/admin 是账号内的授权层级，payer 是组织角色；管理账户进入成员账号依赖 OrganizationAccountAccessRole 等显式通道，权限不自动继承。
- 每月一张合并账单，成员账单仅供参考；RI / Savings Plans / 容量折扣跨账号共享。
- SCP 只约束成员账号（含成员 root），对管理账户无效；管理账户 root 是组织内最难被策略约束的主体。
- 组织内新建的成员账号默认没有 root 凭据；集中式 root 访问可删除、恢复成员 root 并代行特权任务。
- `AKIA` 为长期凭证，`ASIA` 为临时凭证 + SessionToken；临时凭证默认 1 小时、最长 12 小时、角色链强制 1 小时。
- assume role 的语义是“放弃原权限、换用角色权限”；跨账号信任需两侧同时允许，信任策略只是一半。
- 跨账号访问有两条通道：角色信任与资源策略直接授权；KMS 密钥策略是密钥的授权根，IAM 单独放行不生效。
- 信任不传递，委托可组合；角色链的每一跳都是新的权限边界，也是防御方设卡的位置。
- IMDS 可向工作负载提供临时凭证；在特定配置和漏洞条件下，SSRF 或容器隔离失效可能扩大凭证暴露风险，实际影响取决于 IMDS 配置、运行环境与权限范围。

以上边界可按身份、凭证、信任、组织和账单依次审查。前三者决定可执行的操作与凭证来源，组织和账单则用于评估治理与财务影响。

---

## 十、参考

核对日期 2026-10-26：

- AWS IAM User Guide：The AWS account root user — https://docs.aws.amazon.com/IAM/latest/UserGuide/id_root-user.html
- AWS IAM User Guide：Root user best practices for your AWS account — https://docs.aws.amazon.com/IAM/latest/UserGuide/root-user-best-practices.html
- AWS Organizations User Guide：Terminology and concepts — https://docs.aws.amazon.com/organizations/latest/userguide/orgs_getting-started_concepts.html
- AWS Organizations User Guide：Service control policies (SCPs) — https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_scps.html
- AWS Organizations User Guide：Best practices for the management account — https://docs.aws.amazon.com/organizations/latest/userguide/orgs_best-practices_mgmt-acct.html
- AWS Organizations User Guide：Who pays for usage in an organization — https://docs.aws.amazon.com/organizations/latest/userguide/pricing.html
- AWS Organizations FAQ（payer 与管理账户的定义） — https://aws.amazon.com/organizations/faqs/
- AWS Organizations User Guide：Accessing member accounts（OrganizationAccountAccessRole） — https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_accounts_access.html
- AWS IAM User Guide：Perform a privileged task on a member account（AssumeRoot） — https://docs.aws.amazon.com/IAM/latest/UserGuide/id_root-user-privileged-task.html
- AWS Billing：Consolidating billing for AWS Organizations — https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/consolidated-billing.html
- AWS Billing：Consolidated billing process — https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/useconsolidatedbilling-procedure.html
- AWS CUR：bill/PayerAccountId 列定义 — https://docs.aws.amazon.com/cur/latest/userguide/billing-columns.html
- AWS IAM User Guide：Cross-account access using roles — https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies-cross-account-resource-access.html
- AWS IAM User Guide：Updating a role trust policy — https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_update-role-trust-policy.html
- AWS IAM User Guide：Switching to a role（role chaining 会话上限） — https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_use_switch-role-console.html
- AWS IAM User Guide：Securing access keys（AKIA 前缀） — https://docs.aws.amazon.com/IAM/latest/UserGuide/securing_access-keys.html
- AWS IAM User Guide：Unique ID prefixes（ASIA 前缀） — https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_identifiers.html
- AWS IAM User Guide：Requesting temporary security credentials — https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_temp_request.html
- AWS IAM User Guide：SigV4 signing process — https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_sigv.html
- AWS EC2：Retrieve security credentials from instance metadata — https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/instance-metadata-security-credentials.html
- AWS EC2：Configuring the Instance Metadata Service（IMDSv2） — https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/configuring-instance-metadata-service.html
- AWS Security Blog：Defense in depth: open firewalls, reverse proxies, SSRF vulnerabilities, and the EC2 Instance Metadata Service — https://aws.amazon.com/blogs/security/defense-in-depth-open-firewalls-reverse-proxies-ssrf-vulnerabilities-ec2-instance-metadata-service/
- AWS Security Blog：How to use trust policies with IAM roles — https://aws.amazon.com/blogs/security/how-to-use-trust-policies-with-iam-roles/
- AWS News Blog：Centrally managing root access for customers using AWS Organizations — https://aws.amazon.com/blogs/aws/centrally-managing-root-access-for-customers-using-aws-organizations/
- Rhino Security Labs：AWS Privilege Escalation – Methods and Mitigation — https://rhinosecuritylabs.com/aws/aws-privilege-escalation-methods-mitigation/
- PwnedLabs：AWS Privilege Escalation: Techniques and Defenses — https://pwnedlabs.io/blog/aws-privilege-escalation
- Token Security：IAM Role Trust Policies: Misconfigurations Hiding in Plain Sight — https://www.token.security/blog/iam-role-trust-policies-misconfigurations-hiding-in-plain-sight
- Wiz：IMDS Abused: Hunting Rare Behaviors to Uncover Exploits — https://www.wiz.io/blog/imds-anomaly-hunting-zero-day
- Resecurity：SSRF to AWS Metadata Exposure — https://www.resecurity.com/blog/article/ssrf-to-aws-metadata-exposure-how-attackers-steal-cloud-credentials

补充检索经 Jina Search（s.jina.ai）完成。文中的攻击路径仅作理论归类与防御对照，利用方法参考各原始研究的适用条件与授权边界。
