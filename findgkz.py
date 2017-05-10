import sqlite3
import os

name = str(input('Für welche Stadt möchtest du die Gemeindekennziffer wissen? '))

db = os.path.abspath(os.pardir) + '/gemeindedatenbank.db'
connection = sqlite3.connect(db)
c = connection.cursor()
allgkz = c.execute('SELECT NAME, GKZ FROM staedtewiki').fetchall()
possible = []
for stadt in allgkz:
    if name in stadt[0].split():
        possible.append('{:<30}{:>20}'.format(stadt[0], stadt[1]))

print(('{:<30}{:>20}\n--------------------------------------------------'.format('Stadt:', 'Gemeindekennziffer:')))
for line in possible:
    print(line)
