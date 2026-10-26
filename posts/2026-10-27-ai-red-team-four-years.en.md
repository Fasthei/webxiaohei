---
topic: identity
category: Identity & Red Team
---

# Everyone Is a Red Teamer: Four Years of AI Red Teaming

*Collapsing barriers, dual loss of control, and the return of discipline*

ChatGPT launched on November 30, 2022. As of today—October 27, 2026—that was three years, ten months, and twenty-seven days ago.

I want to mark this point in time because it helps answer a question I have been avoiding: how far has AI security come? My answer is that, in less than four years, large-model security has covered parts of a decade to a decade and a half of traditional cybersecurity. Attack discovery, vulnerability fundamentals, lateral movement, supply-chain attacks, and zero trust—stages that took traditional security years to develop—have been compressed into a much steeper curve.

This process may look impossible to quantify, but part of it can be measured: speed can be measured; maturity cannot.

## I. Fifteen Years, Compressed: Speed Can Be Measured

Traditional security evolved organically: vulnerability research, attack chains, lateral movement, supply chains, and zero trust, with years and generations of accumulated experience between each stage. AI security has steepened that curve: prompt injection and jailbreaking (2023) → indirect prompt injection (2023) → Agent toolchain abuse (2024) → attacks at the MCP / A2A protocol layer and memory poisoning (2025) → supply-chain threats (slopsquatting, malicious MCP servers) and zero-trust permission models for Agents (2026). The “five stages” of traditional security have appeared in AI security in a compressed form, with close parallels between them.

The data supports the claim that this is happening quickly:

- **The CVE curve**: Around 18,000 CVEs were publicly disclosed worldwide in 2018, and vulnerabilities took an average of roughly two months to be exploited after disclosure. By 2025, the annual total was approaching 50,000, while the average vulnerability was already being exploited before public disclosure—leaving defenders on the wrong side of the clock ([ProjectDiscovery](https://projectdiscovery.io/blog/the-vulnerability-curve-bent-with-the-ai-curve)). Google Threat Intelligence has likewise confirmed that AI is changing the speed and types of vulnerability discovery and exploitation in practice ([Google GTIG](https://cloud.google.com/blog/topics/threat-intelligence/vulnerability-discovery-and-exploitation-trends-in-the-ai-era)).
- **The Agent attack surface**: In the reported distribution of attack vectors for agentic AI security incidents in 2025, prompt injection accounted for 43%, memory poisoning for 28%, tool abuse for 19%, and privilege escalation for 10%. Agentic incidents took an average of 23 days to detect, compared with 207 days for traditional incidents ([statistics](https://www.linkedin.com/posts/evan-benjamin-a405824_for-anyone-keeping-track-of-agentic-ai-activity-7411280212304236544-wbVQ)). Detection is faster because more people are watching, but the rate at which combinations multiply has increased even faster.
- **The organizational timeline**: Microsoft’s AI Red Team was established as early as 2018—four years before ChatGPT—and its methodology was published in 2023 ([Microsoft AI Red Team](https://www.microsoft.com/en-us/security/blog/2023/08/07/microsoft-ai-red-team-building-future-of-safer-ai/)). In January 2025, Microsoft published *[Lessons from Red Teaming 100 Generative AI Products](https://arxiv.org/abs/2501.07238)*, distilling red-team experience across 100 GenAI products into eight lessons. In July 2026, Microsoft stated in *[Rethinking security for the age of AI](https://blogs.microsoft.com/blog/2026/07/27/rethinking-security-for-the-age-of-ai/)* that “the physics of cybersecurity is changing”: autonomous systems can reason, adapt, and act continuously, while the cost of attacks is falling. This timeline reflects the industry as a whole.

The part that cannot be measured is maturity: detection coverage, incident response, accountability, and legal boundaries. These depend on organizations and people, and they have not been compressed into the same four years. Attack techniques have accelerated; defensive systems have lagged behind.

## II. Barriers Collapse: Everyone Is a Red Teamer

Three years ago, I confidently said AI would not replace red teams for the next decade. Looking back, that was a profoundly poor judgment. I was wrong because I treated red teaming as a “body of knowledge”—and knowledge is precisely what AI is best at compressing and reproducing.

Today, anyone who can build an Agent can become a red teamer: AI has absorbed much of traditional red teaming and can even generalize from it. Give it a target, and it can connect the full chain—from attack-surface enumeration and payload generation to evasion and lateral movement—into an automated workflow. Quietly, I admit that for a while I thought I might lose my job.

This is not a prediction; it is already happening. From late September to early October this year, at least nine banks in South Korea were attacked. Seven financial institutions confirmed data breaches, exposing information on about 68,000 customers: around 25,000 at Shinhan Bank, 40,000 at Yegaram Savings Bank, and 119 at KB Kookmin Bank ([Yonhap News](https://cn.yna.co.kr/view/ACK20261004000800881)). CrowdStrike reported that the attackers used an AI-driven penetration-testing tool called ARTEX ([CrowdStrike](https://www.crowdstrike.com/en-us/blog/unknown-threat-actor-uses-artex-to-target-south-korean-finance/)). After the tool was linked to multiple attacks on South Korean banks, its developers acknowledged that it had been abused by “malicious actors” and discontinued its open-source release ([RFI](https://www.rfi.fr/cn/%E4%B8%AD%E5%9B%BD/20261009-%E9%9F%A9%E5%9B%BD%E5%A4%9A%E5%AE%B6%E9%93%B6%E8%A1%8C%E9%81%AD%E9%BB%91%E5%AE%A2%E6%94%BB%E5%87%BB%E5%90%8E-%E4%B8%80%E6%AC%BE%E4%B8%AD%E5%9B%BDai%E5%B7%A5%E5%85%B7)). The attackers also used AI tools such as Claude Code. The suspect was reportedly a 26-year-old man based in China ([The New York Times Chinese](https://cn.nytimes.com/asia-pacific/20261009/south-korea-bank-hack-china-us-ai/)).

ARTEX is a stark illustration of “everyone is a red teamer”: someone who did not need to write exploits themselves used AI to breach parts of South Korea’s financial ecosystem. The banks protected their core systems, but the surrounding ecosystem was compromised. That is the reality everyone must confront as AI drives the cost of attacks down.

At the same time, research from CSA indicates that autonomous AI red teaming has moved from research demonstrations to commercial products—systems that can independently discover and validate exploitable vulnerabilities in production environments, without an operator directing every step ([CSA](https://labs.cloudsecurityalliance.org/research/csa-research-note-ai-autonomous-red-team-agent-findings-2026/)). In four years, red teaming has gone from a “craft” to a utility.

## III. The Shape of Collaboration: From Teams to Agents

One of my strongest impressions of AI red teaming is that collaboration will increasingly center on Agents rather than teams. The differentiator will not be how ten people coordinate, but how well you design offensive work in an AI context and combine it with the judgment built through years of security practice—where trust boundaries lie and where authorization can fail.

I am also clear-eyed about this: the window may last only a few years. AI is gradually replacing parts of traditional security experience; people cannot compete with machines on speed. As AI grows more capable, people need to move upstream: defining objectives, defining harm, and defining stop conditions, rather than competing over enumeration speed.

## IV. Dual Loss of Control

The exposure surface of AI business systems is broader than that of the traditional web era: models, RAG, Agents, tools, memory, and orchestration protocols are all new surfaces. It is also becoming harder to say that vulnerabilities remain within the bounds of what people can control. Traditional software vulnerabilities are enumerable points; vulnerabilities in AI systems emerge from combinations across the surface. Both the growth in the CVE database and the issues exposed in AWS AgentCore point in the same troubling direction.

The AWS AgentCore case is illustrative: Unit 42 found that AgentCore Harness’s default tool configuration could allow a single indirect prompt injection to escalate into plaintext credential theft—the built-in tool ran as root and shared a memory space with the process that decrypted vault credentials ([CSA / Unit 42](https://labs.cloudsecurityalliance.org/research/csa-research-note-aws-agentcore-credential-exfiltration-2026/)). At the SDK layer, flaws were also found that could let an attacker execute commands inside an AI sandbox and access AWS credentials ([Infosecurity Magazine](https://www.infosecurity-magazine.com/news/aws-agentcore-sdk-flaws-ai/)). Around the same time, agentjacking used MCP injection to hijack an AI coding Agent integrated with Sentry ([Tenet Security / CSA](https://labs.cloudsecurityalliance.org/research/csa-research-note-agentjacking-mcp-sentry-injection-20260612/)).

People have made mistakes for millennia; that has not changed. In the past, machine failures were more controllable: boundaries were clear and consequences more predictable. Now, a machine’s “mistake” is itself part of the attack surface. When two uncontrollable factors—people and machines—combine, someone may write a careless prompt and an Agent may execute it without supervision, turning it into supply-chain poisoning. No one in the chain may have intended harm, yet the consequences are real. I find it difficult to imagine how to estimate that blast radius.

## V. A Rule: Red-Team AI Must Be Kept in a Cage

For now, the first priority in AI red teaming is not capability; it is discipline.

There is little doubt about AI’s breadth of knowledge. For that very reason, AI used in red teaming must be controlled, monitored, and constrained; it cannot be treated casually. If the security rules for a conventional AI application number ten, the rules for AI red teaming need to be “10+1.” The extra rule governs the weapon itself: red-team AI may access undisclosed vulnerabilities, client network topologies, and real credentials. Every tool call it makes can have an order of magnitude more destructive potential than one from an ordinary application.

Second, experience must be turned into an asset. Every engagement’s lessons should be collected deliberately: how prompts were written, how the chain was assembled, which layer stopped it, and how it was bypassed. Whether used for reuse or for retrospective analysis, these lessons are among the most valuable assets. AI models will change and hallucinate, but accumulated attack corpora and judgment frameworks will endure. Microsoft’s ability to distill a book’s worth of lessons from 100 products rests on precisely this kind of institutionalization.

Third, weapon management. In the context of AI, an AI red team’s arsenal really is an arsenal: prompts, jailbreak templates, tools, payloads, and Agent orchestration. It must be protected from leaks—a red-team prompt leaking is equivalent to a weapons leak—and from abuse. ARTEX went from a red-team tool to a criminal tool with only an open-source repository in between. Tools have no position; the people who manage them must.

## Conclusion

Looking back at myself three years ago, my claim that “AI would not replace red teams for ten years” was wrong because I conflated “people” with “knowledge.” Knowledge can be compressed, tools democratized, and barriers collapsed. But the ability to define harm, the authority to set boundaries, and the discipline to know when to stop still belong to people—for now.

As AI’s wheels roll forward, the red-team profession will not disappear, but it will be rewritten: from a craft practiced by a small group of experts, to leverage available to everyone, and then into a weapon that requires discipline. The closer we get to losing control, the more important it is to remember: the key to the armory must stay locked in the cage.
