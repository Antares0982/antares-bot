#!/usr/bin/python3 -O
import sqlite3

conn = sqlite3.connect('data/blacklist.db')
c = conn.cursor()
c.execute('''CREATE TABLE BLACKLIST
        (TGID    INT     NOT NULL    PRIMARY KEY);''')
print("Table created successfully")

conn.commit()
c.close()
