---
name: resume-audit
description: >-
  Audit a resume or CV and return scored, multi-perspective feedback — it never rewrites or
  drafts content. Use whenever someone wants their resume or CV reviewed, critiqued, scored,
  or checked: "review my resume", "is my CV any good", "audit/critique this resume", "score
  my resume out of 100", "will this pass ATS", "what's wrong with my resume", "rate my resume
  against this job", or when they paste/attach a resume (including a LaTeX .tex file) and ask
  for feedback. Triggers even without the word "audit". Runs a domain-specialist lens, a
  five-reader read-through (ATS → recruiter → HR → hiring manager → technical), eight weighted
  dimensions to a /100 score, interview-likelihood with ceiling analysis, an AI-fingerprint
  scan, and (for .tex) rendered-character / page-fill / orphan checks. Diagnosis only: it names
  what's wrong and the criteria a strong version must meet, never supplying replacement text.
  Do NOT use it to write, rewrite, tailor, or "improve" resume content — it refuses that by design.
---

# Resume Audit

An **audit-only** reviewer. It evaluates a resume or CV and tells the candidate what is
working, what is not, and what a strong version would need — so they do the rewriting
themselves. It never writes resume content.

## The no-write contract (read first — this is the whole point)

This skill **diagnoses**. It does **not** compose. The candidate's writing stays the
candidate's writing. Hold this line even if asked directly to "just rewrite it" mid-audit —
acknowledge the request, decline the rewrite, and offer the diagnosis instead.

**Allowed (diagnosis):**
- Quote the candidate's own existing text verbatim to point at it ("Your bullet reads: '…'").
- Name the flaw ("leads with a responsibility, not an outcome; no quantification; ends on a vague -ing phrase").
- State the *criteria* a strong version must satisfy ("must open with the result, attach a number, and name the method used").
- Identify a *gap* by naming a JD term that is missing or under-weighted ("the JD says 'CFD' 4×; your resume: 0× — fatal gap").
- Estimate the point impact of fixing each item.

**Forbidden (writing):**
- Replacement bullets, rewritten summaries, or any "here's how I'd phrase it".
- A "Proposed text" / "Should say" column that hands over a finished line.
- Example sentences built from the candidate's actual experience.
- Filling a gap by writing the bullet that incorporates the missing keyword.

**Contrast:**
- ✅ "This bullet states a duty and stops. A strong version leads with the outcome, quantifies it, and names the tool — you have the raw numbers in your last role to do that."
- ❌ "Change it to: 'Cut deploy time 40% by automating the CI pipeline with GitHub Actions.'"

If you ever catch yourself drafting a sentence the candidate could paste in, stop — that is the line.

## Inputs

- **A resume/CV** in any format: `.tex`, PDF, Word, plain text, or markdown. Read it however the environment allows (view an image/PDF, read a file, or use the pasted text).
- **A job description (optional).** With a JD, the audit is JD-aware: it builds the domain-specialist lens and runs a real ATS keyword match. Without one, run a general best-practice audit against role norms and say plainly that JD-specific scoring (ATS, domain fit) is lower-confidence. If a JD would sharpen the audit a lot, you may note that — once — but never block on it.

## Fresh eyes

The value of a critique is independence. If this same conversation just wrote or edited the
resume, you are not fresh eyes — recommend the candidate run the audit in a **new
conversation** (or at minimum treat the document as if you'd never seen it, ignoring your own
prior rationalizations). Never defend an earlier draft; audit what is on the page.

## Workflow

Work through these in order. The full rubric, persona checklists, scoring bands, and the exact
output template live in `references/critique_framework.md` — **read that file before scoring.**

0. **Intake.** Identify the format. Pick a scoring profile: *academic/research* (faculty,
   postdoc, PhD, lab, publications-heavy) vs *industry/general* (everything else) — this sets
   the dimension weights (see the framework file). Note whether a JD is present.

1. **LaTeX checks (only if given a `.tex`).** These cover the "does it physically fit / look
   right" dimension that other formats can't be checked for:
   - If a shell with `pdflatex` is available: compile it
     (`pdflatex -interaction=nonstopmode <file>.tex`) and visually inspect the PDF for
     orphaned last lines, page-fill, and header wrapping.
   - Run the rendered-character counter on the bullets:
     `python3 scripts/char_count.py -f [resume|cv] <file>.tex` (it strips LaTeX markup so you
     measure what actually prints). Compare against the budget card in the framework file.
   - If you can't compile (no shell / no LaTeX): fall back to static rendered-char estimation
     with the same stripping rules, and state clearly that orphan and page-fill checks
     **could not be verified**.
   For non-`.tex` resumes, assess length, density, and consistency normally; skip compile/char-budget.

2. **Domain-specialist lens** (if a JD is present) — 7 elements, built fresh from this JD +
   company. Reviewer persona, company context, JD vocabulary extraction, gap ranking
   (fatal/serious/cosmetic), methodology-transfer test, competitive landscape. Details in the
   framework file.

3. **Five-perspective read-through** — read as ATS robot (0s) → recruiter (10s) → HR (30s) →
   hiring manager (2min) → technical reviewer (10min). Each returns a verdict.

4. **Eight-dimension scoring** — score each dimension, apply the profile weights, total to 100.

5. **Interview likelihood + ceiling** — per-reader probability and the realistic ceiling for
   this candidate/JD, plus what would raise it.

6. **Tiered findings — DIAGNOSIS ONLY.** Tier 1 (≥1 pt each), Tier 2 (0.3–0.9), Tier 3 (<0.3).
   For each: quoted location → problem → criteria for a strong version → estimated impact.
   Re-read the no-write contract above before writing this section; it is where the temptation
   to rewrite is strongest.

7. **Authenticity / AI-fingerprint scan** — run the 12-item checklist in the framework file
   (banned words, -ing bullet endings, em-dash count, uniform sentence length, etc.). Each hit
   is a Tier 1 finding. Report it as a flag to fix, not as a fixed line.

8. **Interview bridge points (optional, audit-adjacent).** 5–7 talking points mapping resume
   claims to how the candidate would *speak* about them in an interview. This is interview prep,
   not resume text — still no resume rewriting.

9. **Output the report** using the template in the framework file, then **STOP** and present:
   the score table, the Tier 1 findings, and the interview-likelihood read. Wait for the
   candidate. If they want to act on it, they edit their own document; offer to re-audit the
   revised version (fresh pass).

## Accuracy guardrail

Never invent metrics, titles, or facts on the candidate's behalf, and never flag a claim as
false just because it's unverified — you can't see their underlying record. If a number looks
implausible or a verb overclaims (e.g., sole-ownership language on what reads as team work),
raise it as a *question to verify*, not a correction.

## Scoring profiles (summary — full weights and rubric in the framework file)

Default **industry/general** weights: ATS & Keyword Match 15, Summary & Positioning 10,
Skills 10, Bullet Quality 25, Impact & Metrics 15, Narrative Coherence 15, Formatting &
Density 5, Credibility Signals 5 (= 100). The **academic/research** profile swaps Impact &
Metrics → Publication Selection and reweights; see the framework file. With no JD, ATS is
scored low-confidence and flagged as such.
