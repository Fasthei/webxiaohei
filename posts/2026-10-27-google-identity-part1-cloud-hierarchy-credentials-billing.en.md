---
title: "Google Cloud Identity, Resource Hierarchy, and Billing"
date: "2026-10-27"
slug: "google-identity-part1-cloud-hierarchy-credentials-billing"
category: "Cloud Security Research"
summary: "This article reviews consumer and managed identities, the Google Cloud organization-folder-project hierarchy, service-account credentials, and the relationship between Cloud Billing accounts and Google payments."
---

# Google Cloud Identity, Resource Hierarchy, and Billing

Google Cloud's structure can be compared with Microsoft's identity-tenant, resource-subscription, and billing-account boundaries, but the names, ownership, and authorization paths differ. Google's ecosystem includes consumer Google accounts, Workspace or Cloud Identity accounts, and Google Cloud projects and organizations. They share some account protocols, but identity, product access, and billing remain distinct.

The separation is visible in both billing and engineering. Cloud Billing accounts record usage for eligible Google Cloud products, while Google payments profiles belong to Google's broader payments system and are separate from Cloud IAM. Google Cloud also exposes product-specific MCP endpoints and tools; a shared identity system does not imply shared authorization. Product coverage and billing relationships can vary by service and account configuration, so verify the current documentation.

## 1. The resource hierarchy

Except for the top-level resource, each resource has exactly one parent. The hierarchy consists of an organization at the root, optional folders for grouping, and projects that contain service resources such as Compute Engine virtual machines, storage buckets, datasets, and keys.

```text
organization（根，锚定 Workspace/Cloud Identity 域）
└── folder（可选，分组用）
    └── project（实际资源的容器）
        └── 服务资源：VM、bucket、数据集、密钥……
```

Three properties matter.

First, the hierarchy is single-parent. A project cannot belong to multiple organizations, and a folder cannot span organizations. Access across hierarchy boundaries comes from IAM grants rather than combining resource trees. Policies are inherited within the tree; cross-boundary access should be reviewed as an explicit grant.

Second, the organization node is associated with a Workspace or Cloud Identity account rather than created independently as an ordinary cloud resource. An account can be associated with one organization. The organization has an ID, a display name derived from the primary Workspace domain, a creation time, and an immutable Directory API customer ID as its owner. Domain ownership therefore anchors the cloud organization.

Third, initial access needs review. When an organization is created, its default allow policy can grant Project Creator and Billing Account Creator to the Workspace domain. Administrators should confirm that this matches the organization's least-privilege requirements. Projects created by managed users generally belong to the organization; the parent and ownership of existing projects should be checked separately. Projects without an organization parent may come from consumer or unmanaged accounts, or from legacy configurations, and may be migrated. Projects are generally owned by the organization rather than the employee who created them. Deleting an organization affects its resources, so project transfer and archival need an explicit lifecycle plan.

Three policy mechanisms participate in the hierarchy: allow policies, deny policies, and organization policies. A resource's effective policy combines direct assignments with inherited ancestor policies; a deny policy can override an allow. An IAM-only review may miss deny or organization-policy constraints.

> I include projects without an organization parent in asset reconciliation and confirm their owner, billing arrangement, data location, and migration status. Such projects may belong to consumer or unmanaged accounts, or may be legacy assets; their origin and risk should be established rather than inferred from hierarchy alone.

## 2. Identity accounts and principals

Microsoft Entra has a clearly defined tenant object; Google has no direct equivalent. The closest analogue is the combination of a Workspace or Cloud Identity account and its organization node, which sit on the productivity and cloud sides respectively. Google's identity model is best understood by account type rather than by a single tenant container.

There are three broad account types. Consumer accounts, often ending in `@gmail.com`, have no organizational administrator and can access free-tier resources or be granted access as explicit IAM principals. Managed accounts belong to a Workspace or Cloud Identity domain and are administered through the Admin console. An unmanaged account can arise when a person registers a work email address for a personal or unmanaged account before the organization creates a managed account using the same address; the two accounts are separate even though the sign-in identifier looks identical.

The conflict arises because two accounts cannot share the same username. Potential conflicts should be reviewed before adding a user to Cloud Identity. Similar sign-in screens do not indicate the same account, which can also explain why a project's access history does not match the managed mailbox identity.

IAM principals include users, service accounts, groups, domains, and principal sets used by federation. A domain is itself a principal: organization defaults can grant roles to an entire domain. Domain-wide grants should therefore be reviewed as directory-scale authorization.

## 3. Service credentials: short-lived tokens and keys

Like users, service accounts can obtain OAuth 2.0 access tokens for Google APIs, but their credential paths differ. The main distinction is between short-lived credentials and keys.

Short-lived credentials are generally preferred; access tokens commonly expire after one hour. They may be obtained through service-account impersonation with `gcloud --impersonate-service-account`, through Application Default Credentials (ADC) for a service account attached to a Compute Engine instance, or through Workload Identity Federation (WIF) using an external identity provider. The Service Account Credentials API can also issue OAuth 2.0 access tokens, OIDC ID tokens, and self-signed JWTs.

Service-account keys are long-lived credentials. Anyone holding a key can act as the service account by signing a JWT and exchanging it for an access token. A key file is not bound to a particular host, process, or person. Short-lived credential issuance usually provides a clearer audit trail, while use of a service-account key may appear only as the service account itself.

Workload Identity Federation is an alternative to long-lived keys. Supported sources include X.509 client certificates, workloads running on AWS or Azure, on-premises Active Directory, GitHub or GitLab pipelines, and identity providers that support OIDC or SAML 2.0. Under the OAuth 2.0 token exchange model (RFC 8693), an external credential is presented to Security Token Service and exchanged for a federated token. Access can be granted directly to a federated principal or through service-account impersonation. WIF uses workload identity pools and providers; providers may also use uploaded JWKS where an external public OIDC endpoint is unavailable.

Application Default Credentials (ADC) provide a lookup sequence for client libraries: a credential file specified by an environment variable, user credentials installed by gcloud, and a service account attached to a compute resource. An attached service account can also provide credentials through the metadata service.

> I assess service-credential exposure across three paths: files (service-account keys, ADC files, and gcloud configuration), federation (WIF pools and providers), and runtime identity (attached service accounts and metadata services). Each path has different controls and audit signals. Metadata access should be restricted and monitored as part of workload isolation.

## 4. Billing: three account layers

Google billing has three layers with different administrative boundaries: Cloud Billing accounts are cloud resources, while Google payments accounts and payments profiles belong to Google's payments system.

The first layer is the Cloud Billing account. It records usage for projects linked to the account and, depending on product and account configuration, may cover Google Cloud, Google Maps Platform, Firebase, and Google AI Studio. An account uses a single currency. Self-serve accounts are opened online and may be paid by credit card; invoiced accounts have invoice-based billing. Subaccounts are available for reseller scenarios.

The second layer is the Google payments account. It is linked to a Cloud Billing account and pays the charges, with an assigned charging cycle such as prepaid or postpaid. It also manages invoices, statements, payment history, and who can view or receive billing documents.

The third layer is the Google payments profile. Managed through Google Payments Center, it may connect multiple Google services and store payment instruments, country or region, tax details, and responsible contacts. It has its own payments users and permissions, separate from Cloud IAM.

```text
Google payments profile（谷歌级，全家桶共享）
└── Google payments account（充电周期/票据中心）
        │  被链接、代付款
        ▼
Cloud Billing account（云级资源，单一币种）
        │  记账
        ▼
project（实际产生用量的地方）
```

Billing authorization is a separate IAM system. Common roles include:

- Billing Account Creator (`roles/billing.creator`): an organization-level role for creating eligible self-serve billing accounts. Its assignment should be limited and reviewed.
- Billing Account Administrator (`roles/billing.admin`): manages payment methods, billing profiles, exports, costs, payments, project links, and other billing-account roles.
- Billing Account Costs Manager (`roles/billing.costsManager`): manages budgets and cost exports, but not pricing or payment methods.
- Billing Account Viewer (`roles/billing.viewer`): read-only access to costs and transactions, often used by finance teams.
- Billing Account User (`roles/billing.user`): allows projects to be linked to a billing account and has a narrower scope.
- Project Billing Manager (`roles/billing.projectManager`): works with Billing Account User to link or unlink projects and does not grant resource permissions.

Project linking and unlinking require cooperating roles. The design separates resource access from payment authority: a Project Owner can delegate billing management without granting access to project resources.

> `billing.admin` can close, reopen, or move a billing account and manage project associations and billing roles. These high-impact actions can affect payment, billing ownership, and service continuity. They should be controlled through separation of duties, approval, and change auditing. I review billing-account IAM bindings alongside each project's billing association.

## 5. Trust relationships between the trees

There are four main connections between the identity, resource, and billing structures.

First, the domain anchors the organization node: the organization's owner is a Directory API customer ID, and one Workspace or Cloud Identity account can be associated with one organization.

Second, Super Admins are connected to Organization Administrator assignments. Workspace Super Admins verify and recover domain ownership and can grant IAM roles; their cloud-side responsibility commonly includes assigning Organization Administrator to appropriate domain users. This separates Workspace and Google Cloud administration while preserving a defined authorization path between them.

Third, the domain can receive initial project-creation and billing-account-creation grants through the default allow policy. These grants determine who can create resources and billing accounts.

Fourth, projects can be linked to or unlinked from Cloud Billing accounts. The resource hierarchy and billing hierarchy are not a single parent-child tree; their relationship is a changeable association.

```text
 Workspace 域（邮箱侧）                Cloud 侧
 ┌────────────────────┐    锚定    ┌──────────────────────┐
 │ 域名 + Directory    │ ────────→ │ organization 节点      │
 │ customer ID        │           │ （owner 不可改）        │
 │                    │           └──────────────────────┘
 │ 超级管理员          │  默认可授  ┌──────────────────────┐
 │                    │ ────────→ │ Organization          │
 │                    │  OrgAdmin │ Administrator 等 IAM  │
 │ 全域普通用户        │ ────────→ │ Project Creator       │
 │                    │  初始授权  │ Billing Acct Creator  │
 └────────────────────┘           └──────────┬───────────┘
                                             │ 动态链接
                                  ┌──────────▼───────────┐
                                  │ Cloud Billing        │
                                  │ account ⇄ payments   │
                                  └──────────────────────┘
```

## Key points

1. Google has no single root object spanning all businesses; identity, cloud resources, and billing use distinct authorization systems.
2. The resource hierarchy is single-parent. Policies inherit within it; access across its boundaries requires explicit authorization.
3. A Workspace or Cloud Identity account can be associated with one organization; the organization records its Directory customer ID as owner.
4. Organization defaults may grant Project Creator and Billing Account Creator to a domain, which is itself an IAM principal.
5. Allow, deny, and organization policies combine to determine effective access.
6. Service credentials involve file-based credentials, federation, and runtime identities; each has different controls and audit signals.
7. Short-lived credentials commonly last one hour; impersonation and key-based use have different audit characteristics.
8. Billing spans Cloud Billing accounts, Google payments accounts, and Google payments profiles, each with distinct responsibilities and permissions.
9. Billing administrators can perform actions that affect payment and project association, so those actions need governance and audit.
10. The principal cross-tree relationships are domain-to-organization association, administrator grants, domain-level defaults, and project-to-billing links.

## References

Google Cloud documentation: Cloud Platform resource hierarchy — https://cloud.google.com/resource-manager/docs/cloud-platform-resource-hierarchy

Google Cloud documentation: Cloud Billing concepts — https://cloud.google.com/billing/docs/concepts

Google Cloud documentation: Cloud Billing access control — https://cloud.google.com/billing/docs/how-to/billing-access

Google Cloud documentation: Service account credentials — https://cloud.google.com/iam/docs/service-account-creds

Google Cloud documentation: Workload Identity Federation — https://cloud.google.com/iam/docs/workload-identity-federation

Google Cloud documentation: How Application Default Credentials works — https://cloud.google.com/docs/authentication/application-default-credentials

Google Cloud documentation: gcloud auth login — https://cloud.google.com/sdk/gcloud/reference/auth/login

Google Cloud documentation: Metadata server — https://cloud.google.com/compute/docs/metadata/overview

Google Cloud documentation: IAM roles overview — https://cloud.google.com/iam/docs/understanding-roles

Google Cloud documentation: MCP servers for Google Cloud — https://cloud.google.com/mcp

Google Cloud documentation: Supported MCP server products — https://docs.cloud.google.com/mcp/supported-products

Google Cloud documentation: Create Cloud Identity user accounts (conflicting accounts) — https://docs.cloud.google.com/identity/docs/how-to/create-cloud-identity-user-accounts
