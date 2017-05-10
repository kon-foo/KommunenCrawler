import logging
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import TextConverter
from pdfminer.layout import LAParams
from pdfminer.pdfpage import PDFPage
from io import StringIO

from boilerpipe.extract import Extractor
from nltk.stem.snowball import GermanStemmer
from nltk import word_tokenize
import nltk.data
import threading
import datetime
import os
import re

logger = logging.getLogger(__name__)
logging.getLogger('pdfminer').setLevel(logging.CRITICAL)

satztokenizer = nltk.data.load('tokenizers/punkt/german.pickle')
stemmer = GermanStemmer()
stoppwörter = []
with open('traindata/german', 'r') as f:
    for line in f:
        wort = line.split('\n')[0]
        stoppwörter.append(wort.lower())

def preprocess(text):
    try:
        text = re.sub("/innen|\*innen|/-innen", "innen", text)         # Vereinheitlicht unterschiedliche Gender-Varianten
        text = re.sub("-\s*\n", "", text)      #Entfernt Silbentrennung
        text = re.sub('(?:[\t ]*(?:\r?\n|\r)+)', ' ', text)     # Entfernt Zeilenumbrüche
    except TypeError as e:
        logger.info('{}: Kein String, Preprocessing nihct möglich. (vermutlich vcard).')
        return ''
    return text

def tokenize_satz(dokument):
    return satztokenizer.tokenize(dokument)

def tokenize_wort(text):
    text = re.sub(r"[^a-zA-Z \öÖäÄüÜß]", r" ", text)        # Entfernt alles außer Buchstaben (Um Zahlen auch beizubehalten ändern in: [^a-zA-Z0-9 \öÖäÄüÜß] )
    text = re.sub(r"(^|\s+)(\S(\s+|$))+", r" ", text) # Entfernt alles, was nicht länger, als ein Zeichen ist.
    text = ' '.join([word.lower() for word in text.split() if word.lower() not in stoppwörter])         # Entfernt Stoppwörter, schreibt alles Wörter klein.
    return stem_wort(word_tokenize(text, 'german'))

def stem_wort(tokens):
    return [stemmer.stem(item) for item in tokens]

def convert_html_to_string(html):
    ''' Nutzt Boilerpipe, um den Haupttext zu extrahieren. Mögliche extractor= ArticleExtractor, Default extractor, LargestContentExtractor'''
    extractor = Extractor(extractotr='LargestContentExtractor',  html=html)
    return extractor.getText()

def convert_pdf_to_string(path):
    try:
        rsrcmgr = PDFResourceManager()
        retstr = StringIO()
        codec = 'utf-8'
        laparams = LAParams()
        device = TextConverter(rsrcmgr, retstr, codec=codec, laparams=laparams)
        fp = open(path, 'rb')
        interpreter = PDFPageInterpreter(rsrcmgr, device)
        maxpages = 0
        caching = True
        pagenos = set()
        for page in PDFPage.get_pages(fp, pagenos, maxpages=maxpages, caching=caching, check_extractable=True):
            interpreter.process_page(page)
        fp.close()
        device.close()
        output = retstr.getvalue()
        retstr.close()
        os.remove(path)
        return output
    except:
        os.remove(path)
        return
