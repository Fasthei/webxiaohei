---
title: Client Embedding Inversion Test: Access Path and AI Judgment Errors
date: 2026-11-09
slug: embedding-inversion-environment-and-ai-errors
topic: ai
category: AI Security
summary: A sanitized account of an authorized client test, from separating a decoy RAG stack from the real data plane to tracing cross-host trust and examining the evidence behind AI judgment errors.
---

# Client Embedding Inversion Test: Access Path and AI Judgment Errors

An authorized security test for a real client sought to locate a retrieval system holding sensitive documents, obtain an embedding, and determine whether a short text could be recovered from that vector. The test produced a candidate confirmed through independent validation. Two lines of analysis matter: how access to the environment developed, and why automated analysis repeatedly made incorrect judgments at critical points.

Client names, domains, addresses, accounts, passwords, hashes, private keys, raw vectors, and directly reusable commands are withheld. The service relationships, decision evidence, failed paths, and validation methods remain. Sanitization should not remove the causal chain.

## Access path: finding the real data plane

### Why the apparent RAG stack misled the investigation

The test scope included a Windows domain controller, a Windows member server, and a Linux host. The member server exposed a research portal, Qdrant, and MongoDB. Portal copy described a complete retrieval-augmented generation stack, and an activity area claimed that embeddings had been updated. The interface and open ports made the member server look like the target.

The data layer contradicted that account. Qdrant had no collections and no writes matching the portal story in its telemetry. MongoDB held only system databases. References to Qdrant and MongoDB in the portal program appeared in descriptive copy, with no evidence of backend calls. The displayed document count had no supporting data. A single empty collection could reflect permissions or timing, but telemetry, program references, and database contents together justified deprioritizing this stack.

The decisive work in this stage was falsification. A portal can make the existence of a system look convincing. The actual questions are where data is stored, whether requests reach a backend, and whether claimed activity has a corresponding event in storage or telemetry.

### Two vantage points ruled out a network assumption

From the external test host, the Linux machine mainly exposed SSH; no vector service appeared. A second view from the authorized member-server foothold checked whether a RAG service was available only to internal hosts. Neither view found an externally listening RAG service. DNS also contained an old record pointing to a different subnet, but connectivity and port checks did not support a live target there.

These negative results reduced the search space without proving that the Linux host had no vector service. A service could listen only on loopback. The distinction between “not visible in a scan” and “nonexistent” was essential to the next step.

### Deployment residue and credential reuse crossed privilege boundaries

The starting point was a low-privilege identity lead from an earlier authorized stage. Initial attempts around the portal login and common services made little progress. The turning point was deployment residue on the member server. Initialization media remained readable through retained volume information after an apparent unmount, and the metadata exposed administrative credentials. Local administrative access changed what could be seen, so locations that had been inaccessible before needed another inspection.

Local and domain administrative credentials were then found to share an origin, extending the effect of local credential exposure beyond one machine. No particular tool created that weakness. The imaging and initialization process had failed to establish separate secrets for separate identities. Domain-level access broadened the investigation, but a valid credential still did not imply permission for every remote logon method.

The route into the Linux host reflected another trust reuse: an SSH private key on the member server was accepted by the Linux machine. Considerable time had gone into password authentication, while the viable path used a public key. Rechecking files after the privilege change exposed the cross-host relationship. Key material, account mappings, and exact paths are omitted because those details are unnecessary to the security conclusion.

### Loopback service and embedding inversion

Once access to the Linux host was established, the real data plane became clear. Weaviate listened on loopback, which explained its absence from external port scans. Loopback binding reduced network exposure, but the lack of independent database authentication mattered as soon as host access existed. The schema contained several data classes, with the sensitive target in a password-reset policy object. Plaintext properties did not reveal the desired value, while the embedding remained exportable.

Vector dimensions and environment evidence narrowed the possible encoder; dimensions alone could not establish a model identity. Inversion used a known candidate list and multiple templates matching the password-reset context to rank candidates. Agreement among independent templates supplied a strong statistical signal, but statistical agreement alone was not proof. Independent validation confirmed the final result. The candidate and raw vector are withheld.

Most of the effort from initial access to the final result went into identifying the asset, crossing privilege boundaries, and selecting the right authentication method. Once the vector, encoder range, and candidate space were known, inversion converged quickly. Omitting a plaintext property does not eliminate disclosure risk when an embedding retains enough semantics for recovery within a constrained candidate space.

## AI errors: examine the evidence, not just the “hallucination” label

The automation errors were not random slips of wording. They appeared where security fundamentals were poorly understood and tool output was not checked against evidence from the target.

1. **Authentication was mistaken for remote execution rights.** A credential check produced a positive marker and a remote desktop connection initialized a display, leading to a login error screen being interpreted as a command session. Remote logon rights were absent. An open port, a valid identity, interactive logon rights, and command execution are four different claims; session duration cannot establish execution.
2. **An “executed” message was treated as an execution result.** After a remote management tool printed a success message, the expected file was absent on the target and a direct call returned access denied. The problem was not an insufficiently elaborate output channel. Target-side state change had never been established.
3. **Truncated output was treated as complete enumeration.** The terminal buffer discarded the later part of a service list, and the visible text was mistaken for the complete result. Critical enumeration needs a count, retained full output, and readback. Reaching the bottom of a screen does not prove complete collection.
4. **Semantics changed across multiple shells.** Complex filters crossed a terminal, a command interpreter, and PowerShell; quotation marks, variables, and pipe characters changed meaning. Empty results sometimes came from a broken command rather than an absent target. The arguments received at each layer need verification.
5. **A non-interactive authentication option was misused.** An SSH file transfer disabled interaction while still expecting password authentication, causing failure. Misunderstanding the protocol option created an artificial access obstacle.
6. **Password authentication was treated as the only route.** Password attempts continued while public-key authentication and host-side key relationships received insufficient attention. The server's advertised authentication methods should have been considered in parallel rather than exhausting one path first.
7. **Restricted enumeration was not repeated after privilege increased.** A directory inaccessible at low privilege was treated as if no file existed. A later traversal script swallowed errors, producing a second false negative. Access denied, traversal failure, and genuine absence must be recorded separately.
8. **DNS investigation ended too early.** A refused zone transfer, timed-out reverse lookups, and one failed directory query established only that those methods failed. They did not prove that relevant records were absent. “Not fully checked” must remain explicit rather than being written as a factual exclusion.
9. **An unequal sample was used to validate inversion.** A known-text control differed from the target in template conditions, and the control returned an incorrect candidate. That failure exposed a design flaw in the control; by itself, it could not invalidate the real target candidate. A useful control changes only the plaintext under test wherever possible.
10. **A saved message was treated as a completed deliverable.** An initial report printed a success message, but the file was missing on readback. Existence, readability, and content completeness are the delivery evidence. Service rebuilds and network instability during the test also cannot be attributed to test actions merely because of temporal proximity.

The root cause was insufficient knowledge of the relevant domain: Windows logon rights versus credential validity, SSH authentication options, shell quoting layers, log and buffer semantics, and controlled experimental design. Knowledge gaps produced incorrect assumptions first; weak evidence gates then allowed those assumptions to drive more work. More tool calls alone would have amplified the error.

## Changes for defense and execution

- **Remove deployment residue.** Verify that initialization media, metadata, and temporary credentials cannot be read after handoff; the disappearance of a drive letter is insufficient.
- **Separate secrets by identity.** Local and domain administrators, accounts on different hosts, and SSH private keys need independent generation, rotation, and scoped use.
- **Protect the vector data plane.** Loopback binding does not replace authentication and least privilege. Sensitive documents need classification before entering retrieval; removing a plaintext property does not sanitize an embedding.
- **Set evidence gates for automation.** Record tool messages, target-side state, and independent validation separately. Repeat checks previously blocked by insufficient privilege after access changes. Track environment incidents on a separate timeline, without inferring causation from timing alone.

The central lesson from this client test is more precise than “AI makes mistakes.” With insufficient domain knowledge, an automated workflow can merge authentication, authorization, reachability, execution, and validation into one vague notion of success. Knowledge and staged evidence checks are both necessary for a credible access path and a credible final conclusion.
