
        rows = cur.fetchall()
        conn.close()
        return rows
    conn.commit()
    conn.close()
