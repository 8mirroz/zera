import os
import httpx
from typing import Dict, Any, Optional

class PinterestScanner:
    """
    Scans Pinterest profiles/boards to extract visual intelligence 
    using Perplexity Sonar Pro as the reasoning engine.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('PERPLEXITY_API_KEY')
        self.endpoint = "https://api.perplexity.ai/chat/completions"

    async def extract_visual_dna(self, profile_url: str = "https://ru.pinterest.com/deushareAI/") -> Dict[str, Any]:
        """
        Extracts aesthetic trends from a Pinterest profile.
        """
        if not self.api_key:
            return {"error": "Perplexity API key missing"}

        print(f"   🎨 Scanning Pinterest profile for visual DNA: {profile_url}")
        
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
                    self.endpoint,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "sonar-pro",
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
                    return data['choices'][0]['message']['content']
                else:
                    return {"error": f"Failed to fetch metadata: {response.status_code}"}
        except Exception as e:
            return {"error": str(e)}

    def format_as_prompt_context(self, visual_dna: Any) -> str:
        """
        Translates raw JSON DNA into a prompt string for use in generation.
        """
        if isinstance(visual_dna, str):
            import json
            try:
                visual_dna = json.loads(visual_dna)
            except:
                return f"\n[Visual Context]: {visual_dna}\n"

        context = "\n--- 🎨 Pinterest Visual Intelligence ---\n"
        context += f"Aesthetic Vibe: {visual_dna.get('vibe', 'Custom')}\n"
        context += f"Colors: {visual_dna.get('colors', 'N/A')}\n"
        context += f"Typography: {visual_dna.get('typography', 'N/A')}\n"
        context += f"Visual Language: {visual_dna.get('visual_language', 'N/A')}\n"
        context += "----------------------------------------\n"
        return context
