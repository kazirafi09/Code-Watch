import pickle, socket
def handle(sock: socket.socket):
    data = sock.recv(4096)
    obj = pickle.loads(data)
    return obj
