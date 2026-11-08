---
title: From a Client Network to Embedding Inversion: The Full Engagement and AI Errors
date: 2026-11-09
slug: embedding-inversion-environment-and-ai-errors
topic: ai
category: AI Security
summary: A complete sanitized account of an authorized client engagement, from initial access, a misleading RAG stack, and deployment remnants to local and domain privileges, SSH identity matching, vector export, candidate recovery, and ten types of AI error.
---

# From a Client Network to Embedding Inversion: The Full Engagement and AI Errors

This authorized engagement for a real client aimed to identify the retrieval system holding sensitive documents, obtain the relevant embeddings, and determine whether sensitive information could be recovered from them. The final candidate passed independent validation, but reaching that result involved far more than exporting a vector and running an inversion script. Most of the effort went into identifying the real assets, understanding Windows privileges, authenticating across hosts, and interpreting failed attempts.

This account reconstructs the full process according to the dependencies supported by evidence. Each phase explains the available access, checks performed, observations, failed branches, and justification for the next step. The later sections examine errors during AI-assisted execution: insufficient foundational knowledge first produced incorrect judgments, and missing outcome checks allowed those judgments to drive subsequent actions.

Client names, network ranges, accounts, credentials, keys, document names, and the final sensitive value have been replaced. DC-A, WIN-A, and LINUX-A represent the domain controller, Windows member server, and Linux host; SERVICE_USER, LOCAL_ADMIN_A, and DOMAIN_ADMIN are role placeholders. Code includes sanitized command excerpts and examples prepared to explain the checks. Examples such as array readback, checksum comparison, and exception handling do not imply that every step appeared verbatim in the original record. Angle brackets identify placeholders. Output blocks contain sanitized excerpts of key fields, with identity information removed from the original logs.

## 1. Initial Conditions and Task Breakdown

Three hosts were initially visible. A set of low-privilege credentials from an earlier authorized test provided the starting point. No directly usable login credentials were available for the Linux host. The objective pointed toward RAG and embeddings without identifying the machine that actually held the data. A candidate list of approximately ten thousand entries was also available for later validation.

The task was split into five independently verifiable questions: where the real retrieval system was; which identity could access it; whether sensitive content remained in plaintext properties; whether the encoder and candidate space were sufficiently clear if only vectors remained; and how a recovered candidate would be confirmed. This sequence mattered. Without a verified data source, even a carefully chosen inversion method would have nothing relevant to analyze.

| Host | Initial observation | Question to resolve |
| --- | --- | --- |
| DC-A | Directory services, file sharing, Remote Desktop, and standard domain services | What could the known identity read, and what could it not execute? |
| WIN-A | Research portal, Qdrant, MongoDB, and Windows management interfaces | Did the portal connect to real data, and was there a verifiable path to local privileges? |
| LINUX-A | Primarily SSH visible externally | Did it host local-only services, and which authentication methods were usable? |

Initial network discovery was misleading: a broad host-discovery scan marked many addresses as alive, while subsequent port checks found no corresponding host services. The initial analysis attributed this to gateway responses. The defensible conclusion is narrower: an alive marker did not establish the number of real assets, and the specific response mechanism remained unproven without packet captures.

~~~bash
ip route
nmap -Pn -sT -p 22,53,88,135,139,389,445,464,636,3389,5985,5986 <HOST>
~~~

The relevant question was whether a given address returned stable, interpretable service responses. Connection refusal, timeout, authentication failure, and application errors occur at different layers and cannot all be reduced to a single reachable/unreachable label.

## 2. Establish Identity Boundaries Before Assuming Remote Execution

The known identity had different capabilities across hosts and protocols. File sharing and Remote Desktop worked on WIN-A. Domain shares and some directory queries were readable on DC-A, but administrative shares, WMI, and remote management interfaces rejected access. SSH did not automatically accept credentials simply because they worked on Windows.

| Validation surface | Observation | Supported conclusion |
| --- | --- | --- |
| WIN-A SMB and RDP | Authentication and relevant resource access succeeded | An entry point to the member server was established |
| DC-A ordinary domain shares | Readable | Limited file-reading capability existed |
| DC-A administrative shares | Access denied | Administrative privileges were not established |
| DC-A LDAP | Some read-only queries succeeded | Directory information could be collected |
| DC-A RDP | A positive probe marker, but insufficient login rights in the actual session | Valid credentials and remote logon rights had to be distinguished |
| WinRM and WMI | Rejected the initial identity | No corresponding execution channel was available |
| SSH | Rejected access | Account, key, authentication method, and authorization configuration required separate checks |

~~~powershell
whoami
whoami /groups
whoami /priv
net localgroup Administrators
net localgroup "Remote Desktop Users"
net localgroup "OpenSSH Users"
~~~

These findings should have bounded subsequent actions, but a major misinterpretation followed. The DC-A RDP probe produced a positive marker, and the client log reported framebuffer initialization, so the connection was treated as a command session. Its duration of several dozen seconds was then interpreted as a waiting command reaching completion.

The login screen supplied the decisive contradiction:

~~~text
To sign in remotely you need the right to sign in
through Remote Desktop Services.
~~~

The visible connection had kept a login-error screen open until timeout. There was no evidence of a user session capable of executing commands. Named-pipe, callback-script, and output-channel plans built on that assumption therefore lacked a prerequisite. The analysis had to return to the verified boundary: the initial identity primarily had read-only access to the domain controller, and remote execution had not been established.

This was more than a misread log line. The knowledge gap was a failure to distinguish four states: network reachability, identity authentication, logon authorization, and target execution. The first two do not establish the latter two.

## 3. The Research Portal Looked Like RAG, but the Data Layer Did Not Support It

The WIN-A portal had research listings, a dashboard, a login page, and an activity feed. Its introduction described Qdrant-based embedding retrieval and MongoDB metadata storage, while the activity feed included embedding-update entries. Together, these interface elements made it easy to conclude that the target had been found.

The first verification pass used Qdrant's read-only interfaces:

~~~bash
curl -sS http://<WIN_A>:6333/collections
curl -sS http://<WIN_A>:6333/telemetry
~~~

The collection list was empty, and telemetry did not show writes corresponding to the portal's claimed data activity. Query records mainly matched reads initiated during testing. This alone did not exclude permission issues, loading delays, or the wrong instance, so the portal program and metadata service were examined next.

~~~text
Qdrant:
  collections = []
  No write evidence corresponding to portal activity

MongoDB:
  admin
  config
  local

Portal:
  Qdrant / MongoDB references appeared in descriptive copy
  No evidence of corresponding backend calls was found
~~~

The program's visible templates largely matched the page routes, and database-related strings appeared in descriptive content. MongoDB showed only system databases, without the research material advertised by the portal. Searches for common vector and model-data file extensions on the host also failed to establish the presence of a real data pipeline.

The combined evidence was stronger than a page claiming to use RAG: empty vector collections, missing business metadata, and no observed corresponding program calls all pointed toward the same issue. The conclusion narrowed to this portal being an ineffective entry point to the target data. It did not prove that no external backend had ever existed, and a string scan did not constitute complete reverse engineering.

Portal authentication was another unsuccessful branch. Several known identities and candidate passwords produced the same error, without useful differences in form responses. Expanding those attempts could not resolve the missing backend data, so the branch was deprioritized. Attention shifted to host internals and the Linux machine.

### Why the Internal Network View Also Needed Checking

Seeing only SSH externally on LINUX-A did not rule out services restricted to internal sources. From the existing WIN-A access, key ports on the domain controller and Linux host were therefore checked again to compare the external and internal views.

~~~powershell
Test-NetConnection <LINUX_A> -Port 22
Test-NetConnection <LINUX_A> -Port <CANDIDATE_PORT>
Test-NetConnection <DC_A> -Port <CANDIDATE_PORT>
~~~

Neither vantage point revealed a directly accessible, genuine RAG interface. This ruled out several source-address hypotheses but did not establish that the service was absent. It could still listen only on the Linux loopback interface, a hypothesis that required access inside the host to test.

DNS also contained records pointing to an older network range. Zone transfers were refused, and reverse lookups and some directory queries failed. The older addresses were not verified through actual services and could not be treated as additional targets merely because DNS returned them. The stale-record interpretation had supporting evidence, but DNS enumeration remained incomplete and its gaps needed to remain explicit.

## 4. Negative Results During Windows Enumeration

After low-privilege access to WIN-A was established, winPEAS twice failed to produce a useful report. The output files were small and contained errors indicating that the executable was missing or could not run. The notes showed endpoint protection interfering with file delivery. This established a delivery or execution failure, not the absence of privilege-escalation opportunities.

Native system state was then checked individually. Each check tested a specific hypothesis, and failed results were retained to avoid repeating the same attempts under unchanged conditions.

~~~powershell
whoami /priv
sc.exe query state= all
schtasks.exe /query /fo LIST /v
cmdkey.exe /list
Get-Volume
~~~

| Check | Recorded result | Decision |
| --- | --- | --- |
| Token privileges | The initial identity lacked relevant impersonation privileges | Routes requiring those privileges were not treated as defaults |
| Installer policies | No enabled combination supporting elevated installation was found | This configuration route was not pursued |
| Service permissions and file ACLs | No low-privilege writable entry point was found among the services checked | Service replacement or path hijacking was not established |
| Cached credentials | Common credential stores produced no useful lead | Attention shifted to deployment and initialization files |
| Scheduled tasks and startup entries | No startup entry corresponding to the target process was found | The launch source remained unresolved |
| User profiles | Some administrative profiles were unreadable | The permission limit was recorded for rechecking after privilege changes |
| Installation and initialization remnants | Historical passwords and configuration-media clues appeared | Current validity and cleanup state required further examination |

The initial analysis inferred that the host platform must have launched a process because common startup locations had no matching entry. That exceeded the evidence. Missing scheduled-task, service, or startup entries only meant those locations did not explain the launch. Without the complete parent-process chain and host logs, the launcher could not be identified conclusively.

Vulnerability-database searches also failed to produce a direct entry point. Results concerned different versions, operating systems, virtualization prerequisites, or denial of service only. A matching product name did not establish applicability. Inapplicable vulnerabilities were not used, and the absence of a ready-made exploit was not treated as proof that the software was secure.

### The Terminal and Scripts Created False Negatives

Several enumeration failures originated in the execution channel itself. Complex PowerShell expressions crossed the terminal, cmd, and PowerShell, changing the meaning of quotes, variables, and pipes. The result looked like empty output or syntax errors. A service listing was also truncated by the terminal buffer, making an incomplete listing appear complete.

The correction was to put complex logic in a script, invoke it explicitly on the target, and save standard output together with errors. The following illustrates that handling pattern rather than reproducing the complete original output:

~~~powershell
powershell.exe -NoProfile -File .\inventory.ps1 *> .\inventory.log
Get-Item .\inventory.log | Select-Object Length, LastWriteTime
Get-Content .\inventory.log
~~~

Directory traversal also needed to preserve failed paths. Continuing after an exception without recording it merged permission denial, unreadable paths, and absent files into the same zero-result outcome.

~~~powershell
try {
    Get-ChildItem -LiteralPath $CandidatePath -Force -ErrorAction Stop
}
catch {
    Write-Warning ("Enumeration failed: " + $CandidatePath)
    Write-Warning $_.Exception.Message
}
~~~

These errors directly affected later judgments. If output collection was incomplete, any conclusion eliminating a route had to be suspended.

### What Native Enumeration Actually Covered

Service inspection covered execution identities, binary paths, service DACLs, and directory ACLs as well as names. MongoDB ran as NetworkService with a quoted binary path. Checked application directories granted ordinary users read and execute access, with no write access allowing direct executable replacement. The initial token contained only limited ordinary privileges, and SeImpersonatePrivilege was not observed, so routes requiring it were not pursued.

~~~powershell
sc.exe qc MongoDB
sc.exe sdshow MongoDB
sc.exe sdshow sshd
icacls "C:\<APPLICATION_DIRECTORY>"
reg.exe query HKLM\SOFTWARE\Policies\Microsoft\Windows\Installer /v AlwaysInstallElevated
reg.exe query HKCU\SOFTWARE\Policies\Microsoft\Windows\Installer /v AlwaysInstallElevated
~~~

Launch-source checks covered scheduled tasks, Run/RunOnce, startup directories, Winlogon, Active Setup, and permanent WMI event subscriptions. The task list did not match the target process name, and other checks also failed to explain its origin. The launch source remained unresolved; a longer checklist did not turn a hypothesis into fact.

Credential checks covered Credential Manager, user Credentials/Protect directories, browser profiles, and Windows diagnostic logs. Some locations were empty, while others yielded nothing usable. The VSS query returned insufficient privileges and remained incomplete. Among installation remnants, an answer file under Panther provided the old-password lead, while another Sysprep answer file mainly held device configuration and supplied no new credentials. These distinct failure reasons narrowed the next step to initialization rather than indiscriminate password searching.

Vulnerability searches also proceeded product by product. Older MongoDB entries, QEMU Guest Agent denial-of-service entries, and Windows privilege-escalation entries requiring particular virtualization interfaces did not match the host's version and runtime prerequisites. No directly applicable known vulnerability emerged, so configuration remnants and identity relationships took priority.

## 5. From a Historical Password to Readable Configuration Media

An installation answer file first exposed an old password. It was initially treated as a current administrative credential, but validation against different identity scopes failed. Later credential records also placed it in a historical state. Finding plaintext alone therefore did not establish current usability.

The failed lead still mattered. Its contents pointed to automated initialization and password rotation, shifting the question from which other passwords might exist to how the initialization system obtained and cleaned up the new password. A cleanup script claimed to unmount configuration media, yet the corresponding media remained visible in volume information.

The initialization component was cloudbase-init, and the configuration media carried typical configdrive identifiers. Inspection connected the installation answer file, initialization script, and volume state: the answer file held an old value, the initialization process set another value, and the configuration media might still retain its input metadata. Failure of the old password did not end the lead; it indicated a need to trace the source after rotation.

~~~powershell
Get-Volume |
    Select-Object DriveLetter, FileSystemLabel, DriveType, HealthStatus, Size

Get-CimInstance Win32_Volume |
    Select-Object DeviceID, DriveLetter, Label
~~~

The key finding was not a drive letter. It was the distinction between removing a drive letter and making data unreadable. In this instance, an ordinary dir invocation failed to handle the volume GUID path correctly. PowerShell Get-ChildItem -LiteralPath then listed the initialization content. The problem concerned path passing and interpretation; the first failed listing did not establish that the volume was unreadable. Sanitized path and metadata excerpts follow:

~~~text
\\?\Volume{REDACTED-VOLUME-ID}\openstack\latest\meta_data.json

{
  "machine_name": "<WIN_A>",
  "admin_pass": "<REDACTED_BOOTSTRAP_SECRET>"
}
~~~

This established that an initialization secret remained readable. It did not establish that any particular unmount option performed secure erasure. Cleanup needed to cover the media, backend attachment, and secret rotation, with actual readability used to verify the result.

The cleanup logic used mountvol /D primarily to remove a mount point. Continued readability through the volume GUID path was the key evidence in this instance. Simply replacing that command with another unmount operation would not establish that the metadata had been destroyed. This distinction determined whether remediation actually blocked the same access path.

### The Password Was Correct, but Account State Blocked Login

The residual secret did not immediately unlock administrative shares. Validation against the local administrative account returned a specific status:

~~~text
STATUS_PASSWORD_MUST_CHANGE
0xc0000224
~~~

This differed from an incorrect password. Several remote-login and password-change attempts were restricted. Changing the supplied format or using a hash representation of the same password did not resolve the account state. Continuing to treat the problem as password encoding would therefore have pursued the wrong cause.

The successful route adjusted RDP authentication negotiation. The earlier NLA login returned ERRCONNECT_PASSWORD_MUST_CHANGE without reaching an interface where the change could be completed. Using the TLS connection mode supported by this instance reached the interactive forced-password-change flow. After the change, the new local administrative identity was verified. This records the method that worked in this instance; earlier failures through several protocols did not establish that every protocol was impossible or that every environment had only one solution.

The checks concerned observable target state: the new credentials authenticated, administrative shares became accessible, and the token and account relationships matched expectations. Only then could a residual secret be described as confirmed local administrative access.

This identity was LOCAL_ADMIN_A. The built-in administrator credentials obtained in the next phase belonged to a different identity. Combining the two would create an apparent contradiction in which the same password had both changed and remained unchanged.

## 6. How Local Privileges Connected to Domain Privileges

After local administrative access was established, standard remote credential auditing was attempted first. Tool output stopped at local credential reading, and the exit status did not clearly report an error, but the expected result files were absent. A second attempt also produced no useful artifacts. The correct result was that credential material had not been obtained, regardless of a zero exit code.

Investigation continued through an authorized local execution channel. Different channels had different tokens, integrity levels, and registry access: one returned access denied for a protected location, while another attempt to read temporary results returned file not found. UAC, endpoint protection, and timing were considered possible explanations, but not every explanation was independently verified, so observations had to remain distinct from possible causes.

mimikatz was used to examine different credential sources. File upload first encountered two interface errors: SMBConnection.putFile required a callable read callback, and passing a bytes object failed; another client's put arguments were interpreted as one path, so the destination-naming syntax did not match that version. Execution began only after correcting the calls and verifying the remote file's existence and matching length. Successful upload, program execution, and credential recovery were three separate checkpoints.

The WMI channel returned 0x00000005 when reading SECURITY; the scheduled-task channel initially returned STATUS_OBJECT_NAME_NOT_FOUND when reading temporary output. An invocation that collected standard output completely finally produced analyzable results. Token state, protection state, and output collection all changed during the recorded attempts, so eventual success could not identify a single cause for the earlier failures.

~~~text
privilege::debug
  Reported successful privilege enablement

sekurlsa::logonpasswords
  Logon-session reading failed

lsadump::sam
  Returned local account material

lsadump::secrets
  Returned some LSA secrets
~~~

Local account credential material and some local secrets were eventually obtained. LSASS memory extraction failed, but separate reads of local account storage had succeeded. Credential extraction was not a single action with only a binary success or failure outcome.

~~~text
LOCAL_ADMIN_A:
  Current credential state matched the preceding password change

BUILTIN_LOCAL_ADMIN:
  Verifiable local account credential material was obtained

Historical secret:
  Corresponded to the old password in the installation file

LSASS memory extraction:
  No successful result was obtained
~~~

Validation then proceeded identity by identity, avoiding the assumption that any local hash was a domain credential. The decisive finding was that material from the local built-in administrator authenticated as the domain administrator. Other candidate combinations did not succeed in the same way.

This established at least one effective instance of credential reuse across identities. Identical hashes alone did not imply identical authorization. Authentication at the domain endpoint and subsequent privilege verification established that the impact extended beyond the local host.

Directory credential auditing within the authorized scope subsequently obtained domain-account material and cross-checked the identity relationships. The sanitized command preserves the tool and parameter relationships; the target, account, and hash are not disclosed:

~~~bash
impacket-secretsdump \
  -just-dc \
  -hashes :<REDACTED_NT_HASH> \
  '<DOMAIN>/<DOMAIN_ADMIN>@<DC_A>' \
  -outputfile <AUTHORIZED_OUTPUT_PREFIX>
~~~

Result files were stored by purpose and checked for existence, expected record types, and consistency of material for the same identity across sources. These files and all actual credentials are excluded from the public article.

The domain export produced files for NTLM material, Kerberos keys, and other account records. Local machine-account material was also cross-checked against the corresponding domain record. An initial invocation encountered Network unreachable and completed only after network recovery and retry. Network failure could not establish invalid credentials.

Historical secrets in the local output matched the old value in the installation answer file, while LOCAL_ADMIN_A's current and historical material corresponded to the states after and before the password change. These relationships explained why secrets from different stages appeared on the same machine. A template or deployment process might have caused reuse, but without build-pipeline evidence the specific provisioning process remained unconfirmed.

The available wordlist was later used to check some domain-password candidates without a match. That showed only that the tested candidates did not match, not that the password was unrecoverable. More importantly, domain privileges did not automatically provide SSH access to LINUX-A. Windows domain identities and Linux account and authentication configuration required separate validation.

## 7. Kerberos, Clocks, and Unproductive Service Leads

Other domain-side branches included Kerberos, service principals, accounts not requiring preauthentication, and managed secrets. Clock-skew errors appeared, while clock correction interacted with local time synchronization and VPN stability.

~~~text
KRB_AP_ERR_SKEW
KDC_ERR_ETYPE_NOSUPP
Network unreachable
~~~

These errors concerned different problems: clock tolerance, encryption-type negotiation, and network routing. Treating them all as Kerberos failure encouraged authentication-parameter changes even after the network path was down. After adjusting time, the tunnel and target reachability needed checking first, then absolute time, and finally authentication negotiation.

~~~bash
date -u
systemctl is-active systemd-timesyncd chrony ntp
ip route
~~~

The initial notes directly subtracted times displayed in different time zones, exaggerating the apparent offset. A valid comparison required a common time zone or timestamps. VPN disruption after clock correction was an observed sequence; explaining the handshake failure required VPN logs rather than timing alone.

Service-principal enumeration also revealed a database-service marker, but the target had no corresponding listener, service, or running instance. The marker did not establish a new service entry point. The AS-REP query returned no qualifying account, and LAPS and gMSA queries obtained no corresponding objects. These were negative results from the checks performed, not proof that the domain had no other weaknesses.

Domain-authentication attempts against LINUX-A first encountered client capability and option problems: one client path could not use the required GSSAPI functionality, while another rejected the relevant options. Neither local failure established whether the server accepted domain authentication. After switching to a client capable of initiating that method, the server response advertised only public-key and password authentication:

~~~text
allowed authentication methods:
  publickey
  password
~~~

The current SSH endpoint therefore did not support the attempted GSSAPI route. Its response did not establish that Linux could not be joined to a domain. It only justified ending further attempts with that mismatched method at this endpoint.

## 8. Linux Access Required Both the Key and the Correct Identity

LINUX-A was the hardest stage to advance. Several existing passwords, common accounts, domain-account formats, and limited wordlist attempts were rejected. Expanding password attempts produced no useful new information, while public-key authentication had already been advertised by the server.

The first inspection focused on Windows OpenSSH configuration and host-key locations. These contained sshd configuration and server identity keys. Host keys let a server prove its identity; they do not automatically serve as user private keys for logging into another machine. Confusing these roles encouraged further investigation in the wrong direction simply because many key files had been found.

C:\ProgramData\ssh contained RSA, ECDSA, and Ed25519 host keys and sshd_config, but the expected user authorization file was not found there. The configuration distinguished ordinary-user and administrator authorization-file paths and restricted the groups allowed to log in:

~~~text
AuthorizedKeysFile .ssh/authorized_keys
AllowGroups administrators "openssh users"
Match Group administrators
    AuthorizedKeysFile __PROGRAMDATA__/ssh/administrators_authorized_keys
~~~

The local OpenSSH Users group was empty, and the initial identity was not an administrator. This was consistent with that identity's inability to access WIN-A over SSH, but did not replace inspection of LINUX-A. The two sshd instances had separate authentication boundaries; Windows rules could not be applied to Linux.

User profiles were examined next. Some administrative profiles had been unreadable under the initial low-privilege identity. The first traversal after obtaining administrative privileges then returned zero matches because the script swallowed exceptions. These two errors caused the same files to be missed twice. A direct recheck of the restricted profile finally located a user SSH private key and its public key.

~~~powershell
Get-ChildItem -LiteralPath "C:\Users\<PROFILE>\.ssh" -Force |
    Select-Object Name, Length, LastWriteTime
~~~

Finding a private key did not establish Linux access. Its format, passphrase requirement, corresponding public key, and the remote account accepting that public key still needed checking. A public-key comment was a lead, not a substitute for remote authorization verification.

~~~bash
ssh-keygen -y -f <USER_PRIVATE_KEY> > <DERIVED_PUBLIC_KEY>
ssh-keygen -lf <DERIVED_PUBLIC_KEY>
~~~

The private key had no passphrase, but pairing it with several common Linux usernames still failed. Public-key authentication succeeded only after a service identity from the earlier Windows testing was reconsidered. Treating Windows domain usernames and Linux usernames as disjoint sets had pushed the most evidence-backed identity down the candidate list.

~~~bash
ssh \
  -i <USER_PRIVATE_KEY> \
  -o IdentitiesOnly=yes \
  -o PreferredAuthentications=publickey \
  <SERVICE_USER>@<LINUX_A>
~~~

A rejection alone could not distinguish an untrusted key, a nonexistent account, or an account restriction. On success, the actual username and host identity were verified before inspecting local services.

~~~bash
whoami
hostname
ss -lntp
~~~

The established cross-host relationship was a user private key on WIN-A matching a public key trusted by an account on LINUX-A. Domain privileges had helped broaden the investigation, but the direct authentication basis for Linux access was the key-and-account combination.

## 9. The Real Vector Database Appeared on Loopback

After login, several services besides SSH were found listening only on loopback. They included a vector interface and local model-related services, explaining why external scans had primarily found SSH. Port numbers supplied candidate fingerprints, which still required protocol-level verification.

~~~bash
curl -sS http://127.0.0.1:<VECTOR_PORT>/
curl -sS http://127.0.0.1:<VECTOR_PORT>/v1/schema
~~~

Response paths, service metadata, and the schema together identified Weaviate. Several paths guessed from other products returned 404, which did not establish a service fault. Requests using the actual API routes returned the schema successfully.

Within the current access scope, reading the schema and target objects required no API credentials. This established a lack of independent authentication for those reads. The initial analysis extended that result to unrestricted reading and writing of all data, which exceeded the evidence. Without retained write-validation evidence, a read result could not establish arbitrary write access.

| Object class | Object count | Visible properties | Relevance to the objective |
| --- | --- | --- | --- |
| ResearchRecords | 3 | Title, body, source, and related properties | Background material |
| InternalRecords | 2 | Title, body, category, source, and related properties | System and pipeline context |
| SensitivePolicy | 1 | Title, source, and digest identifier, without a body property | Sensitive target vector |

Class names have been replaced. The target object lacked a plaintext body but retained its vector. The schema's vectorizer setting also indicated that vectors had been generated externally and inserted, rather than encoded automatically inside the current database. No enabled quantization was observed, but this did not guarantee successful inversion; it was one condition affecting method selection.

## 10. Vector Export Had to Follow the Actual Schema

The first export applied the same fields to all three classes. One class had a category field and the other two did not, so GraphQL validation rejected the invalid query. This was a type-boundary error, unrelated to networking, authentication, or whether vector data existed.

~~~text
Cannot query field "category" on type "<CLASS_WITHOUT_CATEGORY>"
~~~

The correction was to verify fields against the schema and query each class separately. The following target-object query uses a replacement class name:

~~~graphql
{
  Get {
    SensitivePolicy {
      title
      _additional {
        id
        vector
      }
    }
  }
}
~~~

Business fields, object identifiers, and vectors were saved separately. After export, responses were first checked for errors, followed by object counts and vector lengths. This prevented an error JSON response from being passed to the inversion program as a data file.

~~~python
import json
from pathlib import Path

payload = json.loads(Path("target-response.json").read_text())
if payload.get("errors"):
    raise RuntimeError("GraphQL export failed")

records = payload["data"]["Get"]["SensitivePolicy"]
assert len(records) == 1
vector = records[0]["_additional"]["vector"]
assert len(vector) == 384
assert all(isinstance(value, (int, float)) for value in vector)
~~~

Six vectors were obtained across the three classes, including one 384-dimensional vector for the target object. They were converted to the array format used by the inversion program, while the original responses were retained for cross-checking.

~~~python
import numpy as np

matrix = np.asarray([vector], dtype=np.float32)
assert matrix.shape == (1, 384)
assert np.isfinite(matrix).all()

np.save("target-vector.npy", matrix)
loaded = np.load("target-vector.npy", allow_pickle=False)
assert loaded.shape == matrix.shape
assert np.array_equal(loaded, matrix)
~~~

Array shape, numeric type, readback, and finite-value checks were more reliable than file size alone. Array files also contain format headers, so a simplified byte-count formula cannot establish completeness. Checking the loaded structure and values is more direct.

Dimensionality, normalization, and distance metrics could narrow the encoder candidates but did not uniquely identify a model. all-MiniLM-L6-v2 was used as a candidate encoder, also informed by environmental clues and subsequent matching results. This evidence boundary matters: a dimensional fingerprint is not a definitive model identity.

Other model services were not investigated further because the target vector had been obtained and inversion did not depend on an online chat interface. Observing a particular gRPC port was insufficient to name a specific inference framework.

## 11. Analysis Environment, Method Selection, and File Transfer

After export, recovery calculations moved to a dedicated analysis environment. The notes considered several methods and tools, including template-based candidate matching, beam search, and approaches requiring specialized models or training preparation. The selected template method best matched the available prerequisites and evidence.

The analysis environment had a T4 GPU and a Python virtual environment, along with ALGEN and Vec2Text directories, but lacked the zero-shot scripts needed for this run. generate_templates.py, emb_fin.py, zero2text_impl.py, the candidate wordlist, and the exported array were then supplied. Dependencies and inputs were checked before computation began. A tool directory's presence did not establish that its models and runtime prerequisites were ready.

| Candidate approach | Choice in this engagement | Limit of the conclusion |
| --- | --- | --- |
| emb_fin.py template candidate matching | Prioritized because target context, encoder clues, and a wordlist were available | Searched only the current template and candidate space |
| zero2text_impl.py beam search | Reserved as a fallback if template results were insufficient; not run | No conclusion about its effectiveness on this target |
| ALGEN-related approaches | Required data and interface conditions were not fully prepared | One experimental setup did not define universal method requirements |
| Vec2Text-related approaches | Corresponding models or training workflow were not prepared | No fixed training duration could be generalized to all implementations |

Computation ran in the dedicated analysis environment, while the testing machine handled export and transfer. This division was an execution constraint for the engagement, separate from whether the template method could run on a CPU.

The basis was a target vector already in hand, a relatively narrow set of encoder candidates, text apparently related to password-reset notices, and a defined candidate wordlist. This allowed the problem to be narrowed to which candidate best explained the target vector within a given context. It was not general recovery of arbitrary unknown text.

Not using other methods did not mean that those methods universally required a fixed training duration or write access. Implementations have different prerequisites. The choice here established only that the corresponding models, training resources, or interface conditions had not been prepared at the time.

File transfer also encountered a configuration error: SSH was set to BatchMode=yes while password interaction was still expected. That option suits already-configured noninteractive authentication and should not be added when password entry is required. Removing the option that conflicted with the authentication flow allowed transfer to complete, followed by content verification.

~~~bash
sha256sum target-vector.npy
scp target-vector.npy <ANALYSIS_USER>@<ANALYSIS_HOST>:<WORK_DIRECTORY>/
ssh <ANALYSIS_USER>@<ANALYSIS_HOST> \
  'sha256sum <WORK_DIRECTORY>/target-vector.npy'
~~~

This code illustrates file-integrity verification. Matching digests at both ends established that transfer did not alter the file, not that the vector source, model choice, or recovery algorithm was correct.

## 12. How Template Matching Produced a Candidate

The analysis script first assessed which type of business text best matched the target vector. Password-reset context scored highly, after which approximately twenty thousand templates were generated around notification wording, context order, and language variations. Templates retained password and URL slots rather than comparing an isolated candidate against the vector of an entire document.

~~~text
The default password after resetting is {PASSWORD}.
Please open {URL} and update the password after signing in.

Your account has been reset.
Use {PASSWORD} to sign in at {URL}.
~~~

Recovery first selected high-scoring templates and then removed highly similar ones, preventing five nearly identical sentences from creating a misleading five-way consensus. The candidate list contained approximately ten thousand entries. A coarse pass narrowed the list before multiple templates compared the remaining candidates.

The recorded parameters were more specific: approximately twenty thousand templates were scored, the top fifty were retained, and pairwise cosine similarity was used to select five deduplicated templates. Coarse candidate filtering retained roughly two hundred values for comparison across templates. Deduplication reduced repeated voting by similar wording; it did not make the five templates statistically independent.

Template generation began with business-text domain identification. Among approximately twenty domains, password-reset context scored prominently. The generator expanded seven base templates through pattern, language, structure, and context variations. Similarity between the templates and the target document's wording was an important condition for success. This domain-constrained recovery did not establish that any secret could be recovered from an arbitrary vector.

~~~text
1. Match and rank templates
2. Deduplicate high-scoring templates
3. Coarsely filter candidates
4. Compare candidates across multiple templates
5. Output candidates and scores
6. Perform independent validation
~~~

The sanitized tool invocation follows. These filenames and parameters belong to the script interface used in this engagement and are not universal options for all embedding-inversion tools.

~~~bash
python3 generate_templates.py \
  --output templates.json \
  target-vector.npy \
  --count 20000

python3 emb_fin.py \
  target-vector.npy \
  --chunk 0 \
  --templates templates.json \
  --wordlist candidates.txt \
  --slots PASSWORD
~~~

Five deduplicated templates ultimately supported the same candidate. The tool reported high similarity and a Strong label. This meant one candidate ranked favorably under the current templates, candidate set, and scoring strategy. It was not a probability of correctness and did not prove word-for-word recovery of the source text.

During execution, an initial template match of approximately 71.6% appeared, followed by a best value of 75.6% in the summary. The tool did not report a runner-up and displayed an infinite separation ratio. This reflected the absence of a comparable second-ranked result under its output rules, not an infinite gap between the candidate and every other answer. At the time, the high match score and Strong label led to a decision not to run beam search. That was an execution-stage stopping decision. Independent confirmation obtained later supported the final correctness claim; it could not retrospectively be presented as the reason for the earlier decision.

~~~text
Candidate: <REDACTED_VALUE>
Template agreement: 5 / 5
Best template match: 75.6%
Runner-up: not reported
Tool label: Strong
Independent validation: confirmed
~~~

Independent validation confirmed the final sensitive value. This article retains that conclusion without disclosing the value, raw vectors, or artifacts that could reconstruct the client's sensitive material.

## 13. Why the Failed Known-Text Check Needed Separate Analysis

An important failed experiment accompanied the successful target result. A text containing a known value was constructed, encoded, and passed to the same recovery script. With suitable pipeline and candidate conditions, the known value should have been recovered. Instead, another candidate was returned with a high-confidence label.

This failure showed that the label could not serve as proof. Checks needed to cover whether the known value was in the candidate list, whether case and preprocessing matched, whether the encoder was the same, whether URL and context slots aligned, and whether coarse filtering had discarded the correct candidate too early.

The candidate file contained a lowercase form of the known value, so complete absence from the wordlist was not a sufficient explanation. The constructed sentence used different casing. Even if the encoder's tokenization folded case, candidate processing and output comparison in the recovery script still needed separate checks. Complete ranking evidence was not retained to establish whether coarse filtering had removed the known value, so that possibility also remained unconfirmed.

The constructed sentence used a specific URL, while the recovery run did not align that URL slot. This was an observed difference in experimental conditions, but no successful rerun after correcting it was recorded. It therefore could not be identified as the sole cause. The URL mismatch remained a hypothesis to test through a rerun with aligned conditions.

~~~python
known_text = (
    "The default password after resetting is <KNOWN_VALUE>. "
    "Please sign in at <CONTROL_URL>."
)

control_settings = {
    "encoder": "<SAME_ENCODER_AND_PREPROCESSING>",
    "candidate_list": "<SAME_CANDIDATE_LIST>",
    "url_slot": "<CONTROL_URL>",
    "template_strategy": "<MATCHED_TEMPLATE_STRATEGY>",
}
~~~

A meaningful control would hold encoding, context, candidate set, and template conditions as constant as possible while changing only the value under test. Known values from several semantic categories could also reveal whether a particular candidate category repeatedly won. Two experiments producing candidates from the same semantic category suggested possible bias but did not establish a systematic mechanism.

Independent confirmation of the target candidate did not establish that the recovery pipeline was reliable for arbitrary text. The failed control remained a limitation of the method and needed to be retained alongside the client-objective result.

## 14. Interpreting Environmental Instability and Closing Failed Branches

The engagement included repeated service unavailability, RDP handshake failures, VPN interruptions, and SMB tool timeouts. Some occurred shortly after test requests, inviting the claim that a particular request crashed a service. Recovery, changed directory timestamps, and reachability through other tools supplied additional clues, but attribution remained incomplete without host and server logs.

Anomalies were therefore recorded through four elements: time, concurrent action, target-side observation, and independent retest result. Temporal proximity established correlation, not causation. A timeout in one SMB client while another direct method succeeded primarily suggested a client-path or protocol difference, not immediate proof of a target outage.

In one incident, the portal, Qdrant, and MongoDB became unavailable together and recovered several hours later; storage-directory timestamps also changed. Collection-interface tests had occurred shortly before the interruption, but no server logs established that those requests caused it. Changed timestamps likewise did not prove that the virtual machine had undergone snapshot restoration.

In another incident, the RDP client reported ERRCONNECT_TLS_CONNECT_FAILED while the port remained open. An independent TLS check completed a handshake, and reconnection later succeeded. This supported investigating a transient client or session-path failure but did not identify the precise trigger. SMB NETBIOS timeouts also coexisted with successful direct connections through other clients. The response was to switch clients and continue checking target state rather than treating one tool's timeout as complete host loss.

Endpoint-protection state was adjusted during testing. Early winPEAS delivery failure and later credential-reading success could not establish that protection caused every failure: privileges, execution methods, and output collection also changed. Retaining these variables was necessary to distinguish observed blocking from unverified explanations.

| Investigated route | Negative result or limitation | Scope of the conclusion |
| --- | --- | --- |
| WIN-A portal as the real RAG system | Collections, metadata, and observed program calls did not support it | Limited to the observed instance |
| Linux password authentication | Tested combinations were rejected | Not proof that all account passwords were invalid |
| Linux GSSAPI | The current SSH endpoint did not accept the method | Not proof that Linux could not join a domain |
| Domain database-service marker | No actual instance or listener was found | An SPN did not prove a running service |
| Automated privilege-enumeration tool | File delivery or execution was blocked | Not proof that no privilege-escalation path existed |
| Several local privilege configurations | Checked methods lacked required prerequisites | Not proof that the host had no other weakness |
| Administrative user profiles | Reading failed under low privileges | Required rechecking after privilege elevation |
| Low-privilege execution on DC-A | Insufficient logon rights or missing target-side results | Callback designs could not rely on the unproven channel |
| Known-text inversion control | Wrong candidate, with conditions not fully aligned | Not evidence of generally validated pipeline reliability |

This table defined the conditions under which each route failed. It did not declare every other route closed. Changes in privileges, networking, or environmental state required some negative findings to be revisited.

## 15. Ten Types of AI Error and Their Knowledge Gaps

### 1. Treating Connection and Authentication as Logon Authorization

Partial RDP connection completion did not establish that the target permitted remote logon for the identity. An error screen lasting dozens of seconds did not prove that a command ran for that duration. The missing foundations concerned Windows logon rights, authentication stages, and session state. Correction required the actual interface or target-side events.

### 2. Treating Positive Tool Markers as Execution Results

A remote management tool reported Executed, yet the expected target artifact was absent and direct operations returned access denied. The analysis also attempted to identify exactly which internal API stage the tool had completed, without the corresponding version's source or call trace. That specific explanation was unsupported. The defensible finding was that target effects did not corroborate the positive message.

### 3. Treating Truncated Output as Complete Enumeration

Insufficient terminal buffering, mixed old output, and tail-only reads undermined completeness. A misunderstanding of the observation channel appeared as no services or no files. Collection state and target state required separate verification.

### 4. Treating Multiple Escaping Layers as Mechanical Concatenation

Each interpreter in a command chain has its own rules for quoting, escaping, and variables. Repeatedly modifying an increasingly complex inline command added hidden differences. Moving complex logic into a script, retaining errors, and checking what actually executed helped distinguish target failures from command-construction failures.

### 5. Misusing SSH Interaction Controls

Disabling interaction broke password-based transfer, while other authentication methods could interfere with public-key testing. Whether an option was appropriate depended on the method being tested. Without understanding BatchMode, IdentitiesOnly, and authentication preferences, rejection responses could not be interpreted reliably.

### 6. Treating Passwords as the Only Search Direction

The server already advertised public-key authentication, yet password combinations continued to receive disproportionate attention. Passwords, user keys, account scope, and authorization restrictions should have become separate hypotheses early, ranked by evidence. A larger candidate list was not a more complete approach.

### 7. Reusing Old Zero Results After Privileges Changed

A directory unreadable under low privileges could contain crucial material after administrative access was obtained. Silently swallowed traversal errors then created a second false negative. The mistake extended beyond missing one directory: an observation under one identity was treated as an unchanging environmental fact.

### 8. Treating a Failed Query Method as an Absent Object

Refused zone transfers, PTR timeouts, and interrupted directory queries established only that those methods did not return results. DNS paths had not all been completed, and the gaps needed to remain visible. Turning unfinished checks into exclusions created false confidence that the search space had narrowed.

### 9. Ignoring Variable Control in Inversion Experiments

A failed known-value recovery with a high-confidence label showed that labels and truth were not equivalent. Differing control conditions also made the failure difficult to explain. Domain-knowledge gaps affected machine-learning experimental design, score interpretation, and generalization claims as well as penetration-testing operations.

### 10. Treating Success Logs as Deliverables

A report script claimed to save a file, but the file could not be found during readback. The cause remained unresolved, while failed delivery was certain. Existence, readability, completeness, and final location all required checking; the write function's return value was insufficient.

The common root of these ten errors was insufficient knowledge of the security domain, protocol details, and experimental methods. Missing evidence checks amplified those gaps, allowing incorrect premises to generate further actions. More tool calls or longer execution could not independently correct conceptual errors.

## 16. Reconstructing the Full Path from Evidence

The original operations included parallel work, revisits, and repeated attempts. The sequence below follows dependencies so that the prerequisites for each advance are clear. It does not recast every attempt as a smooth, linear success.

~~~text
Existing low-privilege identity
  → Verify member-server access and domain-side read-only scope
  → Check the portal, Qdrant, and MongoDB; reject the wrong target
  → Compare two network vantage points; retain the loopback-service hypothesis
  → Perform native enumeration and inspect deployment remnants
  → Reject the old password; trace initialization and rotation
  → Find readable configuration media and another local administrative secret
  → Resolve the must-change state; verify local administrative access
  → Inspect local credentials; distinguish local administrator identities
  → Verify credential reuse at the domain endpoint and confirm domain-level impact
  → Revisit user profiles after privilege changes; find an SSH private key
  → Match the key to the Linux account and confirm host access
  → Inspect local listeners and APIs; identify Weaviate
  → Export the target vector according to schema and validate its format
  → Compare template candidates in the analysis environment
  → Independently validate the target candidate
  → Retain the failed known-text control as a separate method limitation
~~~

Only at this point did the two main threads connect: access to the environment made the vectors available, while inversion produced a sensitive-value candidate after model clues, text context, and candidate space had been narrowed. If any stage lacked independent evidence, the conclusion needed to stop at that stage.

## 17. Improvements Indicated by the Client Environment

Deployment secrets need a complete lifecycle. Removing a drive letter, hiding a path, or printing a successful cleanup message does not establish that media and metadata are unreadable. Actual mount state, data accessibility, and secret rotation must be verified.

Local administrative accounts, the built-in administrator, domain administrators, and service identities need separately managed secrets. Reuse expanded a local credential exposure into domain-level impact, while an SSH private key available across hosts opened another access path. Passphrases, purpose restrictions, and usage auditing need to fit the deployment model rather than merely checking whether a key file exists.

Vector databases need independent authentication and least privilege. Loopback binding reduces network exposure, but host access, a proxy, or forwarding can still expose an unauthenticated data interface. Sensitive documents need classification and a necessity review before entering a retrieval pipeline. Removing a body property does not mean its embedding has been sanitized.

Logs need to support reconstruction of process origin, privilege changes, and data access. Missing common startup entries do not establish a particular host-side launch action; missing read events do not establish that a read never occurred. Each conclusion needs an explicit account of log coverage.

Automated testing needs both domain knowledge and outcome verification. Inaccurate understanding of identities, protocols, and experimental methods repeatedly turns reachable, valid credentials, or tool-reported success into executed and verified. The essential record of this engagement is how those distinctions were lost, how evidence disproved the resulting assumptions, and how each correction restored a viable path.
