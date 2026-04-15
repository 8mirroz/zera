# Phase 3: UI & Motion Specification (AURELITH)
Status: COMPLETED (PASS)
Timestamp: 2026-04-14T17:50:00Z

## UI Foundations (Design DNA)
- **Canvas**: Graphite (#0C0C0C) to Obsidian (#050505) gradient.
- **Accents**: Amber Luminous (#FFBF00) for high-intent actions.
- **Materials**: Glassmorphism with `backdrop-filter: blur(20px)` for overlays.

## Motion Choreography
- **Hero Sequence**: 
  - `0-100vh`: Silhouette fade-in.
  - `100-200vh`: Unit expansion using GSAP Flip.
  - `200-300vh`: Floating UI callouts pinned with ScrollTrigger.
- **Micro-interactions**: Framer Motion `whileHover={{ scale: 1.02 }}` on luxury cards.
- **Reduced Motion**: All `y: 100` transforms replaced with `opacity: 0 -> 1` fades.

## Performance Budget
- Total JS: < 250kb (Gzip).
- GSAP Plugins: ScrollTrigger, SplitText (Custom build).
- Lenis Smooth Scroll enabled for global ease.
