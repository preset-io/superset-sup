"""
Mechanisms for authentication and authorization.
"""

from typing import Any, Dict

from requests import Response, Session
from requests.adapters import HTTPAdapter
from urllib3.util import Retry


class Auth:  # pylint: disable=too-few-public-methods
    """
    An authentication/authorization mechanism.
    """

    def __init__(self):
        self.session = Session()
        self.session.hooks["response"].append(self.reauth)

        retries = Retry(
            total=3,  # max retries count
            backoff_factor=1,  # delay factor between attempts
            respect_retry_after_header=True,
        )

        self.session.mount("https://", HTTPAdapter(max_retries=retries))

    def get_headers(self) -> Dict[str, str]:
        """
        Return headers for auth.
        """
        return {}

    def auth(self) -> None:
        """
        Perform authentication, fetching JWT tokens, CSRF tokens, cookies, etc.
        """
        raise NotImplementedError("Must be implemented for reauthorizing")

    # pylint: disable=invalid-name, unused-argument
    def reauth(self, r: Response, *args: Any, **kwargs: Any) -> Response:
        """
        Catch 401 and re-auth.
        """
        if r.status_code != 401:
            return r

        # Prevent infinite recursion by temporarily disabling the hook
        hooks = self.session.hooks
        self.session.hooks = {"response": []}

        try:
            self.auth()
        except NotImplementedError:
            self.session.hooks = hooks
            return r
        except Exception:
            # If auth fails, restore hooks and return the 401 response
            self.session.hooks = hooks
            return r

        self.session.headers.update(self.get_headers())
        r.request.headers.update(self.get_headers())
        
        try:
            # Retry without triggering hooks again
            retry_response = self.session.send(r.request, verify=False)
            return retry_response
        finally:
            # Restore the hooks
            self.session.hooks = hooks
