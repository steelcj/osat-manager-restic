"""The standard-library reader for manager.yaml."""

import unittest

from support import REPO, ManagerError

from osat_manager_restic.manifest import loads, manifest_path

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None


class Reader(unittest.TestCase):

    @unittest.skipIf(yaml is None, "PyYAML is not installed to compare with")
    def test_manager_yaml_reads_as_pyyaml_reads_it(self):
        text = (REPO / "manager.yaml").read_text()
        self.assertEqual(loads(text), yaml.safe_load(text))

    def test_scalars_lists_and_literals(self):
        text = ('a: "x # not a comment"  # a comment\nb: 3\nc: true\n'
                "d: ['p', q]\ne:\n  - one\n  - 'two'\nf: |\n  line 1\n"
                "  line 2\n\ng: null\n")
        self.assertEqual(loads(text), {
            "a": "x # not a comment", "b": 3, "c": True, "d": ["p", "q"],
            "e": ["one", "two"], "f": "line 1\nline 2\n", "g": None})

    def test_outside_the_subset_is_refused(self):
        for text in ("a: &anchor 1\n", "a: *alias\n", "a: {b: 1}\n",
                     "a: >\n  folded\n", "a:\n\t- tab\n", "---\na: 1\n",
                     "a: 1\na: 2\n", "a: !tag x\n", "- a: 1\n"):
            with self.subTest(text=text):
                with self.assertRaises(ManagerError):
                    loads(text)

    def test_the_checkout_manifest_is_found(self):
        self.assertEqual(manifest_path(), REPO / "manager.yaml")


if __name__ == "__main__":
    unittest.main()
