---
title: "Microsoft 365, Copilot, and the Security Control Plane"
date: "2026-10-26"
slug: "microsoft-identity-part2-m365-copilot"
category: "Cloud Security Research"
summary: "This article reviews Microsoft 365's layered authorization model, its boundaries with Azure, workload access paths, Microsoft Graph application permissions, Copilot data access, and the control planes for Sentinel, Purview, Defender, and Intune."
---

# Microsoft 365, Copilot, and the Security Control Plane

The previous article covered identity, resource, and billing boundaries. This article examines Microsoft 365 workload authorization, its relationship with Azure, Copilot's data access, and security and management services such as Sentinel, Purview, Defender, and Intune.

## 1. Microsoft 365 authentication and authorization layers

Microsoft 365 consists of workloads such as Exchange Online, SharePoint Online, OneDrive, Teams, and Office applications. Entra handles sign-in, MFA, Conditional Access, and token issuance. Authorization, however, is implemented through multiple systems that developed independently and are managed in different service portals.

Microsoft 365 has several independently developed role-based authorization systems, each with its own administrative portal. This explains why Exchange has role groups, SharePoint has site permissions, and Teams has policies: these are not one shared authorization model merely because the Entra admin center surfaces some of their roles.

Entra roles fall into three broad groups. Directory roles, such as User Administrator and Application Administrator, manage directory objects. Service-specific roles, such as Exchange Administrator, Intune Administrator, SharePoint Administrator, and Teams Administrator, manage their respective workloads. Cross-service roles, including Global Administrator, Global Reader, Security Administrator, Security Reader, and Compliance Administrator, are recognized across several Microsoft 365 security and compliance services. Some Entra roles map to workload roles—for example, Exchange Administrator has a relationship to the Exchange Organization Management role group—but the effective permissions should be checked against current role definitions.

Each workload also has its own authorization system: Exchange role groups and management roles, SharePoint permissions at site, library, and item levels, and Teams policies and external-access settings. Application consent is another layer. A Microsoft Graph application permission can allow an application to access API data without a specific user, subject to the permission type, administrator consent, and any supported resource-scope controls. Intune compliance state is a device signal that Conditional Access can evaluate.

When reviewing Microsoft 365 access, I separate Entra roles, workload-specific permissions, application consent, and device-compliance conditions. The access model is not fully represented in any one portal.

> The Entra admin center is an entry point to Microsoft 365 permissions, not a complete inventory. Exchange role groups, SharePoint site permissions, Teams policies, and Graph application consent need separate review.

## 2. Microsoft 365 and Azure: shared identity, separate authorization

Microsoft 365 and Azure share an Entra tenant, users, groups, applications, and devices, but they have different authorization planes. Azure RBAC governs Azure resources; Microsoft 365 workloads use the models described above. A subscription Owner does not thereby manage mailboxes, and an Exchange Administrator does not thereby control virtual machines.

Several systems connect the two sides:

- **Identity and policy:** Conditional Access is configured in Entra and can target Microsoft 365 services as well as Azure management APIs. Intune reports device compliance to Entra, where Conditional Access can evaluate it.
- **APIs:** Microsoft Graph is a primary API for Microsoft 365; Azure resource management uses ARM. Graph exposes some directory information, but Azure resource operations remain under ARM.
- **Compliance:** Purview covers Microsoft 365 content and supports selected Azure data sources, depending on the feature and source.
- **Security:** Defender XDR covers Microsoft 365 security workloads, Defender for Cloud protects Azure and supported multicloud resources, and Sentinel can ingest signals from both.
- **Devices:** Intune manages endpoints, device records are registered in Entra, and compliance signals can affect access to Microsoft 365 and Azure.

Microsoft 365 licensing is associated with users and the tenant and does not require an Azure subscription. Sentinel and Defender for Cloud, however, run in Azure subscription contexts. A Microsoft 365 security operation may therefore depend on one or more Azure subscriptions, while its commercial subscription and Azure billing account remain separate.

```text
                 ┌─────────────────────────────┐
                 │   Entra 租户（身份平面）      │
                 │  用户 / 组 / 应用 / 设备 / CA  │
                 └───────┬─────────────┬───────┘
                         │             │
        ┌────────────────▼──┐      ┌──▼────────────────┐
        │  M365（数据平面）    │      │  Azure（资源平面）  │
        │  Exchange/SP/Teams │      │  订阅/管理组/资源    │
        │  Graph API         │      │  ARM + Azure RBAC  │
        └────────────────┬──┘      └──┬────────────────┘
                         │             │
         ┌───────────────┴─────────────┴──────────────┐
         │   安全与管理平面（横跨两边）                  │
         │   Defender XDR · Sentinel · Purview · Intune │
         └─────────────────────────────────────────────┘
```

## 3. Microsoft 365 workload access paths

Each workload has distinct data-access paths and audit records. The relevant question is how data is accessed and which control records that access.

### 3.1 Exchange Online: three access paths

Mailbox access can arise from user delegation, application access, or compliance administration. Applications may use Microsoft Graph application permissions, subject to tenant consent and supported scope controls such as Exchange Online RBAC for Applications. Purview eDiscovery Manager can search and export authorized content locations, subject to case membership, role assignments, and search filters. Exchange Online's ApplicationImpersonation role was retired in February 2025 and should not be treated as a current access path; legacy applications should be checked for migration.

These paths have different audit implications. Delegation is a per-mailbox configuration issue. Application access depends on consent and credentials, so review the permissions granted to each application rather than relying only on user sign-in events. eDiscovery search and export are designed to handle large data sets; whether a given operation is unusual depends on the organization's baseline.

Mailbox rules and forwarding settings are another workload-level configuration surface. Rules can forward or move messages without a directory-role change. Review mailbox rules and forwarding settings directly, in addition to directory logs.

### 3.2 SharePoint and OneDrive: inheritance and sharing

SharePoint permissions can be inherited from sites, libraries, or items, or customized when inheritance is broken. Temporary sharing, guest access, and forgotten unique permissions can accumulate over time. Graph application permissions for files and sites add another access path. External sharing settings—anyone links, specific guests, or organization links—affect the actual visibility of content.

This accumulated permission state can make existing access easier to discover and aggregate, including through AI tools. To assess user-visible content, evaluate permissions from the user's perspective as well as from an administrator's. Review anyone links and sites with broken inheritance before deploying Copilot.

### 3.3 Teams: cross-organization collaboration

Teams boundary settings include federation with external organizations, guest invitations, and shared channels. Shared channels rely on cross-tenant access settings and provide a content-level collaboration path between tenants. Graph application permissions also cover message-related data. Membership and shared-channel content can provide context that is not visible in mailbox audit alone.

### 3.4 Graph application permissions

The common pattern across workloads is application registration, consent, credential use to obtain a token, and access to a workload API. Applications with Mail.Read or Files.Read.All may access corresponding organizational data after consent, but the effective scope can be constrained by Exchange application RBAC, application access policies, or API-specific capabilities.

The consent process controls which applications users can approve, which require administrator consent, and how consent is reviewed. User consent and administrator consent grant different permission types and should be governed accordingly. Permission scope, duration, and credential rotation affect exposure if an application credential is compromised.

> Review the tenant's consented third-party applications, recent application credentials, and user-consent settings. An application credential alone does not grant tenant-wide data access; its effective permissions depend on consent and the relevant resource-scope controls.

### 3.5 Audit and investigation

Purview Audit records activity for supported Microsoft 365 workloads and features, but it does not capture every operation or provide a complete view of permission state. Audit configuration, retention, search privileges, and export privileges are themselves administrative controls. eDiscovery search and export are legitimate compliance functions, so assess their use against roles, case membership, scope filters, and the organization's normal activity.

> Review audit coverage and retention by workload. A unified audit service does not mean that every workload records every event in the same way or for the same period.

## 4. Copilot: data access boundaries and risks

### 4.1 How Copilot accesses data

Copilot combines a language model with organizational data. Microsoft Graph provides access to documents, email, calendars, chats, meetings, and contacts. Semantic indexing supports retrieval and grounding while respecting user permissions. Microsoft states that Copilot surfaces organizational data the user is permitted to view; the underlying workload permissions, including cross-tenant collaboration permissions, remain relevant. Agents and Graph connectors can bring external or third-party data into scope, and their behavior depends on their identity and configuration.

Prompts, responses, and data accessed through Graph are not used to train foundation models under Microsoft's stated Microsoft 365 Copilot data-protection commitments. Built-in safeguards address prompt injection and harmful content, but they are one layer of defense rather than a guarantee against every attack.

### 4.2 Five areas of risk

Copilot combines existing permissions with a new retrieval and interaction layer. Its risks are best assessed through that combination.

First, **permission amplification**: Copilot does not inherently change access rights, but can make information already visible to a user faster to find and summarize. High-visibility accounts and users with broad access therefore warrant careful permission review.

Second, **accumulated sharing**: Copilot can surface content that has been over-shared through anyone links, broken inheritance, or unnecessary guest access. Reviewing Copilot exposure consequently requires reviewing the underlying Microsoft 365 permissions.

Third, **indirect prompt injection**: instructions embedded in documents, email, or Teams content may influence model output or subsequent processing. Potential effects depend on the product, connected identity, and available actions, from misleading responses to unintended actions by an authorized agent. Prompt-injection safeguards should be treated as defense in depth.

Fourth, **agents and connectors**: agents may use delegated user identity, a connection owner's identity, or an application identity, depending on product and configuration. Graph connectors bring external content into search and need appropriate access controls and security trimming. Inventory the agents, identities, data sources, credentials, and authorization owners.

Fifth, **connections to Azure and on-premises systems**: Microsoft 365 Copilot does not automatically grant Azure RBAC to a user. Agents, plugins, and connectors may connect to external APIs, but their reach depends on the configured identity and authorization. Copilot is a retrieval layer, not an implicit cross-boundary grant.

> Microsoft 365 Copilot generally follows the user's existing permissions for organizational data. Agents and connectors depend on their own identities and connection settings. Permission reviews and extension governance remain necessary because retrieval can make authorized content easier to aggregate.

### 4.3 Observability

Purview Audit records supported Copilot and AI application events, which may include the user, time, interaction location, and accessed resources. Some records can include prompt and response information. Searchability, retention, and eDiscovery availability depend on the Copilot product, licensing, audit configuration, and retention policies. Verify the coverage for each product rather than assuming all AI interactions are retained identically. Microsoft also provides data-security capabilities for AI scenarios, including DSPM for AI.

## 5. Security services: Sentinel, Purview, Defender, and Intune

### 5.1 Microsoft Sentinel

Sentinel is a cloud-native SIEM for threat detection, investigation, response, and hunting in multicloud and multiplatform environments. It stores data in a Log Analytics workspace. Its access depends on workspace, subscription, and Sentinel roles. Entra ID, Azure Activity, Microsoft 365 audit, and Defender alerts can be ingested through data connectors.

Sentinel is available in the Defender portal; the Azure portal experience is scheduled to stop being supported after March 31, 2027. Since July 2025, eligible new customer workspaces are automatically connected to the Defender portal when Sentinel is enabled. Eligibility includes required subscription permissions and excludes Azure Lighthouse delegated users. Defender portal access can use Unified RBAC; Azure resources themselves remain governed by Azure RBAC.

Two details matter in access reviews. Role assignments are cumulative, so combine Sentinel roles with Azure Contributor and Log Analytics roles when assessing effective access. Data protection follows Azure Monitor's append-oriented model, but deletion paths remain available for compliance purposes; logs are not absolutely immutable. Sentinel also supports Lighthouse cross-tenant management, which should be included in the cross-tenant inventory.

Sentinel permissions have both investigative and configuration effects. Read permissions allow workspace queries; Sentinel Contributor and higher roles may modify analytics rules, automation rules, and playbooks. Rule changes should be monitored independently from the alerts those rules produce.

### 5.2 Microsoft Purview

Purview provides compliance capabilities including audit, eDiscovery Standard and Premium, DLP, Insider Risk Management, communication compliance, data lifecycle and records management, and AI data-security governance. Insider Risk Management correlates signals to identify potential malicious or accidental risks and uses pseudonymization by default, alongside role-based access and audit.

The eDiscovery Manager role group can search and export authorized content locations, subject to case membership and search-scope filters. Application-only authentication for eDiscovery PowerShell cmdlets is not a supported scenario; Microsoft recommends Microsoft Graph APIs where available. Existing automation guidance should be treated as compatibility information rather than a guarantee. The Entra role Purview Workload Content Administrator can manage or purge Microsoft 365 data from the Purview portal and should be subject to least privilege and audit.

eDiscovery is an authorized bulk-export capability. Review role assignments, case membership, scope filters, DLP, and retention exemptions; compare search and export activity with a workload-specific baseline.

### 5.3 Microsoft Defender XDR

Defender XDR integrates endpoint, identity, email, and application protection. Its components include Defender for Endpoint, Defender for Office 365, Defender for Identity, and Defender for Cloud Apps. Defender for Endpoint Live Response provides remote investigation capabilities, with advanced actions controlled by roles. Defender for Identity sensors operate in on-premises Active Directory and connect on-premises identity signals with the cloud portal. Azure workloads have the separate Defender for Cloud service.

These services integrate with Sentinel through connectors, with Intune for device management and policy, and with Conditional Access through device-risk signals from Defender for Endpoint. This allows endpoint security posture to inform access decisions.

Live Response is a privileged remote investigation capability. Review role assignments and session records, and monitor changes to Defender configuration. Defender for Identity's assessments can also help review on-premises configurations such as AZUREADSSOACC delegation.

> The security control plane itself needs governance. Sentinel rule editors, Defender and Intune operators, and Purview administrators can affect detection, response, devices, and evidence. Review their role assignments and audit records as carefully as business-data permissions.

### 5.4 Intune and MDM

Mobile device management (MDM) is a capability for device enrollment, policy deployment, and compliance reporting. Intune is Microsoft's MDM implementation and endpoint-management service. Conditional Access can require a device to meet security requirements before it accesses organizational data.

Conditional Access can consider user or group membership, IP location, device compliance or configuration, application details, and signals from supported mobile threat-defense partners. Intune supplies device-compliance and mobile-application-management information.

Intune device actions include wipe, retire, delete, remote lock, restart, password reset, and remote assistance, depending on platform and enrollment state. Each action is constrained by Intune RBAC, permissions, and scope. Device objects reside in Entra, enrollment is recorded there, and compliance state can inform Conditional Access. Defender device-risk signals can also influence access.

Intune governance includes policy and software deployment as well as compliance state. Changes to scripts, configurations, compliance policies, and device records should be managed and audited because they can affect device security and access decisions.

### 5.5 Putting the services together

Sentinel operates in Azure subscriptions and observes both Microsoft 365 and Azure signals. Purview provides compliance and content-governance capabilities across supported workloads. Defender XDR covers endpoints, email, identity, applications, and on-premises Active Directory; Intune manages devices and reports compliance. These services are distinct and connect through data connectors and the shared Entra identity plane. Their own administrative roles and configuration surfaces are part of the security boundary.

## 6. Review checklist: Microsoft 365 and the security stack

The following checklist consolidates the configuration areas discussed above:

- **Identity:** password-spray and token-replay exposure, device-code consent, PRT protections, user and administrator consent, application credential additions and rotation, and PIM activation policies.
- **Mail:** Graph application-permission scope, mailbox rules and forwarding, eDiscovery case scope and export baselines, and mailbox delegation.
- **Files:** Graph file permissions, site-collection administrators, anyone links and guests, sites with broken inheritance, and user-perspective access checks.
- **Collaboration:** shared-channel cross-tenant settings, Teams federation and guest policies, and message-related application permissions.
- **AI:** handling of hidden text and document metadata, agent identities and connections, connector data sources, and Copilot audit coverage and retention.
- **Security stack:** Sentinel analytics-rule change auditing, playbook permissions, workspace query access, eDiscovery export baselines, Defender Live Response roles and sessions, and Intune script and compliance-policy changes.

This is a review checklist, not an operating procedure. Verify each item against the organization's actual configuration and document whether it is present.

## 7. From Microsoft 365 to Azure and on-premises

The combined access model can be summarized as follows:

```text
（身份入手）
   用户 / 应用凭据 / 设备（PRT）
        │
        ├─ Entra 角色 ──► 目录与安全栈控制面（GA→elevateAccess→Azure）
        ├─ Graph 应用权限 ──► 经同意的 M365 API 数据（范围取决于权限与资源范围控制）
        ├─ 工作负载 RBAC ──► eDiscovery 导出 / 委托 / 站点管理
        │        └─► Copilot：可见面的一次性兑现（放大器，不是新边界）
        ├─ Azure RBAC ──► 资源平面（托管标识 / IMDS / 订阅）
        └─ 混合链 ──► PHS / PTA / ADFS / SSO / 委派 ⇄ 本地域控（见上篇）
（观测与审查）
   Sentinel（Azure 订阅里的工作区）· Purview（审计/eDiscovery）· Defender（URBAC/Live Response）· Intune（设备动作）
```

The main conclusions are:

- Microsoft 365 authentication is primarily handled by Entra; access reviews should separate Entra roles, workload permissions, application consent, and device-compliance signals.
- Microsoft 365 and Azure share identity but have separate authorization planes. Security services can span both and often depend on Azure subscriptions.
- Graph application permissions are a major workload access path; review granted scopes and resource-scope controls.
- ApplicationImpersonation is retired; review any remaining legacy applications and their migration.
- Copilot generally follows user permissions and can make existing oversharing easier to discover.
- Indirect prompt injection can enter through content that the user or connected service can retrieve; product safeguards are one defense layer.
- Agents and connectors have identities and connections that vary by product and configuration.
- Copilot does not automatically grant Azure RBAC; external access depends on the connector identity and authorization.
- Sentinel uses Azure RBAC and Defender portal RBAC; effective access is cumulative, and analytics-rule changes need monitoring.
- eDiscovery is an authorized export path, governed by case membership and search filters.
- Defender for Identity provides visibility into on-premises Active Directory and should be considered in hybrid reviews.
- Intune controls device actions and compliance signals that can affect access.
- The roles and configurations that operate the security stack are themselves part of the control plane.

## References

The following primary sources underpin this review; interpret product details in the context of the original documentation.

- Microsoft Learn: Understand roles in Microsoft Entra ID — https://learn.microsoft.com/entra/identity/role-based-access-control/concept-understand-roles

- Microsoft Learn: Microsoft Entra built-in roles — https://learn.microsoft.com/entra/identity/role-based-access-control/permissions-reference

- Microsoft Learn: Feature permissions in Exchange Online — https://learn.microsoft.com/exchange/permissions-exo/feature-permissions

- Microsoft Learn: Role Based Access Control for Applications in Exchange Online — https://learn.microsoft.com/exchange/permissions-exo/application-rbac

- Microsoft Learn: Assign permissions in eDiscovery — https://learn.microsoft.com/purview/edisc-permissions

- Microsoft Learn: Microsoft Graph permissions reference — https://learn.microsoft.com/graph/permissions-reference

- Microsoft Learn: Data, Privacy, and Security for Microsoft Copilot — https://learn.microsoft.com/microsoft-365/copilot/microsoft-365-copilot-privacy

- Microsoft Learn: Audit logs for Copilot and AI applications — https://learn.microsoft.com/purview/audit-copilot

- Microsoft Learn: Semantic indexing for Microsoft Copilot — https://learn.microsoft.com/microsoftsearch/semantic-index-for-copilot

- Microsoft Learn: What is Microsoft Sentinel? — https://learn.microsoft.com/azure/sentinel/overview

- Microsoft Learn: Roles and permissions in the Microsoft Sentinel platform — https://learn.microsoft.com/azure/sentinel/roles

- Microsoft Learn: Learn about Insider Risk Management — https://learn.microsoft.com/purview/insider-risk-management

- Microsoft Learn: What is Microsoft Defender XDR? — https://learn.microsoft.com/defender-xdr/microsoft-365-defender

- Microsoft Learn: Microsoft Defender for Endpoint and other Microsoft solutions — https://learn.microsoft.com/defender-endpoint/threat-protection-integration

- Microsoft Learn: Investigate entities on devices using live response — https://learn.microsoft.com/defender-endpoint/live-response

- Microsoft Learn: Microsoft Defender for Identity overview — https://learn.microsoft.com/defender-for-identity/what-is

- Microsoft Learn: Get started with your Microsoft Intune deployment — https://learn.microsoft.com/intune/fundamentals/get-started

- Microsoft Learn: Conditional Access and Intune overview — https://learn.microsoft.com/intune/device-security/conditional-access-integration/overview

- Microsoft Learn: Troubleshooting device actions in Intune — https://learn.microsoft.com/troubleshoot/mem/intune/device-management/troubleshoot-device-actions

- Microsoft Learn: Retire devices action — https://learn.microsoft.com/intune/device-management/actions/retire
