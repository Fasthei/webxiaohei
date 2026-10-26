---
title: "Gemini in Google Workspace: Data Access Boundaries and Security Review"
date: "2026-10-27"
slug: "google-identity-part3-gemini-offense"
category: "Cloud Security Research"
summary: "This article distinguishes the Gemini app, Workspace-integrated features, and Gemini Enterprise; reviews their data-access and administrative boundaries; and uses the publicly disclosed, patched GeminiJack case as historical context for indirect prompt-injection risk."
---

# Gemini in Google Workspace: Data Access Boundaries and Security Review

Gemini access is shaped by identity, Workspace settings, collaboration permissions, and API controls. This article distinguishes the main product forms, explains their data-access and audit boundaries, and discusses prompt-injection risk through a public research case.

## 1. Three Gemini product surfaces

Treating "Gemini" as one product obscures important differences between its main surfaces.

The first is the Gemini app and its Connected Apps or Workspace extensions. In supported Workspace editions, users can reference services such as Gmail, Drive, or Calendar so Gemini can retrieve information or perform supported tasks.

The second is Gemini embedded in Gmail, Docs, Sheets, and other Workspace applications. It operates within the workload, and its privacy treatment is covered by Workspace's Generative AI Privacy Hub.

The third is Gemini Enterprise. It provides enterprise search, AI assistance, and agent capabilities, and can connect to systems such as Confluence, Jira, SharePoint, and ServiceNow. Its connectors, indexes, and agents expand the governance scope, so their identities and authorization boundaries should be reviewed individually.

The Admin console's AI control center provides centralized AI security and compliance settings. Google's placement of these controls in Workspace administration rather than solely in Google Cloud reflects the separation between the productivity and cloud management planes.

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

## 2. Access boundaries: identity, settings, and data

Five aspects help distinguish the relevant boundaries.

First, Gemini is generally not a new permission principal. It uses the user's identity and authorization, so its access depends on what that user can access. The risk is that an existing read scope can be searched and summarized more efficiently.

Second, administrators control whether work or school accounts can use connected applications. Once enabled, users may invoke an application without a separate confirmation for each request. Personal Google accounts do not have the same Workspace administrative control.

Third, a conversation may retain information already retrieved before an administrator disables an application. Disabling access does not necessarily remove content already present in an existing conversation.

Fourth, product capabilities and limitations are documented by service. Examples include restrictions on particular Gmail content or actions, file types in Drive, and grade or announcement actions in Classroom. These details change over time and should be checked against current product documentation.

Fifth, privacy boundaries involve training, conversation visibility, and external sharing. Workspace prompts are customer data under the Cloud Data Processing Addendum and are not used to train models without the required customer permission. Sidebar conversation history is generally visible to the user rather than file collaborators. For externally shared documents, an out-of-domain banner may indicate that generated content could be visible to external collaborators; some features may not use internal Workspace context for such documents.

> Gemini generally follows the access available to users and connectors, but natural-language retrieval changes how content can be discovered and summarized. Review underlying permissions, connector settings, and audit coverage rather than evaluating only the model's identity.

## 3. Security risk A: indirect prompt injection

OWASP lists prompt injection as a significant risk for LLM applications (LLM01:2025). When content contains instruction-like text, systems need to distinguish user intent from untrusted data. In Workspace, relevant inputs may come from shared content:

- Inputs may originate from other people: shared documents, calendar invitations, and email bodies can be included in a prompt context.
- Retrieval may include shared content the user can access, so documents, mail, and calendar items are data sources to include in review.
- Outputs can take different forms, such as summaries, drafts, or suggested next steps, which may make untrusted content appear more authoritative.

Publicly disclosed GeminiJack research demonstrated an indirect prompt-injection risk in Gemini Enterprise retrieval: untrusted shared content could influence search results and their presentation. GeminiJack is a historical case that was publicly disclosed and patched; it should not be presented as currently exploitable. No remediation date is asserted here. The case remains useful for discussing a general design issue: input enters through the data plane, while some safeguards and governance controls sit in the identity and administration planes.

> Prompt injection can cause untrusted content to influence how a model interprets a request or produces a response. For retrieval-based AI, externally supplied content belongs in the input-risk review; actual impact depends on product capabilities, permissions, and safeguards.

## 4. Security risk B: memory and cross-session state

Some Gemini features support cross-session memory or custom instructions. Public research has shown that indirect prompt injection may affect long-term memory. The impact depends on product capabilities and user settings; memory should therefore be treated as state separate from a single conversation, with explicit management, review, and cleanup processes.

Conversation isolation does not necessarily cover every cross-session feature. Data retention and personalization should be checked against the relevant product privacy information and administrative settings.

For governance, determine who can create, view, and delete memory, and whether these records are covered by data-lifecycle processes for employee departures and role changes.

## 5. Security risk C: retrieval and content aggregation

Even without prompt injection, natural-language retrieval can make it easier for users to aggregate information they are already authorized to access.

Organizations should consider the scope of a query, who can see the conversation, and what happens to existing conversation data after an administrative change. Natural-language interactions may make information from multiple locations easier to combine, so establish an appropriate audit baseline.

Domain-wide delegation (DWD) can grant applications access to Workspace data. Its authorization records are in the Admin console and are separate from Google Cloud IAM. If such an identity is used by a search or analytics integration, review the DWD scopes, application credentials, data sources, and downstream services together.

Gemini Enterprise agents and connectors may access data through different identities, depending on product and configuration. Permission awareness does not replace review of privileged users, connector owners, data-source scope, and operation permissions.

> AI retrieval changes the interaction model for reading content, but does not make traditional permissions, audit, or DLP controls irrelevant. Review the subject, query scope, and conversation context using available product events, and confirm that required investigation data is retained.

## 6. Security risk D: the Workspace administration plane

API controls are part of Workspace application-access governance and should be reviewed separately from cloud IAM.

First, Google-owned applications may have different default trust settings from third-party applications. Administrators should verify Gemini-related access in the current console.

Second, API controls and Context-Aware Access (CAA) can jointly affect application access. Review application exemptions and service scope when assessing device and context policies.

Third, administrators who can change API controls or AI settings are high-impact identities. Limit assignment of the relevant roles, protect privileged sessions, and audit configuration changes. Cloud IAM is not a substitute for reviewing Workspace administration.

## 7. Governance checklist

The following checks help organize governance:

1. Review API controls and explicitly approve the Google applications that need access to restricted services.
2. Inventory all DWD client IDs and scopes, minimize them, and require approval for new domain-wide grants.
3. Include memory and custom instructions in periodic review and cleanup processes.
4. Review external sharing, out-of-domain collaborators, and the relevant sharing policies.
5. Define an audit baseline for AI retrieval, including available information about the user, scope, and conversation context.
6. Review API exemptions alongside CAA changes.
7. Protect Super Admin and Service Settings administrator sessions and audit Admin console changes.
8. Explain the differences between work and personal accounts, how conversation data is handled, and how to report unexpected AI access or output.

## Key points

1. Gemini has several product forms: connected apps, Workspace-integrated features, and Gemini Enterprise connectors and agents. Workspace administration governs important settings.
2. Gemini generally uses user or connector access; it can make existing authorized content easier to retrieve and summarize.
3. Workspace administrators control connected-app settings for work or school accounts; personal accounts have different controls.
4. Disabling an application does not necessarily remove data already present in an existing conversation.
5. Product capabilities and restrictions vary by service and should be checked against current documentation.
6. Privacy considerations include model training, conversation visibility, and external sharing; cross-session memory is a separate setting to review.
7. Indirect prompt injection is an input risk for retrieval-based AI. GeminiJack is a publicly disclosed and patched historical case, not evidence of current exploitability.
8. Cross-session memory and custom instructions need their own lifecycle and audit controls.
9. Retrieval and connectors can increase the efficiency of aggregating already-authorized content; review users, application identities, DWD scopes, and data sources.
10. Workspace API controls and Google Cloud IAM are separate management planes; audit their administrators and configuration changes.
11. AI retrieval audits should consider the user, scope, and conversation context available in the product logs.

## References

Google Workspace Help: Control Gemini App access to Workspace services — https://support.google.com/a/answer/15293691

Google Gemini Help: Gemini Apps connected apps (data access and feature boundaries) — https://support.google.com/gemini/answer/14959807

Google Workspace Help: Control which apps access Google Workspace data (API control levels) — https://support.google.com/a/answer/7281227

Google Workspace Help: Control API access with domain-wide delegation — https://support.google.com/a/answer/162106

Google Workspace Knowledge Center: Generative AI in Google Workspace Privacy Hub — https://knowledge.workspace.google.com/admin/generative-ai/generative-ai-in-google-workspace-privacy-hub

Google Workspace Knowledge Center: Explore the AI control center — https://knowledge.workspace.google.com/admin/generative-ai/explore-the-ai-control-center

Google Cloud documentation: What is Gemini Enterprise? — https://cloud.google.com/gemini-enterprise/docs/overview

Google Cloud documentation: Cloud Platform resource hierarchy (Super Admin and organization trust) — https://cloud.google.com/resource-manager/docs/cloud-platform-resource-hierarchy

OWASP GenAI: LLM01:2025 Prompt Injection — https://genai.owasp.org/llmrisk/llm01-prompt-injection/

Expert Insights: GeminiJack Flaw Shows How A Single Poisoned Workspace File Could Hijack Enterprise AI Searches (public research reporting) — https://expertinsights.com/news/geminijack-shows-how-a-poisoned-workspace-can-hijack-enterprise-ai-searches

Gigazine: An indirect prompt injection attack that hacks the long-term memory of Google's AI Gemini (public research reporting) — https://gigazine.net/gsc_news/en/20250214-prompt-injection-gemini-long-term-memory/
