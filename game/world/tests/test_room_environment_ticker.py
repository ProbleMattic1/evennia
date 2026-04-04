"""Room environment ticker wiring (TICKER_HANDLER subscription)."""

from unittest.mock import MagicMock, PropertyMock, patch

from django.test import SimpleTestCase


class RoomEnvironmentTickerTests(SimpleTestCase):
    @patch("evennia.scripts.tickerhandler.TICKER_HANDLER")
    def test_sync_subscribes_when_puppeted_and_not_yet_subscribed(self, TH):
        from typeclasses.rooms import Room, _ENV_TICK_ID, _ENV_TICK_INTERVAL, _NDB_ENV_TICKER_ACTIVE

        r = Room()
        setattr(r.ndb, _NDB_ENV_TICKER_ACTIVE, False)
        r._room_has_puppeted_character = lambda ignore=None: True
        r._sync_environment_ticker()
        TH.add.assert_called_once()
        args, kwargs = TH.add.call_args
        self.assertEqual(args[0], _ENV_TICK_INTERVAL)
        self.assertIs(args[1].__func__, Room.at_environment_tick)
        self.assertEqual(kwargs.get("idstring"), _ENV_TICK_ID)
        self.assertTrue(kwargs.get("persistent"))
        self.assertTrue(getattr(r.ndb, _NDB_ENV_TICKER_ACTIVE))

    @patch("evennia.scripts.tickerhandler.TICKER_HANDLER")
    def test_sync_no_add_when_already_subscribed(self, TH):
        from typeclasses.rooms import Room, _NDB_ENV_TICKER_ACTIVE

        r = Room()
        setattr(r.ndb, _NDB_ENV_TICKER_ACTIVE, True)
        r._room_has_puppeted_character = lambda ignore=None: True
        r._sync_environment_ticker()
        TH.add.assert_not_called()
        TH.remove.assert_not_called()

    @patch("evennia.scripts.tickerhandler.TICKER_HANDLER")
    def test_sync_unsubscribes_when_empty_and_subscribed(self, TH):
        from typeclasses.rooms import Room, _ENV_TICK_ID, _ENV_TICK_INTERVAL, _NDB_ENV_TICKER_ACTIVE

        r = Room()
        setattr(r.ndb, _NDB_ENV_TICKER_ACTIVE, True)
        r._room_has_puppeted_character = lambda ignore=None: False
        r._sync_environment_ticker()
        TH.remove.assert_called_once()
        self.assertEqual(TH.remove.call_args.args[0], _ENV_TICK_INTERVAL)
        self.assertIs(TH.remove.call_args.args[1].__func__, Room.at_environment_tick)
        rkw = TH.remove.call_args.kwargs
        self.assertEqual(rkw.get("idstring"), _ENV_TICK_ID)
        self.assertTrue(rkw.get("persistent"))
        self.assertFalse(getattr(r.ndb, _NDB_ENV_TICKER_ACTIVE))

    @patch("evennia.scripts.tickerhandler.TICKER_HANDLER")
    def test_sync_no_remove_when_never_subscribed(self, TH):
        from typeclasses.rooms import Room, _NDB_ENV_TICKER_ACTIVE

        r = Room()
        setattr(r.ndb, _NDB_ENV_TICKER_ACTIVE, False)
        r._room_has_puppeted_character = lambda ignore=None: False
        r._sync_environment_ticker(leaving=MagicMock())
        TH.remove.assert_not_called()
        TH.add.assert_not_called()

    def test_room_has_puppeted_character_excludes_ignore(self):
        from typeclasses.rooms import Room

        puppet = MagicMock()
        puppet.is_typeclass.return_value = True
        puppet.sessions.count.return_value = 1

        with patch.object(Room, "contents", new_callable=PropertyMock, return_value=[puppet]):
            r = Room()
            self.assertFalse(r._room_has_puppeted_character(ignore=puppet))
            self.assertTrue(r._room_has_puppeted_character(ignore=None))
