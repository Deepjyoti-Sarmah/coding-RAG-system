def validate_token(token):
    return bool(token)


def login(user, token):
    return user if validate_token(token) else None
