import { useEffect, useRef } from 'react';
import gsap from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';

gsap.registerPlugin(ScrollTrigger);

/**
 * Custom hook for premium AURELITH reveal animations.
 * Provides a production-ready pattern for GSAP + ScrollTrigger integration.
 */
export const useAurelithReveal = (options = { stagger: 0.1, duration: 1.2 }) => {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const ctx = gsap.context(() => {
      // Reveal pattern: y-offset + opacity mask
      gsap.from(el.querySelectorAll('.reveal-item'), {
        y: 60,
        opacity: 0,
        stagger: options.stagger,
        duration: options.duration,
        ease: 'power4.out',
        scrollTrigger: {
          trigger: el,
          start: 'top 85%',
          toggleActions: 'play none none reverse',
        },
      });
    }, el);

    return () => ctx.revert();
  }, [options]);

  return containerRef;
};
