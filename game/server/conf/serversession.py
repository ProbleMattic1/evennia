"""
ServerSession

The serversession is the Server-side in-memory representation of a
user connecting to the game.  Evennia manages one Session per
connection to the game. So a user logged into the game with multiple
clients (if Evennia is configured to allow that) will have multiple
sessions tied to one Account object. All communication between Evennia
and the real-world user goes through the Session(s) associated with that user.

It should be noted that modifying the Session object is not usually
necessary except for the most custom and exotic designs - and even
then it might be enough to just add custom session-level commands to
the SessionCmdSet instead.

This module is not normally called. To tell Evennia to use the class
in this module instead of the default one, add the following to your
settings file:

    SERVER_SESSION_CLASS = "server.conf.serversession.ServerSession"

"""

from evennia.contrib.utils.auditing.server import AuditedServerSession

from world.web_stream import normalize_web_stream_meta


class ServerSession(AuditedServerSession):
    """
    This class represents a player's session and is a template for
    individual protocols to communicate with Evennia.

    Each account gets one or more sessions assigned to them whenever they connect
    to the game server. All communication between game and account goes
    through their session(s).

    Outbound client traffic is mirrored onto the puppet Character's web_msg_buffer
    here (everything that leaves via data_out), with headless/API ``Character.msg``
    paths recording in ``Character.msg`` when no sessions receive the line.
    """

    def data_out(self, **kwargs):
        text = kwargs.get("text")
        raw_meta = kwargs.pop("web_stream_meta", None)
        meta = normalize_web_stream_meta(raw_meta if isinstance(raw_meta, dict) else {})

        puppet = getattr(self, "puppet", None)
        if text is not None and puppet is not None:
            recorder = getattr(puppet, "record_web_stream_text", None)
            if callable(recorder) and puppet.is_typeclass(
                "typeclasses.characters.Character", exact=False
            ):
                recorder(text, meta)
        super().data_out(**kwargs)
