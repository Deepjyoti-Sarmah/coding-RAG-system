def create_session(user):
    return {"user": user}


def validate_token(token):
    return len(token) > 8


class Authenticator:
    def __init__(self, secret):
        self.secret = secret

    def login(self, user, token):
        if validate_token(token):
            return create_session(user)
        return None
