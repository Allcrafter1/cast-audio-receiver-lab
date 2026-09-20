from __future__ import annotations

import re
import unittest
from pathlib import Path
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[1]
PUBLIC_ENTRY_DOCS = (
    ROOT / "README.md",
    ROOT / "docs" / "README.md",
    ROOT / "docs" / "how-it-works.md",
    ROOT / "docs" / "installation.md",
)
MARKDOWN_LINK = re.compile(r"(?<!!)\[[^]]+\]\(([^)]+)\)")


class DocumentationTests(unittest.TestCase):
    def test_entry_document_local_links_exist(self) -> None:
        missing: list[str] = []
        for document in PUBLIC_ENTRY_DOCS:
            text = document.read_text(encoding="utf-8")
            for raw_target in MARKDOWN_LINK.findall(text):
                target = raw_target.split(maxsplit=1)[0].strip("<>")
                if target.startswith(("http://", "https://", "mailto:", "#")):
                    continue
                relative = unquote(target.split("#", 1)[0])
                if relative and not (document.parent / relative).resolve().exists():
                    missing.append(f"{document.relative_to(ROOT)} -> {target}")
        self.assertEqual(missing, [])

    def test_home_assistant_button_uses_current_redirect(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        install = (ROOT / "docs" / "installation.md").read_text(encoding="utf-8")
        current = "supervisor_add_addon_repository"
        obsolete = "supervisor_addon_repository"
        for text in (readme, install):
            self.assertIn(f"badges/{current}.svg", text)
            self.assertIn(f"redirect/{current}/", text)
            self.assertNotIn(obsolete, text)
            self.assertIn("repository_url=https%3A%2F%2Fgithub.com%2FAllcrafter1%2Fcast-audio-receiver-lab", text)

    def test_readme_exposes_default_management_address(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("http://HOME_ASSISTANT_IP:8788", readme)
        self.assertIn("Port `8788` is the default", readme)


if __name__ == "__main__":
    unittest.main()
