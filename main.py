import logging
import logging.config
import pandas as pd
import os
import re
import yaml
import multiprocessing
import threading
import sys
import signal
import time

from crawlclass import Crawl
from relevancecheckerSVM import RefRelevance, PageRelevance
from textprocessing import tokenize_satz, preprocess
from readandwrite import append_row_to_csv, append_to_file, write_iterable_to_file
from spiderandparser import getinhalt, LinkFinder, get_domain_name, check_if_filelink
from database import CrawlDatabase

'''Das Frontier des Webcrawlers:'''
def setup_logging(default_path='logging.yaml', default_level=logging.INFO, env_key='LOG_CFG'):
    '''Lädt die Logging-Einstellungen aus Logging.yaml'''
    path = default_path
    value = os.getenv(env_key, None)
    if value:
        path = value
    if os.path.exists(path):
        with open(path, 'rt') as f:
            config = yaml.safe_load(f.read())
        logging.config.dictConfig(config)
    else:
        logging.basicConfig(level=default_level)
setup_logging()
logger = logging.getLogger(__name__)

'''Lädt die Grundeinstellungen aus configuration.local.yaml, bzw. aus configuration.yaml, wenn keine lokale Datei vorhanden ist. '''
if os.path.isfile('configuration.local.yaml'):
    with open ('configuration.local.yaml', 'r') as f:
        config = yaml.load(f)
else:
    with open ('configuration.yaml', 'r') as f:
        config = yaml.load(f)

KERNEL = config['RelevanceCheck']['kernel']
GAMMA = config['RelevanceCheck']['gamma']
NU = config['RelevanceCheck']['nu']
COEF0 = config['RelevanceCheck']['coef0']
DEGREE = config['RelevanceCheck']['degree']
VECT = config['RelevanceCheck']['vectorizer']
PERCENTFEATURES = config['RelevanceCheck']['percentfeatures']
SCHWELLENWERT = config['RelevanceCheck']['schwellenwert']
NGRAMRANGE = config['RelevanceCheck']['ngramrange']
MAINKEYWORDS = config['RelevanceCheck']['keywords']
NUMBER_OF_THREADS = config['NUMBER_OF_THREADS']
CRAWLDEPTH = config['Crawler']['CRAWLDEPTH']
USER_AGENT = config['Crawler']['user-agent']
MAX_CRAWL_FREQ = config['Crawler']['crawlfrequenz']
INPUT_DB = os.path.abspath(os.pardir) + config['Databases']['INPUT_DB']
OUTPUT_DB = os.path.abspath(os.pardir) + config['Databases']['OUTPUT_DB']
GOOGLE_API = config['Google-Settings']['API_KEY']
CUSTOM_SEARCH_ENGINE = config['Google-Settings']['CUSTOM_SEARCH_ENGINE']

GKZ = sys.argv[1]
if GKZ == None:
    print('''Bitte Gemeindekennziffer angeben in Form: "python main.py GKZ"
    GKZ für eine deutsche Stadt kann mit dem findgkz Script ermittelt werden.
    Dazu "python findgkz.py" ausführen.''')

def check_if_exists(gkz):
    '''Überprüft, ob es sich um einen neuen, oder fortgesetzten Suchlauf handelt und legt ggf. neue Ordnerstrukturen an.'''
    if os.path.isfile('tempData/{}/queue.txt'.format(GKZ)) and os.path.isfile('tempData/{}/crawled.txt'.format(GKZ)):
        continue_or_restart = input('Folder {} already exists. (C)ontiniue Crawl or (r)estart?'.format(GKZ))
        if continue_or_restart.lower() == 'c':
            return True
        else:
            import shutil
            shutil.rmtree('tempData/{}/'.format(GKZ))
    if not os.path.exists('tempData/{}'.format(GKZ)):
        os.mkdir('tempData/{}'.format(GKZ))
        os.mknod('tempData/{}/output.csv'.format(GKZ))
        os.mknod('tempData/{}/queue.txt'.format(GKZ))
        os.mknod('tempData/{}/crawled.txt'.format(GKZ))
    return False


def signal_handler(signal, frame):
    '''Routine, die durchgeführt wird, wenn der Suchlauf durch den Benutzer durch [Strg+C] unterbrochen wird.'''
    '''NewCrawl.shutdown wird auf True gesetzt, damit Threads keine neuen Aufgaben anfangen.'''
    '''Laufende Threads können die Untersuchung der aktuellen Webseite beenden. Nach 120 Sekunden werden sie jedoch unterbrochen.'''
    '''Output, der Duplikat-Test, die PriorityQueue, und die Crawled-Liste werden gespeichert.'''
    logger.info('\n{:*^40}\n'.format('Crawl wird unterbrochen.'))
    NewCrawl.monitor.killcounter()
    NewCrawl.shutdown = True
    shutdowntime = time.time()
    while NewCrawl.threads_alive > 0 and (time.time() - shutdowntime) < 120:
        logger.info('Warte auf {} Thread(s). Timeout in {}'.format(NewCrawl.threads_alive, int(round(120 - (time.time() - shutdowntime), 0))))
        NewCrawl.threads_alive = sum(1 if not thread.getName() in ['MainThread', 'QueueFeederThread' ] else 0 for thread in threading.enumerate())
        time.sleep(1)
    logger.info('\n{:*^40}\n'.format('Speichere Output'))
    while NewCrawl.savequeue.empty() == False:
        tosave = NewCrawl.savequeue.get()
        append_row_to_csv('tempData/{}/output.csv'.format(GKZ), tosave[0])
        append_row_to_csv('tempData/{}/duplicatetest.csv'.format(GKZ), tosave[1])
    logger.info('\n{:*^40}\n'.format('Alle gefundenen relevanten Seiten gespeichert.'))
    logger.info('\n{:*^40}\n'.format('Speichere Queue und Crawled Liste.'))
    while NewCrawl.workqueue.empty() == False:
        tosave = NewCrawl.workqueue.get()
        append_to_file('tempData/{}/queue.txt'.format(GKZ), str(tosave))
    write_iterable_to_file('tempData/{}/crawled.txt'.format(GKZ), NewCrawl.crawled)
    logger.info('\n{:*^40}\n'.format('Done.'))
    logger.info('\n{:*^40}\n'.format('Tschüss.'))
    sys.exit(0)


def set_up_relevancechecker():
    '''Trainiert eine zentrale Instanz der Relevanzbewertungsklasse mit den Trainingsdaten.'''
    traintable = pd.read_csv('traindata/trainingsdaten.csv', header=0, names=['ID', 'Link', 'Text']) # 'Link',
    traindata = traintable.Text #.apply(tuple, axis =1)
    traindata = [tokenize_satz(preprocess(text)) for text in traindata]
    trainsätze = [satz for liste in traindata for satz in liste]
    refferenz = RefRelevance(trainsätze, KERNEL, GAMMA, NU, COEF0, DEGREE, VECT, PERCENTFEATURES, NGRAMRANGE, SCHWELLENWERT, MAINKEYWORDS)
    return refferenz

def run():
    '''Aufagben, die das Frontier alle 2 Sekunden ausführt, solange Links in der Queue sind und der Benutzer den Suchlauf nicht manuell unterbricht.'''
    NewCrawl.monitor.startmonitor(maxf1=MAX_CRAWL_FREQ*0.9, acc=10)
    worktodo = True
    while worktodo == True:
        rapport()
        if NewCrawl.workqueue.empty() == False and NewCrawl.shutdown == False:
            start_worker_threads()
        if NewCrawl.savequeue.empty() == False:
            start_saving_process()
        time.sleep(2)
        if NewCrawl.savequeue.empty() == True and NewCrawl.workqueue.empty() == True:
            write_iterable_to_file('tempData/{}/crawled.txt'.format(GKZ), NewCrawl.crawled)
            worktodo == False
            return
    NewCrawl.monitor.killcounter()
    NewCrawl.shutdown == True
    return

def start_worker_threads():
    '''Alle 2 Sekunden überprüft das Frontier, wieviele Threads laufen und startet entsprechend der Konfiguration neue Threads.'''
    NewCrawl.threads_alive = sum(1 if not thread.getName() in ['MainThread', 'QueueFeederThread' ] else 0 for thread in threading.enumerate())
    for _ in range(NewCrawl.threads_alive, NewCrawl.NUMBER_OF_THREADS):
        t = threading.Thread(target=arbeit)
        t.daemon = True
        t.start()
    return

def rapport():
    '''Alle 2 Sekunden gibt das Frontier Informationen zum aktuellen Stand des Suchlaufs aus.'''
    now = time.time()
    logger.info('Queue:{} | Crawled:{} | relevant: {}'.format(NewCrawl.workqueue.qsize(), NewCrawl.monitor.currentcount() , NewCrawl.addedrelevants))
    logger.info('Threads alive: {} | Crawl-Frequency Av. :{}| Crawl-Frequency Latest: {}'.format(NewCrawl.threads_alive, round(NewCrawl.monitor.getmeanfrequency(), 3), round(NewCrawl.monitor.getcurrentfrequency(), 3) ))
    return

def start_saving_process():
    '''Alle 2 Sekunden wird, wenn Threads in der SaveQueue sind, überprüft, ob der Speicher-Prozess noch läuft und ggf. neu gestartet.'''
    if NewCrawl.save_process.is_alive() == False:
        NewCrawl.save_process = multiprocessing.Process(target=speichern, args=(NewCrawl.savequeue,))
        NewCrawl.save_process.daemon = True
        NewCrawl.save_process.start()
    return


'''Der Speicherprozess'''

def speichern(queue):
    '''Routine, die vom Speicher-Prozess ausgeführt wird, solange Links in der SaveQueue sind.'''
    while queue.empty() == False:
        tosave = queue.get()
        append_row_to_csv('tempData/{}/output.csv'.format(GKZ), tosave[0])
        append_row_to_csv('tempData/{}/duplicatetest.csv'.format(GKZ), tosave[1])
    return


'''Die Threads:'''

def arbeit():
    '''Hauptarbeitsschleife eines jeden Threads, inklusive Downloader, Relevanzbewertung und Parser.'''
    while NewCrawl.workqueue.empty() == False and NewCrawl.shutdown == False:
        NewCrawl.monitor.currenttoohigh.wait() # Blockiert, wenn die Crawl-Frequenz zu hoch ist.
        priorityandlink = NewCrawl.workqueue.get()
        #logger.info('Thread {}| Now crawling {}'.format(threading.current_thread().name, link))
        link = priorityandlink[1]
        if NewCrawl.crawled.__contains__(link):
            NewCrawl.workqueue.task_done()
            continue
        if not NewCrawl.robotparser.can_fetch(USER_AGENT, link):
            addlinkstocrawled(truelink, link)
            continue
        '''Der Downloader.'''
        truelink, typ, rawcontent, timestamp, do_follow = getinhalt(NewCrawl.CHARSET, NewCrawl.BASE_URL, link)
        NewCrawl.monitor.plusone()
        if typ == None:
            addlinkstocrawled(truelink, link)
            continue
        '''Die Relevanzbewertung'''
        relevancecheck = PageRelevance(Refferenz)
        relevancecheck.feed(typ, rawcontent)
        titlerelevant = relevancecheck.titlerelevance()
        contentrelevant = relevancecheck.contentrelevance()
        if contentrelevant == 'Duplikat':
            addlinkstocrawled(truelink, link)
            continue
        elif contentrelevant == True:
            childpriority = 1
            outputline = relevancecheck.getoutput()
            for i in (truelink, typ, timestamp, rawcontent):
                outputline[0].append(i)
            NewCrawl.savequeue.put(outputline)
            NewCrawl.addedrelevants += 1
        else:
            childpriority = priorityandlink[0] + 1
        '''Der Parser'''
        if childpriority < NewCrawl.CRAWLDEPTH and typ == 'html' and do_follow == 1:
            findandaddlinks(truelink, rawcontent, childpriority)
        addlinkstocrawled(truelink, link)
    return

def findandaddlinks(truelink, rawcontent, childpriority):
    '''Der LinkFinder exthrahiert alle internen Links aus der HTML Datei.'''
    '''Links werden zur PriorityQueue hinzugefüht, wenn: Sie noch nicht gecrawled wurden, interner Links sind und nicht mit einer bekannten Dateiendung enden.'''
    finder = LinkFinder(NewCrawl.BASE_URL, truelink)
    finder.feed(rawcontent)
    links = finder.page_links()
    for link in links:
        if NewCrawl.crawled.__contains__(link) == True:
            continue
        elif get_domain_name(link) != NewCrawl.DOMAIN:
            continue
        elif check_if_filelink(link) == True:
            continue
        else:
            NewCrawl.workqueue.put((childpriority,link))
    return

def addlinkstocrawled(truelink, link):
    '''Fügt den gecrawlten Link zum Crawled-Set hinzu. Wenn einer Weiterleitung gefolgt wurde, wird auch dieser Link hinzugefügt.'''
    if not truelink == link:
        NewCrawl.crawled.add(truelink)
        NewCrawl.crawled.add(link)
    else:
        NewCrawl.crawled.add(link)
    NewCrawl.workqueue.task_done()
    return

if __name__ == '__main__':
    starttime = time.time()
    logger.info('''

    --------------------------------------------------
    Starte Suchlauf. Zeitpunkt: {}
    Initialisiere GKZ: {}
    --------------------------------------------------

     '''.format(time.time(), GKZ))
    continue_crawl = check_if_exists(GKZ)
    Database = CrawlDatabase(INPUT_DB, OUTPUT_DB, GKZ)
    name, base_url = Database.initialisierung(continue_crawl)
    NewCrawl = Crawl(continue_crawl, NUMBER_OF_THREADS, CRAWLDEPTH, base_url, GKZ)
    Refferenz = set_up_relevancechecker()
    signal.signal(signal.SIGINT, signal_handler)
    run()
    endtime = time.time()
    logger.info('''
    --------------------------------------------------
    Der Crawl von {} ist abgeschlossen.
    Die Ergebnisse werden gespeichert ...
    '''.format(name))
    Database.writedb()
    logger.info('''

    In {} Sekunden wurden {} Seiten gecrawlt.
    Dabei wurden {} relevante Seiten gefunden und in
    der Tabelle {} gespeichert.
    --------------------------------------------------

    '''.format(round((endtime - starttime), 2), len(NewCrawl.crawled), Database.num_rel_links, Database.tablename))
    time.sleep(1)
    logger.info('\n{:*^40}\n'.format('Tschüss.'))
