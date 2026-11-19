"""Tests of tools/versions.py on a server (--db): what to update, install, or look at.

    python3 -m unittest tools/test_versions.py"""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import versions  # noqa: E402


def module(version, project=True, **manifest):
    return (version, {"version": version, **manifest}, project)


class TestServerPlan(unittest.TestCase):

    def test_what_changed_is_updated_the_rest_left(self):
        code = {
            "ocd_live": module("20.0.1.25.0"),
            "ocd_live_shop": module("20.0.1.47.0"),
            "ocd_vote": module("20.0.1.3.0"),
        }
        rows = [("base", "installed", "20.0.1.3"), ("ocd_live", "installed", "20.0.1.24.0"),
                ("ocd_live_shop", "installed", "20.0.1.47.0"), ("ocd_vote", "installed", "20.0.1.4.0")]
        todo = versions.plan(code, rows)
        self.assertEqual(todo["update"], [("ocd_live", "20.0.1.24.0", "20.0.1.25.0")])
        self.assertEqual(todo["older"], [("ocd_vote", "20.0.1.4.0", "20.0.1.3.0")], "A wrong branch deployed is said")
        self.assertEqual(todo["install"], [])

    def test_versions_compare_as_numbers(self):
        todo = versions.plan({"ocd_live": module("20.0.1.10.0")}, [("ocd_live", "installed", "20.0.1.9.0")])
        self.assertEqual([name for name, *_rest in todo["update"]], ["ocd_live"])

    def test_a_new_module_and_the_ones_that_come_with_it(self):
        code = {
            "ocd_business": module("20.0.1.1.0", depends=["ocd_live_shop"]),
            "ocd_business_whatsapp": module("20.0.1.0.0", depends=["ocd_business", "ocd_live_shop_whatsapp"],
                                            auto_install=True),
            "ocd_clips_whatsapp": module("20.0.1.0.0", depends=["ocd_clips", "ocd_live_whatsapp"], auto_install=True),
            "ocd_live_demo": module("20.0.1.0.0"),
            "web_responsive": module("20.0.1.0.0", project=False),
        }
        rows = [("ocd_live_shop", "installed", "20.0.1.47.0"), ("ocd_live_shop_whatsapp", "installed", "20.0.1.0.0"),
                ("ocd_clips", "installed", "20.0.1.0.0"), ("ocd_live_whatsapp", "installed", "20.0.1.0.0")]
        todo = versions.plan(code, rows)
        notes = {name: note for name, _version, note in todo["new"]}
        self.assertEqual(set(notes), {"ocd_business", "ocd_business_whatsapp", "ocd_clips_whatsapp", "ocd_live_demo"},
                         "The modules of other authors are not proposed")
        self.assertIn("comes with ocd_business", notes["ocd_business_whatsapp"])
        self.assertIn("never on a real server", notes["ocd_live_demo"])
        self.assertEqual(todo["install"], ["ocd_clips_whatsapp"],
                         "Every module it needs is installed: Odoo would have installed it with them")

    def test_a_command_that_stopped_is_run_again(self):
        code = {"ocd_business": module("20.0.1.1.0"), "ocd_live": module("20.0.1.25.0")}
        rows = [("ocd_business", "to install", None), ("ocd_live", "to upgrade", "20.0.1.25.0")]
        todo = versions.plan(code, rows)
        self.assertEqual(todo["install"], ["ocd_business"])
        self.assertEqual([name for name, *_rest in todo["update"]], ["ocd_live"])
        self.assertEqual(todo["half"], [("ocd_business", "to install"), ("ocd_live", "to upgrade")])

    def test_a_short_version_takes_the_series(self):
        self.assertEqual(versions.full_version("1.0", "20.0"), "20.0.1.0")
        self.assertEqual(versions.full_version("20.0.1.2.0", "20.0"), "20.0.1.2.0")
        todo = versions.plan({"remove_odoo_enterprise": module("1.0", project=False)},
                             [("base", "installed", "20.0.1.3"), ("remove_odoo_enterprise", "installed", "20.0.1.0")])
        self.assertEqual(todo["update"], [])

    def test_the_connection_of_the_server(self):
        with tempfile.NamedTemporaryFile("w", suffix=".conf", delete=False) as file:
            file.write("[options]\ndb_host = db\ndb_port = False\ndb_user = odoo\ndb_password = s%cret\n")
        self.addCleanup(os.unlink, file.name)
        self.assertEqual(versions.read_conf(file.name), {"host": "db", "user": "odoo", "password": "s%cret"})
        self.assertEqual(versions.read_conf(None), {})


if __name__ == "__main__":
    unittest.main()
