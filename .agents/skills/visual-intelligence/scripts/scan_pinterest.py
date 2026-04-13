#!/usr/bin/env python3
import os
import sys
import json
import argparse
import asyncio
import httpx
from typing import Dict, Any, Optional

# Constants
PERPLEXITY_ENDPOINT = "https://api.perplexity.ai/chat/completions"
DEFAULT_MODEL = "sonar-pro"

class PinterestScanner:
    """
    Scans Pinterest profiles/boards to extract visual intelligence 
    using Perplexity Sonar Pro as the reasoning engine.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('PERPLEXITY_API_KEY')
        if not self.api_key:
            print("❌ Error: PERPLEXITY_API_KEY environment variable is not set.", file=sys.stderr)
            sys.exit(1)

    async def extract_visual_dna(self, profile_url: str) -> Dict[str, Any]:
        """
        Extracts aesthetic trends from a Pinterest profile.
        """
        print(f"🔍 Scanning Pinterest profile for visual DNA: {profile_url}...")
        
        prompt = f"""
        Analyze the visual design style of this Pinterest profile: {profile_url}.
        Extract the following architectural and design parameters:
        1. Color Palette (Primary, Secondary, Accent in hex or HSL).
        2. Typography (Fonts, weights, stylistic feel).
        3. Visual Language (Shapes, border styles, textures, effects like glassmorphism).
        4. Overall Vibe (e.g., 'Modern Minimalist', 'Cyberpunk', 'Luxury Dark').
        
        Return the result as a structured JSON object.
        """

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    PERPLEXITY_ENDPOINT,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": DEFAULT_MODEL,
                        "messages": [
                            {"role": "system", "content": "You are a professional Creative Director and Design Researcher."},
                            {"role": "user", "content": prompt}
                        ],
                        "response_format": {"type": "json_object"}
                    },
                    timeout=60.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    content = data['choices'][0]['message']['content']
                    try:
                        return json.loads(content)
                    except json.JSONDecodeError:
                        return {"raw_content": content}
                else:
                    return {"error": f"Failed to fetch metadata: {response.status_code}", "details": response.text}
        except Exception as e:
            return {"error": str(e)}

    def format_as_prompt_context(self, visual_dna: Dict[str, Any]) -> str:
        """
        Translates raw JSON DNA into a prompt string for use in generation.
        """
        context = "\n--- 🎨 Pinterest Visual Intelligence ---\n"
        context += f"Aesthetic Vibe: {visual_dna.get('Overall Vibe', visual_dna.get('vibe', 'Custom'))}\n"
        context += f"Colors: {json.dumps(visual_dna.get('Color Palette', visual_dna.get('colors', 'N/A')), indent=2)}\n"
        context += f"Typography: {json.dumps(visual_dna.get('Typography', visual_dna.get('typography', 'N/A')), indent=2)}\n"
        context += f"Visual Language: {json.dumps(visual_dna.get('Visual Language', visual_dna.get('visual_language', 'N/A')), indent=2)}\n"
        context += "----------------------------------------\n"
        return context

async def main():
    parser = argparse.ArgumentParser(description="Extract visual DNA from Pinterest using Perplexity.")
    parser.add_argument("--url", required=True, help="Pinterest profile or board URL")
    parser.add_argument("--format", choices=["json", "prompt"], default="json", help="Output format")
    args = parser.parse_args()

    scanner = PinterestScanner()
    dna = await scanner.extract_visual_dna(args.url)

    if "error" in dna:
        print(json.dumps(dna, indent=2))
        sys.exit(1)

    if args.format == "json":
        print(json.dumps(dna, indent=2, ensure_ascii=False))
    else:
        print(scanner.format_as_prompt_context(dna))

if __name__ == "__main__":
    asyncio.run(main())
