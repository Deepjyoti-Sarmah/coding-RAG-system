from .auth import Authenticator


class AdminAuthenticator(Authenticator):
    def login(self, user, token):
        return super().login(user, token)
