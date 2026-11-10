---
title: Staying Alert to AI: What Comes With the Convenience?
date: 2026-11-10
slug: ai-progress-risk-and-the-cure
topic: ai
category: AI and Society
summary: AI drug research, dual-use experiments and an MCP security case illustrate the risks that accompany growing capability and convenience, and how dependence can weaken vigilance.
draft: false
---

# Staying Alert to AI: What Comes With the Convenience?

The more tangible AI's benefits become, the easier it is to put its risks aside. Writing code, supporting research and finding treatment candidates offer real reasons for hope. Greater capability does not make the accompanying security problems disappear.

That is the question I want to examine: as AI becomes more useful, will we still be willing to look closely at its problems?

## 1. Results can arrive faster than understanding

On September 8, 2026, OpenAI announced a result on the Navier–Stokes Millennium Prize Problem, reporting a proof from an internal system and releasing a paper and Lean formalization.[1] On October 6, it published a further collection of mathematical results and formalizations.[2]

These are institutional announcements. Formal checking, researchers understanding a proof and the mathematical community assessing its significance remain separate activities. Publication alone does not establish that independent scrutiny is complete.

Useful results may arrive before we fully understand them. Faster generation does not remove the work of deciding whether an answer deserves trust.

Mathematics has relatively explicit routes for formal verification. Drugs and materials must eventually work in the physical world. Predicted structures and candidate molecules still face experiments, manufacturing and long-term observation. A stream of impressive results can make unfinished work look like progress already delivered.

## 2. If it can save a life, will we still care about risk?

Imagine someone with a terminal illness. AI offers a treatment that people do not fully understand. Trying it offers some hope; refusing it offers none. What would that person choose?

This resembles Geoffrey Hinton's 2020 black-box surgeon thought experiment: if an AI surgeon has a better cure rate than a human surgeon but cannot explain how it works, is that alone a reason to prohibit it?[3] The original concerned explainability and outcomes, not a successful but mysterious cancer drug. The patient and medicine here extend that hypothetical; they are not a clinical case.

I find it difficult to blame someone who would try. Their loss is already concrete, and treatment may represent all their remaining hope. An abstract technological risk is hard to weigh against that.

That also makes me uneasy. When hope is strong enough, will people still ask what supports the claim of effectiveness? Evidence of benefit with an incomplete account of the mechanism is different from a confident model answer without evidence of benefit. Someone desperate for an answer can lose that distinction behind the words “it could save your life.”

When the capacity exists to create something capable of saving all of humanity, it also carries the capacity to destroy all of humanity. This is a warning about dual use, not a factual claim about current systems or a prediction that catastrophe is inevitable.

## 3. Tangible progress can push vigilance into the background

The 2025 rentosertib phase IIa study in Nature Medicine provides a concrete example. This randomized, double-blind, placebo-controlled trial studied an AI-discovered and designed drug candidate for idiopathic pulmonary fibrosis. It enrolled 71 participants over a 12-week treatment period.[4]

AI-assisted discovery has reached clinical research. A 71-person, 12-week trial also cannot replace long-term observation or every step required for approval. Both facts remain true.

Materials research offers a similar distinction. When Google DeepMind introduced GNoME in 2023, it reported around 2.2 million predicted crystal structures, including roughly 380,000 considered more stable and worth experimental exploration.[5] That expands the search for candidates; it does not mean an equal number of mature industrial materials already exist.

These studies have real value. But as they reach a wider audience, candidates, experimental results and practical applications can collapse into a single claim: “AI has done it.” One successful example is memorable. Unknowns and limitations tend to stay in the paper.

My concern is that the more exciting progress becomes, the easier it is to treat what remains unknown as unimportant.

## 4. A life-saving capability need not be used to save lives

The 2022 Nature Machine Intelligence paper “Dual use of artificial-intelligence-powered drug discovery” examined this directly. It presented a computational proof of concept generating potentially toxic molecular candidates using drug-discovery technology.[6]

This was not a demonstration of manufacturing a weapon. Computational candidates still have to cross the distance to synthesis, toxicity testing and real-world harm. Chemical hazards cannot simply be equated with transmissible biological weapons.

Yet it identifies a specific issue: capability intended to find treatments can be redirected toward harmful objectives. Being good at search and optimization does not confine a system to its original purpose.

There is no need to inflate candidates into a disaster that has already happened. Nor does the continuing need for materials, equipment and experiments make the computational advance irrelevant. Shortening a previously difficult search is itself a change.

The same advance can make useful work easier while lowering barriers to harmful activity.

Security testing shows another concrete form of this problem. An [earlier MCP case](/articles/mcp-stdio-configuration-trust-boundary/) traced a path from configuration access to server-side execution. The application allowed a stdio tool to be configured and launched its process when testing the connection. The child process inherited the application's environment and occupied a network position from which internal resources were reachable.

Connecting tools was meant to let the AI application do more. Behind those tools were processes, environment variables, network access and database permissions. A connection test in the interface could already be an execution with real privileges on the backend.

This does not establish the same flaw in every MCP application. Launching a local process is normal stdio behavior. The issue lay in how that application connected configuration rights, execution rights and data access.

The capability is no longer just text. Once AI is connected to a business system, what it can call and operate becomes part of that system's risk. Looking only at whether an answer appears normal can miss what has happened outside the answer.

## 5. Dependence can make us explain risks away

A deeper concern may appear after success. If AI makes people healthier and more productive, and more work depends on it, acknowledging a problem will involve more than accepting an argument.

It may mean confronting costs, lost efficiency and a way of life we have grown accustomed to. Could dependence make us keep telling ourselves that a risk can wait?

That is a concern about dependence, not an established social outcome. The studies and case above do not prove that AI must become uncontrollable. They show that benefits and security problems can grow together. Convenience does not erase the latter.

I am not trying to magnify AI's harms or offer a plan that solves every problem. Its achievements deserve attention. So do the problems that come with them.

Especially when AI becomes something we do not want to lose, “I need it” must not quietly become “there is nothing wrong with it.”

## Sources and verification notes

This is an opinion article retaining the original article's cited factual sources. The patient and unknown medicine are a thought experiment, not treatment advice or a real clinical case. The discussion of future dependence is the author's judgment.


[1] [OpenAI: On the Navier–Stokes Millennium Prize Problem](https://openai.com/index/navier-stokes-solution/), September 8, 2026. This essay describes the institutional announcement without asserting prize recognition or completion of all independent review.

[2] [OpenAI: Sharing AI progress in mathematics](https://openai.com/index/sharing-ai-progress-in-mathematics/), October 6, 2026, including the October 15 update.

[3] [Geoffrey Hinton's original post](https://twitter.com/geoffreyhinton/status/1230592238490615816/), February 20, 2020. Direct retrieval was unavailable; the attribution was cross-checked through [InfoQ's contemporary report and original-post link](https://www.infoq.com/news/2020/03/explainable-ai-survey/) and [teaching material preserving a screenshot](https://ai.ethicsworkshop.org/Library/AI-Case-Disease.pdf). This essay paraphrases the thought experiment and does not attribute the unknown-drug scenario to Hinton.

[4] [Xu et al.: A generative AI-discovered TNIK inhibitor for idiopathic pulmonary fibrosis: a randomized phase 2a trial](https://www.nature.com/articles/s41591-025-03743-2), Nature Medicine, June 3, 2025.

[5] [Google DeepMind: Millions of new materials discovered with deep learning](https://deepmind.google/blog/millions-of-new-materials-discovered-with-deep-learning/), November 29, 2023.

[6] [Urbina et al.: Dual Use of Artificial Intelligence-powered Drug Discovery](https://pmc.ncbi.nlm.nih.gov/articles/PMC9544280/), Nature Machine Intelligence, March 7, 2022. The citation concerns dual-use potential, not experimentally validated weapons.
