# SPEC.md: what we will build for Project XYZ

Briefly describe the project in up to three sentences. This defines the Source of Truth for features.
- User stories, acceptance criteria, and functional requirements.
- Utility: Agents refer to this to ensure they aren't "hallucinating" features that don't belong.
- **DO NOT** put the "how" here, that is done in AGENTS.md

## Motivation (Problem Statement and Solution)

Summarize the problem we wish to solve in a few bullet points. Then give an overview of the solution we will build.

## Product Requirements (Functional)

- Bulleted list of product (customer facing) requirements for the project
- Label each requirement as P0 (priority zero, must have) or P1 (priority 1, nice to have).
- Make each requirement concise and clear. Wherever possible each requirement should tie back to the problem statement.

### Examples of Good Requirements
- **P0:** Users must be able to reset their password via an emailed magic link within 5 minutes of request.
- **P0:** Dashboard must display a real-time count of active fitness sessions.
- **P1:** Users can export their workout history as a PDF.
*Why: They are measurable, specific, and define the 'What' without specifying the 'How'.*

### Examples of Poor Requirements
- **Poor:** Make the login page look "clean." (Subjective)
- **Poor:** Use a SQL database to store user names. (Prescriptive "How" - belongs in ARCHITECTURE.md)
- **Poor:** The app should be fast. (Not measurable)

## Technical Requirements (Non-Functional)

- Bulleted list of technical requirements to achieve the product requirements.
- Be concise but specific.

### Examples of Good Requirements
1. All APIs should target a p90 latency of 100 milliseconds.
2. All PII (Personally Identifiable Information) must be encrypted at rest using AES-256.
3. The system must support 500 concurrent WebSocket connections.
4. Carefully design the uniqueness of primary keys. **Default to UUIDv7** for any UUID primary key — it is time-sortable and gives B-tree locality close to serial integers without giving up global uniqueness. Reach for UUIDv4 only when unguessability dominates and you accept the index-locality cost.
5. If storing datetime information, default to high-fidelity data types that store both time and timezone information (e.g., `timestamptz` for PostgreSQL).

### Examples of Bad Requirements
1. Don't use too much memory. (Vague)
2. Use a Node.js server. (Implementation detail, belongs in ARCHITECTURE.md)

## Milestones

Break the project down into logical sets of release criteria.

1. **Prototype:** Implement a subset of P0 requirements to test core functionality and feasibility.
2. **GA (General Availability):** All P0 requirements are complete, tested, and documented.

> **Where do hardening / operational items live?** Standards you commit to (e.g. "automated nightly backups with quarterly restore drill", "monthly dependency upgrade cadence") belong in **Technical Requirements** above. Tracking whether each one is done yet belongs in **IMPLEMENTATION_PLAN.md**. SPEC.md describes *what the project is*, not *what work is outstanding*.
