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
    def test_every_real_manager_yaml_reads_as_pyyaml_reads_it(self):
        found = [p for p in REPO.rglob("manager.yaml") if ".git" not in p.parts]
        self.assertTrue(found)
        for path in found:
            with self.subTest(path=str(path.relative_to(REPO))):
                text = path.read_text()
                self.assertEqual(loads(text), yaml.safe_load(text))

    @unittest.skipIf(yaml is None, "PyYAML is not installed to compare with")
    def test_mutations_fail_closed_or_agree_with_pyyaml(self):
        """Any edit to manager.yaml either is refused as outside the subset,
        or reads exactly as PyYAML reads it; never a different result."""
        import random
        text = (REPO / "manager.yaml").read_text()
        rng = random.Random(9)
        alphabet = " :-|>&*!{}[],#'\"\n\tabc0123"
        for _ in range(2000):
            chars = list(text)
            for _ in range(rng.randint(1, 3)):
                i = rng.randrange(len(chars))
                action = rng.randrange(3)
                if action == 0:
                    chars[i] = rng.choice(alphabet)
                elif action == 1:
                    chars.insert(i, rng.choice(alphabet))
                else:
                    del chars[i]
            mutated = "".join(chars)
            try:
                ours = loads(mutated)
            except ManagerError:
                continue
            try:
                theirs = yaml.safe_load(mutated)
            except yaml.YAMLError:
                self.fail(f"accepted YAML that PyYAML refuses:\n{mutated}")
            self.assertEqual(ours, theirs, mutated)

    def test_scalars_lists_and_literals(self):
        text = ('a: "x # not a comment"  # a comment\nb: 3\nc: true\n'
                "d: [p, q]\ne:\n  - one\n  - 'two'\nf: |\n  line 1\n"
                "  line 2\n\ng: null\n")
        self.assertEqual(loads(text), {
            "a": "x # not a comment", "b": 3, "c": True, "d": ["p", "q"],
            "e": ["one", "two"], "f": "line 1\nline 2\n", "g": None})

    def test_outside_the_subset_is_refused(self):
        for text in ("a: &anchor 1\n", "a: *alias\n", "a: {b: 1}\n",
                     "a: >\n  folded\n", "a:\n\t- tab\n", "---\na: 1\n",
                     "a: 1\na: 2\n", "a: !tag x\n", "- a: 1\n",
                     "a: b\n  continued\n", "a b: 1\n", "a:\n  - - x\n",
                     "a: \"unterminated\n", "a: 'x\n", "? a\n: b\n",
                     "%YAML 1.2\na: 1\n", "a: [x, [y]]\n", "a: |2\n  x\n",
                     "a: 1\n b: 2\n", "a: 0x1F\n", "a: 1.5\n", "a: yes\n",
                     "a: 2026-10-09\n", "a: .inf\n"):
            with self.subTest(text=text):
                with self.assertRaises(ManagerError):
                    loads(text)

    def test_the_checkout_manifest_is_found(self):
        self.assertEqual(manifest_path(), REPO / "manager.yaml")


if __name__ == "__main__":
    unittest.main()
