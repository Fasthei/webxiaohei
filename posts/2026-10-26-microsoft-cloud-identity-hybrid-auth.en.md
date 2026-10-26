---
title: "Microsoft Cloud Identity and Hybrid Authentication: Tenants, Subscriptions, and Kerberos"
date: "2026-10-26"
slug: "microsoft-cloud-identity-hybrid-auth"
category: "Cloud Security Research"
summary: "This article examines Microsoft Entra tenant, Azure subscription, and billing boundaries; role systems and workload identities; and the hybrid authentication paths connecting on-premises Active Directory with Microsoft Entra."
---

# Microsoft Cloud Identity and Hybrid Authentication: Tenants, Subscriptions, and Kerberos

## 1. Establishing the boundaries

When reviewing Azure, I distinguish three boundaries: the Entra tenant manages identities, the Azure subscription contains resources and Azure role assignments, and the billing account records financial responsibility. They are related, but serve different purposes.

```text
        身份树（认证）                    资源树（授权）                  计费树（账单）

   ┌──────────────────────┐        ┌──────────────────────┐       ┌──────────────────────┐
   │ Microsoft Entra tenant│        │ 管理组 root（=租户ID） │       │ 计费账户（EA/MCA/MPA）│
   │ 目录 / 用户 / 应用 / 设备│        │  ├── 管理组            │       │  ├── 计费配置文件        │
   └──────────┬───────────┘        │  └── 订阅             │       │  └── 发票区 → 订阅      │
              │ 1 个订阅信任 1 个租户   └──────────┬───────────┘       └──────────┬───────────┘
              └──────────────► 订阅 ◄─────────────┘                          │
                                   ▲                                           │
                                   └───────────────────────────────────────────┘
                                        账单归属（与身份树相互独立）
```

The billing hierarchy in this diagram is illustrative; actual scopes and roles vary by agreement type and account configuration.

Microsoft's subscription-association documentation describes the relationship clearly: a subscription is a scope for managing Azure resources and Azure role assignments; a tenant is the directory containing identities used for sign-in and access. Azure roles control resource access, while Entra roles manage directory objects such as users, groups, and domains.

> A subscription is associated with one directory at a time, while a directory can be associated with multiple subscriptions. Directory association and billing ownership are separate relationships; changing one does not necessarily change the other.

I use one principle throughout: access to one boundary does not automatically grant access to an adjacent boundary. Tenant administrators and subscription Owners have different responsibilities; the explicit authorization between them matters.

## 2. Tenant-to-tenant access

An Entra tenant represents an organization in Microsoft Entra ID. Each tenant has a unique tenant ID and an initial `*.onmicrosoft.com` domain. An organization commonly has one tenant, but that is a convention, not a technical requirement.

Tenants do not automatically trust one another. A user from tenant A needs an access path configured by resource tenant B. Common options include:

The first is B2B collaboration. An invited external user appears in the resource tenant as a guest object. The resource tenant generally does not manage the guest's home password; authentication takes place through the user's home tenant or a supported external identity provider. The guest UPN often includes the external email address and `#EXT#`, but the directory object is the source of truth.

The second is cross-tenant access settings, which separately control inbound and outbound collaboration. A resource tenant can decide whether to trust MFA or device claims from a specific external tenant and use those claims in Conditional Access. The two directions are configured independently; if both organizations need access to each other's resources, review both.

The third is a multitenant organization and cross-tenant synchronization. These can help synchronize users across tenants that an organization maintains for compliance, acquisition, or administrative reasons.

> A guest is not necessarily read-only. Directory roles, resource permissions, and role-assignable groups can all be assigned to guest objects. Review the guest's roles, groups, scope, home tenant, and cross-tenant access settings.

Billing and identity do not necessarily have the same scope. An MCA billing account is associated with a selected Entra tenant, while an Enterprise Agreement enrollment can involve accounts and subscriptions across tenants. Users may also access multiple billing accounts. Verify the account type and actual configuration rather than assuming a fixed one-to-one relationship.

## 3. Tenant and subscription: a directory association

An Azure subscription is associated with one Entra tenant and relies on that directory to authenticate and authorize security principals and devices. If a subscription expires, its directory association remains, but principals lose access to Azure resources. One subscription can be associated with one directory at a time; a directory can have multiple subscriptions.

There is an asymmetry when associating a subscription with a directory: the subscription Owner does not thereby become a Global Administrator of the directory, while the user who creates a new tenant becomes its Global Administrator. A resource Owner does not automatically enter the identity hierarchy.

### 3.1 Costs of changing directories

Before changing a subscription's directory association, review the migration impact for its services. Azure RBAC assignments and custom roles are permanently removed from the source directory and are not automatically copied to the destination. System-assigned managed identities need to be disabled and re-enabled; user-assigned managed identities need to be recreated in the destination directory. Key Vault tenant IDs and access policies also need updating. AKS clusters and related resources cannot be moved directly to another directory and require separate migration planning.

Changing a directory association does not rotate every resource credential. Storage access keys, management certificates, and local virtual-machine accounts should be assessed and rotated through their own mechanisms. Recreate required role assignments and custom roles in the target directory. CSP subscriptions do not support this directory-change process; confirm the subscription type first.

> Directory changes remove role assignments but do not automatically rotate all independent credentials. During migration validation, I separately check storage keys, management certificates, and local VM accounts, then rotate any credentials still in use according to the organization's process.

### 3.2 Global Administrator elevation to Azure

This is an important documented bridge between the directory and Azure resource hierarchy.

By default, Entra roles and Azure RBAC are separate; Global Administrator does not automatically have Azure resource access. A Global Administrator can use **elevate access** to grant themselves User Access Administrator at the Azure root scope and manage role assignments for subscriptions and management groups associated with the tenant. The elevation affects the current user; review and revoke it when no longer needed.

```text
目录中的 Global Administrator
      │  打开 Access management 开关（elevateAccess）
      ▼
根作用域 / 上的 User Access Administrator
      │  在任意订阅、管理组上分配角色
      ▼
任意订阅的 Owner → 资源控制与数据面
```

> This is an explicit cross-boundary path. Review directory audit events for elevation and root-scope role assignments; do not treat an ordinary Entra role or subscription role as a permission in the other system.

## 4. Subscriptions, management groups, and billing

### 4.1 Three meanings of "organization"

Microsoft documentation uses "organization" in several senses. An Entra organization is the identity boundary represented by the tenant. A Microsoft 365 organization is the tenant's productivity-workload context. A billing organization refers to billing accounts, EA enrollments, or a CSP customer organization. These may align, but they do not have to: an agreement or subscription configuration can involve multiple tenants, and users may access several billing accounts.

### 4.2 Management groups

Management groups are governance containers above subscriptions. Each directory has a top-level root management group whose ID matches the tenant ID. Management groups and subscriptions form a hierarchy. The root management group can be used for policy and role governance across subscriptions associated with the directory. It cannot be moved or deleted, and each management group or subscription has one parent in the hierarchy. Policies and RBAC assignments inherit according to their respective rules. Check current documentation for limits on hierarchy depth and object counts.

Two defaults are worth confirming: by default, tenant principals can create management groups, and the requirement for authorization must be enabled explicitly to restrict that behavior. Microsoft also documents that nobody automatically has access to the root management group.

> Root management-group policies and role assignments can affect descendants. Review parent-child relationships, not only the root object. Restrict management-group creation if the organization does not intend all tenant principals to create them.

### 4.3 Billing accounts

Billing scopes depend on the agreement. A MOSP pay-as-you-go account bills individual usage. In an EA, an Enterprise Administrator can create subscriptions under active enrollment accounts, while an Account Owner can create subscriptions under an enrollment they own. An MCA billing account is associated with a tenant; subscription creation limits depend on account type, quota, and current Microsoft rules. MPA is designed for CSP partners managing customer billing and subscriptions. Verify current quotas in the account portal rather than generalizing one account's limit.

Subscription-creation authority is distributed across billing scopes. MCA creation can require Owner or Contributor at an invoice section, billing profile, or billing account, or the Azure subscription creator role at an invoice section. EA creation requires an Enterprise Administrator or Account Owner. An EA Account Owner must sign in through the home tenant; signing in as a guest in another directory is not sufficient even when the role is present.

> Billing roles can include subscription-creation rights. When reviewing a new subscription, I check its management-group placement, notification recipients, and inherited organizational policies.

### 4.4 Three ways to move or delegate a subscription

Changing a directory association can leave billing ownership unchanged, but role assignments and some identity integrations need reconfiguration. A billing transfer changes the relevant billing relationship. Alternatively, Azure Lighthouse can delegate a subscription or resource group to another tenant without moving the subscription. Review both resources delegated out of the tenant and resources delegated into it.

## 5. Entra roles and Azure RBAC

Azure formerly had classic administrator roles, including Account Administrator, Service Administrator, and Co-Administrator. Classic administrator roles were retired on August 31, 2024. In December 2025, users in the public cloud who still had Co-Administrator or Service Administrator assignments began receiving Owner at subscription scope automatically; by May 2026, the classic roles and portal tab had been removed. Review the resulting Owner assignments and reduce them where possible.

Entra roles and Azure RBAC manage different objects and scopes:

| Dimension | Entra roles | Azure RBAC roles |
| --- | --- | --- |
| Managed objects | Users, groups, applications, devices, policies | VMs, storage, networks, key vaults |
| Management plane | Microsoft Graph and Entra admin center | Azure Resource Manager |
| Scope | Tenant, administrative unit, object | Management group, subscription, resource group, resource |
| Boundary relationship | Separate from Azure RBAC; Global Administrator can explicitly elevate Azure access | Separate from Entra directory roles |

Global Administrator does not automatically have every Azure resource permission, and subscription Owner does not automatically manage directory objects. Global Administrator can explicitly use elevate access; also review service delegation, workload identities, and application permissions.

Role permissions change as products evolve. The following list is a task-oriented summary, not a complete permission reference; check the current role definitions before assigning a role.

### 5.1 Entra: common tasks and least-privileged roles

- Manage role assignments and PIM role settings: Privileged Role Administrator. Because this role can manage role assignment, it should itself be subject to strong controls.
- Create and manage app registrations, enterprise applications, and credentials: Application Administrator; Cloud Application Administrator has similar app permissions but excludes application proxy. Neither manages Conditional Access or grants admin consent for Azure AD Graph or Microsoft Graph application permissions; Privileged Role Administrator is required for those API grants.
- Manage authentication-method policies, per-user MFA, and password protection: Authentication Policy Administrator.
- Change authentication methods and sensitive attributes for non-administrators: Authentication Administrator. For privileged users, use Privileged Authentication Administrator.
- Reset non-admin passwords, revoke refresh tokens, and read device BitLocker recovery keys: Helpdesk Administrator (formerly Password Administrator in the Azure portal).
- Create users, manage groups, assign licenses, and reset non-admin passwords: User Administrator; this role cannot manage MFA or shared mailboxes.
- Manage Entra Connect, PTA, PHS, Seamless SSO, and federation settings: Hybrid Identity Administrator, excluding Entra Connect Health.
- Manage Conditional Access: Conditional Access Administrator or Security Administrator.
- Read Windows LAPS local-administrator passwords for Entra-joined devices: Cloud Device Administrator or Intune Administrator. Helpdesk Administrator, Security Administrator, and Security Reader can read metadata but not passwords.
- Manage Intune device policies and compliance: Intune Administrator.
- Manage Exchange organization configuration: Exchange Administrator; this does not by itself mean access to mailbox content.
- Manage purchasing and billing: Billing Administrator.

### 5.2 Azure RBAC and billing: common tasks and roles

- Assign Azure roles: Owner, User Access Administrator, or Role Based Access Control Administrator. Each can create role assignments; RBAC Administrator is limited in using other mechanisms such as Azure Policy to manage access. Contributor cannot assign roles.
- Access blob data with Entra credentials: a data-plane role such as Storage Blob Data Reader, Contributor, or Owner, plus the required management-plane visibility in the portal. Control-plane Contributor does not automatically provide blob-data access.
- Access data with a storage account key: a role containing `Microsoft.Storage/storageAccounts/listkeys/action` is required. Contributor, Owner, Storage Account Contributor, and Reader and Data Access include this operation. This is a second data-access route that should be considered separately from Entra data-plane roles.
- Key Vault data-plane access: use a data-plane role such as Key Vault Secrets Officer or Crypto Officer; access-policy management is a control-plane permission.
- Create an MCA subscription: Owner or Contributor at an invoice section, billing profile, or billing account, or Azure subscription creator at an invoice section; the creator role can cancel only subscriptions it created.
- Create an EA subscription: Enterprise Administrator or Account Owner, signed in through the home tenant.
- Assign roles at the root management group: first obtain Owner or User Access Administrator at that scope; Global Administrators can use elevate access.

### 5.3 Less obvious boundaries

First, Application Administrator and Cloud Application Administrator can add credentials to applications and use them as the application identity. If that application has powerful permissions, the role holder may act beyond their direct role. Microsoft explicitly flags this as a potential privilege escalation relative to role assignments.

Second, Authentication Administrator can modify authentication methods for several high-value categories, including application owners, Azure subscription Owners, security-group or Microsoft 365 group owners, and some service administrators. Changing an owner's authentication methods can affect the associated identity; include these categories in monitoring.

Third, Cloud Device Administrator and Intune Administrator can read local administrator passwords for Entra-joined devices. Roles limited to metadata cannot read the passwords. This is a direct device-access boundary.

Fourth, Contributor manages resources but cannot assign Azure roles and does not inherently include storage data-plane permissions. It can, however, include `listkeys`; evaluate both control-plane actions and account-key access.

Fifth, billing roles and Azure RBAC are separate. A billing-profile Owner can manage invoices, payments, and subscription creation at billing scopes, but does not thereby get Azure resource permissions; a subscription Owner does not automatically gain invoice-section access.

PIM separates eligible assignments from active assignments. Eligible roles normally require activation; whether activation requires MFA, approval, or justification depends on configuration. Review permanent and eligible assignments, activation policies, and audit records.

## 6. Workload identities: applications, service principals, and managed identities

An application object is the global representation of an application in its home Entra tenant. A service principal is the application's local representation in a tenant and determines its access there. Registering an application creates a service principal in the home tenant; a multitenant application has a service principal in each tenant that consents to it. Service-principal types include Application, Managed identity, and Legacy.

Common application credentials include client secrets, certificates, and federated identity credentials for workload identity federation. Application owners and administrators can manage credentials subject to role, application-type, and permission constraints. A multitenant application can operate only in tenants where the required consent and permissions have been granted; credentials alone do not give it access to every tenant or resource.

When reviewing application identities, check recently added or expiring credentials, tenant-consent records for enterprise applications, and high-privilege API permissions. Permission names and scope vary by API and permission type; verify what the application actually needs.

Managed identities are a special kind of service principal without an application object. A system-assigned identity is tied to a resource's lifecycle and can be used only by that resource. A user-assigned identity is an independent resource that can be attached to multiple resources. The platform manages its credentials, so the application does not need to store or rotate a client secret. Resources request tokens through supported endpoints such as Azure Instance Metadata Service. When using multiple user-assigned identities, specify which identity to use. Managed identities cannot sign in interactively like ordinary users. Directory changes affect them: system-assigned identities usually need to be re-enabled, while user-assigned identities need to be recreated in the target directory.

Managed identities avoid application-managed long-lived secrets but still need permission review. Check which resources they can access and who can modify the identity or run code on associated resources; effective access depends on both identity assignments and target-service authorization.

Service principals, managed identities, and ordinary users repurposed as service accounts have different credential and audit models. Do not assume that all are non-interactive or produce no sign-in records.

## 7. On-premises TGTs and cloud "domains"

### 7.1 Kerberos fundamentals

Windows Kerberos is a three-party protocol involving a client, a target service, and a trusted Key Distribution Center (KDC). The KDC runs as a domain service on domain controllers and uses the AD DS database as its account database. At sign-in, the client proves its identity to the KDC and receives a ticket-granting ticket (TGT), which it can use to request service access without sending its password again. The client stores the TGT in its ticket cache. Under default domain policy, a Windows TGT commonly lasts about ten hours; Protected Users and domain policy can change lifetime and renewal behavior.

TGT issuance has three steps: the KDC creates a logon session key protected with the user's key, then places a copy of that session key and authorization data in a TGT protected with the KRBTGT account key. The client decrypts the session key and stores the TGT. For a service request, the client presents the TGT to obtain a service ticket encrypted with the target service's key; the service can validate that ticket without contacting the domain controller.

```text
KRB_AS_REQ（预认证）→ KDC 签发 TGT（KRBTGT 密钥加密）+ 会话密钥（用户密钥加密）
      │
      ▼
KRB_TGS_REQ（出示 TGT）→ KDC 签发服务票据（目标服务密钥加密）
      │
      ▼
AP_REQ（出示服务票据）→ 服务解密校验，全程不再需要用户密码
```

The security model depends on the appropriate keys: domain controllers use the KRBTGT account key to protect TGTs; service-account keys participate in service-ticket issuance and validation; and the user's key is used during client authentication. Risks depend on how these keys are protected and used.

### 7.2 Entra ID is not an on-premises Kerberos domain

Entra ID is not an on-premises domain controller and does not use the on-premises KRBTGT account to issue tickets. Entra supports OAuth 2.0, OIDC, and SAML. At a high level, an access token is issued to a resource, a refresh token can obtain new tokens where policy permits, and a Primary Refresh Token (PRT) supports SSO on supported devices. Lifetime and scope depend on token type, resource, and policy.

A PRT is a security artifact issued for Microsoft's first-party token broker to support device SSO across applications. It carries user and device claims for Conditional Access evaluation. PRTs commonly have a 90-day lifetime, and Windows CloudAP attempts renewal every four hours while the user continues using the device. The PRT supports SSO; actual application access still depends on authorization, device state, and Conditional Access.

There is no exact cloud equivalent of a TGT. PRT and TGT can be compared only in their broad SSO function: they use different protocols and security mechanisms. KRBTGT key compromise creates Kerberos ticket-forgery risks; PRT protections rely on device keys and proof mechanisms. Assess PRT exposure in the context of token type, device protection, and the identity platform's validation process.

### 7.3 Three cloud concepts called "domain"

Three different systems can be confused because they use the word "domain."

First, **Microsoft Entra Kerberos** allows Entra ID to act as a KDC in supported scenarios, using the `KERBEROS.MICROSOFTONLINE.COM` domain. Cloud TGTs support specific workloads such as Azure Files, Azure Virtual Desktop, and Windows authentication for Azure SQL Managed Instance. Ticket keys and configuration vary by workload.

Second, **OnPremTgt** can be issued in configured hybrid identity and Entra Kerberos scenarios. It is a partial TGT that contains the user's SID but not complete on-premises group information and is not sufficient by itself to access on-premises resources. The local KDC completes the relevant Kerberos process according to domain configuration and authorization. The exact flow and supported resources depend on deployment; do not generalize it to every SMB or SQL environment. Synchronization, Kerberos server objects, and domain-controller configuration are prerequisites. Microsoft documentation also says not to synchronize sensitive accounts such as `krbtgt_AzureAD` into on-premises AD.

Third, **Microsoft Entra Domain Services** is a Microsoft-managed AD DS domain with a real KRBTGT account. It is distinct from Entra ID despite the similar name.

> Cloud TGTs and on-premises TGTs cannot be used interchangeably. In supported hybrid configurations, a PRT can participate in obtaining an OnPremTgt, while the local KDC and domain policy govern subsequent ticket issuance and resource access. Confirm Cloud Kerberos Trust, the Kerberos server object, and synchronization exclusions in the actual deployment.

## 8. Hybrid identity: paths between on-premises AD and Entra

Organizations connect on-premises AD and Entra using directory synchronization, pass-through authentication, federation, Seamless SSO, and Entra Kerberos. Microsoft notes that hybrid deployments connect on-premises infrastructure to cloud identities, so on-premises authentication components, synchronization scope, and federation trust belong in cloud-security reviews.

### 8.1 Password hash synchronization (PHS)

PHS obtains password-hash material from on-premises AD, applies additional processing, and synchronizes it to Entra authentication services. Microsoft Learn describes a two-minute synchronization cycle, with password changes generally reflected in the cloud within minutes. On-premises password changes update the cloud hash; an administrator reset in Entra may temporarily take precedence until a later on-premises password change synchronizes.

In Entra Connect Sync, the synchronization agent uses MS-DRSR to request the stored `unicodePwd` hash attribute from a domain controller. The AD DS Connector account needs the relevant directory-replication permissions. The agent does not obtain plaintext passwords, and the cloud does not store the original on-premises MD4 hash. Because the synchronization permissions are sensitive, protect Entra Connect Sync servers and service accounts as Tier 0 assets. Review server administrators, configuration changes, synchronization scope, and cloud privileges of synchronized accounts. Entra Cloud Sync uses a different implementation and should be reviewed against its own documentation.

Microsoft Learn states that the `accountExpires` attribute does not synchronize to Entra. If the organization uses this attribute for temporary accounts or offboarding, also ensure that cloud account disablement, session revocation, and offboarding procedures are in place.

### 8.2 Pass-through authentication (PTA)

With PTA, an on-premises authentication agent validates sign-in requests against Active Directory. After registration, Entra protects the request with the agent's public key and sends it through a queue; the agent retrieves, decrypts, and validates the request locally, then returns the result. Agents maintain a connection to the service and rely on certificates and queue access controls.

Password validation occurs on-premises, but the sign-in process still involves cloud services and encrypted transport. Protect agent hosts as sensitive systems and review both Entra Smart Lockout and on-premises account-lockout policies.

> First identify whether the tenant uses PHS, PTA, or federation. Then review the servers, synchronization accounts, certificates, and sign-in policies relevant to that method. The authentication model determines where trust resides, but does not eliminate other credential risks.

### 8.3 AD FS federation

With federated authentication, a user is redirected to an identity provider such as on-premises AD FS. Entra validates the returned token using the configured trust. The token-signing certificate is central to this trust; compromise of its private key can enable forged assertions, a risk commonly called Golden SAML. The actual impact depends on federation configuration, tenant policy, and token validation.

Protect signing keys and the AD FS management plane, monitor trust and certificate changes, and assess which domains and applications still require federation. Migration to Entra authentication should follow organizational requirements, application compatibility, and current Microsoft guidance.

### 8.4 Seamless SSO (`AZUREADSSOACC`)

When Seamless SSO is enabled, Entra Connect creates the `AZUREADSSOACC` computer account in a synchronized AD forest and configures its Kerberos SPN. Its Kerberos key is securely shared with Entra for supported network and browser sign-in scenarios. This is a login integration, not a general-purpose cloud Kerberos service.

Microsoft recommends tightly limiting management of this account, disabling Kerberos delegation, and rotating its key at least every 30 days. Seamless SSO supports AES and RC4; Microsoft recommends AES. Starting with the July 2026 Windows Server update, AD DS defaults to AES-256 Kerberos encryption. If `AZUREADSSOACC` still depends on RC4, evaluate compatibility using current Microsoft guidance; rotate the account key before switching to AES to avoid SSO disruption.

> Treat Seamless SSO as a sign-in integration with explicit prerequisites, not as a generic bridge that converts all Kerberos tickets into cloud tokens. Review account permissions, delegation attributes, encryption type, and key-rotation history.

### 8.5 Cloud Kerberos Trust and OnPremTgt

In supported hybrid deployments, Entra can issue an OnPremTgt containing the user's SID but not complete group information. It must be exchanged with an on-premises domain controller to obtain the ticket used for local resource access. Documented prerequisites include synchronized users, a configured and synchronized Kerberos server object, supported Windows devices that are Entra-joined or hybrid-joined, configured domain controllers, and device connectivity to a domain controller. Supported passwordless sign-in methods include Windows Hello for Business and FIDO2; user access also depends on RODC allow and deny policy. Verify current support requirements and Windows lifecycle status.

Cloud Kerberos Trust is not a default path for every cloud user. Review the deployment, device and user prerequisites, Kerberos server object, RODC policy, and domain-controller configuration.

### 8.6 Kerberos delegation models

Kerberos delegation can allow a front-end service to access a back-end service on behalf of a user. The three models differ in who controls the allowed targets:

- **Unconstrained delegation:** broad trust; Microsoft does not recommend it for new designs. Review and remove or migrate legacy configurations where possible.
- **Constrained delegation:** the front-end service specifies the services it may access on a user's behalf.
- **Resource-based constrained delegation (RBCD):** the back-end resource specifies which front-end services may act on a user's behalf.

Configuration location, cross-domain behavior, and compatibility differ by model. Review the delegation scope, administrators of the relevant objects, and whether `AZUREADSSOACC` has delegation disabled as required by Seamless SSO guidance.

### 8.7 Comparing the five hybrid mechanisms

These mechanisms can be compared by where authentication is validated and which configuration must be protected:

```text
                  本地 AD                          Microsoft Entra ID
             ┌──────────────────┐              ┌──────────────────────┐
   PHS       │ 密码哈希材料 ────┼─ 通常每2分钟 ►│ Entra 认证服务         │
   PTA       │ 本地 AD 验证 ◄───┼─ 认证代理通道 ┤ 加密请求队列          │
   ADFS      │ 身份提供方签名 ──┼─ SAML 断言 ──►│ 验证联邦信任          │
   SSO       │ AZUREADSSOACC ──┼─ Kerberos SSO ►│ 按配置验证登录        │
   CKT       │ 本地 KDC ◄──────┼─ OnPremTgt ───│ 受支持的混合流程      │
             └──────────────────┘              └──────────────────────┘
```

The trust material differs: PHS uses directory-replication permissions; PTA uses authentication agents; AD FS relies on federation-signing certificates; Seamless SSO uses `AZUREADSSOACC`; and Cloud Kerberos Trust depends on the Kerberos server object and local KDC. Microsoft recommends protecting cloud administrators and limiting the privileges of synchronized identities. Review these controls alongside each mechanism's own keys, roles, and configuration.

## 9. Tickets, tokens, and review boundaries

### 9.1 On-premises Kerberos risk

On-premises Kerberos security depends on account keys, domain controllers, and service configuration. KRBTGT protects domain TGTs, service-account keys participate in service-ticket flows, and preauthentication, password strength, and encryption types affect risk. For review, identify high-value keys and accounts, compare configuration with organizational baselines, and correlate unusual authentication across domain-controller and endpoint logs.

If KRBTGT compromise is suspected, follow Microsoft's recovery guidance for staged resets and account for domain-controller replication and outstanding ticket lifetimes. Disabling one user or changing one password is not a complete domain-level recovery.

### 9.2 Cloud tokens and device state

PRTs and Kerberos TGTs both support SSO, but they are different credentials. PRTs commonly have a 90-day lifetime; Windows CloudAP attempts renewal every four hours while the user uses the device. Conditional Access sign-in-frequency controls can require reauthentication. A PRT relies on supported devices and platform validation; it is not a universal bearer token for every resource.

The impact of token exposure depends on token type, device binding, target-resource authorization, and Conditional Access. Device registration, device compliance, and user authentication are distinct states; review how each policy applies to the target application.

### 9.3 Reviewing hybrid environments

I treat hybrid authentication as a set of conditional trust relationships rather than one general "on-premises-to-cloud" channel. For each enabled mechanism, document its components, accounts, keys, synchronization scope, and policies, then identify owners, monitoring, and recovery procedures. Entra Kerberos also requires review of device and user prerequisites, RODC policy, and domain-controller configuration.

### 9.4 Logs and detection

No single event proves or rules out an attack. Correlate Entra audit and sign-in logs, Azure activity logs, domain-controller security logs, device state, synchronization-component logs, and federation-service logs. Global Administrator elevation, role changes, synchronization changes, `AZUREADSSOACC` key or delegation changes, and unusual token or device activity should be assessed with actor, source, target, and change-window context.

`klist cloud_debug` can help diagnose Cloud TGT status on Windows devices, but it is not sufficient evidence of a security incident. Defender for Identity, Entra, and other products vary by license, configuration, and product updates; confirm the detection coverage enabled in the actual tenant.

## 10. Reviewing the architecture

I review the environment using a configuration checklist rather than a fixed attack sequence:

- Record each subscription's tenant, management-group placement, and billing relationship; check directory-migration impact and CSP limitations.
- Inventory Entra directory roles, Azure RBAC, and data-plane roles separately; review the root management group and Global Administrator elevation.
- Review guests, cross-tenant access, application consent, application credentials, and managed-identity permissions.
- Confirm billing roles have a business need to create subscriptions and that new subscriptions enter the intended management group and policy scope.
- Identify which of PHS, PTA, AD FS, Seamless SSO, and Cloud Kerberos Trust are actually deployed, and review only the relevant configuration.
- Protect synchronization servers, authentication agents, federation-signing material, and `AZUREADSSOACC`; review synchronization scope, key rotation, and delegation.
- Review PRT, device-join and compliance, Conditional Access, sign-in frequency, log retention, and alert coverage against current licensing.

Role status and product behavior in this article were checked against Microsoft Learn on 2026-10-27. Tenant configuration, licensing, and service changes can affect capabilities; consult the linked documentation for a specific deployment.

This article covers identity, resource, and billing boundaries and common hybrid authentication methods. Microsoft 365 and Azure, Copilot data access, Sentinel, Purview, Defender, and Intune are discussed in *Microsoft 365, Copilot, and the Security Control Plane*.

## References

The following primary documentation and research inform this review:

- Microsoft Learn: Associate or add an Azure subscription to your Microsoft Entra tenant — https://learn.microsoft.com/entra/fundamentals/how-subscriptions-associated-directory
- Microsoft Learn: Transfer an Azure subscription to a different Microsoft Entra directory — https://learn.microsoft.com/azure/role-based-access-control/transfer-subscription
- Microsoft Learn: What are Azure management groups? — https://learn.microsoft.com/azure/governance/management-groups/overview
- Microsoft Learn: Billing accounts and scopes in the Azure portal — https://learn.microsoft.com/azure/cost-management-billing/manage/view-all-accounts
- Microsoft Learn: Understand Microsoft Customer Agreement administrative roles in Azure — https://learn.microsoft.com/azure/cost-management-billing/manage/understand-mca-roles
- Microsoft Learn: Create an Enterprise Agreement subscription — https://learn.microsoft.com/azure/cost-management-billing/manage/create-enterprise-subscription
- Microsoft Learn: Azure roles, Microsoft Entra roles, and classic subscription administrator roles — https://learn.microsoft.com/azure/role-based-access-control/rbac-and-directory-admin-roles
- Microsoft Learn: Azure classic subscription administrators — https://learn.microsoft.com/azure/role-based-access-control/classic-administrators
- Microsoft Learn: Elevate access to manage all Azure subscriptions and management groups — https://learn.microsoft.com/azure/role-based-access-control/elevate-access-global-admin
- Microsoft Learn: Microsoft Entra built-in roles — https://learn.microsoft.com/entra/identity/role-based-access-control/permissions-reference
- Microsoft Learn: Least privileged roles by task in Microsoft Entra ID — https://learn.microsoft.com/entra/identity/role-based-access-control/delegate-by-task
- Microsoft Learn: Delegate app roles — https://learn.microsoft.com/entra/identity/role-based-access-control/delegate-app-roles
- Microsoft Learn: Windows Local Administrator Password Solution in Microsoft Entra ID — https://learn.microsoft.com/entra/identity/devices/howto-manage-local-admin-passwords
- Microsoft Learn: Steps to assign an Azure role — https://learn.microsoft.com/azure/role-based-access-control/role-assignments-steps
- Microsoft Learn: Choose how to authorize access to blob data — https://learn.microsoft.com/azure/storage/blobs/authorize-data-operations-portal
- Microsoft Learn: Troubleshoot Azure Blob Storage access issues — https://learn.microsoft.com/troubleshoot/azure/azure-storage/blobs/authentication/storage-troubleshoot-portal-access-issues
- Microsoft Learn: Application and service principal objects in Microsoft Entra ID — https://learn.microsoft.com/entra/identity-platform/app-objects-and-service-principals
- Microsoft Learn: What is managed identities for Azure resources? — https://learn.microsoft.com/entra/identity/managed-identities-azure-resources/overview
- Microsoft Learn: Protect Microsoft 365 from on-premises attacks — https://learn.microsoft.com/entra/architecture/protect-m365-from-on-premises-attacks
- Microsoft Learn: Implement password hash synchronization with Microsoft Entra Connect Sync — https://learn.microsoft.com/entra/identity/hybrid/connect/how-to-connect-password-hash-synchronization
- Microsoft Learn: Microsoft Entra Cloud Sync overview — https://learn.microsoft.com/entra/identity/hybrid/cloud-sync/what-is-cloud-sync
- Microsoft Learn: Microsoft Entra pass-through authentication: Technical deep dive — https://learn.microsoft.com/entra/identity/hybrid/connect/how-to-connect-pta-how-it-works
- Microsoft Learn: Microsoft Entra pass-through authentication security deep dive — https://learn.microsoft.com/entra/identity/hybrid/connect/how-to-connect-pta-security-deep-dive
- Microsoft Learn: Kerberos authentication troubleshooting guidance — https://learn.microsoft.com/troubleshoot/windows-server/windows-security/kerberos-authentication-troubleshooting-guidance
- Microsoft Learn: Kerberos Constrained Delegation Overview — https://learn.microsoft.com/windows-server/security/kerberos/kerberos-constrained-delegation-overview
- Microsoft Learn: Understanding Primary Refresh Token (PRT) — https://learn.microsoft.com/entra/identity/devices/concept-primary-refresh-token
- Microsoft Learn: Introduction to Microsoft Entra Kerberos — https://learn.microsoft.com/entra/identity/authentication/kerberos
- Microsoft Learn: Microsoft Entra seamless single sign-on: Technical deep dive — https://learn.microsoft.com/entra/identity/hybrid/connect/how-to-connect-sso-how-it-works
- Microsoft Learn: Kerberos authentication overview in Windows Server — https://learn.microsoft.com/windows-server/security/kerberos/kerberos-authentication-overview
- Microsoft Learn: Key Distribution Center — https://learn.microsoft.com/windows/win32/secauthn/key-distribution-center
- Microsoft Learn: Microsoft Defender for Identity overview — https://learn.microsoft.com/defender-for-identity/what-is
- Microsoft Learn: Cross-cloud collaboration with Microsoft 365 — https://learn.microsoft.com/microsoft-365/enterprise/cross-cloud-collaboration
- Microsoft Learn: What is cross-tenant access? — https://learn.microsoft.com/entra/external-id/cross-tenant-access-overview
