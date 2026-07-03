# Critique Framework — Multi-Perspective, Diagnosis-Only

Adapted from the critique system in `ARPeeketi/claude-resume-kit` (MIT License). The original
critiques a resume *and proposes rewritten text*. This version is **audit-only**: every part
below has been converted to diagnosis. You identify problems and state the criteria a strong
version must meet — you never supply replacement text. See the no-write contract in `SKILL.md`.

**Table of contents**
1. Part 0 — Domain-specialist lens (JD-aware)
2. Part 1 — Five-perspective read-through
3. Part 2 — Eight-dimension scoring (+ profile weights)
4. Part 3 — Interview likelihood + ceiling
5. Part 4 — Tiered findings (diagnosis-only)
6. Part 5 — Interview bridge points
7. Part 6 — Authenticity / AI-fingerprint scan (12 items)
8. Part 7 — Mechanical & structural verification
9. LaTeX rendered-character budget card
10. Output template

---

## Part 0: Domain-Specialist Lens (build only if a JD is present)

Construct fresh for THIS job + company. No templates. Produce 7 elements:

1. **Reviewer persona** — who actually reads this? Title, seniority, what they do daily, how
   many resumes they've seen for this posting, what makes them roll their eyes, what would
   impress them.
2. **Company context** — what the company makes/sells/researches, R&D culture, recent
   priorities, and the vocabulary that signals "insider" vs "applied generically". Flag
   assumptions; web-search 1–2× if context is thin and search is available.
3. **JD vocabulary extraction** — read the JD three times (requirements / culture / vocabulary).
   Pull the 8–10 most important terms, ranked by frequency, title-vs-body placement, and
   binary-capability vs spectrum-skill.
4. **Gap map (diagnosis, not rewrite)** — for each high-value JD term, is it present, partial,
   or absent in the resume? Do **not** write the line that would add it. Use this shape:

   | JD term | Times in JD | In resume? | Gap severity |
   |---|---|---|---|
   | [term] | [N] | YES / PARTIAL / NO | Fatal / Serious / Cosmetic |

   - **Fatal:** binary capability the JD requires, a title-line term, or anything repeated 3+×.
   - **Serious:** preferred quals competitive candidates will have.
   - **Cosmetic:** buried nice-to-haves most candidates also lack.
   - For each gap, note whether it's bridgeable truthfully or a hard background limitation —
     but leave the bridging to the candidate.
5. **Methodology-transfer test** — for the candidate's top ~5 achievements, can you write one
   honest sentence explaining how an expert at THIS company sees it mapping to their work? If
   yes, the resume bridged it; if you struggle, the resume hasn't made the transfer explicit;
   if you can't honestly, it's a hard gap. Report which bucket each falls in — don't write the
   bridge into their resume.
6. **Competitive landscape** — who's the "obvious fit" candidate, what this candidate offers
   that they don't, and what they offer that this candidate doesn't. This tells you what the
   resume must emphasize vs. what it must bridge.

(If no JD: skip Part 0. ATS and domain-fit scoring become low-confidence — say so.)

---

## Part 1: Five-Perspective Read-Through

Read the resume as five readers in order; each sees only what they'd actually read in their
window. Return a verdict per reader. All five read *through* the Part 0 lens when a JD exists.

- **ATS robot (0s, keyword scan):** extract top ~20 JD keywords; for each, verbatim / semantic /
  absent. Match rate: ≥70% PASS, 60–69% MARGINAL, <60% FAIL. Flag any JD term appearing 3+×
  with 0 resume hits. Output: match table + rate + top 3 truthfully-addable gaps (named as
  gaps, not written in).
- **Recruiter (10s):** reads name, current title/employer, education line, tagline, first 2
  summary lines. Verdict: Forward / Maybe / Reject + one sentence.
- **HR screen (30s):** summary + skills headers + first bullet per role + education. Does the
  summary bridge to the target domain? Do skills *group names* signal relevance? Verdict: Phone
  screen / Borderline / Pass + one sentence.
- **Hiring manager (2min, domain expert):** everything. Methodology transfer visible? Narrative
  arc logical? Red flags / overclaiming? Differentiator visible? Verdict: Interview / Maybe / No
  + top 3 observations + predicted first interview question.
- **Technical reviewer (10min):** every bullet. Truthfulness (flag implausible/unverifiable
  claims as *questions to verify*, not corrections), verb discipline (hedged verbs for shared
  work), internal consistency (summary vs bullets vs any cover letter), keyword over-saturation
  (concern at 9+ repeats). Output: claims-to-verify list + inconsistencies.

---

## Part 2: Eight-Dimension Scoring

Score each dimension 0–10 (rubric below), multiply by the profile weight, total to 100.

**Industry / general profile (default):**

| # | Dimension | Weight | Assess |
|---|---|---|---|
| 1 | ATS & Keyword Match | 15% | JD coverage, verbatim vs semantic, missing high-value terms (low-confidence if no JD) |
| 2 | Summary & Positioning | 10% | Bridge sentence, target-domain language, prestige signal, forward intent |
| 3 | Skills Section | 10% | Group names signal relevance, content relevance, no filler, emphasis accuracy |
| 4 | Bullet Quality | 25% | Outcome-first, quantification, action verbs, JD alignment per bullet (HIGH/MED/LOW) |
| 5 | Impact & Metrics | 15% | Quantified results, scope/scale, business or research value made explicit |
| 6 | Narrative Coherence | 15% | Header-to-footer story, consistent thread, first-impression timing |
| 7 | Formatting & Density | 5% | Length/page budget, layout consistency, orphans/page-fill (LaTeX), readability |
| 8 | Credibility Signals | 5% | Awards, named entities, leadership/ownership evidence, adoption/recognition |

**Academic / research profile:** replace #5 *Impact & Metrics* with **Publication Selection**
(venue prestige, tag relevance, first-author ratio, domain-gap acknowledgment) and use these
weights: ATS 15, Summary 10, Skills 10, Bullets 25, Publications 10, Narrative 15, Formatting &
Visual 5, Credibility 10.

**Per-dimension band:** 9–10 essentially optimal for this candidate/JD · 8–8.5 strong, diminishing
returns · 7–7.5 good but closable gaps · 6–6.5 significant gaps (missing bridge, wrong vocabulary,
weak bullets) · <6 major problems (wrong framing, overclaiming, format violations).

**Total band:** 85+ at/near ceiling, submit · 80–84 strong, 1–2 targeted fixes · 75–79 good base,
missing reframing or key bullets · 70–74 first-draft, needs systematic pass · <70 fundamental issues.

---

## Part 3: Interview Likelihood + Ceiling

| Reader | Time | Question | Outcome |
|---|---|---|---|
| ATS | 0s | Keywords match? | PASS / FAIL |
| Recruiter | 10s | Credible for this level? | FORWARD / REJECT |
| HR | 30s | Meets basic quals? | PHONE SCREEN / PASS |
| Hiring manager | 2m | Would I learn something in an interview? | INTERVIEW / MAYBE / NO |
| Technical | 10m | Can they do the work? | STRONG YES / YES / CONCERNS |

Give each reader a probability + the single deciding factor. Then a ceiling read: current score →
max achievable with the top fixes → hard ceiling set by background → what (truthfully) would
raise the ceiling. Frame all of this as analysis; don't write the fixes for them.

---

## Part 4: Tiered Findings — DIAGNOSIS ONLY

The most important section, and the one where rewriting tempts hardest. **No replacement text.**
For every finding use exactly this shape:

- **Location:** quote the candidate's current text verbatim (reference only).
- **Problem:** what's wrong and why it costs points.
- **Criteria for a strong version:** what it must *do* (lead with outcome / attach a metric /
  name the method / cut to one line / etc.) — never a sentence they could paste.
- **Estimated impact:** points.

Tiers: **Tier 1** ≥1 pt each (missed reframing, fatal keyword gap, weak/empty summary bridge,
a weak bullet that a stronger existing achievement should replace) · **Tier 2** 0.3–0.9 ·
**Tier 3** <0.3 (saturation trim, minor polish). End with a verdict: which tiers are worth the effort.

---

## Part 5: Interview Bridge Points (audit-adjacent, optional)

5–7 points mapping a resume topic to how the candidate would *talk* about it. This is spoken
interview prep, not resume copy.

| Resume topic | Target-domain equivalent | What to be ready to say |
|---|---|---|
| [their achievement] | [how it maps] | [the connection to make aloud — a prompt, not a script] |

---

## Part 6: Authenticity / AI-Fingerprint Scan (12 items)

Run on the full document. Each hit is a Tier 1 finding — reported as a flag, never fixed for them.

1. Any Tier-1 banned word? (delve, tapestry, multifaceted, pivotal, realm, synergy, paradigm,
   holistic, nuanced, foster, embark, leverage, utilize, harness, spearhead, cornerstone,
   metaphorical landscape/journey, cutting-edge, groundbreaking, "novel"/"innovative" unless
   quoting the JD)
2. Any banned phrase? ("proven track record", "passionate about", "demonstrated ability to",
   "well-versed in", "adept at", "at the intersection of X and Y", "in today's rapidly evolving…")
3. More than 2 em-dashes (`---`) in the document?
4. Any bullet ending on a vague `-ing` analysis phrase ("…enabling improved efficiency")? This is
   the #1 structural AI tell. (A bullet ending on a concrete metric — "…contributing to a 15%
   reduction" — is fine.)
5. Three or more consecutive sentences of similar length?
6. Paragraph/section openers repeating the same structure ("My research…", "My experience…")?
7. More than 2 "X, Y, and Z" triplets in the document?
8. Cover letter (if present) opens with a generic line rather than a company-specific reference?
9. Metaphorical "landscape / journey / realm / tapestry"?
10. Passive voice in more than ~20% of bullet verbs?
11. Honors/Fellowships items using `---` instead of `. `?
12. Any banned adverb (meticulously, notably, subsequently, remarkably, seamlessly, thereby)?

---

## Part 7: Mechanical & Structural Verification (pass/fail)

- Bullets within character limits (LaTeX: per the budget card; other formats: not over ~2 lines).
- Multi-line bullets clear the orphan threshold (LaTeX only, requires compile).
- Page count / length within the target budget; page 2+ adequately filled.
- Dates consistent (Mon YYYY -- Mon YYYY); company/institution names spelled consistently.
- Contact line present and internally consistent.
- (LaTeX) file compiles standalone; if compile fails, say "visual checks not verified".

Any fail → Tier 1 finding.

---

## LaTeX Rendered-Character Budget Card

Measure *rendered* characters (strip `\textbf{}`, `\textit{}`, `\ce{}`, `$…$`, `\href{url}{text}`
→ text; `--` → 1; `$\beta$` → 1). Use `scripts/char_count.py`.

```
RESUME (2-page, 10pt):  1-line bullet 105–111 (HARD MAX 117) | 2-line 189–205, target ~200
                        (HARD MAX 218; last line ≥ 78 chars or it orphans)
                        Summary ~5 lines, 500–555 chars. Skills 5 groups (≈4-3-2-2-2, 13 lines).
CV (5-page, 11pt):      2-line 168–182 (MAX 190) | 3-line 250–268, target ~260 (MAX 280;
                        last line ≥ 65). ~45 rendered bullet lines total.
```
Aim for the middle of the range, not the hard max. Bold steals width (~0.4 char per bold char).
These are diagnostic thresholds — report over-budget/orphan bullets as findings; don't rewrite them.

---

## Output Template

```markdown
# Resume Audit — [Role / Target, or "general"] · Score: XX.X/100

**Reviewed:** [filename or "pasted resume"] · **JD:** [provided / none] · **Profile:** [industry | academic]
[If LaTeX and not compiled: "⚠ Could not compile — orphan/page-fill checks unverified."]

## Score
| Dimension | Score | Weight | Weighted | Note |
|---|---|---|---|---|
| … | X/10 | NN% | X.XX | [one line] |
| **Total** | | **100%** | **XX.X** | |

## Domain-Specialist Lens   [omit if no JD]
[Reviewer persona · company context · JD vocabulary · gap map · methodology-transfer · landscape]

## Five Readers
- ATS: [rate] — [PASS/MARGINAL/FAIL]
- Recruiter (10s): [Forward/Maybe/Reject] — [reason]
- HR (30s): [Phone screen/Borderline/Pass] — [reason]
- Hiring manager (2m): [Interview/Maybe/No] — [top 3 + predicted first question]
- Technical (10m): [claims to verify] · [inconsistencies]

## Interview Likelihood
| Reader | Probability | Deciding factor |
[Ceiling: current XX → with top fixes XX → hard ceiling XX → what would raise it]

## Findings (diagnosis only — no rewrites)
### Tier 1 (do these)
- **Location:** "[quoted current text]" · **Problem:** … · **Strong version must:** … · **+N pts**
### Tier 2 (optional)
### Tier 3 (skip)
**Verdict:** [which tiers are worth it]

## Authenticity scan
[Pass, or list of flagged items]

## Interview bridge points   [optional]
[5–7 talking-point prompts]
```

After producing the report, STOP and present the score table, Tier 1 findings, and interview
likelihood. The candidate edits their own document; offer a fresh re-audit of the revision.
