import logging
from numpy import zeros
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn import svm
from textprocessing import *
logger = logging.getLogger(__name__)


class RefRelevance(object):

    def __init__(self, trainsentences, NGRAM_RANGE, MINDESTÄHNLICHKEIT, SCHWELLENWERT, MAINKEYWORDS ):
        self.trainsentences = trainsentences
        self.ngrammin = NGRAM_RANGE[0]
        self.ngrammax = NGRAM_RANGE[1]
        self.vectorizer = TfidfVectorizer(analyzer='word', tokenizer=tokenize_wort, ngram_range=(self.ngrammin,self.ngrammax))#self.ngrammin, self.ngrammax))
        self.classifier = onesvm_count = svm.OneClassSVM(nu=0.1, kernel="linear", gamma='auto', cache_size = 1000)
        self.tfidf = self.vectorizer.fit_transform(trainsentences)
        self.supportvector = self.classifier.fit(self.tfidf)
        self.duplicatetest = set()
        self.schwellenwert = SCHWELLENWERT
        self.keywords = MAINKEYWORDS


class PageRelevance(object):

    def __init__(self, Refferenz):
        self.classifier = Refferenz

        self.relevanz = 0
        self.pagetfidf = zeros(shape=(1,1))
        self.titlerelevant = False
        self.contentrelevant = False

        self.title = ''
        self.text = ''
        self.sätze = []

    def feed(self, typ, raw):
        try:
            self.title = str(raw).split('<title>')[1].split('</title>')[0]
        except IndexError:
            pass
        if typ == 'html':
            try:
                text = convert_html_to_string(raw)
            except Exception as e:
                logger.warning('Text-Extraktion aus HTML fehlgeschlagen für Link.')
                return
        else:
            try:
                text = convert_pdf_to_string(raw)
            except Exception as e:
                logger.warning('Text-Extraktion aus PDF fehlgeschlagen.')
                return
        self.text = preprocess(text)
        print(self.text)
        self.sätze = tokenize_satz(self.text)

    def titlerelevance(self):
        for i in tokenize_wort(self.title):
            if i in [word.lower() for word in self.classifier.keywords]:
                self.titlerelevant = True
                return True
        return False

    def contentrelevance(self):
        # if len(self.sätze) <= 1:
        #     self.contentrelevant = False
        #     return False
        try:
            self.pagetfidf = self.classifier.vectorizer.transform(self.sätze)
        except ValueError as e:
            logger.warning('Keine Features', exc_info=True)
            self.contentrelevant = False
            return False
        self.relevanz = self.classifier.classifier.predict(self.pagetfidf).mean()
        if self.relevanz >= self.classifier.schwellenwert:
            if (self.pagetfidf.getnnz(), self.relevanz) in self.classifier.duplicatetest:
                self.contentrelevant = 'Duplicat'
                return 'Duplicat'
            else:
                self.classifier.duplicatetest.add((self.pagetfidf.getnnz(), self.relevanz))
                self.contentrelevant = True
                return True
        return False

    def getoutput(self):
        return [[self.relevanz, self.title, self.text], [self.pagetfidf.getnnz(), self.relevanz]]
