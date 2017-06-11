import multiprocessing
import time
from itertools import dropwhile

class FreqMonitor(object):
    '''Ein Prozess zum Überwachen von Frequenzen.'''
    '''Bei Initialisierung werden alle Kommunikationkanäle zum Prozess erstellt.'''
    '''Eine Queue: jedes Element in der Queue, zählt als eione Einheit.'''
    '''3 Signale: zwei die 'False' werden, wenn die durchschnittliche, bzw. die Frequenz im vorgegebenen Zeitraum überschritten werden und um den Prozess zu beenden, '''
    '''3 Werte, die von außen abgelesen werden können: Aktuelle und durchschnittliche Crawl-Frequenz, sowie Anzahl an gezählten Einheiten.'''
    def __init__(self):
        self.currenttoohigh = multiprocessing.Event()
        self.meantoohigh = multiprocessing.Event()
        self.killsignal = multiprocessing.Event()
        self.countqueue = multiprocessing.Queue()
        self.currentfreq = multiprocessing.Value('f', 0)
        self.meanfreq = multiprocessing.Value('f', 0)
        self.countedsofar = multiprocessing.Value('i', 0)
        self.counter = multiprocessing.Process()

    def monitor(self, currenttoohigh, meantoohigh, killsignal, countqueue, currentfrequency, meanfrequency, fullcount, maxfreq1, maxfreqall, accuracy):
        '''Zählt die Eingaben, die über die Queue hereinkommen. Wenn Durchschnitts-Frequenz, bzw. aktuelle Frequenz
        das vorgegebene Maß übertreten, werden Events ausgelöst, die zum Blockieren von Prozessen genutzt werden können.'''
        delay = 0.01
        currenttoohigh.set()
        meantoohigh.set()
        countqueue.get() #Blockiert, bis das erste mal gezählt werden muss.
        starttime = time.time()
        fullcount.value += 1
        latest = []
        while not killsignal.is_set():
            time.sleep(delay)
            while countqueue.empty() == False:
                countqueue.get()
                fullcount.value += 1
                latest.append(time.time())
            accu = time.time() - accuracy
            latest = list(dropwhile(lambda x: x < accu, latest)) #Entfernt alle Einträge, die älter als n Sekunden sind.
            currentfrequency.value = len(latest)/ accuracy
            meanfrequency.value = fullcount.value / (time.time() - starttime)
            if not maxfreqall == None:
                if meanfrequency.value > maxfreqall:
                    meantoohigh.clear()
                else:
                    meantoohigh.set()
            if not maxfreq1 == None:
                if currentfrequency.value > maxfreq1 - delay:
                    currenttoohigh.clear()
                else:
                    currenttoohigh.set()
        currenttoohigh.set()
        meantoohigh.set()
        return

    def startmonitor(self, **kwargs):
        maxfreq1 = kwargs.get('maxf1', None)
        maxfreqall = kwargs.get('maxf8', None)
        accuracy = kwargs.get('acc', 10)
        self.counter = multiprocessing.Process(target=self.monitor, args=(self.currenttoohigh, self.meantoohigh, self.killsignal, self.countqueue, self.currentfreq, self.meanfreq, self.countedsofar, maxfreq1, maxfreqall, accuracy))
        #self.counter.daemon == True
        self.counter.start()


    def killcounter(self):
        self.killsignal.set()

    def getcurrentfrequency(self):
        return self.currentfreq.value

    def getmeanfrequency(self):
        return self.meanfreq.value

    def currentcount(self):
        return self.countedsofar.value

    def undermaxfrequency(self):
        return self.toohigh.is_set()

    def plusone(self):
        self.countqueue.put(1)

    def plusrange(self, n):
        for i in range(n):
            self.countqueue.put(1)
