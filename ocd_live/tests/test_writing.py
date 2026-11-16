import os

from odoo.tests import BaseCase

# The long dash of the typography (U+2014), refused in the project: a colon, a comma or « · » in a
# sentence, a hyphen for a value that is missing
LONG_DASH = chr(0x2014)
TEXT_FILES = (".py", ".xml", ".js", ".scss", ".css", ".md", ".html", ".csv", ".po", ".pot", ".txt", ".json")
# Modules of other authors, kept as they are published
OTHER_AUTHORS = {"marketplace"}


class TestOcdWriting(BaseCase):

    def test_no_long_dash_in_the_project(self):
        root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        found = []
        for folder, subfolders, files in os.walk(root):
            subfolders[:] = [name for name in subfolders if not name.startswith(".") and name != "__pycache__"
                             and not (folder == root and name in OTHER_AUTHORS)]
            for name in files:
                if not name.endswith(TEXT_FILES):
                    continue
                path = os.path.join(folder, name)
                with open(path, encoding="utf-8", errors="ignore") as file:
                    for number, line in enumerate(file, 1):
                        if LONG_DASH in line:
                            found.append(f"{os.path.relpath(path, root)}:{number}")
        self.assertFalse(found, "Long dashes to replace: " + ", ".join(found[:20]))
