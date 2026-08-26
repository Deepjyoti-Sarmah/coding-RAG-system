from auth import Authenticator, create_session


def handle_request(user, token):
    authenticator = Authenticator("s3cret")
    session = authenticator.login(user, token)
    return create_session(user)
