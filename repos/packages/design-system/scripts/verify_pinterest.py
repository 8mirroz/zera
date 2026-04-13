import asyncio
import os
import sys

# Add src to path
sys.path.append(os.path.join(os.getcwd(), "src"))

from antigravity_design_system.adaptive_system import AdaptiveDesignSystem

async def verify():
    print("Starting verification of Pinterest integration...")
    ds = AdaptiveDesignSystem()
    
    # Simulate Pinterest board ID
    os.environ["PINTEREST_BOARD_ID"] = "12345"
    
    print("Generating design output with Pinterest inspiration...")
    output = await ds.generate(
        product_type="landing_page",
        style="modern-minimal"
    )
    
    print(f"Primary Color: {output.tokens.colors['primary']}")
    print(f"Secondary Color: {output.tokens.colors['secondary']}")
    
    # Check if Pinterest colors are applied
    # Mock colors from pinterest_client.py: ["#E60023", "#BD081C", "#FFFFFF"]
    if output.tokens.colors["primary"] == "#E60023":
        print("✅ SUCCESS: Pinterest colors applied correctly.")
    else:
        print("❌ FAILURE: Pinterest colors not applied.")
        
    found_pinterest = any(comp.source == "pinterest" for comp in output.components)
    if found_pinterest:
        print("✅ SUCCESS: Pinterest components found in output.")
    else:
        print("❌ FAILURE: No Pinterest components found.")

if __name__ == "__main__":
    asyncio.run(verify())
