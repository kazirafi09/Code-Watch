DB_PASSWORD = "prod-master-2024!"
def connect():
    import psycopg2
    return psycopg2.connect(host="db", user="admin", password=DB_PASSWORD)
