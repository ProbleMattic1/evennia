"""
Replacement for evennia.web.utils.middleware.SharedLoginMiddleware (wired in settings).

- Webclient-only branch: load AccountDB before writing website_authenticated_uid (fixes
  anonymous request.user.id being written first in upstream Evennia).
- Omits per-request webclient_authenticated_nonce increments that forced a Django session
  save on nearly every HTTP request once webclient_authenticated_uid was set.
"""

from django.contrib.auth import authenticate, login

from evennia.accounts.models import AccountDB
from evennia.utils import logger


class SharedLoginMiddleware:
    """Synchronize website and webclient login (same behavior contract as Evennia upstream)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        self.make_shared_login(request)
        return self.get_response(request)

    @classmethod
    def make_shared_login(cls, request):
        csession = request.session
        account = request.user
        website_uid = csession.get("website_authenticated_uid", None)
        webclient_uid = csession.get("webclient_authenticated_uid", None)

        if not csession.session_key:
            csession.save()

        if account.is_authenticated:
            if website_uid is None:
                csession["website_authenticated_uid"] = account.id
            if webclient_uid is None:
                csession["webclient_authenticated_uid"] = account.id

        elif webclient_uid:
            if website_uid is None:
                account = AccountDB.objects.get(id=webclient_uid)
                csession["website_authenticated_uid"] = account.id
                try:
                    authenticate(autologin=account)
                    login(request, account)
                except AttributeError:
                    logger.log_trace()
