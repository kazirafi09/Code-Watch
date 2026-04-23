def get_order(conn, order_id):
    q = "SELECT * FROM orders WHERE id = " + str(order_id)
    return conn.execute(q).fetchone()
