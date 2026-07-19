# Atlas Paper 002
## Defining the Personal Internet Presence Layer
*A boundary model for person-controlled Internet presence, relationships, context and trust*

**Version 0.1 - Working Proposal - July 2026**

> This document is intended for public technical review. It is not a production security claim or standards submission.

## Contents

01. [Executive Summary](#executive-summary)
02. [Problem Statement and Research Boundary](#problem-statement-and-research-boundary)
03. [Terminology](#terminology)
04. [Design Principles](#design-principles)
05. [Proposed Layer Boundary](#proposed-layer-boundary)
06. [Actors and Trust Domains](#actors-and-trust-domains)
07. [Logical Components](#logical-components)
08. [Lifecycle Operations](#lifecycle-operations)
09. [Context Separation and Privacy](#context-separation-and-privacy)
10. [Relationship to Existing Technologies](#relationship-to-existing-technologies)
11. [Candidate Interaction Model](#candidate-interaction-model)
12. [Security Threats and Abuse Cases](#security-threats-and-abuse-cases)
13. [Governance Requirements](#governance-requirements)
14. [Deployment Models](#deployment-models)
15. [Minimum Viable Research Prototype](#minimum-viable-research-prototype)
16. [Falsifiable Hypotheses and Evaluation Criteria](#falsifiable-hypotheses-and-evaluation-criteria)
17. [Open Questions for Industry Review](#open-questions-for-industry-review)
18. [Conclusion](#conclusion)
19. References

## 01 Executive Summary

Atlas Paper 001 proposed a research question: is the Internet missing a broadly adopted, person-controlled layer that can represent an individual across changing networks, devices, providers and organizational relationships? This paper narrows that question. It defines the proposed boundary of a Personal Internet Presence Layer without treating the hypothesis as proven or prescribing a finished implementation.

The working model is a personal coordination and policy plane. It would sit above existing identity, credential, device, network and secure-transport capabilities. Its role would be to let a person establish, separate, present and withdraw digital relationships without requiring one employer, platform, government, identity provider or network operator to own the complete representation of that person.

This proposal does not create trust by itself. Banks, employers, governments, professional bodies and other issuers would continue to make authoritative claims. Applications and organizations would continue to set access policy. Networks would continue to operate addressing, routing and transport. The proposed layer would coordinate how a person uses those systems, which context is active, which claims are presented and which connectivity or privacy policy applies.

The strongest objection is composability: existing identity wallets, passkeys, verifiable credentials, secure tunnels, mesh networks, Zero Trust systems and operating-system account frameworks may already provide enough primitives. If these technologies can be assembled into a portable, interoperable and person-controlled experience without a distinct layer, the Atlas thesis should be narrowed or rejected.

The largest design risk is correlation. A durable personal presence could become a universal tracking identifier, a coercive identity requirement or a high-value control point. Atlas therefore distinguishes durable control from permanent presentation. A viable design must support pairwise or context-specific identifiers, selective disclosure, local decision-making, revocation, recovery and the ability to remain unknown where identification is unnecessary.

This paper presents terminology, scope, actors, logical components, trust boundaries, lifecycle operations, privacy requirements, abuse cases, deployment models and falsifiable hypotheses. It is a working proposal for technical review, not a production security claim or standards submission.

## 02 Problem Statement and Research Boundary

Internet systems usually observe a person indirectly. A network sees addresses, sessions and device behaviour. An application sees an account. An employer sees a workforce identity. A bank sees a customer relationship. A government sees a legal or administrative identity. These representations can be accurate within their domains, but none is inherently the person's portable Internet presence.

Fragmentation is not automatically a defect. Context-specific identities can protect privacy and limit blast radius. Organizations also need independent authority over their own records and policies. The research problem is therefore not to combine every identity into one record. It is to determine whether the person lacks a coherent control boundary across those separate relationships.

Atlas uses the term Personal Internet Presence to describe that possible boundary. The presence would be durable enough to survive device replacement, provider changes and network movement, but it would not need to expose one stable public identifier. It could present different identifiers, credentials, routes and policies to different parties.

The proposal covers coordination across identity relationships, credentials, devices, context, trust presentation and connectivity policy. It excludes ownership of external facts, unilateral authority over relying-party decisions, replacement of Internet routing, and any assumption that every interaction requires a verified civil identity.

The central research question for Paper 002 is narrower than the vision statement: can a distinct logical layer be defined that adds useful person-controlled coordination while preserving the authority, security boundaries and privacy properties of existing systems?

## 03 Terminology

Person: the human participant whose relationships, devices, contexts and policies are being coordinated. Atlas uses person rather than user because a person may act across many services and roles, while user commonly describes an account inside one system.

Personal Internet Presence: a durable, person-controlled logical presence through which relationships, contexts, credentials, devices and connectivity preferences can be coordinated. Durability refers to continuity of control, not universal visibility.

Presence Controller: the logical authority that applies the person's policy and authorizes changes to the presence. It may run locally, be delegated, or be distributed across trusted components.

Context: a bounded presentation of the person for a purpose or relationship, such as employment, banking, healthcare, public participation, private communication or pseudonymous activity.

Relationship: an association between a context and another party. A relationship may include identifiers, credentials, consent, policy, keys, endpoints and history, but it does not imply that either party owns the other.

Claim: a statement about a subject. A claim can be self-asserted or issued by an external authority. Atlas must preserve that distinction.

Credential: a cryptographically or procedurally verifiable container for one or more claims. The presence may store a credential, reference it, or invoke an external wallet; it does not become the issuer.

Relying Party: a service or organization that receives an identifier, claim, credential, proof or connection request and makes its own trust or access decision.

Presence Agent: software acting on behalf of the presence on a device, gateway or service. An agent is not automatically trusted merely because it is enrolled.

Recovery Authority: a person, device, institution or mechanism allowed to participate in restoring control after loss or compromise. Recovery is a governed process, not a bypass around security.

Provider Independence: the ability to preserve the person's control and relationships when a specific hosting, network, identity or application provider changes. It does not mean operating without all providers.

Selective Disclosure: presentation of the minimum claims or derived proofs needed for an interaction, rather than disclosure of an entire identity record.

## 04 Design Principles

Person-controlled, not person-authored. The person should govern participation, context and disclosure, but cannot rewrite claims issued by independent authorities.

Durable control, variable presentation. Continuity should reside in keys, recovery, policy and relationship state. Public identifiers and network attributes should be replaceable, contextual or pairwise wherever possible.

Composition before invention. Atlas should reuse deployed standards and open protocols. A new protocol is justified only when a demonstrated interoperability gap cannot be addressed through profiles, conventions or existing extension points.

No mandatory universal identity. Anonymous, pseudonymous and minimally identified interactions are legitimate Internet modes. The presence must not force civil identity into contexts where it is unnecessary.

Explicit trust boundaries. Every assertion must identify who made it, what evidence supports it, how it can be verified, when it expires and how it can be revoked or disputed.

Local-first policy where practical. Sensitive relationship maps, context rules and disclosure decisions should remain on person-controlled devices unless external processing is required and knowingly authorized.

Provider portability. Hosting and recovery designs should make exit possible. A provider must not become the permanent owner of the person's presence merely because it operates infrastructure.

Fail bounded, not open. Loss of an optional coordination service must not silently broaden access, merge contexts or disclose additional information.

Inspectable operation. People and reviewers need understandable logs showing which context acted, which claims were released, which device participated and which policy produced the result.

Falsifiability. Atlas should publish conditions under which the layer is unnecessary, unsafe or technically incoherent.

## 05 Proposed Layer Boundary

The proposed layer is best described as a personal control and coordination plane rather than a new data plane. It decides how existing capabilities are invoked; it does not carry every packet, authenticate every transaction or issue every credential.

Below the layer are operating systems, secure hardware, key stores, identity protocols, credential formats, network interfaces, DNS, IP routing, encrypted transports, mesh systems, VPNs and application protocols. Above or beside it are the applications, organizations and services with which the person interacts.

Within the boundary are the person's relationship catalogue, context definitions, device enrolment state, disclosure rules, trust preferences, recovery policy and connectivity intentions. Implementations may distribute these functions, but their combined effect should remain under person-authorized control.

Outside the boundary remain authoritative source records, relying-party authorization policy, network-provider operational controls, lawful governance processes and the independent decisions of other people. The presence can request, prove, negotiate and revoke; it cannot compel trust.

The layer should expose stable interfaces rather than require one monolithic product. A wallet could provide credential operations. A mesh system could provide private reachability. An identity provider could authenticate a relationship. A local policy engine could decide what to reveal. Atlas would define how those parts relate from the person's perspective.

This boundary may ultimately be a reference architecture rather than a deployable protocol layer. That outcome would still be useful if it creates a common model for interoperability and exposes where current systems bind identity, policy and connectivity too tightly to providers.

## 06 Actors and Trust Domains

Person. The person authorizes creation, context separation, relationship establishment, recovery choices and disclosure policy. Human intent must be distinguished from automation performed by agents.

Device. A phone, computer, wearable, vehicle, home gateway or other endpoint may hold keys, collect context or provide connectivity. Device possession is evidence, not proof of the human's intent in every transaction.

Presence Agent. The agent enforces local policy and communicates with other components. Agents require scoped authority, software integrity controls and revocation.

Credential Issuer. Governments, employers, banks, schools, certification bodies and other organizations issue claims. Their signatures establish provenance, while relying parties decide whether the issuer and claim are sufficient.

Identity Provider. An identity provider authenticates accounts and may supply federation assertions. Atlas must integrate without turning one identity provider into the root of the entire presence.

Network Provider. An ISP, mobile operator, enterprise network, cloud network or access venue supplies connectivity and enforces its own operational policy. Atlas may express routing or privacy preferences but cannot unilaterally control provider infrastructure.

Secure Connectivity Provider. VPN, mesh, overlay or private-access services may supply encrypted paths and policy enforcement. Their control planes represent a significant trust and metadata boundary.

Relying Party. The relying party validates presented information and applies service policy. It must not assume that an Atlas-mediated presentation is intrinsically truthful.

Recovery Participant. Recovery may involve additional devices, trusted people, escrow services or institutional identity proofing. Each method introduces coercion, availability and compromise risks.

Governance and Audit Body. Specifications, conformance programs, public logs or independent auditors may improve interoperability and accountability, but centralized governance can also create gatekeeping and capture.

## 07 Logical Components

Presence Controller. Maintains the root policy and authorizes lifecycle operations. It should support hardware-backed keys where available and threshold or multi-device authorization for sensitive changes.

Relationship Manager. Stores relationships as separate objects with purpose, identifiers, credentials, consent, endpoints, expiration and revocation state. It should prevent accidental cross-context linkage.

Context Manager. Defines personal, employment, financial, healthcare, public, private and pseudonymous contexts. Contexts may have separate keys, names, network paths and disclosure rules.

Credential Interface. Interacts with wallets, issuers and verifiers. Atlas should not require one credential format, but interoperability profiles may be needed to make selective disclosure and status checking predictable.

Device Registry. Records enrolled devices, keys, posture capabilities, last known state and allowed operations. Device state should be treated as time-bound evidence.

Policy Engine. Evaluates purpose, relationship, device, requested claims, risk, location sensitivity and user preferences. High-impact decisions should be explainable and reviewable.

Disclosure Engine. Produces the minimum presentation allowed by policy, including pairwise identifiers, derived attributes or proofs. It must prevent an application from silently escalating a request from one claim to an entire profile.

Connectivity Orchestrator. Selects existing transports, private overlays, egress policies or service endpoints. It should not require that all traffic traverse an Atlas operator.

Trust Verifier. Validates signatures, issuer chains, freshness, status, audience and proof binding. Verification results should retain uncertainty and not collapse into a universal trust score.

Recovery Manager. Coordinates replacement of compromised keys and restoration of relationships. Recovery events should be visible to affected parties where appropriate.

Audit and Transparency Service. Records security-relevant changes and disclosures in a privacy-preserving manner. Logs should avoid becoming a centralized history of the person's life.

Developer Interface. Allows applications to request a relationship, a claim or a connection through structured scopes. The interface should make purpose and requested disclosure clear to the person.

## 08 Lifecycle Operations

Creation. A presence begins by establishing controller keys, recovery policy and one or more contexts. Creation should not require a government identity unless a selected relationship requires it.

Device enrolment. A new device proves possession of a key and receives scoped authority. Sensitive enrolment may require confirmation from an existing device or recovery quorum.

Relationship establishment. The person and relying party exchange context-specific identifiers, endpoints and requested claims. The relationship object records purpose, scope and expiration.

Credential acquisition. An issuer delivers a credential to a wallet or compatible service. The presence records how it may be used but does not change the issuer's statement.

Presentation. A service requests information for a stated purpose. Policy selects the context, determines whether the request is acceptable and creates a minimal presentation bound to the relying party and transaction.

Connectivity selection. The presence may choose direct Internet access, a private mesh, enterprise access, a privacy-preserving relay or another existing path based on relationship policy.

Context transition. Moving from personal to employment activity must require a clear boundary. Applications should not inherit identifiers, routes or credentials from another context without explicit policy.

Revocation. A device, relationship, credential permission or transport authorization can be withdrawn independently. Revocation must propagate with defined timing and offline behaviour.

Recovery. After device loss or key compromise, the person reconstructs control through the selected recovery policy. Recovery should rotate affected keys and identify relationships that require re-binding.

Migration. The person exports or re-establishes the presence with another implementation or provider. Portability requires documented data formats, key transition mechanisms and relationship continuity rules.

Retirement. A person can close contexts or the entire presence. External organizations may retain records under their own legal obligations, but Atlas-controlled discovery, keys and active relationships should be withdrawable.

## 09 Context Separation and Privacy

Context separation is not an optional user-interface feature. It is a security requirement. Without it, a durable personal presence could make correlation easier than today's fragmented account model.

Each context should be capable of using separate identifiers, keys, credentials, network routes and contact endpoints. A context may disclose that two relationships involve the same person only when required and authorized.

Pairwise identifiers reduce passive correlation but do not eliminate it. Timing, IP addresses, device fingerprints, credential attributes and behavioural patterns can still link activity. Atlas therefore needs a layered privacy model rather than an identifier-only solution.

Selective disclosure should minimize attributes. A service asking whether a person is over a threshold should not automatically receive a birth date. A service verifying employment should not automatically learn the person's employee number or other employers.

The presence should support anonymous and pseudonymous contexts. Accountability can be relationship-specific; it does not require public legal identity. For example, a community may enforce reputation and moderation through a persistent pseudonym without knowing a civil name.

Network privacy and identity privacy are distinct. A private credential presentation may still be observable through traffic metadata. Conversely, an encrypted tunnel may conceal transport while the application receives a stable account identifier. Atlas must model both.

Consent cannot carry the entire privacy burden. People routinely accept complex requests under pressure. Defaults, data minimization, context isolation and limits on secondary use are necessary even when consent exists.

Recovery data presents special risk. Social recovery relationships, backup providers and identity-proofing events can reveal the person's most sensitive associations. Recovery metadata should be minimized and distributed where practical.

A presence must never imply invisibility from lawful or technical accountability. It should instead make disclosure explicit, bounded and attributable while resisting unnecessary surveillance.

## 10 Relationship to Existing Technologies

Identity and access management systems manage accounts, authentication and authorization within organizational boundaries. Atlas would consume those relationships but shift cross-provider coordination toward the person. The overlap is substantial; the distinction must be demonstrated through portability and context control.

Passkeys improve phishing-resistant authentication through public-key credentials scoped to relying parties. They are important building blocks but do not by themselves define cross-provider relationship policy, connectivity or recovery across a person's complete Internet activity.

Verifiable Credentials provide a standardized model for issuer-signed claims and presentations. They may supply much of the credential layer. Atlas should not invent a competing credential container and should treat current W3C work as primary prior art.

Decentralized Identifiers define identifiers controlled through cryptographic material and DID methods. They may support provider-independent or pairwise relationships, but their privacy and governance properties depend heavily on the chosen method and resolution system.

OAuth and OpenID Connect provide delegated authorization and federated authentication. They are service interaction protocols, not a complete personal presence, but a practical Atlas prototype would likely use them extensively.

Zero Trust architectures remove implicit trust based on network location and make access decisions using subject, device and resource context. Their typical control boundary is an enterprise or service operator. Atlas asks whether a complementary person-controlled policy boundary is missing.

VPN and mesh systems provide encrypted transport, alternate egress and private reachability. Some already bind users, devices, identity providers and policy in a coherent experience. They are among the strongest evidence that Atlas may be implemented as orchestration above existing systems rather than a new network protocol.

Personal data stores, wallets and consent systems address custody and disclosure of information. They overlap strongly with the relationship and credential portions of Atlas but may not coordinate network presence or secure connectivity.

Operating-system accounts and cloud ecosystems provide cross-device continuity, key synchronization, recovery and application identity. Their usability demonstrates the value of integrated presence, while their provider dependence demonstrates the portability question Atlas is investigating.

The research burden is to show a residual function after these technologies are composed. Similarity is not evidence of novelty.

## 11 Candidate Interaction Model

A service publishes a structured request describing the relationship purpose, requested claims, intended retention, acceptable issuers and supported proof mechanisms.

The person's Presence Agent evaluates the request inside the active context. It identifies which information is available, which disclosures are permitted and whether the service request conflicts with policy.

The agent presents a human-readable decision: the service, purpose, requested information, duration, connectivity requirement and consequences of refusal. Routine low-risk requests may follow standing policy; sensitive requests require direct confirmation.

The disclosure engine creates a presentation bound to the relying party, audience and transaction. Where possible it uses pairwise identifiers and derived proofs rather than raw source data.

The relying party verifies the proof and applies its own authorization policy. It returns a relationship object containing service identifiers, endpoints, renewal conditions and revocation methods.

The relationship manager stores the object only in the selected context. Connectivity policy may then invoke an existing secure path for that relationship without changing unrelated traffic.

Subsequent interactions use the established relationship while re-evaluating freshness, device state and requested scope. Material changes trigger renewed consent or policy evaluation.

Either party can terminate the active relationship. Termination does not erase records the other party is lawfully required to retain, but it stops future Atlas-mediated discovery, presentation and connectivity.

## 12 Security Threats and Abuse Cases

Universal correlation. A stable presence identifier could allow services, brokers or governments to combine activity. Mitigations include pairwise identifiers, unlinkable presentations, local relationship storage and prohibition of unnecessary global identifiers.

Controller compromise. Theft of controller keys could expose many relationships. Mitigations include hardware-backed keys, threshold authorization, operation-specific keys, transaction confirmation and rapid relationship re-binding.

Recovery takeover. Attackers may exploit identity proofing, trusted contacts or provider support. Recovery must be rate-limited, visible, challengeable and unable to silently preserve compromised keys.

Malicious agent software. A compromised device agent could release claims or merge contexts. Agents require least privilege, signed updates, local isolation, attestation where appropriate and clear revocation.

Provider capture. A dominant Atlas host could recreate the same provider ownership the project seeks to avoid. Portability, open formats, multiple implementations and independent key control are required.

Issuer overreach. Credential issuers may add unnecessary identifiers or tracking endpoints. The presence should expose credential privacy properties and allow the person to choose alternatives where accepted.

Relying-party coercion. Services may demand complete identity or link contexts as a condition of access. Technical minimization cannot fully solve market or legal coercion; governance and competition remain necessary.

False trust aggregation. Combining many credentials into a score could create opaque exclusion. Atlas should preserve claim provenance and avoid a universal reputation metric.

Metadata concentration. Relationship directories, revocation checks and routing services could reveal associations even when content is encrypted. Designs should minimize centralized queries and support privacy-preserving status mechanisms.

Lawful-process ambiguity. Provider-independent systems may complicate jurisdiction and evidence handling. Atlas must not promise immunity; it should document which operators hold which data and keys.

Denial of presence. Attackers or providers could block resolution, recovery or policy services. Offline credentials, redundant providers and local operation can reduce dependence, but some relationships will still require online validation.

Automation without intent. AI agents may act through a person's presence at machine speed. Delegation requires scopes, budgets, context limits, audit and revocation distinct from the human controller.

## 13 Governance Requirements

Governance must separate protocol conformance from authority over people. A standards body may define formats and interoperability but should not decide who a person is.

Implementations should publish threat models, data inventories, key custody models, recovery procedures, interoperability profiles and security contact information.

Conformance testing should verify context isolation, export, revocation, proof binding and failure behaviour. A product should not claim Atlas compatibility merely because it displays a persistent profile.

Open specifications are necessary but insufficient. Network effects, proprietary recovery systems and issuer acceptance can still produce lock-in. Governance should measure practical portability, not only format availability.

Versioning must permit correction. Atlas Papers should retain public change history, review comments and rejected proposals with rationale.

Privacy review should include people affected by coercive identity systems, not only enterprise and vendor stakeholders. Requirements that appear convenient in corporate access systems may be dangerous when generalized to public life.

The project should avoid premature certification or branding programs. Technical boundaries and reference tests must mature before compatibility marks have meaning.

Patents and licensing can obstruct implementation. The research phase should prefer royalty-free standards and clearly document intellectual-property concerns before architectural dependence develops.

## 14 Deployment Models

Local-first model. The primary controller, relationship catalogue and policy engine run on person-controlled devices. External services provide optional backup, credential status and connectivity. This model minimizes centralized metadata but complicates availability and recovery.

Hosted model. A provider operates most control functions for usability and continuous availability. Strong portability and person-held authorization keys are required to prevent provider ownership.

Federated model. Multiple providers host compatible presence services with migration and cross-provider relationships. Federation improves choice but introduces discovery, trust-framework and downgrade risks.

Enterprise-linked model. An organization supplies a work context connected to the person's broader presence. Employment credentials and policies remain employer-controlled, while the person can remove the context from personal devices when the relationship ends.

Wallet-centred model. An existing credential wallet becomes the main user experience, with relationship and connectivity extensions. This may be the simplest prototype and a strong test of whether Atlas requires a distinct platform.

Network-centred model. A mesh or secure-access system expands from private connectivity into personal relationship orchestration. This offers immediate network value but risks making tunnel membership the definition of presence.

Hybrid model. Local keys and policy are combined with redundant hosted discovery, recovery and connectivity services. A realistic implementation will probably be hybrid, but each outsourced function must have a defined exit path.

## 15 Minimum Viable Research Prototype

The first prototype should not attempt to create a global identity or new routing system. It should test the smallest residual function that existing products do not already provide coherently.

A useful prototype would create three isolated contexts on one person's devices: personal, employment and pseudonymous. Each context would have separate identifiers, keys, relationship objects and connectivity policies.

The prototype would integrate an existing identity provider for one relationship, a verifiable credential wallet for another, passkey authentication for a service and an existing WireGuard-based or similar mesh for private connectivity.

A relying-party demonstration would request a minimal claim, establish a pairwise relationship and receive an optional private service endpoint. The user would see exactly which context and claims were used.

The person would then move between home Wi-Fi, mobile data and public Wi-Fi without changing the relationship. Transport could change while the relationship identifier and policy remain valid.

A second device would be enrolled with scoped authority. The first device would then be revoked, and the prototype would measure propagation, recovery and relationship continuity.

The experiment would fail if it requires a universal identifier, leaks linkage across contexts, cannot migrate between controller implementations, or adds no meaningful function beyond configuring the component systems independently.

The prototype should produce packet-level, identity-flow and metadata diagrams so reviewers can identify hidden centralization and correlation.

## 16 Falsifiable Hypotheses and Evaluation Criteria

Hypothesis H1: People and services can gain useful continuity across providers without exposing one global identifier. Reject H1 if practical interoperability requires stable cross-context identifiers.

Hypothesis H2: Existing identity, credential and secure-connectivity systems leave a residual coordination problem. Reject H2 if the same user outcome can be achieved through documented composition with no new architectural boundary.

Hypothesis H3: A person can control disclosure while issuers and relying parties retain independent authority. Reject H3 if control requires the person to alter authoritative claims or override relying-party policy.

Hypothesis H4: Context separation can be strong enough to reduce correlation compared with conventional account ecosystems. Reject H4 if the presence creates more linkable metadata than the systems it coordinates.

Hypothesis H5: Provider portability is feasible without unacceptable usability or recovery costs. Reject H5 if safe migration is too complex for ordinary use or depends on one permanent operator.

Hypothesis H6: Connectivity policy can attach to relationships without routing all traffic through one Atlas service. Reject H6 if coherent presence requires centralized data-plane control.

Evaluation should measure disclosure minimization, cross-context linkability, key compromise blast radius, recovery time, revocation delay, migration completeness, service integration effort, user comprehension and metadata concentration.

Success is not the number of features implemented. Success is evidence that the proposed boundary is distinct, safer than alternatives and understandable to people and relying parties.

## 17 Open Questions for Industry Review

Which deployed architecture already provides portable person-controlled relationships across identity, credentials, devices and connectivity?

Is Personal Internet Presence a valid logical layer, or is personal control plane, wallet architecture or reference profile a more accurate description?

Which functions should never be combined because their metadata creates unacceptable correlation?

Can pairwise identifiers and selective disclosure work across mainstream services without excessive issuer and relying-party complexity?

What is the correct trust root for device enrolment and recovery when no single provider should own the person?

How should employment and other institution-controlled contexts attach to and detach from a personal presence?

Which existing standards should Atlas profile rather than extend?

What minimum information must a relying party learn to support abuse prevention and dispute resolution?

How can AI agents receive useful delegated authority without becoming indistinguishable from the person?

What evidence would justify ending the Atlas architecture effort because the problem is already solved or the risks exceed the benefit?

## 18 Conclusion

Atlas Paper 002 defines Personal Internet Presence as a proposed coordination and policy boundary, not a universal identity, new tunnel or replacement for existing Internet infrastructure.

The proposal is useful only if it leaves authoritative claims with issuers, access decisions with relying parties, network operation with providers and meaningful control with the person. It must preserve contextual identities rather than collapse them.

Existing technologies already provide most necessary primitives. That is a design advantage and a challenge to novelty. The next stage should test composition, privacy and portability through a constrained prototype before proposing new protocols.

The Atlas thesis remains provisional. Reviewers are invited to identify prior art, unsafe assumptions, unnecessary components and experiments capable of disproving the proposed layer.

## 19 References

[1] Project Atlas, Atlas Paper 001: The Missing Layer of the Internet, Version 0.1, July 2026.
[2] NIST Special Publication 800-207, Zero Trust Architecture, August 2020.
[3] W3C, Verifiable Credentials Data Model v2.0, W3C Recommendation, May 2025.
[4] W3C, Decentralized Identifiers (DIDs) v1.0, W3C Recommendation, July 2022; DID v1.1 work remains under development in 2026.
[5] IETF RFC 6749, The OAuth 2.0 Authorization Framework, October 2012.
[6] OpenID Foundation, OpenID Connect Core 1.0 incorporating errata set 2, December 2023.
[7] W3C, Web Authentication: An API for Accessing Public Key Credentials, Level 2, April 2021.
[8] IETF RFC 9421, HTTP Message Signatures, February 2024.
[9] IETF RFC 9449, OAuth 2.0 Demonstrating Proof of Possession, September 2023.
[10] Jason A. Donenfeld, WireGuard: Next Generation Kernel Network Tunnel, 2017.
[11] NIST Special Publication 800-63 Digital Identity Guidelines series.
[12] IETF RFC 8446, The Transport Layer Security (TLS) Protocol Version 1.3, August 2018.

---
**Call for review:** Identify prior art, unsafe assumptions, unnecessary components, and experiments that could disprove the proposed layer.