import logging
from numpy import zeros
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.feature_extraction.text import CountVectorizer
from sklearn import svm

from textprocessing import *
logger = logging.getLogger(__name__)


class RefRelevance(object):
    '''Wird einmal pro Crawl initialisiert mit den Einstellungen zur Relevanzbewertung.
    Beinhaltet den den Clasifier, den Vectorizer, den Schwellenwert und ein Set,
    in dem, die Sparse-Matrix der Vektorisierung für jedes gefunden Dokument gespeichert wird,
    um Duplikate mit unterschiedlichen Domains zu verhindern.'''
    def __init__(self, trainsentences, kernel, gamma, nu, coef, degree, vect, percentfeatures, ngram_range , schwellenwert, mainkeywords):
        self.vectorizer, self.vector = self.buildvectorizer(vect, trainsentences, percentfeatures, ngram_range[0], ngram_range[1])
        self.classifier = svm.OneClassSVM(nu=nu, kernel=kernel, gamma=gamma, coef0=coef, degree=degree, cache_size = 1000)
        self.supportvector = self.classifier.fit(self.vector)

        self.schwellenwert = schwellenwert
        self.keywords = mainkeywords
        self.duplicatetest = set()

    def buildvectorizer(self, vect, trainsentences, percent, ngrammin, ngrammax):
        '''Initialisiert den gewünschten Vectorizer und erstellt Sparse-Matrix aus Trainingssätzen.'''
        if vect == 'count':
            firstvectorizer = CountVectorizer(analyzer='word', tokenizer=tokenize_wort, ngram_range=(ngrammin,ngrammax))
        else:
            firstvectorizer = TfidfVectorizer(analyzer='word', tokenizer=tokenize_wort, ngram_range=(ngrammin,ngrammax))
        fullvector = firstvectorizer.fit_transform(trainsentences)
        if percent == 1:
            vector = fullvector
            vectorizer = firstvectorizer
        else:
            numfeat = int(fullvector.shape[1] * percent)
            if vect == 'count':
                vectorizer = CountVectorizer(analyzer='word', tokenizer=tokenize_wort, ngram_range=(ngrammin,ngrammax), max_features = numfeat)
            else:
                vectorizer = TfidfVectorizer(analyzer='word', tokenizer=tokenize_wort, ngram_range=(ngrammin,ngrammax), max_features = numfeat)
            vector = vectorizer.fit_transform(trainsentences)
        return vectorizer, vector




class PageRelevance(object):
    '''Wird für jedes untersuchte Dokument initialisiert und bewart relevante Informationen zur Relevanz des Dokuments.'''
    def __init__(self, Refferenz):
        self.classifier = Refferenz

        self.relevanz = 0
        self.pagetfidf = zeros(shape=(0,0))
        self.titlerelevant = False
        self.contentrelevant = False

        self.title = ''
        self.text = ''
        self.sätze = []

    def feed(self, typ, raw):
        '''Aus dem zu untersuchendes Dokument wird Text und Titel extrahiert.'''
        if typ == 'html':
            try:
                text = convert_html_to_string(raw)
            except Exception as e:
                logger.warning('Text-Extraktion aus HTML fehlgeschlagen für Link.')
                return
            try:
                self.title = str(raw).split('<title>')[1].split('</title>')[0]
            except IndexError:
                pass
        else:
            try:
                text = convert_pdf_to_string(raw)
            except Exception as e:
                logger.warning('Text-Extraktion aus PDF fehlgeschlagen.')
                return
        self.text = preprocess(text)
        self.sätze = tokenize_satz(self.text)

    def titlerelevance(self):
        '''Überprüft, ob der Titel relevante Keywords enthält.'''
        for i in tokenize_wort(self.title):
            if i in [word.lower() for word in self.classifier.keywords]:
                self.titlerelevant = True
                return True
        return False

    def contentrelevance(self):
        '''Klassifiziert jeden Satz und berechnet die Relevanz für das Dokument'''
        self.pagetfidf = self.classifier.vectorizer.transform(self.sätze)
        if self.pagetfidf.shape[0] == 0:
            self.contentrelevant = False
            return False
        self.relevanz = self.classifier.classifier.predict(self.pagetfidf).mean()
        if self.relevanz >= self.classifier.schwellenwert:
            if self.pagetfidf.getnnz() in self.classifier.duplicatetest:
                self.contentrelevant = 'Duplikat'
                return 'Duplikat'
            else:
                self.classifier.duplicatetest.add(self.pagetfidf.getnnz())
                self.contentrelevant = True
                return True
        return False

    def getoutput(self):
        '''Stellt gewünschte Informationen als Liste bereit, wenn sie gespeichert werden sollen.'''
        return [[self.relevanz, self.title, self.text], [self.pagetfidf.getnnz(), self.relevanz]]
