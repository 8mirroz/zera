"use client";

import React, { useEffect, useRef } from 'react';
import { motion } from 'framer-motion';
import gsap from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';

gsap.registerPlugin(ScrollTrigger);

export const AurelithHero = () => {
  const heroRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const ctx = gsap.context(() => {
      // Pinned storytelling sequence
      ScrollTrigger.create({
        trigger: heroRef.current,
        start: "top top",
        end: "+=200%",
        pin: true,
        scrub: 1,
      });
    }, heroRef);
    return () => ctx.revert();
  }, []);

  return (
    <section ref={heroRef} className="h-screen bg-[#0C0C0C] flex flex-col items-center justify-center relative overflow-hidden">
      <motion.div 
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 1.5, ease: "circOut" }}
        className="z-10 text-center"
      >
        <span className="text-amber-500 uppercase tracking-[0.3em] text-sm mb-4 block">Aurelith One</span>
        <h1 className="text-white text-6xl md:text-8xl font-serif tracking-tight">
          Quiet <br/> Intelligence
        </h1>
      </motion.div>
      
      {/* Background Cinematic Silhouette - Simplified Placeholder */}
      <div className="absolute inset-0 bg-gradient-to-b from-transparent to-[#050505] opacity-60" />
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-slate-800/10 rounded-full blur-[120px]" />
    </section>
  );
};
