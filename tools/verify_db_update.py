#!/usr/bin/env python3
import sqlite3

conn = sqlite3.connect('memory/experience.sqlite')
cursor = conn.cursor()
cursor.execute('SELECT pulse_id, event_type, outcome FROM event ORDER BY timestamp DESC LIMIT 6')
print('Recent events:')
for row in cursor.fetchall():
    print(f'  {row[0]}: {row[1]} ({row[2]})')
conn.close()

