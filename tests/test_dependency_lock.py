"""Check exact pins and dependency closure on the current CI platform."""

import unittest
from importlib.metadata import distribution
from pathlib import Path

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name


REQUIREMENTS = Path(__file__).resolve().parents[1] / "requirements.txt"


class DependencyLockTests(unittest.TestCase):
    def setUp(self):
        self.requirements = [
            Requirement(line.strip())
            for line in REQUIREMENTS.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
        self.active = {
            canonicalize_name(req.name): req
            for req in self.requirements
            if req.marker is None or req.marker.evaluate()
        }

    def test_all_requirements_have_exact_versions(self):
        names = [canonicalize_name(req.name) for req in self.requirements]
        self.assertEqual(len(names), len(set(names)), "Duplicate package pins")
        for req in self.requirements:
            with self.subTest(package=req.name):
                specs = list(req.specifier)
                self.assertIsNone(req.url)
                self.assertEqual(len(specs), 1)
                self.assertEqual(specs[0].operator, "==")
                self.assertNotIn("*", specs[0].version)

    def test_installed_dependencies_and_extras_are_fully_pinned(self):
        pending = list(self.active.values())
        visited = set()
        while pending:
            req = pending.pop()
            name = canonicalize_name(req.name)
            key = (name, frozenset(req.extras))
            if key in visited:
                continue
            visited.add(key)
            with self.subTest(package=str(req)):
                self.assertIn(name, self.active, f"Missing transitive pin: {req}")
                installed = distribution(name)
                self.assertIn(installed.version, self.active[name].specifier)
                self.assertIn(installed.version, req.specifier)
                for raw in installed.requires or []:
                    dependency = Requirement(raw)
                    if dependency.marker is None or any(
                        dependency.marker.evaluate({"extra": extra})
                        for extra in {"", *req.extras}
                    ):
                        pending.append(dependency)
