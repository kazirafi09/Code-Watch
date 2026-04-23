import random, string
def new_token():
    return "".join(random.choice(string.ascii_letters) for _ in range(32))
