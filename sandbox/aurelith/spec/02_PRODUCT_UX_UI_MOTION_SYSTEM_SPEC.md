# AURELITH — Product, UX, UI and Motion System Specification
Version: 1.0
Role: L1 / Design + Frontend System Spec
Owner: Design Architect Agent
Depends on: 01_MASTER_CREATIVE_EXECUTION_BRIEF.md

## 1. Full Information Architecture

### 1. Site Header
Goal:
- establish brand
- provide immediate navigation
- keep conversion visible without stealing hero focus

Question answered:
- Where am I and what can I do first?

Content hierarchy:
1. wordmark
2. nav links
3. secondary CTA
4. primary CTA

Motion meaning:
- subtle fade/slide on load
- compact transform on scroll
- reinforces control and polish

### 2. Hero
Goal:
- create emotional lock-in
- establish the premium robotics thesis
- deliver immediate intrigue plus action path

Question answered:
- What is AURELITH and why should I care?

### 3. Trust / Social Proof
Goal:
- create credibility quickly
- reduce “fictional luxury vaporware” skepticism

Question answered:
- Is this brand credible, serious, and premium?

### 4. Feature Storytelling Sequence
Goal:
- convert abstract magic into understandable capabilities

Question answered:
- What does the product actually do?

### 5. Immersive Motion Showcase
Goal:
- demonstrate elegance of product behavior in a cinematic way

Question answered:
- How does it feel in motion?

### 6. Product Mechanics / How It Works
Goal:
- explain sensing, learning, actuation, environment logic

Question answered:
- What is happening behind the scenes?

### 7. Value / Comparison Block
Goal:
- frame AURELITH against conventional smart-home clutter

Question answered:
- Why this instead of typical fragmented automation stacks?

### 8. Testimonials / Credibility
Goal:
- establish social proof, aspiration and expert framing

Question answered:
- Who trusts this and what outcomes do they describe?

### 9. Primary CTA Block
Goal:
- concentrate intent after narrative build-up

Question answered:
- What should I do next?

### 10. FAQ
Goal:
- remove objections
- reduce friction before conversion

Question answered:
- What would stop me from taking action?

### 11. Footer
Goal:
- close with confidence and clarity
- offer low-friction secondary paths

Question answered:
- Where do I go if I need details, contact, legal, or follow-up?

---

## 2. Section-by-Section UI Spec

### Header
Elements:
- logo mark
- wordmark
- nav cluster
- “Watch in motion” secondary CTA
- “Book private preview” primary CTA
- mobile menu trigger

Layout:
- max-width container
- glass-dark elevated surface on top
- transparent at top, denser after scroll threshold

Responsive:
- desktop full nav
- tablet compressed nav
- mobile drawer

Interaction:
- hover underline / opacity shift
- focus visible ring
- sticky compression on scroll

Accessibility:
- semantic header
- nav inside landmark
- mobile menu button with correct expanded state

---

### Hero
Elements:
- overline label
- main headline
- subheadline
- primary CTA
- secondary CTA
- trust line
- visual anchor
- scroll cue

Layout:
- 2-column desktop
- stacked mobile
- narrative-led central focal composition

Typography:
- headline XL display
- supporting text max 2–3 concise lines
- strong CTA contrast

Motion:
- layered reveal
- visual object breath/float
- scroll-driven parallax
- hero handoff into pinned sequence

Accessibility:
- headline visible as actual text, not canvas-only
- buttons keyboard accessible
- all critical content available without motion interpretation

---

## 3. Hero Cinematic Breakdown

### Opening Composition
- near-black architectural background
- fine orbital grid lines
- ambient light sweep
- central robotic silhouette emerging from darkness
- headline enters from low-opacity masked reveal
- UI chrome remains minimal

### First 100vh
- wordmark and header appear with soft delayed precision
- hero headline reveals line by line
- robot silhouette resolves into product form
- CTA pair appears after headline lock
- trust indicator fades in last
- scroll cue animates subtly, not bouncing aggressively

### 100–200vh
- hero becomes pinned on desktop
- product object rotates minimally or shifts perspective
- supporting callouts appear around the object
- subheadline compresses as story transitions
- background depth layers move slower than foreground copy

### 200–300vh
- hero transitions into product intelligence sequence
- robotic object fractures into system layers:
  sensing / movement / orchestration / adaptation
- CTA remains reachable in fixed logical position or reappears at section boundary
- pinned phase ends before fatigue

### Handoff
- hero exits by dimming visual dominance
- next section inherits spatial grid and motion axis
- transition feels like “moving inside the product system”

---

## 4. Motion System

### Principles
- motion must explain state, hierarchy, causality
- motion density alternates by section rhythm
- heavier choreography reserved for hero and one showcase section
- content-heavy sections use restrained reveals

### Duration Scale
- fast: 120–180ms
- base: 220–320ms
- expressive: 420–650ms
- cinematic: 900–1600ms
- scrub-linked timelines tied to scroll distance, not arbitrary fixed time

### Easing
- standard: smooth UI transitions
- emphasized: primary CTA and focused reveal
- exit: accelerated but soft
- no rubber-band or novelty easing

### Reveal Rules
- text: mask or y+opacity, never over-stylized
- cards: subtle translateY + opacity
- large panels: scale 0.98 to 1 + opacity
- section intros: stagger only when it improves scan order

### Pinning Rules
- only hero + one storytelling section pinned on desktop
- mobile pinning reduced or removed
- pin must not trap user
- pin length tied to actual narrative payoff

### Reduced Motion
- replace transforms with opacity / immediate state changes
- disable parallax, magnetic motion, scroll-linked depth
- preserve content hierarchy and CTA prominence

---

## 5. Design Tokens (Concept Layer)

### Colors
- color.bg.canvas
- color.bg.surface
- color.bg.elevated
- color.text.primary
- color.text.secondary
- color.text.muted
- color.accent.brand
- color.accent.soft
- color.border.subtle
- color.border.strong

### Typography
- type.display.1
- type.display.2
- type.heading.1
- type.heading.2
- type.body.lg
- type.body.md
- type.label.sm
- type.caption.sm

### Motion
- motion.duration.instant
- motion.duration.fast
- motion.duration.base
- motion.duration.slow
- motion.duration.cinematic
- motion.ease.standard
- motion.ease.emphasized
- motion.ease.exit

---

## 6. Conversion Logic

Primary CTA:
Book a private preview

Why:
Luxury robotics at early-stage premium positioning is better suited to:
- invite
- consultation
- access
- preview
than direct commodity purchase

Secondary CTA:
Watch the system in motion

Progressive commitment:
hero → motion proof → mechanics → trust → CTA → FAQ → CTA repeat
