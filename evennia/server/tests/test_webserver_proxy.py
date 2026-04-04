# -*- coding: utf-8 -*-
"""Reverse proxy client: tolerate inbound disconnect before upstream completes."""

import unittest
from unittest.mock import MagicMock

from evennia.server.webserver import EvenniaProxyClient, EvenniaProxyClientFactory


class TestEvenniaProxyClient(unittest.TestCase):
    def _client(self, father, headers=None):
        return EvenniaProxyClient(
            b"GET",
            b"/path",
            b"HTTP/1.1",
            headers if headers is not None else {},
            b"",
            father,
        )

    def test_handle_response_end_skips_finish_when_disconnected(self):
        father = MagicMock()
        father._disconnected = True
        client = self._client(father)
        client.transport = MagicMock()
        client.handleResponseEnd()
        father.finish.assert_not_called()
        client.transport.loseConnection.assert_called_once()

    def test_handle_response_end_finishes_when_connected(self):
        father = MagicMock()
        father._disconnected = False
        client = self._client(father)
        client.transport = MagicMock()
        client.handleResponseEnd()
        father.finish.assert_called_once()
        client.transport.loseConnection.assert_called_once()


class TestEvenniaProxyClientFactory(unittest.TestCase):
    def test_client_connection_failed_skips_when_disconnected(self):
        father = MagicMock()
        father._disconnected = True
        factory = EvenniaProxyClientFactory(b"GET", b"/", b"HTTP/1.1", {}, b"", father)
        factory.clientConnectionFailed(MagicMock(), MagicMock())
        father.setResponseCode.assert_not_called()
