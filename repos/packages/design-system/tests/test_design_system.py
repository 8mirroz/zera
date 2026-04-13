import asyncio
import os
import tempfile
import unittest

from antigravity_design_system.adaptive_system import AdaptiveDesignSystem
from antigravity_design_system.core import search, search_stack
from antigravity_design_system.design_system import generate_design_system


class DesignSystemTests(unittest.TestCase):
    def test_domain_search_returns_results(self):
        result = search("minimal dashboard", "style", max_results=2)
        self.assertGreaterEqual(result.get("count", 0), 1)

    def test_stack_search_returns_results(self):
        result = search_stack("forms", "html-tailwind", max_results=2)
        self.assertGreaterEqual(result.get("count", 0), 1)

    def test_generate_design_system_markdown(self):
        output = generate_design_system("fintech saas", "FinTest", output_format="markdown")
        self.assertIn("### Colors", output)
        self.assertIn("### Typography", output)

    def test_generate_design_system_with_persist(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = generate_design_system(
                "healthcare app",
                "Health Project",
                output_format="markdown",
                persist=True,
                page="dashboard",
                output_dir=tmp,
            )
            self.assertIn("### Colors", output)
            master_path = os.path.join(tmp, "design-system", "health-project", "MASTER.md")
            page_path = os.path.join(tmp, "design-system", "health-project", "pages", "dashboard.md")
            self.assertTrue(os.path.exists(master_path))
            self.assertTrue(os.path.exists(page_path))

    def test_adaptive_system_generate(self):
        async def run_test():
            engine = AdaptiveDesignSystem()
            result = await engine.generate(
                product_type="landing_page",
                style="modern-minimal",
                platforms=["web"],
            )
            self.assertIn("primary", result.tokens.colors)
            self.assertIn("content:", result.tailwind_config)

        asyncio.run(run_test())


if __name__ == "__main__":
    unittest.main()
