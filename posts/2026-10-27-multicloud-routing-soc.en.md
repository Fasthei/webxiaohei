---
title: "Multicloud Network Control Planes: Routing and Security Operations Across OCI, GCP, Azure, and AWS"
date: "2026-10-27"
slug: "multicloud-routing-soc"
category: "Cloud Security Research"
summary: "Using a hypothetical OCI, Google Cloud, Azure, and AWS deployment, this article reviews interconnects, routing control planes, Kubernetes networking, private endpoints, and multicloud security operations."
---

# Multicloud Network Control Planes: Routing and Security Operations Across OCI, GCP, Azure, and AWS

This article uses a hypothetical network connecting OCI, Google Cloud, Azure, and AWS to discuss routing control planes and their security operations. Kubernetes hosts inference and training workloads, while private circuits, gateways, and routing policy constrain cross-cloud traffic.

In multicloud environments, route advertisements, trust relationships, and configuration changes matter as much as firewall policy. This review focuses on those control-plane elements and their auditability: understanding reachability boundaries, identifying configuration drift, and bringing relevant signals into security operations.

The assumed design uses Azure Virtual WAN in East US 2 as the core network node, with a hybrid ExpressRoute hub connecting AWS, Google Cloud, and OCI. OCI provides an edge and access network; Google Cloud is a distributed aggregation layer for databases, Redis, and queues; Azure and AWS carry core workloads. AWS also hosts distributed service-state checks, and Kubernetes runs across the clouds.

With private endpoints, public service exposure may be small, but internal reachability still depends on route tables, private circuits, and private DNS. Review cross-cloud paths against both configuration and business dependencies. SOC connectors belong in the same review: they support operations, but excessive permissions or weak trust configuration can expand cross-cloud impact.

## 1. Architecture overview: roles of the four clouds

Define the boundaries before reviewing the network. Each cloud has a network role that determines how its prefixes are advertised and how its trust boundary is configured.

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

| Cloud | Network role | Workload role | Security review focus |
| --- | --- | --- | --- |
| Azure East US 2 | vWAN hub and ExpressRoute aggregation | Core workloads and AKS | Hub route tables and cross-cloud propagation |
| OCI | Edge and business-network access | OKE and ingress | Prefix ownership and private connectivity |
| Google Cloud | Global aggregation layer | Databases, Redis, queues, and GKE | Aggregated data paths and reachability |
| AWS | Workload platform across multiple AZs | EKS inference/training and state checks | Protect shared workload and detection dependencies |

From a network-governance perspective, three areas warrant review. First, the edge and aggregation layers are separate, so review each routing domain along cross-cloud paths. Second, AWS state checks—health, consistency, and traffic observations—are part of service availability and security monitoring; protect their configuration, data sources, and alert chain. Third, availability zones in different clouds are not equivalent; assess failure domains, link dependencies, and recovery objectives separately.

> I start by recording prefix ownership, advertisement sources, and propagation scope, then map those to application dependencies. That puts network reachability and business boundaries into the same review.

## 2. Physical connectivity: interconnects at the hub

Routing policy depends on physical connectivity. This design mixes direct and managed services to connect AWS, Google Cloud, and OCI to the same vWAN hub.

**OCI: OCI-Azure Interconnect.** Oracle FastConnect and Azure ExpressRoute can cross-connect in paired data centers, with an Azure circuit attached to a vWAN ExpressRoute gateway and an OCI connection attached to a FastConnect DRG. BGP runs between the two sides. East US and OCI Ashburn are a supported pairing for this design. BGP and prefix filters are configured on the connection, providing flexibility and requiring careful configuration management.

**Google Cloud and AWS: Cross-Cloud Interconnect and AWS Interconnect – multicloud.** AWS and Google announced a jointly engineered multicloud-networking service in November 2025, and AWS Interconnect reached general availability in April 2026. Google Cloud uses Cross-Cloud Interconnect and AWS uses Interconnect – multicloud, with an initial set of five regional pairs that includes the eastern United States. The link between AWS and partner devices uses MACsec (IEEE 802.1AE) by default and forwards customer traffic only when the encrypted session is active. The managed service avoids customer-managed physical routers, cross-connects, and BGP peering; AWS attaches through a Direct Connect gateway. Azure availability is Preview, while OCI interoperability is available in the eastern United States.

**Exchange fabrics as another option.** Network-as-a-service providers such as Equinix and Megaport offer cloud routers, including Megaport MCR, to connect cloud circuits through a shared fabric and manage BGP. This can extend coverage where direct connections are unavailable, but it adds a third-party routing domain where prefixes may be re-advertised or aggregated. The trust boundary then includes the provider.

> The physical layer defines connectivity boundaries. With direct connections, review BGP and prefix filters at both gateways. With managed interconnects, review the attachment and prefix-allowlist configuration at each end. Identify the connection type before interpreting route tables.

## 3. Routing policy: three control planes, one business network

The design uses three routing control planes—Azure vWAN, AWS Transit Gateway, and Google Cloud Router—with BGP as the common protocol. Each cloud's routing model determines how prefixes are accepted and propagated.

### 3.1 Azure vWAN: association, propagation, and hub route tables

The vWAN virtual hub router is the network hub. Its three basic concepts are:

- **Association:** each connection—VNet, ExpressRoute, or VPN—is associated with one hub route table, which determines the table used for forwarding. By default, connections use the hub's Default route table.
- **Propagation:** connections can advertise routes into one or more tables; labels such as the Default label can group propagation across hubs. The hub also advertises routes in its tables back to branches using BGP. Propagating to a None route table means that routes are not propagated.
- **Static routes:** hub route tables can contain static routes, with a VNet connection or Azure Firewall as a next hop. For the same prefix, a static route takes precedence over a learned dynamic route.

Additional features include Hub Routing Preference for choosing among VPN, ExpressRoute, and SD-WAN paths to the same on-premises prefix; routing intent and policy for directing Internet and private traffic to Azure Firewall or an NVA; route maps for aggregation, filtering, and BGP-attribute changes; and effective-routes views for reviewing active routes.

Three configuration areas deserve particular attention: `0.0.0.0/0` behavior across hubs, preventing Azure-learned routes from being re-advertised back into Azure, and consistent association and propagation of branch connections. Review these settings as a complete hub policy rather than in isolation.

> The vWAN association and propagation matrix expresses network policy. Validate custom route tables, None-table propagation, and static routes against the intended isolation design; an unexpected static route can override a learned route.

### 3.2 AWS: DXGW, Transit VIF, and Transit Gateway route tables

AWS Direct Connect is the network entry point, while the combination of Direct Connect gateway (DXGW), transit virtual interface, and Transit Gateway (TGW) handles routing.

- A Transit VIF attaches a TGW to a DXGW; the TGW ASN must differ from the DXGW ASN.
- The DXGW advertises attached VPC and TGW prefixes using its ASN, providing a consolidated view to the BGP peer.
- TGW route-table association determines which table an attachment uses for forwarding; propagation determines which tables receive its routes. The default TGW route table is enabled for default association and propagation, so production designs should review whether explicit tables are needed.
- Isolation options include blackhole routes, disabling propagation, and dedicated route tables for isolated attachments.
- Direct Connect BGP route selection uses attributes such as local preference, AS path, and MED. AS-path prepending and communities can support traffic engineering, but need careful validation to avoid unintended asymmetry.

**Workload implications:** EKS VPCs attach to TGW, and multi-AZ subnet design is part of the routing and resilience model. If business-state checks run in AWS, the paths and observability through TGW are also operational dependencies.

> TGW propagation and DXGW attachments define which networks can communicate. Review the route tables, associations, propagation, and shared gateway attachments together, including any paths that do not traverse the intended vWAN controls.

### 3.3 Google Cloud Router: advertisements and BGP route policies

Google Cloud Router provides routing advertisements for the aggregation layer, either directly or through an NCC hub:

- **Advertisement mode:** default mode advertises VPC subnets and imported NCC subnets or dynamic routes; custom mode can include configured IPv4 and IPv6 prefixes.
- **BGP route policies:** policies can filter and modify learned inbound routes and advertised outbound routes by peer and prefix, including MED, AS path, and communities.
- **Multiple paths:** VLAN attachments and BGP sessions for Cross-Cloud or Partner Interconnect may install more than one path. Use route policy, MED, or AS-path controls to define intended primary and backup paths.

With databases, Redis, and queues in Google Cloud, aggregation prefixes are important dependencies. Cloud Router session state and route advertisements can help operators understand which cloud routes are visible and whether they match the approved design.

> Custom advertisement lists determine which prefixes are announced. Put changes to advertisements and BGP policies under approval, review, and drift monitoring; an unplanned prefix changes the network exposure model.

### 3.4 Unified view: BGP is the protocol; routes are policy

The three control planes combine into a network with a control plane and a business plane:

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

Routing tables can act as an implicit reachability control. Security groups and firewalls govern whether a session is allowed; routing determines whether a path exists. In multicloud environments, that routing configuration is often reviewed less consistently. A prefix may pass from OCI through vWAN, DXGW, TGW, and an EKS VPC; each propagation setting should be included in network change review.

## 4. Kubernetes: Pod CIDR as a second routing plane

Inference and training workloads run on Kubernetes (EKS, AKS, GKE, and OKE), which introduces Pod CIDR and Service CIDR ranges into the network plan.

Container ranges should be included in the global CIDR plan and advertised where required: EKS pod ranges may need to traverse TGW and DXGW to vWAN; GKE secondary ranges may be advertised by Cloud Router; AKS and OKE ranges need equivalent consideration. Cross-cluster traffic, such as model distribution or scheduling, may use a multicluster network such as Cilium ClusterMesh or Submariner, which depends on underlying pod-to-pod reachability.

For security review, two issues matter. First, advertising a Pod CIDR expands network reachability, so review it alongside Kubernetes NetworkPolicy. Second, workload identity federation can provide workloads with short-lived credentials in other clouds. Review cross-cloud claim mappings and target-role permissions independently from network isolation; network boundaries alone do not constrain identity-based access.

> I review Pod-range advertisements, workload-identity bindings, and multicluster connections as separate objects, checking each one's scope, owner, and change record.

## 5. Private endpoints and route visibility

This section distinguishes the service surface from the network control plane. In the assumed design, OCI access services sit behind Private Endpoints, which reduces public exposure; service-to-service reachability still depends on routes, circuits, name resolution, and access controls.

### 5.1 Private Endpoints and the service boundary

The access services have no public IP addresses and are exposed through private subnets and Private Endpoints, reachable through the VCN or FastConnect private paths. Security lists, NSGs, and IAM constrain network and control-plane access. Reduced public visibility does not eliminate internal reachability; inventory private endpoints, DNS zones, and permitted paths.

### 5.2 Public exposure and boundary validation

When a service has only a private address and its network policies are correct, public requests generally cannot connect to it. Review the following boundaries rather than inferring resource existence from a scan result:

- **Public addresses and listeners:** confirm whether a public entry point exists and review firewall, security-list, and NSG allow rules.
- **Private network paths:** review reachability across VNets, VPCs, VCNs, and private circuits, including default routes and shared gateways.
- **Control-plane permissions:** separate permissions to read inventories from permissions to change network configuration, and retain audit records.
- **Identity entry points:** verify that public sign-in surfaces, identity providers, and application access policies match the deployment.

Private Endpoints reduce public service exposure; they do not replace internal routing and identity governance. Configuration review and change auditing remain necessary.

### 5.3 Governance of routing information

Private Endpoints require routes to be reachable by workloads. Route tables, propagation relationships, and private DNS records therefore describe the communication paths allowed by the design. Treat this information as sensitive configuration and manage it through access controls, baselines, and change auditing.

```text
资产与路由治理                         安全运营
┌──────────────────────┐           ┌─────────────────────┐
│ 前缀归属与用途登记     │ ────────► │ 路由基线与变更审计   │
│ 专线与网关依赖         │ ────────► │ 可达性与策略复核     │
│ 私有 DNS 与端点范围    │ ────────► │ 异常配置关联告警     │
└──────────────────────┘           └─────────────────────┘
```

I treat routing information as governance data: prefixes, parent gateways, propagation targets, and DNS records should have owners and map to approved business flows. Minimize read access because a complete route view can reveal organizational network dependencies.

> Private Endpoints reduce public exposure but do not remove internal reachability risk. Route-read permissions, private DNS zones, and cross-cloud connectivity matrices belong in asset inventories, continuous monitoring, and change management.

## 6. Routing and identity risk review

The following sections organize common risks by network configuration, identity trust, and detection. The focus is finding and correcting misconfiguration.

### 6.1 Route and asset inventory

A cross-cloud network inventory should cover effective routes, hub-route-table associations and propagation, TGW route tables and attachments, Cloud Router advertisements, and BGP session state. Compare these configurations with the prefix inventory and business dependencies to identify unexpected propagation or scope mismatches.

Perform asset discovery and permission review through approved management interfaces, recording the querying identity and scope. Do not use access-denied responses to infer whether a resource exists; confirm configuration through the authorized inventory process.

### 6.2 Configuration risks

Review for unexpected propagation into isolated route tables, Direct Connect gateway attachments outside the intended path, static routes that override expected routes, unapproved Cloud Router advertisements, and overly broad workload-identity federation claim mappings. These issues may appear first as control-plane changes rather than obvious network alerts; configuration baselines and audit logs are important.

### 6.3 Detection and available signals

In the assumed design, AWS hosts workload-state checks, while cloud security services monitor configuration and threats: GuardDuty and Security Hub for AWS, Defender for Cloud for Azure and connected AWS/GCP resources, Security Command Center for Google Cloud, and Cloud Guard for OCI. Network API events are distributed across CloudTrail, Azure Activity Log, Google Cloud Audit Logs, and OCI Audit. Changes to effective vWAN routes, TGW propagation, or Cloud Router advertisements may be reconstructable from those records.

Operators should confirm which network read and change events reach audit systems, whether GuardDuty and other cloud services detect relevant activity, and whether the SOC can correlate events across clouds. Coverage depends on service, license, and log configuration and should be validated in the deployed environment.

### 6.4 Change validation

After an approved network or identity change, validate the intended routes, service reachability, and log coverage using the change plan. A successful control-plane operation does not establish that the business path behaves as expected; the system owner should perform the validation and retain results and rollback conditions.

### 6.5 Trust-boundary table

The architecture's boundaries can be categorized as configuration-enforced or dependent on detection:

| Boundary | Type | Enforcement | Review implication |
| --- | --- | --- | --- |
| OCI Private Endpoint ingress | Configuration-enforced | Private subnets, security lists/NSGs, IAM | Verify route reachability and endpoint authorization |
| SOC cross-cloud connector | Configuration-enforced | Entra application ↔ IAM role with external ID | Apply least privilege and review trust and identity changes |
| vWAN association/propagation | Configuration-enforced | Hub route-table configuration | Compare propagation scope with intended isolation |
| TGW association/propagation | Configuration-enforced | TGW route-table configuration | Review propagation scope and DXGW attachments |
| Cloud Router advertisements | Configuration-enforced | Advertisement mode and BGP policy | Baseline advertised prefixes and monitor changes |
| Hub firewall and routing intent | Configuration-enforced | Azure Firewall or NVA next hop | Validate the next hop and intended inspection path |
| AWS state-detection layer | Detection and configuration | Health logic and network observation | Protect the layer and monitor configuration and availability |
| Workload Identity Federation | Configuration-enforced | Trust policy and claim mapping | Review mapping scope and intended identity boundaries |
| Cloud security services | Detection-dependent | Detection rules | Verify rule coverage, alert routing, and auditability |

## 7. Multicloud SOC: operational aggregation and configuration risk

A SOC collects alerts, configuration, and incidents from the four clouds into a common timeline so teams can detect, investigate, and respond. Aggregation improves operations, but each cross-cloud connector adds configuration and permission risk. The connectors can be among the deepest cross-cloud relationships in the architecture, so their permissions and trust configuration deserve careful review.

The service landscape includes:

- **Microsoft Defender for Cloud** connects AWS accounts and Google Cloud projects and provides a combined Azure/AWS/GCP inventory, including supported container, AI/ML, and identity resources. It also supports risk prioritization, attack paths, KQL/ARG queries, and cloud-scope RBAC.
- **AWS Security Hub and GuardDuty** focus on AWS posture and threat detection; findings can be forwarded to a SIEM.
- **Google Cloud Security Command Center** covers Google Cloud posture and threats and can export findings.
- **OCI Cloud Guard** provides OCI detection and response recipes.
- **OCI integration gap:** Defender for Cloud's multicloud inventory does not include OCI. A SIEM such as Sentinel or a third-party system can bring Cloud Guard alerts into the shared timeline. Schemas, time sources, and entity naming differ among cloud providers, adding integration work.

### 7.1 Connector configuration and AWS inventory

Connecting Defender for Cloud to AWS EC2 requires a cross-cloud trust relationship. An AWS CloudFormation template creates an IAM role whose trust policy identifies the Microsoft service principal and uses an external ID; an Entra application represents the connector identity. The connector then reads EC2 configuration and can onboard Defender for Servers alerts and assets into the shared inventory.

Each component should be configured narrowly. A wildcard principal, broader-than-required permissions, client secrets stored in source control or an unprotected pipeline, missing key rotation, or lingering access after personnel changes can all expand the connector's impact. Use supported federated credentials where available and review the actual role permissions and connector identity.

> SOC connectors are authorized cross-cloud relationships. Inventory their AWS roles, Entra applications, credentials, and permissions; apply least privilege and monitor changes to both trust policies and connector identities.

### 7.2 SOC coverage and resilience

Three coverage areas need validation. First, **routing visibility**: cloud security-center coverage of IAM, workloads, and exposure does not necessarily include route configuration; route-table changes should have their own baseline and audit process. Second, **cross-cloud event correlation**: a single-cloud alert may not reconstruct a multicloud business path, so verify that entity identifiers, timestamps, and log fields support investigation. Third, **protection of the detection layer**: include AWS state checks, cloud security centers, and cross-cloud connectors in asset inventories, permission reviews, and change monitoring.

> When reviewing a multicloud SOC, I look for gaps in route visibility, cross-cloud correlation, connector trust, and protection of the detection layer. These are integration and governance questions as much as product-capability questions.

## 8. Multicloud network governance checks

The following checks can serve as a multicloud network-governance baseline:

1. **Prefix ownership:** maintain an authoritative inventory of all CIDRs, including pod and service ranges, their owners, advertisements, and propagation scope.
2. **Explicit propagation:** review default route-table association and propagation in vWAN and TGW; use custom tables, None tables, and blackhole routes where required by the isolation design.
3. **DXGW topology:** regularly review attachments under each DXGW and confirm that cross-cloud paths match the intended vWAN mediation.
4. **Advertisement change control:** require approval and diff notifications for Cloud Router custom advertisements and BGP policy changes.
5. **Route baselines and drift detection:** periodically record effective routes, TGW propagation, and advertised routes, then compare them with the approved baseline.
6. **Protect detection systems:** treat AWS state-check components, cloud security connectors, and detection rules as critical assets; alert on their changes.
7. **Workload identity federation:** review claim mappings and trust-policy changes; alert on unexpected long-lived credentials in place of federation.
8. **Least-privilege route access:** restrict and audit read access to route tables, effective routes, and propagation configuration. A complete route view may reveal organizational network dependencies.
9. **Internal-traffic observability:** baseline east-west VCN Flow Logs and VPC Flow Logs, and monitor unusual private DNS queries and traffic that departs from business baselines.
10. **SOC connector governance:** begin with read-only roles, pin trust to the expected principal and external ID, store credentials in managed secret systems, rotate them, and treat authorization changes as high risk.

## 9. Closing perspective

Multicloud network review centers on prefix ownership, route propagation, business dependencies, and cross-cloud identity trust. A single-cloud view is insufficient to show all of these relationships; configuration and business paths need to be reviewed together. The SOC aggregates operational data, but its connectors introduce their own identity and permission boundaries. Connector configuration, route changes, and alert coverage all belong in ongoing review.

This article focuses on four governance areas: cloud-network fundamentals (Section 5.2), route-information governance (Section 5.3), reachability controls expressed by route tables (Section 3.4), and cross-cloud trust through SOC connectors (Section 7.1). Together, they determine reachability, visibility, and the potential impact of configuration changes.

---

## 10. References

References checked on 2026-10-27:

- Microsoft Learn: About virtual hub routing — https://learn.microsoft.com/azure/virtual-wan/about-virtual-hub-routing
- Microsoft Learn: About Route-maps for virtual hubs — https://learn.microsoft.com/azure/virtual-wan/route-maps-about
- Microsoft Learn: Virtual hub routing preference — https://learn.microsoft.com/azure/virtual-wan/about-virtual-hub-routing-preference
- Microsoft Learn: Virtual WAN FAQ — https://learn.microsoft.com/azure/virtual-wan/virtual-wan-faq
- Microsoft Learn: Static routes in Virtual WAN — https://learn.microsoft.com/azure/virtual-wan/static-routes
- Microsoft Learn: Virtual WAN routing deep dive — https://learn.microsoft.com/azure/virtual-wan/routing-deep-dive
- Microsoft Learn: Global transit network architecture - Azure Virtual WAN — https://learn.microsoft.com/en-us/azure/virtual-wan/virtual-wan-global-transit-network-architecture
- Microsoft Learn: Connect Azure ExpressRoute with Oracle Cloud Infrastructure — https://learn.microsoft.com/en-us/azure/virtual-machines/workloads/oracle/configure-azure-oci-networking
- Oracle: Learn about OCI Azure Interconnect — https://www.oracle.com/cloud/azure/interconnect/
- Oracle Blog: Network latency using OCI-Azure Interconnect and best practices — https://blogs.oracle.com/cloud-infrastructure/network-latency-oci-azure-best-practices
- AWS Docs: What is AWS Interconnect — https://docs.aws.amazon.com/interconnect/latest/userguide/what-is-interconnect.html
- AWS Docs: AWS Interconnect – region availability — https://docs.aws.amazon.com/interconnect/latest/userguide/region-availability.html
- AWS Docs: How AWS Transit Gateways work — https://docs.aws.amazon.com/vpc/latest/tgw/how-transit-gateways-work.html
- AWS Docs: Transit gateway route propagation — https://docs.aws.amazon.com/vpc/latest/tgw/tgw-route-tables.html
- AWS Docs: Direct Connect gateways and Transit Gateway associations — https://docs.aws.amazon.com/directconnect/latest/UserGuide/direct-connect-transit-gateways.html
- AWS Docs: Create a transit virtual interface — https://docs.aws.amazon.com/directconnect/latest/UserGuide/create-transit-vif-dx.html
- AWS Architecture Blog: Field Notes - Working with Route Tables in AWS Transit Gateway — https://aws.amazon.com/blogs/architecture/field-notes-working-with-route-tables-in-aws-transit-gateway/
- AWS Builder: BGP traffic engineering on AWS — https://builder.aws.com/content/3GleTaxT35WNVZ9IoSGxLgE5Gp8/bgp-traffic-engineering-on-aws-as-path-communities-and-the-edge-cases-that-bite-resilient-cloud-networking-on-aws-patterns-from-the-field-article-7
- AWS Blog: AWS and Google Cloud collaborate to simplify multicloud networking — https://aws.amazon.com/blogs/networking-and-content-delivery/aws-and-google-cloud-collaborate-to-simplify-multicloud-networking/
- Google Cloud Blog: AWS and Google Cloud collaborate on multicloud networking — https://cloud.google.com/blog/products/networking/aws-and-google-cloud-collaborate-on-multicloud-networking
- InfoQ: AWS Interconnect Reaches General Availability — https://www.infoq.com/news/2026/04/aws-interconnect-multicloud-ga/
- Google Cloud Docs: Cloud Router advertised routes — https://docs.cloud.google.com/network-connectivity/docs/router/concepts/advertised-routes
- Google Cloud Docs: BGP route policies overview — https://docs.cloud.google.com/network-connectivity/docs/router/concepts/bgp-route-policies-overview
- Google Cloud Blog: BGP route policies - Top 3 use cases — https://cloud.google.com/blog/products/networking/bgp-route-policies-top-3-use-cases-by-customer-demand
- Google Cloud Docs: Configure Workload Identity Federation with AWS or Azure VMs — https://docs.cloud.google.com/iam/docs/workload-identity-federation-with-other-clouds
- Microsoft Learn: Use cloud asset inventory — https://learn.microsoft.com/azure/defender-for-cloud/asset-inventory
- Microsoft Learn: What is Microsoft Defender for Cloud — https://learn.microsoft.com/azure/defender-for-cloud/defender-for-cloud-introduction
- Microsoft Learn: Defender for Cloud in Defender portal — https://learn.microsoft.com/azure/defender-for-cloud/defender-portal/defender-for-cloud-defender-portal
- Microsoft Learn: Automate Microsoft Defender for Cloud connector deployment — https://learn.microsoft.com/azure/defender-for-cloud/plan-multicloud-security-automate-connector-deployment
- AWS IAM User Guide: Cross-account confused deputy prevention — https://docs.aws.amazon.com/IAM/latest/UserGuide/confused-deputy.html
- AWS IAM User Guide: External IDs for third-party access — https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_common-scenarios_third-party.html
- Cilium: Deep Dive into Cilium Multi-cluster (ClusterMesh) — https://cilium.io/blog/2019/03/12/clustermesh/
- AWS Containers Blog: A multi-cluster shared services architecture with EKS using Cilium ClusterMesh — https://aws.amazon.com/blogs/containers/a-multi-cluster-shared-services-architecture-with-amazon-eks-using-cilium-clustermesh/
- Noction: BGP and Multi-Cloud Routing — https://www.noction.com/blog/bgp-multi-cloud-routing
- Megaport: Cross-Cloud Connectivity Made Easy with Oracle and Megaport — https://www.megaport.com/blog/cross-cloud-connectivity-made-easy-with-oracle-and-megaport/
- Sysdig: Threat detection in the cloud - Defender vs GuardDuty vs Security Command Center — https://www.sysdig.com/learn-cloud-native/threat-detection-in-the-cloud-defender-vs-guardduty-vs-security-command-center

This article discusses architectural risk categories and defensive review; validate the examples against the actual network and authorization design.
