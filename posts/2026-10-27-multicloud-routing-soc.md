---
title: "多云网络控制面：OCI、GCP、Azure 与 AWS 的路由和安全运营"
date: "2026-10-27"
slug: "multicloud-routing-soc"
category: "云安全研究"
summary: "本文以 Azure Virtual WAN、OCI、Google Cloud 与 AWS 的互联为例，梳理跨云物理连接、路由控制平面、Kubernetes 网络与多云安全运营，并讨论私有端点和跨云连接器的治理要求。"
---

# 多云网络控制面：OCI、GCP、Azure 与 AWS 的路由和安全运营

本文以 OCI、Google Cloud、Azure 与 AWS 互联的假设架构为例，讨论路由控制面及其安全运营要求。Kubernetes 承载推理与训练工作负载，跨云流量则由专线、网关与路由策略共同约束。

分析多云网络时，路由公告、信任关系和配置变更往往与防火墙策略同等重要。本文聚焦这些控制面要素及其审计方式；重点是如何理解可达性边界、识别配置漂移，并把相关信号纳入安全运营。

架构的基本形态是：**以美东2（East US 2）的 Azure Virtual WAN 作为核心网络节点，在 hub 区域用混合 ExpressRoute 服务连接 AWS、GCP、OCI 三朵云**。OCI 作为边界区域，承担业务网络承载与接入；GCP 网络作为全球分布式业务汇聚层，主要部署数据库、Redis 与队列处理；Azure 与 AWS 都是核心承载，其中在 AWS 上处理分布式业务的状态检测，并让 AWS 的多 AZ 承担类似 Azure 可用区的角色。K8s 跑在四朵云上，推理与训练是最核心的工作负载。

在私有端点架构中，公网服务面可能很小，但内部可达性仍由路由表、专线连接和私有 DNS 决定。跨云路径因此需要按配置和业务依赖共同审查。SOC 连接器也应纳入这一范围：它们承担安全运营职责，但权限过宽或信任配置不当时，也会扩大跨云影响面。本文围绕这一组边界展开。

## 一、架构总览：四云的角色分工

先界定边界，再分析安全控制。这套架构里每朵云都承担不同的网络角色，影响其前缀公告方式与信任边界。

```text
                        全球分布式业务汇聚层（GCP）
                    ┌─────────────────────────────────┐
                    │  Cloud Router / NCC hub          │
                    │  ├── 数据库（跨区副本）             │
                    │  ├── Redis（分布式缓存/会话）       │
                    │  └── 队列（业务事件总线）           │
                    └────────────┬────────────────────┘
                                 │ Cross-Cloud Interconnect
                                 │ （↔ AWS Interconnect – multicloud）
   边界/接入区（OCI）              │
┌──────────────────┐     ┌───────┴─────────────────────────┐
│ FastConnect      │     │  核心网络节点（Azure 美东2）        │
│ 边界业务网络承载    │────►│  Virtual WAN hub（secured hub）  │
│ 入口暴露面最靠外    │ER   │  ├── ExpressRoute gateway        │
└──────────────────┘     │  ├── hub route tables / intent    │
                         │  └── Azure Firewall / NVA         │
                         └───────┬─────────────────────────┘
                                 │ DXGW + transit VIF
                    ┌────────────┴────────────────────┐
                    │  业务承载点（AWS，多 AZ）            │
                    │  Transit Gateway                 │
                    │  ├── EKS：推理 / 训练              │
                    │  ├── 分布式业务状态检测              │
                    │  └── 多 AZ = Azure AZ 的等价冗余    │
                    └─────────────────────────────────┘
       （Azure 侧另挂 AKS/GKE/OKE 于各自 VNet/VPC/VCN 内）
```

| 云 | 网络角色 | 业务角色 | 安全评估关注点 |
| --- | --- | --- | --- |
| Azure 美东2 | vWAN 核心枢纽，ExpressRoute 汇聚 | 核心承载 + AKS | 全网路由的中枢，改一张表影响四朵云 |
| OCI | 边界区域，业务网络承载接入 | OKE + 接入层 | 暴露面最靠外的入口，前缀从这里进 BGP |
| GCP | 全球分布式汇聚层 | 数据库 / Redis / 队列 + GKE | 数据面终点，crown jewel 所在 |
| AWS | 业务承载点，多 AZ | EKS 推理/训练 + 状态检测 | 攻击面与检测面重叠的高价值平面 |

从网络治理角度看，有三点值得确认。第一，**汇聚层与入口分离**：OCI 位于边界、GCP 承载汇聚服务，跨域路径经过的路由域应逐段纳入变更审查。第二，**状态检测放在 AWS**：健康检查、一致性判断和流量观测属于业务可用性与安全监测的一部分，需要保护其配置、数据源和告警链。第三，**多 AZ 的职责边界**：不同云的可用区并不等价；冗余设计应分别评估故障域、链路依赖与恢复目标。

> 我通常先整理前缀归属、公告来源和传播范围，再将它们与应用依赖对应。这样可以把网络可达性与业务边界放在同一份审查材料中。

## 二、物理层：专线如何落到美东2

路由策略再精巧，也要先有物理通道。这一层的关键词是"混合"：hub 区域同时用直连型与托管型两类服务，把 AWS、GCP、OCI 三朵云接到同一个 vWAN hub 上。

**OCI 方向：OCI-Azure Interconnect。** 这是四云互联里成熟度最高的一条通道：Oracle FastConnect 与 Azure ExpressRoute 在成对的数据中心里直接交叉连接，两边各建一条电路，Azure 侧挂到 vWAN 的 ExpressRoute gateway 上，OCI 侧挂到 FastConnect 的 DRG 上，BGP 在两端直谈。美东正是这条通道的成熟落点（East US 与 OCI Ashburn 成对），这也是"美东2 vWAN 做核心节点"在物理上成立的原因——OCI 的边界业务网络从这里接入整张网。这条链路上 BGP、前缀过滤全部自行配置，自由度最高，配置错误的空间也最大。

**GCP 与 AWS 方向：Cross-Cloud Interconnect 与 AWS Interconnect – multicloud。** 2025 年 11 月 AWS 与 Google 宣布了联合工程的多云网络方案，2026 年 4 月 AWS Interconnect 达到 GA：GCP 侧用 Cross-Cloud Interconnect，AWS 侧用 Interconnect – multicloud，两者对接成一条托管通道，首发五个区域对（含美东）。审查时需确认两个特性：AWS 与伙伴设备之间的链路**默认启用 MACsec（IEEE 802.1AE）加密**，且只有加密会话激活时才转发客户流量；该服务**不需要客户自行配置物理路由器、交叉连接或 BGP 对等**，容量以托管的 interconnect 对象交付，AWS 侧通过 Direct Connect gateway 挂进网络。Azure 方向目前是 Preview，OCI 方向在美东已支持互通。

**混合的另一层含义：交换中心 fabric 兜底。** Equinix、Megaport 这类 NaaS 交换商提供云路由器（如 Megaport MCR），可以把四朵云的专线在同一张 fabric 里互通，BGP 由 fabric 代管。这种模式在"直连型通道覆盖不到的区域对"上很实用，但代价是多了一层第三方路由域——前缀在 MCR 上可以被再播、被聚合，信任边界从"云与云之间"变成了"云与厂商之间"。

> 物理互联定义了网络边界。对直连型连接，应审查两端网关的 BGP 配置与前缀过滤；对托管型连接，应审查接口和允许前缀。理解连接类型有助于正确解读路由表和责任分界。

## 三、路由策略核心：三套控制平面，一套业务

这是全文的核心。四朵云、三套路由控制平面（Azure vWAN、AWS TGW、GCP Cloud Router），BGP 是唯一的普通话，但每家的"方言"决定了路由判断的具体做法。下文按云分别展开，再回到统一视角。

### 3.1 Azure vWAN：关联、传播与 hub 路由表

vWAN 的虚拟 hub 路由器是全网中枢，它的三个原语必须吃透：

- **关联（association）**：每条连接（VNet 连接、ExpressRoute 连接、VPN 连接）关联到恰好一张 hub 路由表，关联决定"这条连接的流量按哪张表转发"。默认所有连接都关联到每 hub 自带的 **Default route table**。
- **传播（propagation）**：连接把路由**动态传播进**一张或多张路由表（用 label 分组，比如内置的 Default label 会跨 hub 应用到所有 Default 表）；同时 hub 通过 BGP 把表里路由回播给分支侧。每 hub 还有一张 **None route table**，传播到它等于"不播"。
- **静态路由**：可以在 hub 路由表里写静态路由（下一跳可以是 VNet 连接或 hub 内的 Azure Firewall）；**同前缀下静态路由优先于动态学到的路由**。

围绕这三个原语，Azure 提供了四个高级能力：**Hub routing preference（HRP）** 在 VPN / ExpressRoute / SD-WAN NVA 同时可达同一 on-prem 前缀时控制选路倾向；**routing intent 与 routing policy** 把 Internet 流量与私网流量整体引向 hub 内的 Azure Firewall 或 NVA 下一跳（启用后所有连接改播到 None 表，Default 表只剩静态路由）；**Route-maps** 可以在连接上做路由聚合、过滤，并修改 BGP 属性（AS-PATH、Community）来影响优选；**effective routes** 视图则能直接看到某张表当前生效的全部路由。

三条风险点值得单独记录，它们同时是防守盲区与枚举线索：第一，**0.0.0.0/0 只留在本 hub 的路由表里，不跨 hub 传播**——所以跨 hub 的默认路由行为要靠显式配置，断链与绕行都发生在这里；第二，**不要把 Azure 的路由再播回 Azure**（移除 BGP community 后再回灌会造成环路或中断）；第三，**分支连接（ER/VPN）必须全部关联 Default 表、并传播到同一组表**，不一致的传播配置会形成典型的"半隔离"状态。

> vWAN 的关联和传播矩阵表达了网络信任边界。默认表的行为应结合实际配置验证；隔离通常依赖自定义路由表和明确的传播设置。静态路由优先级可能覆盖动态路由，因此相关变更应经过审批、差异检查和审计。

### 3.2 AWS：DXGW、Transit VIF 与 TGW 路由表

AWS 侧的网络入口是 Direct Connect，但真正承载路由判断的是两条链的组合：**Direct Connect gateway（DXGW）+ transit virtual interface + Transit Gateway（TGW）**。要点如下：

- Transit VIF 把 TGW 挂到 DXGW 上；**TGW 的 ASN 必须与 DXGW 的 ASN 不同**，这是一个硬校验，也解释了跨云 BGP 会话里 ASN 的错位是设计出来的。
- DXGW 本身用它的 ASN 广播所有挂接的 VPC/TGW 前缀，跨云对端（无论是 vWAN 的 ER 电路还是 GCP 的 Interconnect）看到的是 DXGW 播出的统一视图。
- **TGW 路由表的 association 与 propagation** 与 vWAN 命名相近，但语义需要对齐：association 决定 attachment 的出向选表，propagation 决定 attachment 的路由进哪张表。TGW 自带 default route table（默认同时是默认关联与默认传播表）——生产环境几乎一定要关掉这个默认行为，改成显式的多表设计。
- 隔离手段：黑洞路由（blackhole）、把 attachment 的传播关掉、或用独立的隔离路由表承接"只进不出"的 attachment。
- DX 上的 BGP 选路遵循标准属性序：local preference、AS-path、MED；AS-path prepending 与 community 都可以用来做主备与分流，但字段级细节的坑（非对称、优选意外）在多云场景会被放大。

**业务侧的落点**：EKS 的 VPC 挂到 TGW，多 AZ 的子网分布让"AZ 级冗余"成为 TGW 传播设计里的一等公民；分布式状态检测（健康检查、一致性判断）跑在 AWS，意味着跨云业务的"心跳"路径都要经过 TGW 的选路——这条路径的质量与可见性，攻防双方同样关心。

> TGW 的路由传播决定 attachment 间的可达范围，应与安全域设计一起审查。DXGW 的挂接关系也可能提供不经过预期 vWAN 控制的路径；应通过拓扑清单确认所有连接是否符合设计。

### 3.3 GCP：Cloud Router 的广告模式与 BGP 路由策略

GCP 作为汇聚层，路由出口收敛在 Cloud Router（或 NCC hub 里的 Cloud Router）上：

- **广告模式**：default 模式只播 VPC 子网与 NCC 导入的子网/动态路由；custom 模式在子网之外**自定义 IPv4/IPv6 前缀**——汇聚层对外暴露什么，完全由这张自定义广告列表决定。
- **BGP route policies**：可以从"按对等、按前缀"的粒度过滤与修改**入站方向学到的路由**与**出站方向广告的路由**，支持改 MED、AS-path（含 prepend）、community 等属性——这是 GCP 侧做流量工程、前缀治理的正规位置。
- **Cross-Cloud Interconnect / Partner Interconnect** 的 VLAN attachment 与 Cloud Router 的 BGP 会话是多路径的：两条 attachment 各自建会话时，GCP 侧可能两个 BGP 路径都装表，需要用 route policy / MED / prepend 显式收敛成主备，否则出向流量分裂、路径质量不可控。

**业务侧的落点**：数据库、Redis、队列集中在 GCP，意味着"汇聚层前缀"是全图最敏感的一段 CIDR——所有云的出向策略最终都指向它；反过来，从 GCP 汇聚层的视角看，四朵云的来访路由都在 Cloud Router 的 BGP 会话上可见，这里是防守方做路由侧检测的最好位置，也是业务判断时信息密度最高的位置。

> Cloud Router 的自定义广告列表决定了向邻接网络公布的前缀范围。广告或过滤规则的变化可能先表现为配置漂移，而非明显的流量特征，因此应纳入审批、基线和变更告警。

### 3.4 统一视角：BGP 是普通话，路由表是策略

三套控制平面拼起来，这张网的统一逻辑其实只有两层：

```text
   控制平面（BGP，云间唯一协议）
   ┌─────────────────────────────────────────────────┐
   │  vWAN hub router ←→(ER电路)→ DXGW / FastConnect   │
   │        ↕                     ↕                    │
   │  hub route tables        TGW route tables         │
   │  （关联/传播/label）      （association/propagation）│
   │        ↕                     ↕                    │
   │  Route-maps(AS-path/     DX BGP 属性              │
   │  community/聚合)          (local pref/MED)         │
   └─────────────────────────────────────────────────┘
              ↕ GCP Cloud Router（广告模式+BGP policy）↕
   业务平面（前缀 → 业务归属 → 数据流向）
   OCI边界前缀 → AWS状态检测路径 → GCP汇聚层(DB/Redis/队列)
```

**路由表在这套架构里就是隐式防火墙**。安全组、防火墙策略管的是"会话放不放行"，路由表管的是"路存不存在"——而后者在多云环境里几乎不做集中审计。一个前缀从 OCI 边界播出、被 vWAN Default 表收下、经 DXGW 转播进 TGW、再从 TGW 传播到 EKS 的 VPC，这条链上任何一环的传播配置都比防火墙规则更少被 review。这是"路由即策略"的正面与反面。

## 四、K8s 层：Pod CIDR 是第二张路由平面

推理与训练是这套架构的最核心业务，K8s（EKS/AKS/GKE/OKE）跑在四朵云上，网络层因此多出一张平面：**Pod CIDR / Service CIDR**。

规矩很朴素：每朵云的容器网段必须纳入整体 CIDR 规划，并像任何 VCN/VPC 子网一样被播出——EKS 的 pod CIDR 要能通过 TGW 与 DXGW 到达 vWAN，GKE 的 secondary range 要进 Cloud Router 的广告，AKS 与 OKE 同理。跨集群的东西向（推理集群拉训练集群的模型、多集群调度）则依赖 Cilium ClusterMesh 或 Submariner 这类多集群网络方案，它们的本质都是把集群间的 pod 到 pod 可达性建立在这张底层路由网上。

从安全审查角度看，这一层有两个主要问题。第一，Pod CIDR 的公告会扩大网络可达范围，因此应将其与 Kubernetes NetworkPolicy 一并审查，避免路由范围超出策略预期。第二，工作负载身份联邦使集群工作负载能够获取其他云的短期凭据；跨云 claim 映射和目标角色授权应与网络隔离分别核验，不能认为网络边界本身足以约束身份访问。

> 我会把 Pod 网段公告、工作负载身份绑定和集群间连接作为三个独立的审查对象，分别核对其范围、所有者和变更记录。

## 五、私有端点与路由可见性

本节讨论私有端点架构中服务面与网络控制面的不同作用。假设 OCI 接入服务均配置在 Private Endpoint 后，公网暴露面会相应缩小；但服务之间的可达性仍取决于路由、专线、名称解析和访问控制配置。

### 5.1 Private Endpoint 与服务边界

在这一假设中，接入层服务没有公网 IP，而是通过私有子网和 Private Endpoint 暴露，只能经 VCN 内部或 FastConnect 私有路径访问；安全列表、NSG 与 IAM 分别约束网络和控制面访问。公网可见性降低并不意味着内部服务不可达，因此私有端点、DNS 区域和允许的连接范围仍需持续盘点。

### 5.2 公网暴露面与边界验证

当服务仅有私有地址且网络策略正确时，公网请求通常无法建立到这些端点的连接。审查时应分别确认以下边界，而不要仅凭扫描结果判断资源是否存在：

- **公网地址与监听面**：确认服务是否配置公网入口，以及防火墙、安全列表和 NSG 的允许范围。
- **私有网络路径**：核对跨 VNet、VPC、VCN 和专线的可达性，尤其是默认路由和共享网关。
- **控制面权限**：将读取资源清单和变更网络配置的角色分开管理，并保留相应审计记录。
- **身份入口**：确认公网登录界面、身份提供方和应用访问策略与实际部署一致。

Private Endpoint 缩小的是公网服务面，不会替代内部路由与身份治理。配置审查和变更审计因此仍是必要控制。

### 5.3 路由信息的治理

私有端点必须通过路由才能被业务访问，因此路由表、传播关系和私有 DNS 记录能够说明网络设计所允许的通信范围。这些信息应作为敏感配置进行权限管理、基线比对和变更审计。

```text
资产与路由治理                         安全运营
┌──────────────────────┐           ┌─────────────────────┐
│ 前缀归属与用途登记     │ ────────► │ 路由基线与变更审计   │
│ 专线与网关依赖         │ ────────► │ 可达性与策略复核     │
│ 私有 DNS 与端点范围    │ ────────► │ 异常配置关联告警     │
└──────────────────────┘           └─────────────────────┘
```

我会把路由信息视为一种治理数据：前缀、父级网关、传播目标和 DNS 记录应有明确负责人，并能与已批准的业务流量对应。读取权限也需要最小化，因为完整路由视图可能揭示组织的网络依赖。

> 私有端点降低公网暴露，并不消除内部网络的可达性风险。路由读取权限、私有 DNS 区域和跨云连接矩阵应纳入资产登记、持续监控与变更管理。

## 六、路由与身份风险分析

以下按网络配置审查、身份信任审查和检测能力三个方面整理常见风险。重点是识别并修复错误配置，而不是提供操作流程。

### 6.1 路由与资产清单

跨云网络清单应覆盖有效路由、hub 路由表的关联与传播、Transit Gateway 的路由表和 attachment，以及 Cloud Router 的公告前缀和 BGP 会话状态。将这些配置与前缀登记表和业务依赖对应，可以发现意外传播或范围不一致。

资产发现与权限审查应通过组织批准的管理接口完成，并记录查询主体和范围。访问被拒绝不应被用作资源存在性的判断依据；应通过资产所有者和授权后的清单流程确认配置状态。

### 6.2 配置风险

需要重点复核的配置包括：隔离路由表中的意外传播、未纳入预期路径的 Direct Connect gateway attachment、覆盖已有路由的静态项、未经审批的 Cloud Router 前缀公告，以及范围过宽的工作负载身份联邦 claim 映射。这些问题可能先表现为控制面配置变化，而非明显的网络告警；应通过变更审批、配置基线和审计日志共同发现。

### 6.3 检测：先确认防御侧实际可见的信号

这一步必须落在具体产品上。这套架构里检测的分布是：**AWS 承担分布式业务的状态检测**（健康检查、一致性、流量观测），各云安全中心承担配置与威胁检测——GuardDuty/Security Hub（AWS）、Defender for Cloud（Azure，且能挂 AWS/GCP 连接器）、Security Command Center（GCP）、Cloud Guard（OCI）。路由变更类的信号分散在 CloudWatch/CloudTrail、Activity Log、Cloud Audit Logs、OCI Audit 里的网络 API 事件；vWAN 侧的 effective routes 突变、TGW 传播新增、Cloud Router 广告变更，理论上都能从审计日志还原。

运行团队应确认网络读取和变更事件是否进入相应审计日志，GuardDuty、Defender for Cloud、Security Command Center 与 Cloud Guard 的告警能否与跨云流量关联，以及 SOC 是否具备跨云时间线。具体覆盖范围取决于启用的服务、许可和日志配置，应以实际环境验证。

### 6.4 变更验证

网络或身份配置变更后，应通过获批的测试和变更记录验证预期路由、服务可达性及日志覆盖。控制面调用成功并不代表业务路径符合预期；验证应由系统所有者依据变更方案执行，并留存结果与回滚条件。

### 6.5 信任边界表

按"策略型 / 推理型"给这张架构的边界归类：

| 边界 | 类型 | 强制机制 | 审查重点 |
| --- | --- | --- | --- |
| OCI 私有端点入口 | 策略型 | 私有子网+安全列表/NSG+IAM | 核实路由可达范围与端点授权 |
| SOC 跨云连接器 | 策略型 | Entra 应用 ↔ IAM 角色（external ID） | 最小化权限并审核信任策略与身份变更 |
| vWAN 关联/传播 | 策略型 | hub 路由表配置 | 将配置与预期隔离域及传播范围比对 |
| TGW association/propagation | 策略型 | TGW 路由表配置 | 审查传播范围及 DXGW 连接关系 |
| Cloud Router 广告列表 | 策略型 | BGP 广告模式与 policy | 对公告范围和变更建立基线 |
| hub 内防火墙（routing intent） | 策略型 | Azure Firewall 下一跳 | 核验下一跳及预期检查路径 |
| AWS 状态检测层 | 推理型+策略型 | 健康判断逻辑+网络观测 | 纳入保护范围并监测配置与可用性 |
| workload identity federation | 策略型 | 信任策略+claim 映射 | 复核映射范围与预期身份边界 |
| 各云安全中心 | 推理型 | 检测规则 | 验证规则覆盖、告警路由和审计能力 |

## 七、多云 SOC：安全运营的汇聚点，也是配置错误的重灾区

SOC 的职责是把多个云环境的告警、配置和事件汇入统一时间线，支持检测、调查与响应。跨云汇聚提升运营效率，同时也增加配置和权限治理成本。连接器的身份、授权范围及信任关系应纳入架构审查。

现实拼图是这样的：

- **Microsoft Defender for Cloud** 是四家里唯一原生跨三云的：通过 connector 把 AWS 账号与 GCP 项目接进来，asset inventory 给出 Azure/AWS/GCP 的统一资产视图（含容器、AI/ML 资源、身份资源分类），风险优先级、attack path、KQL/ARG 查询、cloud scopes 分组 RBAC 都是围绕"多云一张图"做的。
- **AWS Security Hub + GuardDuty** 深耕 AWS 侧的配置基线与威胁检测，Findings 体系可以外送到 SIEM。
- **GCP Security Command Center** 覆盖 GCP 侧的 posture 与威胁，同样可外送。
- **OCI Cloud Guard** 管 OCI 侧的检测与响应 recipe。
- **缺口在 OCI**：Defender 的多云清单不含 OCI，四云全景需要把 Cloud Guard 的告警通过 SIEM（如 Sentinel 或第三方）管道拼进同一时间线——四朵云的日志 schema、时间源、实体命名（账号/项目/订阅/租户）各不相同，拼接成本就是全景的"长尾"本身。

### 7.1 配置错误的代价：Azure 安全中心接管 AWS EC2

以最常见的场景为例：**Azure 安全中心（Defender for Cloud）要接管 AWS 的 EC2**。这不是单击一次按钮就能完成的事，它要求先建立一条跨云信任链：AWS 侧用 CloudFormation 模板创建一个 IAM 角色（信任策略里钉死 Microsoft 侧的服务主体，并带 external ID 条件），Azure 侧注册一个 Entra 应用作为连接器身份，两边握手之后，安全中心才能读取 EC2 的配置、纳管 Defender for Servers 的告警、把资产并进统一清单。

这条信任链上的每个配置都需要最小化和持续审查。范围过宽的 principal、超出读取需求的权限、凭据存储不当、缺少轮换或人员离职后未撤销的访问，都会扩大连接器的影响范围。优先采用受支持的联合身份方式，并核对实际角色权限和凭据生命周期。

> SOC 连接器是经授权的跨云关系。盘点 AWS 角色、Entra 应用、凭据和实际权限，并将信任策略及连接器身份的变更纳入审计。

### 7.2 SOC 的覆盖与韧性

需要确认三类覆盖情况。第一，**路由面是否可见**：各云安全中心对 IAM、工作负载和暴露面的覆盖不等同于路由配置监控，路由表变更应纳入独立的基线和审计。第二，**跨云事件是否可关联**：单云告警未必能还原跨云业务链路，应核对实体、时间源与日志字段能否支持调查。第三，**检测层是否受保护**：AWS 状态检测、各云安全中心及跨云连接器本身都应纳入资产清单、权限审查和变更监控。

> 评估多云 SOC 时，我会检查路由可见性、跨云事件关联、连接器信任关系，以及检测层本身是否纳入保护范围。这些既是产品覆盖问题，也是集成和治理问题。

## 八、多云网络治理检查项

以下检查项可作为多云网络的治理基线：

1. **前缀归属登记**：全部 CIDR（含 pod/service 网段）进一张权威登记表，谁播出、允许传播到哪，写清楚；登记表之外的前缀一律视为异常。
2. **传播白名单化**：vWAN 与 TGW 都关掉 default route table 的默认关联/传播，所有连接显式进自定义表；隔离域之间用 None 表与黑洞路由表达"设计上不通"。
3. **DXGW 拓扑审计**：定期枚举同一 DXGW 下的所有挂接，确认不存在绕过 vWAN 仲裁的云对云直达路径。
4. **广告列表纳入变更管理**：Cloud Router 的 custom advertisement 与 BGP policy 改动走审批与 diff 通知，广告漂移等于暴露面漂移。
5. **路由基线与漂移检测**：定期记录 effective routes / TGW 传播 / advertised routes，并与批准的基线比对。
6. **保护检测层自身**：AWS 状态检测组件、各云安全中心的连接器与规则，按 crown jewel 定级；对它们的任何变更本身就是高优先级告警。
7. **workload identity 联邦审计**：跨云 claim 映射、信任策略的每次修改都过审；token 方言差异处（AWS↔Azure↔GCP）最容易被静态密钥回填，密钥回填出现即报警。
8. **路由读权限最小化**：路由表、effective routes 和传播关系的读取权限按最小授权管理，并纳入审计。完整路由视图可能揭示组织的网络依赖。
9. **内网流量可观测性**：对 VCN Flow Logs / VPC Flow Logs 建立东西向基线，监测异常的私有 DNS 查询和偏离业务基线的流量。
10. **SOC 连接器治理**：跨云连接器（如 Defender 的 AWS/GCP 连接器）的 IAM 角色一律只读起步，信任策略钉死 principal + external ID + 租户，密钥入 Key Vault/KMS 并强制轮换；连接器身份的每次授权变更按高危流程审——这是配置错误代价最大的一类资产。

## 九、结语：路由与配置治理

多云网络的关键审查对象包括前缀归属、路由传播、业务依赖和跨云身份信任。单云视角难以完整呈现这些关系，因此需要把配置与业务链路放在同一套治理和审计流程中。SOC 汇聚了多云运营数据，也引入连接器及其权限边界；连接器配置、路由变化和告警覆盖应一并纳入持续审查。

本文围绕四项治理要素展开：云网络的基础机制（5.2）、路由信息的管理（5.3）、路由表对可达性的约束（3.4），以及 SOC 连接器的跨云信任关系（7.1）。它们共同决定多云架构的可达性、可见性与配置影响范围。

---

## 十、参考

参考资料（2026-10-27 核对）：

- Microsoft Learn：About virtual hub routing（关联/传播/label/静态路由/附加考虑） — https://learn.microsoft.com/azure/virtual-wan/about-virtual-hub-routing
- Microsoft Learn：About Route-maps for virtual hubs — https://learn.microsoft.com/azure/virtual-wan/route-maps-about
- Microsoft Learn：Virtual hub routing preference — https://learn.microsoft.com/azure/virtual-wan/about-virtual-hub-routing-preference
- Microsoft Learn：Virtual WAN FAQ（0.0.0.0/0 不跨 hub、Azure 路由不得回灌） — https://learn.microsoft.com/azure/virtual-wan/virtual-wan-faq
- Microsoft Learn：Static routes in Virtual WAN（分支关联/传播最佳实践） — https://learn.microsoft.com/azure/virtual-wan/static-routes
- Microsoft Learn：Virtual WAN routing deep dive — https://learn.microsoft.com/azure/virtual-wan/routing-deep-dive
- Microsoft Learn：Global transit network architecture - Azure Virtual WAN — https://learn.microsoft.com/en-us/azure/virtual-wan/virtual-wan-global-transit-network-architecture
- Microsoft Learn：Connect Azure ExpressRoute with Oracle Cloud Infrastructure — https://learn.microsoft.com/en-us/azure/virtual-machines/workloads/oracle/configure-azure-oci-networking
- Oracle：Learn about OCI Azure Interconnect — https://www.oracle.com/cloud/azure/interconnect/
- Oracle Blog：Network latency using OCI-Azure Interconnect and best practices — https://blogs.oracle.com/cloud-infrastructure/network-latency-oci-azure-best-practices
- AWS Docs：What is AWS Interconnect（multicloud/last-mile、MACsec 默认加密） — https://docs.aws.amazon.com/interconnect/latest/userguide/what-is-interconnect.html
- AWS Docs：AWS Interconnect – region availability（GCP/Azure Preview/OCI 美东） — https://docs.aws.amazon.com/interconnect/latest/userguide/region-availability.html
- AWS Docs：How AWS Transit Gateways work — https://docs.aws.amazon.com/vpc/latest/tgw/how-transit-gateways-work.html
- AWS Docs：Transit gateway route propagation — https://docs.aws.amazon.com/vpc/latest/tgw/tgw-route-tables.html
- AWS Docs：Direct Connect gateways and Transit Gateway associations — https://docs.aws.amazon.com/directconnect/latest/UserGuide/direct-connect-transit-gateways.html
- AWS Docs：Create a transit virtual interface（TGW 与 DXGW ASN 必须不同） — https://docs.aws.amazon.com/directconnect/latest/UserGuide/create-transit-vif-dx.html
- AWS Architecture Blog：Field Notes - Working with Route Tables in AWS Transit Gateway — https://aws.amazon.com/blogs/architecture/field-notes-working-with-route-tables-in-aws-transit-gateway/
- AWS Builder：BGP traffic engineering on AWS（local pref/AS-path/MED 与非对称坑） — https://builder.aws.com/content/3GleTaxT35WNVZ9IoSGxLgE5Gp8/bgp-traffic-engineering-on-aws-as-path-communities-and-the-edge-cases-that-bite-resilient-cloud-networking-on-aws-patterns-from-the-field-article-7
- AWS Blog：AWS and Google Cloud collaborate to simplify multicloud networking — https://aws.amazon.com/blogs/networking-and-content-delivery/aws-and-google-cloud-collaborate-to-simplify-multicloud-networking/
- Google Cloud Blog：AWS and Google Cloud collaborate on multicloud networking — https://cloud.google.com/blog/products/networking/aws-and-google-cloud-collaborate-on-multicloud-networking
- InfoQ：AWS Interconnect Reaches General Availability（2026-04 GA、五区域对含美东） — https://www.infoq.com/news/2026/04/aws-interconnect-multicloud-ga/
- Google Cloud Docs：Cloud Router advertised routes（default/custom 广告模式） — https://docs.cloud.google.com/network-connectivity/docs/router/concepts/advertised-routes
- Google Cloud Docs：BGP route policies overview — https://docs.cloud.google.com/network-connectivity/docs/router/concepts/bgp-route-policies-overview
- Google Cloud Blog：BGP route policies - Top 3 use cases — https://cloud.google.com/blog/products/networking/bgp-route-policies-top-3-use-cases-by-customer-demand
- Google Cloud Docs：Configure Workload Identity Federation with AWS or Azure VMs — https://docs.cloud.google.com/iam/docs/workload-identity-federation-with-other-clouds
- Microsoft Learn：Use cloud asset inventory（Defender 多云资产清单） — https://learn.microsoft.com/azure/defender-for-cloud/asset-inventory
- Microsoft Learn：What is Microsoft Defender for Cloud（多云 CSPM/CWPP） — https://learn.microsoft.com/azure/defender-for-cloud/defender-for-cloud-introduction
- Microsoft Learn：Defender for Cloud in Defender portal（cloud scopes / attack path） — https://learn.microsoft.com/azure/defender-for-cloud/defender-portal/defender-for-cloud-defender-portal
- Microsoft Learn：Automate Microsoft Defender for Cloud connector deployment（CloudFormation 建角色、Security Connectors API） — https://learn.microsoft.com/azure/defender-for-cloud/plan-multicloud-security-automate-connector-deployment
- AWS IAM User Guide：Cross-account confused deputy prevention（external ID） — https://docs.aws.amazon.com/IAM/latest/UserGuide/confused-deputy.html
- AWS IAM User Guide：External IDs for third-party access — https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_common-scenarios_third-party.html
- Cilium：Deep Dive into Cilium Multi-cluster（ClusterMesh） — https://cilium.io/blog/2019/03/12/clustermesh/
- AWS Containers Blog：A multi-cluster shared services architecture with EKS using Cilium ClusterMesh — https://aws.amazon.com/blogs/containers/a-multi-cluster-shared-services-architecture-with-amazon-eks-using-cilium-clustermesh/
- Noction：BGP and Multi-Cloud Routing — https://www.noction.com/blog/bgp-multi-cloud-routing
- Megaport：Cross-Cloud Connectivity Made Easy with Oracle and Megaport — https://www.megaport.com/blog/cross-cloud-connectivity-made-easy-with-oracle-and-megaport/
- Sysdig：Threat detection in the cloud - Defender vs GuardDuty vs Security Command Center — https://www.sysdig.com/learn-cloud-native/threat-detection-in-the-cloud-defender-vs-guardduty-vs-security-command-center

本文的攻击路径仅作理论归类与防御对照，不构成可执行攻击指引；相关推演仅适用于已获授权的靶场与工程。
