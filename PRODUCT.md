# Product

## Register

product

## Users

An internal, mixed-skill team at an AI market-research company. Some are trained
researchers with domain fluency; others are PMs, operators, or generalists who
need a well-structured guide without formal research training. They use this tool
as one step in a larger pipeline: the interview-guide template they build here is
handed off to an **AI interviewer agent** that conducts real interviews from it.
Their context is focused work inside a professional workflow — they want to get a
trustworthy guide built and move on, not linger in the tool.

## Product Purpose

A single-page builder where the user chats with an AI assistant that fills a
structured interview-guide template in real time. The output is not the end
product — it is an instrument that downstream AI agents execute. That raises the
stakes on structure and clarity: a vague objective or sloppy pacing rule becomes a
worse interview at scale. Success is the user leaving with a solid, well-structured
guide **quickly** and **trusting** that it will drive good interviews.

## Brand Personality

Precise and professional. Calm, exact, trustworthy — the interface should read
like a serious research instrument, not a marketing surface. Restraint over
flourish. Voice is direct and competent; it guides without hand-holding and never
performs. The tool should feel considered and quietly confident, so a mixed-skill
team trusts the output enough to ship it to the interviewer agent.

**This tool is joining Forven, an existing product with an established design
system.** Personality must be expressed *through* that house style, not against it:
a warm terracotta accent, peach/apricot tints, navy-slate ink, cool blue-gray
ground, humanist sans, and uppercase tracked eyebrows. See DESIGN.md for the full
visual spec. The builder's current indigo (`#4f46e5`) is inherited, off-brand, and
slated for migration onto the Forven palette.

## Anti-references

- **Consumer / playful.** No bright rounded gamified energy, no emoji-as-decoration,
  no cute microcopy. This is a professional tool, not a consumer app.
- **Heavy enterprise.** No dense, gray, cluttered legacy-software feel; using it
  should not be a chore. Density in service of the task, never clutter for its own sake.
- **Over-designed / flashy.** No animation-heavy, decorative, attention-grabbing
  design that competes with the work. Motion and ornament must earn their place.
- **Off-brand accents.** No indigo/cool-blue accent (the current inherited
  `#4f46e5`) and nothing that fights Forven's warm terracotta identity.

> **Note on "AI-slop" defaults.** Generic design guidance flags warm/cream tints and
> per-section uppercase eyebrows as AI-slop tells. That guidance does **not** apply
> here: warm peach/apricot tints and tracked eyebrows are Forven's deliberate,
> established house style. Identity-preservation wins — keep them. What still counts
> as slop for this project: gradient accents, hero-metric blocks, glassmorphism, and
> identical icon-card grids used without purpose.

## Design Principles

1. **The guide is an instrument, not a document.** Every design choice should make
   structure and clarity legible, because a downstream agent executes what's here.
   Surface the shape of the template, not just its text.
2. **Confidence through clarity.** A mixed-skill team should always know what a
   field means, why it matters, and whether it's good enough. Trust is earned by
   making quality visible, not by decoration.
3. **Speed is a feature.** Reduce friction to a finished guide. Defaults, live
   feedback, and quick actions should shorten the path; nothing should slow a
   confident user down.
4. **Restraint over flourish.** When in doubt, remove. The interface recedes so the
   template and the conversation are the focus.
5. **Earn every signal.** The limited color and motion budget (one committed accent,
   a secondary alert hue) is spent only where it carries meaning — state, emphasis,
   or warning — never for decoration.

## Accessibility & Inclusion

Target WCAG 2.1 AA. Body text ≥ 4.5:1 contrast (large text ≥ 3:1), including
placeholder and muted-label text. Full keyboard operability with visible focus
states on all interactive controls (buttons, sliders, inputs, modal). Honor
`prefers-reduced-motion` with a non-motion alternative for every animation. Modal
and dynamic (SSE-updated) regions should be announced appropriately to assistive
tech.
