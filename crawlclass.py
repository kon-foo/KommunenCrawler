import logging
from urllib import robotparser
from urllib.request import urlopen, Request
from multiprocessing import Process, Queue
from threading import Event

from uniquepriorityqueue import UniquePriorityQueueWithReplace as PQueue
from spiderandparser import get_domain_name
from threadsafeset import LockedSet
from readandwrite import *
from startingpoint import get_starting_point
from monitor_frequency import FreqMonitor

logger = logging.getLogger(__name__)

class Crawl(object):
    '''Enthält alle für den Crawl relevanten Informationen'''
    def __init__(self, continue_crawl, number_of_threads, crawldepth, base_url, gkz):
        self.GKZ = gkz
        self.BASE_URL = base_url
        self.DOMAIN = get_domain_name(self.BASE_URL)
        self.CHARSET = ''
        self.NUMBER_OF_THREADS = number_of_threads
        self.CRAWLDEPTH = crawldepth

        self.robotparser = robotparser.RobotFileParser()
        self.robotparser.set_url(self.BASE_URL + '/robots.txt')
        self.robotparser.read()

        self.monitor = FreqMonitor()
        self.save_process = Process()
        self.threads_alive = 0
        self.addedrelevants = int()

        self.workqueue = PQueue()
        self.savequeue = Queue()
        self.crawled = LockedSet(set())

        self.continue_crawl = continue_crawl
        self.shutdown = False

        self.build_queue(self.continue_crawl)
        self.check_charset(self.BASE_URL)

    def build_queue(self, continue_crawl):
        '''Erstellt die Anfangs-Queue, bei einem forstgesetzten Suchlauf aus der
        gespeicherten Queue, bei einem neuen Suchlauf werden die Top-10 Links von Google verwendet.'''
        if continue_crawl == True:
            logger.info('Lade Queue')
            queueset = file_to_set('tempData/{}/queue.txt'.format(self.GKZ))
            for line in queueset:
                self.workqueue.put(line)
            self.crawled = LockedSet(file_to_set('tempData/{}/crawled.txt'.format(self.GKZ)))
            try:
                self.addedrelevants = length_of_csv('tempData/{}/output.csv'.format(self.GKZ))
            except FileExistsError:
                self.addedrelevants = 0
                pass
            logger.info('Queue erstellt mit {} Links aus Queue-File.'.format(self.workqueue.qsize()))
            logger.info('Crawled-Liste geladen mit {} Links'.format(len(self.crawled)))
        else:
            queset = get_starting_point(self.GKZ, self.DOMAIN, self.BASE_URL)
            for line in queset:
                self.workqueue.put((line))
            logger.info('Queue erstellt mit {} Links.'.format(self.workqueue.qsize()))

    def check_charset(self, base_url):
        '''Ermittelt das auf der Webpräsenz verwendete charset.'''
        charsets = ["UTF-8", "ISO-8859-1", "ASCII"]
        html_bytes = urlopen(Request(self.BASE_URL, headers={'User-Agent': 'KommunenCrawler | https://github.com/elpunkt/KommunenCrawler/'})).read()
        for encoding in charsets:
            try:
                test = html_bytes.decode(encoding)
                self.CHARSET = encoding
                return
            except:
                continue
        if self.CHARSET == '':
            logger.warning('No charset could be identified.')
            print(self.BASE_URL)
            self.CHARSET = input('Enter manually:')
