import logging
import logging.config
import pandas as pd
import os
import re
import yaml
import multiprocessing
import threading
import pandas as pd
from crawlclass import Crawl
from relevancecheckerSVM import RefRelevance, PageRelevance
from textprocessing import tokenize_satz, preprocess
from readandwrite import append_row_to_csv, append_to_file, write_iterable_to_file
from spiderandparser import getinhalt, LinkFinder, get_domain_name, check_if_filelink
from database import CrawlDatabase
import sys
import signal
import time


def setup_logging(
        default_path='logging.yaml',
        default_level=logging.INFO,
        env_key='LOG_CFG'
    ):
        """Setup logging configuration."""
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


if os.path.isfile('configuration.local.yaml'):
    with open ('configuration.local.yaml', 'r') as f:
        config = yaml.load(f)
else:
    with open ('configuration.yaml', 'r') as f:
        config = yaml.load(f)

SCHWELLENWERT = config['RelevanceCheck']['schwellenwert']
NGRAMRANGE = config['RelevanceCheck']['ngramrange']
MINDESTÄHNLICHKEIT = config['RelevanceCheck']['mindestähnlichkeit']
MAINKEYWORDS = config['RelevanceCheck']['keywords']
NUMBER_OF_THREADS = config['NUMBER_OF_THREADS']
CRAWLDEPTH = config['Crawler']['CRAWLDEPTH']
INPUT_DB = os.path.abspath(os.pardir) + config['Databases']['INPUT_DB']
OUTPUT_DB = os.path.abspath(os.pardir) + config['Databases']['OUTPUT_DB']
GOOGLE_API = config['Google-Settings']['API_KEY']
CUSTOM_SEARCH_ENGINE = config['Google-Settings']['CUSTOM_SEARCH_ENGINE']
STANDARD_KEYWORD = config['Google-Settings']['STANDARD_KEYWORD']
GKZ = sys.argv[1]


def signal_handler(signal, frame):
    logger.info('\n{:*^40}\n'.format('Crawl wird unterbrochen.'))
    NewCrawl.shutdown = True
    shutdowntime = time.time()
    while threading.active_count() > 2 and (time.time() - shutdowntime) < 120:
        logger.info('Warte auf {} Thread(s). Timeout in {}'.format(threading.active_count()-2, int(round(120 - (time.time() - shutdowntime), 0))))
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
    sys-exit(0)

def set_up_relevancechecker():
    traintable = pd.read_csv('traindata/trainingsdaten.csv', header=0, names=['ID', 'Link', 'Text']) # 'Link',
    traindata = traintable.Text #.apply(tuple, axis =1)
    traindata = [tokenize_satz(preprocess(text)) for text in traindata]
    trainsätze = [satz for liste in traindata for satz in liste]
    refferenz = RefRelevance(trainsätze, NGRAMRANGE, MINDESTÄHNLICHKEIT, SCHWELLENWERT, MAINKEYWORDS)
    return refferenz

def run():
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
    return

def start_worker_threads():
    print('Active Count {}'.format(threading.active_count()))
    print('Process alive? {}'.format(NewCrawl.save_process.is_alive()))
    if NewCrawl.save_process.is_alive() == True:
        x = 2
    else:
        x = 1
    print(x)
    NewCrawl.threads_alive = threading.active_count() - x
    print(NewCrawl.threads_alive)
    print(range(NewCrawl.threads_alive, NewCrawl.NUMBER_OF_THREADS))
    for _ in range(NewCrawl.threads_alive, NewCrawl.NUMBER_OF_THREADS):
        t = threading.Thread(target=arbeit)
        #t.daemon = True
        t.start()
    return

def start_saving_process():
    if NewCrawl.save_process.is_alive() == False:
        NewCrawl.save_process = multiprocessing.Process(target=speichern, args=(NewCrawl.savequeue,))
        #NewCrawl.save_process.daemon = True
        NewCrawl.save_process.start()
        print(NewCrawl.save_process.is_alive())
        return
    return

def arbeit():
    print('Thread started')
    while NewCrawl.workqueue.empty() == False or NewCrawl.shutdown == False:
        print('Thread continue')
        priorityandlink = NewCrawl.workqueue.get() # Taking Tuple with Relevance and Link from Queue.
        #logger.info('Thread {}| Now crawling {}'.format(threading.current_thread().name, link))
        link = priorityandlink[1]
        if NewCrawl.crawled.__contains__(link):
            NewCrawl.workqueue.task_done()
            print('Thread ended crawled')
            continue
        print('inhalt bekommen')
        truelink, typ, rawcontent, timestamp = getinhalt(NewCrawl.CHARSET, link)
        print('inhalt gegettet')
        if typ == None:
            NewCrawl.crawled.add(truelink)
            NewCrawl.workqueue.task_done()
            continue
        relevancecheck = PageRelevance(Refferenz)
        print(truelink)
        relevancecheck.feed(typ, rawcontent)
        titlerelevant = relevancecheck.titlerelevance()
        contentrelevant = relevancecheck.contentrelevance()
        trueorfalse = int(input('0 or 1?'))
        if contentrelevant == True:
            childpriority = 0
        #     outputline = relevancecheck.getoutput()
        #     for i in (truelink, typ, timestamp, rawcontent):
        #         outputline[0].append(i)
        #     NewCrawl.addedrelevants += 1
        #     NewCrawl.savequeue.put(outputline)
        elif contentrelevant == 'Duplicat':
            NewCrawl.crawled.add(truelink)
            NewCrawl.workqueue.task_done()
            print('DUPLICAT')
            continue
        else:
            childpriority = priorityandlink[0] + 1
        outputline = relevancecheck.getoutput()
        newoutputline = [[trueorfalse, relevancecheck.relevanz, truelink,relevancecheck.title, relevancecheck.text, timestamp],outputline[1]]
        NewCrawl.savequeue.put(newoutputline)
        if childpriority < NewCrawl.CRAWLDEPTH and typ == 'html':
            finder = LinkFinder(NewCrawl.BASE_URL, truelink)
            finder.feed(rawcontent)
            links = finder.page_links()
            addlinkstoqueue(links, childpriority)
        NewCrawl.crawled.add(truelink)
        NewCrawl.workqueue.task_done()
        print('Thread ended normally')
    return

def speichern(queue):
    #while queue.empty() == False:
    tosave = NewCrawl.savequeue.get()
    append_row_to_csv('tempData/{}/output.csv'.format(GKZ), tosave[0])
    append_row_to_csv('tempData/{}/duplicatetest.csv'.format(GKZ), tosave[1])
    print('SAVED!')
    #time.sleep(20)
    #return

def addlinkstoqueue(links, childpriority):
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

def rapport():
    now = time.time()
    NewCrawl.crawledlastminutelist.append((len(NewCrawl.crawled), now))
    reducedtooneminute = False
    while reducedtooneminute == False:
        if now - NewCrawl.crawledlastminutelist[0][1] > 60:
            NewCrawl.crawledlastminutelist.pop(0)
        else:
            crawledlastminute = NewCrawl.crawledlastminutelist[-1][0] - NewCrawl.crawledlastminutelist[0][0]
            reducedtooneminute = True
    logger.info('Queue:{} | crawled:{} | relevant: {}'.format(NewCrawl.workqueue.qsize(), len(NewCrawl.crawled) , NewCrawl.addedrelevants))
    logger.info('Threads alive: {} | Crawling {} Pages per Minute'.format(NewCrawl.threads_alive, crawledlastminute))
    time.sleep(2)
    return

def check_for_queue(gkz):
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


# GKZ = str(argv[1])
# name, base_url, new_or_continue = database(GKZ)
if __name__ == '__main__':
    starttime = time.time()
    logger.info('''

    --------------------------------------------------
    Starting Crawl. Time: {}
    Initializing ID: {}
    --------------------------------------------------

     '''.format(time.time(), GKZ))
    continue_crawl = check_for_queue(GKZ)
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
    ''')
    Database.writedb()
    logger.info('''

    In {} Sekunden wurden {} Seiten gecrawlt.
    Dabei wurden {} relevante Seiten gefunden und in
    der Tabelle {} gespeichert.
    --------------------------------------------------

    '''.format((endtime - starttime), len(NewCrawl.crawled), Database.num_rel_links, Database.tablename))
    time.sleep(1)
    logger.info('\n{:*^40}\n'.format('Tschüss.'))
