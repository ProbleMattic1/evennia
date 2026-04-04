"""Smoke test: single Script base in typeclasses.scripts."""

import importlib
import inspect

from django.test import SimpleTestCase

from evennia.scripts.scripts import DefaultScript


class ScriptBaseImportTests(SimpleTestCase):
    def test_single_script_class_subclasses_default_script(self):
        mod = importlib.import_module("typeclasses.scripts")
        script_classes = [
            obj
            for name, obj in inspect.getmembers(mod, inspect.isclass)
            if name == "Script" and obj.__module__ == mod.__name__
        ]
        self.assertEqual(len(script_classes), 1)
        Script = script_classes[0]
        self.assertTrue(issubclass(Script, DefaultScript))
        self.assertIs(Script.__bases__[0], DefaultScript)
