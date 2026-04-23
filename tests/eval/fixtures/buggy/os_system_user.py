import os
def archive(name):
    os.system("tar czf /tmp/out.tgz " + name)
