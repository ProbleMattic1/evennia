"""instance_prototypes.json loads."""

from django.test import SimpleTestCase

from world.instance_prototypes import clear_instance_prototype_cache, load_instance_prototypes


class InstancePrototypesLoaderTests(SimpleTestCase):
    def tearDown(self):
        clear_instance_prototype_cache()
        super().tearDown()

    def test_load_has_templates(self):
        tpl = load_instance_prototypes()
        self.assertIsInstance(tpl, dict)
        self.assertGreater(len(tpl), 0)
