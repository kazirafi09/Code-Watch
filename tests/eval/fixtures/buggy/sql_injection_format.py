def find_by_email(conn, email):
    return conn.execute("SELECT id FROM users WHERE email = '{}'".format(email)).fetchall()
