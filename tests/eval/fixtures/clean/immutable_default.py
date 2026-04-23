def append_user(user, users=None):
    users = list(users or [])
    users.append(user)
    return users
