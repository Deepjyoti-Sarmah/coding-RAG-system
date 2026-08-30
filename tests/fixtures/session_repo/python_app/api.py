from .auth import login


def handle_request(user, token):
    return login(user, token)
