---
title: "AWS Identity and Billing Boundaries: Root, Management Accounts, and Cross-Account Trust"
date: "2026-10-26"
slug: "aws-identity-root-payer-trust"
category: "Cloud Security Research"
summary: "AWS concentrates identity, credentials, trust, and billing around the account boundary. This article reviews the root user, the management account's payer role, credential lifetimes, and cross-account authorization."
---

# AWS Identity and Billing Boundaries: Root, Management Accounts, and Cross-Account Trust

AWS and Microsoft use structurally different identity and billing models. Microsoft separates identity tenants, resource subscriptions, and billing accounts; AWS centers these functions on the account. An account is a resource and identity container, with IAM inside it, and an independent billing entity. I use the account boundary to organize this review of authentication, credentials, trust, and billing.

Above individual accounts, AWS Organizations is created by a management account. Member accounts can be arranged in organizational units beneath the organization's root. The account root user and the Organizations root container are different concepts.

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

The two models differ across three boundaries:

| Boundary | Azure | AWS |
| --- | --- | --- |
| Identity | Entra tenant (directory) | Within an account (root and IAM); accounts are independent |
| Resources | Subscriptions and management groups | Accounts, with resources deployed in Regions |
| Billing | Billing account, profiles, and invoice sections | Organization; the management account is the payer |

Two implications follow:

- In Azure, changing a subscription's directory association is an attribute change, and resource and billing relationships can be handled separately. In AWS, crossing accounts means crossing a container boundary: resource migration, identity setup, and explicit trust may all be involved. Cross-account role access requires trust and permission configuration; resource policies can also grant external principals access, as discussed later.
- Organizations does not erase member-account independence. Without relevant organizational controls, member-account owners use their own credentials and authorize access within their accounts. Consolidated billing and permissions are separate dimensions; payer status does not by itself grant full cross-account control.

## 2. Root: the account's identity origin

The root user is the unique sign-in identity created with an account and has full access to that account's services and resources. Its credentials use the email address and password registered for the account.

Three properties follow:

- **The root identity is associated with an email address, not a person.** The recovery path includes access to the root email inbox. A group mailbox and separate custodians for the password and MFA can reduce dependence on one individual.
- **Root represents the account's maximum authority.** IAM identity policies do not restrict the root user, although resource policies can explicitly deny access. Recovering access to a resource whose policy blocks all principals may require the root user.
- **Some tasks are root-only.** These include certain account settings, closing or reopening an account, recovering locked-out IAM administration, enabling IAM billing-console access, some billing and tax operations, S3 MFA Delete, and other service-specific account recovery tasks. Check the current root-task documentation for the precise list.

Credential discipline matters: do not create long-term root access keys. If interactive CLI access is required, `aws login` can use console sign-in to obtain temporary credentials. AWS requires MFA for root users; an unconfigured root user must register MFA within 14 days of first sign-in. This requirement applies to all AWS account types.

Member-account root access has a separate governance model. Organizations accounts created with centralized root access can be provisioned without root credentials. When centralized root access is enabled, the management account or delegated administrator can remove member-account root passwords, access keys, and signing certificates, and can perform supported privileged root tasks or allow password recovery. This consolidates root access at the governance layer; administrators who can perform root tasks are consequently high-value identities. A member-account root represents that account, while management-account root combines organization governance, billing, and exemption from member-account SCP controls.

## 3. Payer: the organization's payment role

### 3.1 Payer is the management account's economic role

An organization is created by a management account, which is also the payer responsible for paying charges accrued by member accounts. The Cost and Usage Report `bill/PayerAccountId` field identifies the payer; in AWS Organizations, this is the management account.

The relationship is therefore: **one account, with root as its identity origin and payer as its economic role**. An organization has one management account and one payer. A billing transfer is a separate path for transferring billing management; it is not an in-place change to the organization's management account.

### 3.2 Root and the payer account

Three properties are relevant:

- **The management account root is an organization-level authority.** Organization creation, member-account management, delegated-administrator assignments, and enabling all features are managed through the management account. The organization's root container is also above its accounts.
- **The management account is less constrained by SCPs.** SCPs affect IAM users and roles in member accounts, including member-account root, but not users and roles in the management account. An SCP attached to the organization root does not constrain the management account.
- **The management account root must have MFA.** AWS's root-user MFA requirement applies to all account types; where MFA is absent, the first-sign-in registration grace period is 14 days.

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

These properties make the management account root a high-impact identity: it can change organization-level rules without first crossing into a member account.

The supposed `root → admin → payer` permission ladder does not exist; it combines two independent axes. Root and an IAM administrator are account-local authorization identities. Payer is an organization's billing role. A member account's root or administrator has no default access to the management account, and the management account does not automatically have IAM permissions in member accounts. Cross-account roles, delegated root tasks, and service integrations provide specific paths:

- **`OrganizationAccountAccessRole`**: Organizations creates this role in a new member account with `AdministratorAccess` and trust for the management account. Assuming it grants administrative access in that member account. An invited account may need this role configured separately.
- **Delegated administration and AssumeRoot**: when centralized root access is enabled, the management account or a delegated administrator can perform supported privileged root tasks in member accounts.
- **SCP asymmetry**: SCPs constrain member accounts but do not constrain the management account.

### 3.3 Payer and payment

- **Consolidated billing:** AWS charges the management account for member-account usage each month. Member-account bills are informational; payment is made by the management account.
- **Discount sharing:** Reserved Instances, Savings Plans, and capacity discounts can be shared within an organization.
- **Payment methods belong to the management account.** Payment methods, billing contacts, and invoices are configured on the payer side, subject to special arrangements such as resale contracts.
- **Billing visibility is centralized.** The management account can view consolidated cost and member-account detail. When an account leaves an organization, it loses access to Cost Explorer history from its time in the organization; the data remains with the management account.
- **Some organizations have default safeguards.** Organizations created through the console after July 10, 2026, automatically receive an SCP at the organization root that denies member accounts `organizations:LeaveOrganization` and `account:CloseAccount`. Older organizations must add equivalent controls themselves.
- **Billing management can be transferred externally.** Billing transfer can move billing management to another organization's management account, separating payment and billing visibility from account governance.

For defense, restrict management-account access, maintain resilient root-email and MFA recovery procedures, avoid deploying workloads in the management account, and use appropriate SCP guardrails for member accounts.

> In governance reviews, I prioritize the management account's payment methods, billing visibility, and account-lifecycle controls. Its permissions do not automatically become member-account IAM permissions; access to member resources still depends on specific cross-account roles, delegated tasks, or service integrations. Billing and resource access should be reviewed separately.

## 4. Three layers of authentication

Authentication is the process of establishing an identity; credentials are the material used to prove it. Human authentication is concentrated in the console and IAM Identity Center, while machine authentication uses signed requests and temporary credentials. AWS services generally use roles rather than independent service-account users; service credentials are the temporary credentials of an assumed role.

### 4.1 Three identity types

- **Root:** the account's original identity, using email and password, with MFA and a set of root-only tasks.
- **IAM user:** a long-lived account identity that can have a console password, access keys, and MFA. This traditional model is increasingly replaced by IAM Identity Center and temporary credentials.
- **IAM role or federated identity:** a temporary identity defined by trust and permission policies. A principal uses STS `AssumeRole` or federation through OIDC or SAML to obtain temporary credentials. IAM Identity Center is the recommended centralized human-identity model; permission sets map to roles in target accounts.

### 4.2 Console and API planes

Console sign-in occurs at an account's identity entry point using root or IAM-user credentials and MFA. After authentication, the console obtains a session for the principal; console operations also use temporary credentials and signed requests. API requests are signed with SigV4. Federation replaces the account password with an identity-provider assertion that STS validates before issuing temporary credentials. Sign-in entry points are also part of the account's exposure: root users sign in with an account ID or alias and the root email; IAM users use an account alias or ID and a username. An account alias visible in a page or document is a public identifier, not a secret. MFA factors are separately enrolled for root, IAM users, and Identity Center; do not treat them as one shared factor. Console-session activity appears in sign-in events, while API credentials are reflected in signed requests.

### 4.3 SigV4: the secret key is not sent over the network

The signing process canonicalizes the method, path, query string, headers, and payload hash, then derives a signing key through an HMAC chain (`kSecret → kDate → kRegion → kService → kSigning`). The resulting signature is sent in the `Authorization` header alongside the access-key ID.

The SecretAccessKey is not transmitted in the request. The service recomputes the signature from its key material and compares it with the request signature. Credential exposure therefore principally concerns the secret key; the access-key ID is an identifier. Temporary credentials consist of an access-key ID, SecretAccessKey, and SessionToken, all three of which are required.

## 5. Service credentials: lifetime defines exposure

Credentials can be classified by lifetime and storage location:

| Type | Form | Lifetime | Typical acquisition or storage |
| --- | --- | --- | --- |
| Root access key | `AKIA…` + Secret | Until manually deleted | Human, script, or configuration file; strongly discouraged |
| IAM user key | `AKIA…` + Secret | Until manually rotated | Local configuration, CI variables, application configuration |
| STS temporary credentials | `ASIA…` + Secret + SessionToken | One hour by default; up to 12 hours where configured | `AssumeRole`, federation, Identity Center |
| EC2 instance identity | Instance profile → IMDS | Rotated with the session | `169.254.169.254` (IMDSv2 first obtains a token with PUT) |
| Container / EKS | Task role, IRSA / Pod Identity | Rotated with the session | Projected token or metadata endpoint |
| CI/CD | OIDC federation for temporary credentials | Pipeline session | External identity provider such as GitHub Actions |
| Service-linked role | SLR; trust restricted to a service principal | Service lifecycle | Service operations on behalf of an account |

A service-linked role is a service-specific role whose trust policy identifies the service principal. Users do not directly assume it; the service uses it to perform authorized operations in the account.

Two credential forms are easy to miss. Some services issue their own credentials without STS, such as ECR Docker login tokens (typically valid for about 12 hours) and CodeCommit Git credentials; each service defines its own issuance and rotation rules. IAM-only inventories can miss these. Local credential storage also matters: IAM user keys may appear in `~/.aws/credentials`, environment variables, CI variables, or application configuration. Identity Center sessions are cached under `~/.aws/sso/cache` and may include a refresh token. Machine credentials are usually obtained at runtime through IMDS or projected tokens rather than written to disk. Theft of a long-term key can persist until rotation; stolen session material has a time-limited renewal window.

Four assessment rules:

- Key prefixes are useful indicators: `AKIA` is a long-term access key for an IAM user or root; `ASIA` is an STS temporary credential. Treat the first as a rotation concern and the second as an expiration and session-source concern.
- Role chaining imposes a one-hour maximum session duration, regardless of the target role's longer configured maximum.
- Machine identity is a credential-acquisition path. IMDS provides credentials to an instance, while containers and CI obtain their credentials through corresponding runtime or federation paths. Restrict and monitor these paths; IMDSv2's token exchange mitigates some metadata access risks.
- `get-caller-identity` can identify the principal, account, and role associated with credentials during authorized incident response and validation.

> I assess credential risk across storage location, lifetime, and permissions. Long-lived credentials close to application code generally have a larger exposure window; IMDS should be treated as an important runtime-identity boundary.

## 6. Trust relationships: who can become whom

An IAM role has two policy components: the trust policy defines who can assume it, and the permission policy defines what the assumed role can do. `AssumeRole` switches the caller to the role's session permissions rather than adding the role's permissions to the caller's original identity.

Three principal categories correspond to common sources of role assumption:

- AWS accounts, users, or roles for same-account and cross-account access;
- Service principals, such as `ec2.amazonaws.com`, for service operations on behalf of a resource;
- Federated identities from SAML or OIDC identity providers.

Four assessment rules:

- **Cross-account role access requires both sides to allow it.** The target role's trust policy and the caller's identity policy must permit `sts:AssumeRole`.
- **Trusting an account delegates part of the authorization decision.** A trust principal such as `arn:aws:iam::ACCOUNT_ID:root` allows administrators in that account to authorize its principals, subject to the relevant policies.
- **Confused-deputy risks have standard mitigations.** Use ExternalId for third-party multi-tenant scenarios; consider `aws:PrincipalOrgID` for organization boundaries and `aws:SourceAccount` or `aws:SourceArn` for service principals.
- **SCPs and trust policies are separate dimensions.** SCPs constrain member-account principals, not the management account or principals from an external organization. An SCP on account A does not govern an external account B principal accessing A's resource through a resource policy.

Cross-account access has parallel paths. The identity path uses roles and trust policies. The resource path uses resource policies that name external principals, such as S3 bucket, KMS key, and SNS topic policies. KMS key policies are particularly important: IAM policies do not independently authorize key use if the key policy does not allow it. Review both paths when assessing external access.

The permission-evaluation model includes explicit Deny, organizational guardrails, permission boundaries, session policies, identity policies, and resource policies. A permission boundary limits the maximum available permissions; it does not grant permissions.

> Permission policies answer what an identity can do; trust policies answer who may assume a role. I review both directions: roles available to account identities and external principals trusted by local roles. Broad principals and missing conditions deserve particular scrutiny.

## 7. Role chaining and transitivity

- Trust is not transitive, but delegation can be composed: A trusts B, and B may separately delegate access to C. Each hop needs an explicit grant, though the combined effect may exceed the intent of an individual hop.
- Role chaining has a one-hour maximum session duration.
- Each hop changes the active permissions and can increase or decrease effective access. Model the chain as a directed graph and review trust conditions at every step.
- Conditions on service principals provide another boundary. `aws:SourceAccount` and `aws:SourceArn` can restrict service use of a role to a specific account or resource where supported.

## 8. Review sequence and detection

For authorized incident response or architecture review, I organize evidence in five areas:

1. **Identity:** identify the principal, account, and role.
2. **Credentials:** determine whether the credentials are long-lived or temporary, their expiration, and their issuance path.
3. **Trust:** review role-assumption permissions and external principals trusted by the account.
4. **Organization:** establish the account's organizational position, payer relationship, and delegated-administrator permissions.
5. **Billing:** identify where usage appears and which identities can affect payment and account lifecycle.

Relevant monitoring areas include:

- CloudTrail events for `AssumeRole`, trust-policy updates, access-key creation, login-profile creation, and console sign-ins, interpreted with source and frequency context;
- IAM Access Analyzer for cross-account trust and externally accessible resources;
- GuardDuty findings related to root-credential use and unusual credential activity;
- organization and billing events, including new account membership, anomalous costs, payment-method changes, and billing transfers;
- host and network telemetry for unexpected requests to `169.254.169.254`.

Defensive controls include MFA and recovery planning for root, no long-lived root keys, short-lived credentials, narrow trust policies with appropriate conditions, management-account isolation and monitoring, billing alerts, and SCP guardrails.

## 9. Key points

- An AWS account contains resources, identities, and an independent billing entity; Organizations groups accounts but does not erase member-account independence.
- Root is the account's original identity and has full account access. IAM identity policies do not restrict it, although resource policies can deny access.
- Payer is the management account's economic role, not a separate account type; organization billing and payment methods are managed there.
- Root and IAM administrator are account-level identities; payer is an organizational billing role. Member access relies on explicit paths such as `OrganizationAccountAccessRole`.
- Consolidated billing and discount sharing are separate from member-account IAM access.
- SCPs constrain member accounts, including their root users, but not the management account.
- Centralized root access can manage member-account root credentials and supported privileged tasks.
- `AKIA` indicates long-lived access keys and `ASIA` indicates STS temporary credentials; temporary sessions have configurable durations and role chaining is capped at one hour.
- `AssumeRole` uses the role's session permissions; cross-account role access needs both caller permission and target trust.
- Cross-account access can also come from resource policies; KMS key policies are a key authorization boundary.
- Trust is not transitive, but explicit delegation can be composed across multiple roles.
- IMDS is a runtime credential source and should be included in workload isolation and monitoring.

For authorized review, I follow the sequence identity → credentials → trust → organization → billing. The first three describe permissions and credential provenance; the last two establish organizational and financial impact.

---

## 10. References

Sources checked on 2026-10-26:

- AWS IAM User Guide: The AWS account root user — https://docs.aws.amazon.com/IAM/latest/UserGuide/id_root-user.html
- AWS IAM User Guide: Root user best practices for your AWS account — https://docs.aws.amazon.com/IAM/latest/UserGuide/root-user-best-practices.html
- AWS Organizations User Guide: Terminology and concepts — https://docs.aws.amazon.com/organizations/latest/userguide/orgs_getting-started_concepts.html
- AWS Organizations User Guide: Service control policies (SCPs) — https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_scps.html
- AWS Organizations User Guide: Best practices for the management account — https://docs.aws.amazon.com/organizations/latest/userguide/orgs_best-practices_mgmt-acct.html
- AWS Organizations User Guide: Who pays for usage in an organization — https://docs.aws.amazon.com/organizations/latest/userguide/pricing.html
- AWS Organizations FAQ (payer and management-account definitions) — https://aws.amazon.com/organizations/faqs/
- AWS Organizations User Guide: Accessing member accounts (`OrganizationAccountAccessRole`) — https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_accounts_access.html
- AWS IAM User Guide: Perform a privileged task on a member account (`AssumeRoot`) — https://docs.aws.amazon.com/IAM/latest/UserGuide/id_root-user-privileged-task.html
- AWS Billing: Consolidating billing for AWS Organizations — https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/consolidated-billing.html
- AWS Billing: Consolidated billing process — https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/useconsolidatedbilling-procedure.html
- AWS CUR: `bill/PayerAccountId` column definition — https://docs.aws.amazon.com/cur/latest/userguide/billing-columns.html
- AWS IAM User Guide: Cross-account access using roles — https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies-cross-account-resource-access.html
- AWS IAM User Guide: Updating a role trust policy — https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_update-role-trust-policy.html
- AWS IAM User Guide: Switching to a role (role-chaining session limit) — https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_use_switch-role-console.html
- AWS IAM User Guide: Securing access keys (`AKIA` prefix) — https://docs.aws.amazon.com/IAM/latest/UserGuide/securing_access-keys.html
- AWS IAM User Guide: Unique ID prefixes (`ASIA` prefix) — https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_identifiers.html
- AWS IAM User Guide: Requesting temporary security credentials — https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_temp_request.html
- AWS IAM User Guide: SigV4 signing process — https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_sigv.html
- AWS EC2: Retrieve security credentials from instance metadata — https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/instance-metadata-security-credentials.html
- AWS EC2: Configuring the Instance Metadata Service (IMDSv2) — https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/configuring-instance-metadata-service.html
- AWS Security Blog: Defense in depth: open firewalls, reverse proxies, SSRF vulnerabilities, and the EC2 Instance Metadata Service — https://aws.amazon.com/blogs/security/defense-in-depth-open-firewalls-reverse-proxies-ssrf-vulnerabilities-ec2-instance-metadata-service/
- AWS Security Blog: How to use trust policies with IAM roles — https://aws.amazon.com/blogs/security/how-to-use-trust-policies-with-iam-roles/
- AWS News Blog: Centrally managing root access for customers using AWS Organizations — https://aws.amazon.com/blogs/aws/centrally-managing-root-access-for-customers-using-aws-organizations/
- Rhino Security Labs: AWS Privilege Escalation – Methods and Mitigation — https://rhinosecuritylabs.com/aws/aws-privilege-escalation-methods-mitigation/
- PwnedLabs: AWS Privilege Escalation: Techniques and Defenses — https://pwnedlabs.io/blog/aws-privilege-escalation-techniques-and-defenses
- Token Security: IAM Role Trust Policies: Misconfigurations Hiding in Plain Sight — https://www.token.security/blog/iam-role-trust-policies-misconfigurations-hiding-in-plain-sight
- Wiz: IMDS Abused: Hunting Rare Behaviors to Uncover Exploits — https://www.wiz.io/blog/imds-anomaly-hunting-zero-day
- Resecurity: SSRF to AWS Metadata Exposure — https://www.resecurity.com/blog/article/ssrf-to-aws-metadata-exposure-how-attackers-steal-cloud-credentials

Supplementary searches were conducted through Jina Search. The attack paths in this article are presented as conceptual categories and defensive review topics; apply them only within authorized environments.
