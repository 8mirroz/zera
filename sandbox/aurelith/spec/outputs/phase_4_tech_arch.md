# Phase 4: Frontend Architecture (AURELITH)
Status: COMPLETED (PASS)
Timestamp: 2026-04-14T17:55:00Z

## Tech Stack
- **Core**: Next.js 14 (App Router), TypeScript.
- **Styling**: Tailwind CSS + `clsx` for dynamic grouping.
- **Motion**: 
  - `GSAP` + `ScrollTrigger` (Orchestration).
  - `Framer Motion` (Local UI Transitions).
  - `Lenis` (Smooth Scrolling).

## Directory Structure
```text
app/
  aurelith/
    page.tsx            (Main Entry)
    layout.tsx          (Lenis Provider)
components/
  ui/
    aurelith/
      Hero.tsx          (GSAP Pinned)
      FeatureWall.tsx   (Staggered Reveal)
      CTA.tsx           (Magnetic Hover)
hooks/
  useAurelithMotion.ts  (Global Reveal Context)
tokens/
  v1/
    colors.ts           (Brand Tokens)
```

## Boundary Rules
- **Server Components**: Content layers, SEO headers, static layout parts.
- **Client Components**: Hero Cinematic, Feature Interactivity, Pinned sections (`"use client"`).
