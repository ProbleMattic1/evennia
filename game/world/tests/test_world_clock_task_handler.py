"""World clock immediate tick uses TASK_HANDLER."""

from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase


class WorldClockTaskHandlerTests(SimpleTestCase):
    def test_schedule_world_clock_queues_task_handler(self):
        from world.evennia_tasks import schedule_world_clock_immediate_tick

        script = MagicMock()
        script.id = 123

        with patch("evennia.TASK_HANDLER") as mock_th:
            mock_th.add.return_value = MagicMock()
            schedule_world_clock_immediate_tick(script, delay_seconds=0.25)
            mock_th.add.assert_called_once()
            args, kwargs = mock_th.add.call_args
            self.assertEqual(args[0], 0.25)
            self.assertFalse(kwargs.get("persistent", False))
