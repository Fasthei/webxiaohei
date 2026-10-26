---
title: "Google Workspace Identity Management and Apple Federation"
date: "2026-10-27"
slug: "google-identity-part2-workspace-gmail-apple"
category: "Cloud Security Research"
summary: "This article reviews Workspace domain and directory boundaries, organizational units, administrator roles, 2-Step Verification, federation, API controls, domain-wide delegation, unmanaged accounts, and federation with Apple Business Manager."
---

# Google Workspace Identity Management and Apple Federation

Workspace, together with Cloud Identity, is the closest equivalent to a tenant boundary in Google's ecosystem: it has a domain, directory, and administration console, and is linked to its own billing arrangements. Its administrative model, authorization relationship with Google Cloud, and external federation options differ from Microsoft Entra. This article focuses on Workspace authentication and administration, and its federation with Apple Business Manager.

## 1. The domain is the identity anchor

Workspace is built around a primary domain and a directory. The Directory API customer ID identifies that directory; the corresponding Google Cloud organization records this ID as its owner, and it cannot be changed. The term "tenant" does not refer to a standalone Google Cloud object: the directory on the email side is reflected in the cloud hierarchy.

Workspace offers two service families: paid Google Workspace editions and the free Cloud Identity service. Cloud Identity provides identity and device management; Workspace adds productivity services. For enterprise boundaries, both provide managed accounts, an organization node, and the Admin console.

Organizational units (OUs) are Workspace's administrative units. Users and devices can be arranged in an OU hierarchy, and service settings and policies can be applied by OU. Google Cloud IAM has no equivalent OU hierarchy: OUs belong to Workspace administration, while cloud resource policies follow the Google Cloud resource hierarchy. A person can therefore have one administrative context in Workspace and a different IAM context in Google Cloud.

Workspace uses predefined administrator roles, which can be scoped to OUs. This role system is separate from Google Cloud IAM: Workspace roles are reviewed in the Admin console, while cloud roles are reviewed in IAM. Similar role names do not imply shared authorization.

## 2. Super administrators and recovery

The Super Admin role is at the top of Workspace administration and has several important capabilities.

First, it controls administrator assignments and can reset administrator passwords; other administrator roles cannot reset administrator passwords.

Second, the organization needs a recovery path. Google recommends having at least one Super Admin and planning for recovery. The recovery process can use a preconfigured secondary email address, which may be outside the managed domain and should be treated as a trusted recovery channel.

Third, a Super Admin is involved in domain ownership verification and recovery. In Google Cloud, the role is associated with the ability to grant IAM roles; its primary cloud-side responsibility is often to grant Organization Administrator to appropriate people in the domain.

Fourth, at least one Super Admin can be designated as the primary administrator for important billing and Google notifications.

Together, these responsibilities make the Super Admin role a high-impact identity. Domain recovery, administrator recovery, and cloud-side authorization may converge on this role. Recovery methods and privileged sessions therefore deserve the same protection and monitoring as the primary administrator account.

## 3. User authentication: 2-Step Verification, federation, and context

For ordinary users, authentication commonly combines a password with a second factor. Administrators can move 2-Step Verification (2SV) from optional to required and can configure exceptions by OU or group. Second-factor methods range from SMS and one-time codes to security keys; their phishing resistance varies, and security keys provide stronger phishing resistance than SMS or voice codes. The administrator policy sets the authentication baseline for the domain.

Workspace can also federate sign-in to a third-party identity provider through SAML or OIDC. An organization may use its existing identity system as the authentication source for Google accounts. Google can also act as an identity provider for other services, including the Apple integration discussed later. The direction differs, but each arrangement depends on a configured trust relationship. When changing federation, identify users who might lose access and ensure that recovery administrators are not unintentionally locked behind the same federation dependency.

Context-Aware Access (CAA) applies conditions such as device state, location, or IP address to service access. For API access, an administrator can configure OAuth applications to be exempt from CAA blocking; the exemption also needs to be reflected in the relevant CAA assignment. Device trust, authentication strength, and context conditions jointly shape Workspace access decisions for both browser and API sessions.

## 4. API controls: Workspace's application access boundary

Admin console's **Security → Access and data control → API controls** is an application access policy keyed by OAuth client ID, including client IDs for service accounts. The policy offers four levels:

- **Specific Google data**: the application can request only the scopes configured for it.
- **Trusted**: the application can access all Google Workspace services, including restricted services.
- **Limited**: the application can access only unrestricted services.
- **Blocked**: the application cannot access Google data.

Three structural rules affect how this policy should be reviewed.

First, some Google-owned applications may receive a different default trust treatment from third-party applications. Review the current console setting for each application rather than assuming a universal default.

Second, Blocked can override an allowlist configured for devices: where API and device policies conflict, the API control can determine access.

Third, an application marked Trusted may retain API access when CAA is tightened, depending on the service and policy configuration. Review API controls and CAA together.

These rules illustrate an important boundary: Google Cloud IAM does not grant access to Workspace mailbox data, while Workspace API controls can determine whether a cloud-side service account or third-party OAuth application may access Workspace services. For a cloud identity that appears to have limited IAM permissions, also review how its client ID is classified in the Admin console.

> "Workspace over Cloud" describes an authorization boundary, not a universal hierarchy. Cloud IAM cannot grant mailbox access, while Workspace's API controls can govern Google Cloud identities that request Workspace data. Security teams should review both systems rather than assume that either console presents the complete picture.

## 5. Domain-wide delegation and application access

Domain-wide delegation (DWD) allows a Super Admin to grant a client application access to data across Workspace users without requiring each user to consent.

The configuration associates an application client ID—such as a service account or third-party OAuth application—with a set of OAuth scopes in **Manage Domain Wide Delegation**. Once authorized, the application may access data covered by those scopes.

The cloud and Workspace views are separate. In Google Cloud, the identity may be an ordinary service account with narrow IAM bindings; in Workspace, its client ID may have broad scopes recorded in the Admin console's DWD configuration. No single view necessarily shows both the cloud roles and Workspace scopes.

> DWD should be governed as a domain-level grant. Review each client ID and scope, keep scopes narrow, remove grants that are no longer needed, and require approval and audit for changes. A service account's cloud IAM role does not describe its Workspace access.

## 6. Conflicting and unmanaged accounts

The same email address may identify an unmanaged personal account and a separate managed Workspace account. The sign-in screens can look similar, but the accounts are distinct. Potential account conflicts should be reviewed and resolved before adding the user to Cloud Identity.

Unmanaged accounts complicate asset ownership and lifecycle management. Projects created under unmanaged accounts may sit outside the organization's resource hierarchy; OAuth grants and subscriptions may also remain associated with the unmanaged identity after a managed account is disabled. Inventory and offboarding procedures should account for both identities and their associated resources.

## 7. Apple federation: Workspace identity and device ownership

Apple Business Manager (ABM) supports federated authentication with Google Workspace. An administrator selects **Sign in with Google** in ABM and configures the Workspace administrator identity; Managed Apple ID authentication then uses Google credentials.

Google also supports management of organization-owned iOS devices through the Admin console, provided Apple Business Manager or Apple School Manager is linked to a Workspace or Cloud Identity subscription. The integration launched in 2020, when ABM was still known as the Device Enrollment Program, and brought iOS device management into Google's device view.

This federation spans three control planes: Workspace authenticates the person, ABM determines whether a device belongs to the organization, and mobile device management reports device state. These systems govern different facts—who the user is, whether the device is organization-owned, and whether it meets policy.

> The three planes should be reviewed independently and together. Changes to a Workspace account can affect Managed Apple ID sign-in; device enrollment and ownership remain governed by ABM; device compliance is reported through MDM. Confirm administrative ownership and recovery paths for each system.

## Key points

1. Workspace and Cloud Identity provide the closest Google equivalent to a tenant boundary; the domain anchors identity, and the Directory customer ID is recorded by the cloud organization.
2. OUs are Workspace administrative units and do not mirror Google Cloud resource folders.
3. Super Admin accounts control administrator assignments and recovery paths and can grant cloud IAM roles.
4. 2SV methods vary in phishing resistance; federation and recovery paths should be reviewed together.
5. API controls classify applications by OAuth client ID, including service accounts.
6. Google-owned applications may have different defaults; Blocked, CAA, and allowlist behavior must be checked against current settings.
7. Workspace API controls and Google Cloud IAM are separate authorization systems.
8. DWD associates client IDs with scopes and can grant broad Workspace data access without per-user consent.
9. A service account's Workspace access is determined by its DWD scopes, not solely by its Google Cloud roles.
10. Unmanaged accounts can own projects, OAuth grants, or subscriptions outside the managed directory.
11. Apple federation spans Workspace authentication, ABM device ownership, and MDM compliance.

## References

Google Workspace Help: Prebuilt administrator roles — https://support.google.com/a/answer/2405986

Google Workspace Help: Deploy 2-Step Verification — https://support.google.com/a/answer/9176657

Google Workspace Help: Control which apps access Google Workspace data — https://support.google.com/a/answer/7281227

Google Workspace Help: Control API access with domain-wide delegation — https://support.google.com/a/answer/162106

Google Workspace Help: Domain-wide delegation best practices — https://support.google.com/admin/apps/domain-wide-delegation-best-practices

Google Cloud documentation: Create Cloud Identity user accounts (conflicting accounts) — https://docs.cloud.google.com/identity/docs/how-to/create-cloud-identity-user-accounts

Google Cloud documentation: Cloud Platform resource hierarchy (Super Admin and organization) — https://cloud.google.com/resource-manager/docs/cloud-platform-resource-hierarchy

Google Workspace Help: Set up management of company-owned iOS devices — https://support.google.com/a/answer/9904735

Apple Support: Use federated authentication with Google Workspace in Apple Business Manager — https://support.apple.com/guide/apple-business-manager/axmaef1a0154/web

Google Workspace Updates: Simplify management of company-owned iOS devices with new Apple Business Manager integration — https://workspaceupdates.googleblog.com/2020/07/ios-device-management-google-endpoint-apple.html
