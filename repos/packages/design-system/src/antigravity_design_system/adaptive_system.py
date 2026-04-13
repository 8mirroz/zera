"""
Adaptive Design System - Aggregates design patterns from 4 sources.

Версия: 3.1 (Global Integration)
Дата: 6 февраля 2026

Sources (Priority Order):
1. Google Stitch (PRIMARY - uses STITCH_API_KEY)
2. 21st.dev (Fallback, via MCP magic-21st)
3. MagicUI (Fallback, via MCP magic-ui)
4. Pinterest (Visual inspiration)

Fallback: When Stitch quota < 80%, switch to alternatives.
"""

import asyncio
import os
import json
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Union
from .pinterest_client import PinterestClient


@dataclass
class DesignTokens:
    """Design tokens extracted from sources."""
    colors: Dict[str, str] = field(default_factory=dict)
    typography: Dict[str, Any] = field(default_factory=dict)
    spacing: Dict[str, Any] = field(default_factory=dict)
    effects: Dict[str, Any] = field(default_factory=dict)
    radii: Dict[str, str] = field(default_factory=dict)
    layout: Dict[str, Any] = field(default_factory=dict)  # Added for layout patterns
    depth: Dict[str, Any] = field(default_factory=dict)   # Added for Spatial UI (Vision Pro)


@dataclass
class ComponentSpec:
    """Specification for a UI component."""
    name: str
    source: str  # stitch, 21st, magicui, pinterest
    variants: List[str] = field(default_factory=list)
    props: Dict[str, Any] = field(default_factory=dict)
    code: Optional[str] = None


@dataclass
class DesignOutput:
    """Output from the design system."""
    tokens: DesignTokens
    platforms: Dict[str, Dict[str, Any]]
    tailwind_config: str
    components: List[ComponentSpec]
    source_used: str  # Track which source was used


class AdaptiveDesignSystem:
    """
    Aggregates design patterns from:
    - https://stitch.withgoogle.com/ (PRIMARY, Material Design 3.0)
    - https://21st.dev/community/components (via MCP magic-21st)
    - https://magicui.design/ (via MCP magic-ui)
    - Pinterest board (custom integration)
    
    Fallback Logic: Stitch → 21st.dev + MagicUI → Pinterest
    Threshold: When Stitch quota < 20%, switch to fallback
    """
    
    STITCH_FALLBACK_THRESHOLD = 0.8  # 80% remaining quota triggers fallback
    
    def __init__(self):
        self.stitch_api_key = os.getenv("STITCH_API_KEY")
        self.stitch_quota_remaining = 1.0  # 100% initially
        self.sources = {
            "stitch": "https://stitch.withgoogle.com",
            "21st": "https://21st.dev",
            "magicui": "https://magicui.design",
            "pinterest": "https://ru.pinterest.com/deushareAI/"
        }
        self.cache: Dict[str, Any] = {}
        self._active_source = "stitch" if self.stitch_api_key else "21st"
        self.pinterest_client = PinterestClient()
    
    async def generate(
        self,
        product_type: str,
        inspiration: Optional[Dict] = None,
        platforms: List[str] = None,
        style: str = "modern-minimal"
    ) -> DesignOutput:
        """
        Generate adaptive design system.
        
        Steps:
        1. Fetch components from all sources
        2. Extract design tokens (colors, spacing, typography)
        3. Create platform-specific adaptations
        4. Generate Tailwind config + component library
        
        Args:
            product_type: Type of product (landing_page, ecommerce, etc.)
            inspiration: Optional design inspiration data
            platforms: Target platforms ["web", "mobile"]
            style: Design style (modern-minimal, glassmorphism, etc.)
            
        Returns:
            DesignOutput with tokens, config, and components
        """
        if platforms is None:
            platforms = ["web"]
        
        # Step 1: Fetch components (parallel)
        components = await self._fetch_all_components(product_type)
        
        # Step 2: Extract tokens
        tokens = self._extract_design_tokens(components, inspiration, style)
        
        # Step 3: Platform adaptations
        adapted = {}
        for platform in platforms:
            adapted[platform] = self._adapt_for_platform(tokens, platform)
        
        # Step 4: Generate config
        tailwind_config = self._generate_tailwind_config(tokens)
        component_specs = self._generate_component_specs(components, tokens)
        
        return DesignOutput(
            tokens=tokens,
            platforms=adapted,
            tailwind_config=tailwind_config,
            components=component_specs,
            source_used=self._active_source
        )
    
    async def _fetch_all_components(self, product_type: str) -> Dict[str, List[Dict]]:
        """Parallel fetch from all design sources."""
        # In production, these would be actual API calls or MCP tool calls
        tasks = [
            self._fetch_stitch_components(product_type),
            self._fetch_21st_components(product_type),
            self._fetch_magicui_components(product_type),
            self._fetch_pinterest_inspiration()
        ]
        
        results = await asyncio.gather(*tasks)
        
        return {
            "stitch": results[0],
            "21st": results[1],
            "magicui": results[2],
            "pinterest": results[3]
        }
    
    async def _fetch_stitch_components(self, product_type: str) -> List[Dict]:
        """Fetch from Google Stitch (Material Design 3.0)."""
        if self.stitch_api_key:
            try:
                # Actual integration point if API was public/documented
                # print(f"   🧵 Fetching Stitch components for {product_type}...")
                pass 
            except Exception as e:
                print(f"⚠️ Stitch API error: {e}")
        
        return [
            {"name": "Button", "variants": ["filled", "outlined", "text"]},
            {"name": "Card", "variants": ["elevated", "filled", "outlined"]},
            {"name": "TextField", "variants": ["filled", "outlined"]}
        ]
    
    async def _fetch_21st_components(self, product_type: str) -> List[Dict]:
        """Fetch from 21st.dev via MCP magic-21st."""
        api_key = os.getenv("MAGIC21ST_API_KEY")
        if api_key:
            try:
                # print(f"   ✨ Fetching 21st.dev components for {product_type}...")
                pass
            except Exception as e:
                print(f"⚠️ 21st.dev API error: {e}")

        # Fallback simulation
        return [
            {"name": "HeroSection", "source": "21st", "variant": "modern", "url": "https://21st.dev/s/hero-1"},
            {"name": "FeatureGrid", "source": "21st", "variant": "bento", "url": "https://21st.dev/s/features-2"},
            {"name": "Navbar", "source": "21st", "variant": "glass", "url": "https://21st.dev/s/nav-3"}
        ]
    
    async def _fetch_magicui_components(self, product_type: str) -> List[Dict]:
        """Fetch from MagicUI via MCP magic-ui."""
        # This simulates an MCP call: mcp.call("magic-ui", "getAllComponents")
        return [
            {"name": "ConfettiButton", "source": "magicui", "effect": "confetti"},
            {"name": "BlurInText", "source": "magicui", "effect": "blur"},
            {"name": "Dock", "source": "magicui", "effect": "floating"}
        ]
    
    async def _fetch_pinterest_inspiration(self) -> List[Dict]:
        """Fetch from Pinterest board."""
        board_id = os.getenv("PINTEREST_BOARD_ID")
        return self.pinterest_client.get_inspiration_tokens(board_id)
    
    def _extract_design_tokens(
        self,
        components: Dict[str, List[Dict]],
        inspiration: Optional[Dict],
        style: str
    ) -> DesignTokens:
        """Extract and normalize design tokens."""
        
        # Base tokens by style
        style_presets = {
            "modern-minimal": {
                "colors": {
                    "primary": "#6366f1",
                    "secondary": "#8b5cf6",
                    "accent": "#ec4899",
                    "background": "#0a0a0a",
                    "foreground": "#fafafa",
                    "muted": "#71717a",
                    "border": "#27272a"
                },
                "effects": {
                    "shadow_sm": "0 1px 2px rgba(0,0,0,0.05)",
                    "shadow_md": "0 4px 6px rgba(0,0,0,0.1)",
                    "blur": "backdrop-blur-md"
                }
            },
            "glassmorphism": {
                "colors": {
                    "primary": "#818cf8",
                    "secondary": "#a78bfa",
                    "accent": "#f472b6",
                    "background": "rgba(10,10,10,0.8)",
                    "foreground": "#ffffff",
                    "muted": "#a1a1aa",
                    "border": "rgba(255,255,255,0.1)"
                },
                "effects": {
                    "glass": "backdrop-blur-xl bg-white/5",
                    "glow": "shadow-lg shadow-primary/20"
                }
            },
            "bento": {
                "colors": {
                    "primary": "#3b82f6",
                    "background": "#f8fafc",
                    "foreground": "#0f172a",
                    "card": "#ffffff",
                    "border": "#e2e8f0"
                },
                "layout": {
                    "gap": "1rem",
                    "columns": 12,
                    "radius": "1.5rem"
                }
            },
            "neo-brutalism": {
                "colors": {
                    "primary": "#ffde03",
                    "background": "#ffffff",
                    "foreground": "#000000",
                    "border": "#000000"
                },
                "effects": {
                    "shadow": "4px 4px 0px #000000",
                    "border_width": "2px"
                }
            },
            "claymorphism": {
                "colors": {
                    "primary": "#60a5fa",
                    "background": "#f0f9ff",
                    "foreground": "#1e293b"
                },
                "effects": {
                    "shadow_outer": "8px 8px 16px rgba(0,0,0,0.1)",
                    "shadow_inner": "inset 8px 12px 16px rgba(255,255,255,0.6), inset -8px -12px 16px rgba(0,0,0,0.05)"
                }
            },
            "spatial-glass": {
                "colors": {
                    "primary": "#ffffff",
                    "background": "rgba(255,255,255,0.1)",
                    "foreground": "#ffffff"
                },
                "depth": {
                    "z_offset": "20px",
                    "parallax": 0.1
                },
                "effects": {
                    "blur": "backdrop-blur-3xl",
                    "specular": "shine"
                }
            }
        }
        
        preset = style_presets.get(style, style_presets["modern-minimal"])
        
        # Override with inspiration from components (e.g. Pinterest)
        pinterest_inspiration = components.get("pinterest")
        if pinterest_inspiration:
            for item in pinterest_inspiration:
                if item.get("type") == "color_palette":
                    colors = item.get("colors", [])
                    if len(colors) >= 3:
                        preset["colors"]["primary"] = colors[0]
                        preset["colors"]["secondary"] = colors[1]
                        preset["colors"]["accent"] = colors[2]

        # Override with manual inspiration if provided
        if inspiration:
            if isinstance(inspiration, dict) and "colors" in inspiration:
                preset["colors"].update(inspiration["colors"])
        
        return DesignTokens(
            colors=preset["colors"],
            typography={
                "sans": ["Inter", "system-ui", "sans-serif"],
                "mono": ["JetBrains Mono", "Fira Code", "monospace"],
                "heading": ["Outfit", "Inter", "sans-serif"],
                "sizes": {
                    "xs": "0.75rem",
                    "sm": "0.875rem",
                    "base": "1rem",
                    "lg": "1.125rem",
                    "xl": "1.25rem",
                    "2xl": "1.5rem",
                    "3xl": "1.875rem",
                    "4xl": "2.25rem"
                }
            },
            spacing={
                "base": 4,
                "scale": [0, 1, 2, 3, 4, 5, 6, 8, 10, 12, 16, 20, 24, 32, 40, 48, 64]
            },
            effects=preset.get("effects", {}),
            radii={
                "none": "0",
                "sm": "0.125rem",
                "md": "0.375rem",
                "lg": "0.5rem",
                "xl": "0.75rem",
                "2xl": "1rem",
                "full": "9999px"
            },
            layout=preset.get("layout", {}),
            depth=preset.get("depth", {})
        )
    
    def _adapt_for_platform(self, tokens: DesignTokens, platform: str) -> Dict:
        """Platform-specific adaptations."""
        if platform == "web":
            return {
                "framework": "React + Tailwind CSS",
                "responsive": ["mobile", "tablet", "desktop"],
                "breakpoints": {"sm": "640px", "md": "768px", "lg": "1024px", "xl": "1280px"},
                "tokens": tokens
            }
        elif platform == "mobile":
            return {
                "framework": "React Native",
                "responsive": ["phone", "tablet"],
                "tokens": self._convert_to_react_native(tokens)
            }
        elif platform == "vision-pro":
            return self._adapt_for_vision_pro(tokens)
        elif platform == "blockchain":
            return self._adapt_for_blockchain(tokens)
        return {"framework": "generic", "tokens": tokens}

    def _adapt_for_vision_pro(self, tokens: DesignTokens) -> Dict:
        """Adapt for Apple Vision Pro (Spatial UI)."""
        return {
            "platform": "visionOS",
            "render_engine": "SwiftUI / RealityKit",
            "depth_layers": ["background", "main", "ornament"],
            "materials": ["glass", "vibrant", "ultra-thin"],
            "tokens": {
                **tokens.__dict__,
                "spatial": {
                    "z_step": "20px",
                    "hover_depth": "10px"
                }
            }
        }

    def _adapt_for_blockchain(self, tokens: DesignTokens) -> Dict:
        """Adapt for Blockchain (TON/Wallet UI)."""
        return {
            "platform": "TON DSL / Telegram Mini App",
            "states": {
                "confirmed": "#22c55e",
                "pending": "#f59e0b",
                "failed": "#ef4444"
            },
            "wallet_specific": {
                "address_color": tokens.colors.get("muted"),
                "balance_style": "semi-bold"
            },
            "tokens": tokens
        }
    
    def _convert_to_react_native(self, tokens: DesignTokens) -> DesignTokens:
        """Convert web tokens to React Native format."""
        # React Native uses numbers for spacing, not rem
        return tokens  # Simplified for now
    
    def _generate_tailwind_config(self, tokens: DesignTokens) -> str:
        """Generate tailwind.config.ts from design tokens."""
        config = f'''/** @type {{import('tailwindcss').Config}} */
export default {{
  content: ['./src/**/*.{{js,jsx,ts,tsx}}', './app/**/*.{{js,jsx,ts,tsx}}'],
  darkMode: 'class',
  theme: {{
    extend: {{
      colors: {{
        primary: '{tokens.colors.get("primary", "#6366f1")}',
        secondary: '{tokens.colors.get("secondary", "#8b5cf6")}',
        accent: '{tokens.colors.get("accent", "#ec4899")}',
        background: '{tokens.colors.get("background", "#0a0a0a")}',
        foreground: '{tokens.colors.get("foreground", "#fafafa")}',
        muted: '{tokens.colors.get("muted", "#71717a")}',
        border: '{tokens.colors.get("border", "#27272a")}',
      }},
      fontFamily: {{
        sans: {tokens.typography.get("sans", ["Inter", "sans-serif"])},
        mono: {tokens.typography.get("mono", ["monospace"])},
        heading: {tokens.typography.get("heading", ["Inter", "sans-serif"])},
      }},
      borderRadius: {{
        sm: '{tokens.radii.get("sm", "0.125rem")}',
        md: '{tokens.radii.get("md", "0.375rem")}',
        lg: '{tokens.radii.get("lg", "0.5rem")}',
        xl: '{tokens.radii.get("xl", "0.75rem")}',
      }},
    }},
  }},
  plugins: [],
}}
'''
        return config
    
    def _generate_component_specs(
        self,
        components: Dict[str, List[Dict]],
        tokens: DesignTokens
    ) -> List[ComponentSpec]:
        """Generate component specifications."""
        specs = []
        
        for source, comps in components.items():
            for comp in comps:
                specs.append(ComponentSpec(
                    name=comp.get("name", "Unknown"),
                    source=source,
                    variants=comp.get("variants", []),
                    props=comp,
                    code=comp.get("image_url") # Use image_url as code/ref for now
                ))
        
        return specs


# === CONVENIENCE FUNCTIONS ===

_design_system: Optional[AdaptiveDesignSystem] = None


def get_design_system() -> AdaptiveDesignSystem:
    """Get or create global design system instance."""
    global _design_system
    if _design_system is None:
        _design_system = AdaptiveDesignSystem()
    return _design_system


# === EXAMPLE USAGE ===
if __name__ == "__main__":
    async def main():
        ds = AdaptiveDesignSystem()
        
        output = await ds.generate(
            product_type="landing_page",
            style="modern-minimal",
            platforms=["web"]
        )
        
        print("=== Design Tokens ===")
        print(f"Colors: {output.tokens.colors}")
        print(f"Typography: {output.tokens.typography}")
        
        print("\n=== Tailwind Config ===")
        print(output.tailwind_config[:500] + "...")
        
        print("\n=== Components ===")
        for comp in output.components[:5]:
            print(f"- {comp.name} ({comp.source})")
    
    asyncio.run(main())
