import logging
import sqlite3
import os

import csv
import sys
from readandwrite import length_of_csv, csv_to_list
logger = logging.getLogger(__name__)

class CrawlDatabase(object):

    def __init__(self, input_db, output_db, gkz):
        self.gemeindedb = input_db
        self.bbsitesdb = output_db

        self.gkz = gkz
        self.name = ''
        self.homepage = ''
        self.tablename = ''

        self.num_rel_links = 0

    def homepage_and_name(self):
        db = sqlite3.connect(self.gemeindedb)
        c = db.cursor()
        c.execute('SELECT webpraesenz, name FROM staedtewiki WHERE gkz = ?', (self.gkz,))
        both = c.fetchall()[0]
        self.homepage = both[0]
        self.name = both[1]
        self.tablename = '[{}_{}]'.format(self.name, self.gkz)
        db.close()

    def create_result_index_db(self):
        db = sqlite3.connect(self.bbsitesdb)
        c = db.cursor()
        creation = 'CREATE TABLE IF NOT EXISTS {} (id INTEGER PRIMARY KEY, TITEL TEXT, URL TEXT UNIQUE, TYP TEXT, RELEVANCE REAL, INHALT TEXT, ABGERUFEN DATETIME, HTML TEXT);'.format(self.tablename)
        c.execute(creation)
        db.commit()
        c.execute('INSERT OR IGNORE INTO AAAIndex (gkz, name, TABELLE) VALUES (?, ?, ?);', (self.gkz, self.name, self.tablename))
        db.commit()
        db.close()
        logger.info('Tabelle "{}" und Indexeintrag wurden angelegt!'.format(self.tablename))

    def initialisierung(self, neworexisting):
        self.homepage_and_name()
        logger.info('Kommune: {} | GKZ: {}'.format(self.name, self.gkz))
        if neworexisting == False:
            self.create_result_index_db()
        return self.name, self.homepage

    def writedb(self):
        csv.field_size_limit(sys.maxsize)
        db = sqlite3.connect(self.bbsitesdb)
        c = db.cursor()
        if length_of_csv('tempData/{}/output.csv'.format(self.gkz)) > 0:
            results = csv_to_list('tempData/{}/output.csv'.format(self.gkz))
            db = sqlite3.connect(self.bbsitesdb)
            insertion = 'INSERT OR IGNORE INTO {} (RELEVANCE, TITEL, INHALT, URL, TYP, ABGERUFEN, HTML) VALUES (?, ?, ?, ?, ?, ?, ?);'.format(self.tablename)
            for line in results:
                c.execute(insertion, line)
                self.num_rel_links += 1
            db.commit()
            c.execute('UPDATE AAAIndex SET relLinks = ?, redo = ? WHERE gkz = ?', (self.num_rel_links, 1, self.gkz))
            db.commit()
        else:
            c.execute('UPDATE AAAIndex SET redo = ?, relLinks = ? WHERE gkz = ?', (1, 0, self.gkz))
            db.commit()
            logger.warning('Die CSV-Datei von {} ist leer. Keine Links hinzugefügt.'.format(self.name))
        db.close()
