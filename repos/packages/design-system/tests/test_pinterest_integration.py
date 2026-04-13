import os
import asyncio
import unittest

from antigravity_design_system.adaptive_system import AdaptiveDesignSystem
from antigravity_design_system.pinterest_client import PinterestClient

class PinterestIntegrationTests(unittest.TestCase):
    def test_pinterest_integration_mock(self) -> None:
        async def run() -> None:
            """
            Test that the design system correctly uses mock Pinterest inspiration
            when the client is not authenticated.
            """
            ds = AdaptiveDesignSystem()

            os.environ.pop("PINTEREST_ACCESS_TOKEN", None)

            output = await ds.generate(
                product_type="landing_page",
                style="modern-minimal",
            )

            self.assertEqual(output.tokens.colors["primary"], "#E60023")
            self.assertEqual(output.tokens.colors["secondary"], "#BD081C")
            self.assertEqual(output.tokens.colors["accent"], "#FFFFFF")

            found_pinterest = any(comp.source == "pinterest" for comp in output.components)
            self.assertTrue(found_pinterest)

        asyncio.run(run())

    def test_pinterest_client_mock_data(self) -> None:
        client = PinterestClient()
        inspiration = client.get_inspiration_tokens()

        self.assertGreater(len(inspiration), 0)
        self.assertEqual(inspiration[0]["type"], "color_palette")
        self.assertEqual(len(inspiration[0]["colors"]), 3)


if __name__ == "__main__":
    unittest.main()
