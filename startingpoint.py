import os
import logging
import yaml
from googleapiclient import discovery
logger = logging.getLogger(__name__)

if os.path.isfile('configuration.local.yaml'):
    with open ('configuration.local.yaml', 'r') as f:
        config = yaml.load(f)
else:
    with open ('configuration.yaml', 'r') as f:
        config = yaml.load(f)

logging.getLogger('googleapiclient').setLevel(logging.WARNING)
GOOGLE_API = config['Google-Settings']['API_KEY']
CUSTOM_SEARCH_ENGINE = config['Google-Settings']['CUSTOM_SEARCH_ENGINE']
STANDARD_KEYWORD = config['Google-Settings']['STANDARD_KEYWORD']

'''Nutzt die Google-Suche-API, um die ersten 10 Links zu bekommen.
Dazu wird eine Suchanfrage, die sich auf die zu durchsuchende Domain beschränkt,
mit dem Keyword Bürgerbeteiligung durchgeführt.'''

def get_starting_point(gkz, domain, homepage):
    tempqueue = []
    tempqueue.append((0, homepage))
    googlelinks = google_searchandextract_with_api(domain)
    if google_searchandextract_with_api(domain) == None:
        logger.info('''Extraction of google results with API failed.
        It is possible to try to scrape them without API.
        But that would violate Googles Terms and Conditions of Use.
        Otherwise you may add starting links manually to "tempData/{}/queue.txt".
        Line by Line in the format (Priority, URL) e.g. (0, 'https://wikipedia.org')
        wheras 0 is the highest Priority.))'''.format(gkz))
        violate = input('Violate Google Terms and Conditions of Use to find some Links? (Y)es or (N)o')
        if violate.lower() in ['y']:
            googlelinks = google_searchandextract_without_api(domain)
    for link in googlelinks:
        tempqueue.append((0, link))
    logger.info('Found {} links as starting points'.format(len(tempqueue)))
    return tempqueue

def google_searchandextract_with_api(domain):
    key = ' {}'.format(STANDARD_KEYWORD)
    if GOOGLE_API == None:
        logger.info('Google Custom Search API required. Please visit: https://console.developers.google.com/apis/')
        return
    if CUSTOM_SEARCH_ENGINE == None:
        logger.info('Google Custom Search Engine required. Please visit: https://console.developers.google.com/apis/')
        return
    service = discovery.build("customsearch", "v1", developerKey=GOOGLE_API)
    parameter = " -filetype:ppt -filetype:doc"
    results = service.cse().list(
        q="site:"+ domain + key + parameter,
        cx=CUSTOM_SEARCH_ENGINE
        ).execute()
    googlequeue = [link for link in [dic['link'] for dic in results['items']]]
    return googlequeue

def search(domain, keyword ): #, fheaders):
    '''Funktiniert auch ohne API, dann ist es aber gegen die Google-Geschäftsbedingungen.'''
    q = quote('site:{} {}'.format(domain, keyword))
    user_agent = 'Mozilla/5.0 (Windows; U; Windows NT 5.1; de-DE; rv:1.9.0.7) Gecko/2009021910 Firefox/3.0.7'
    search = 'https://www.google.de/search?&q={}'.format(q)
    headers = {'User-Agent': user_agent,}
    request = Request(search, None, headers)
    response = urlopen(request)
    html_bytes = response.read()
    soup = BeautifulSoup(html_bytes, "lxml")
    return soup

def extract(soup):
    linklist = []
    try:
        data = soup.find_all('h3',attrs={'class':'r'}) #Links sind in den Google Ergebnissen in einem <h3> mit der Klasse "r"
        for row in data:
            links = row.find_all('a') #In jedem Elemt soll os.path.abspath(os.pardir) +  der <a> Tag gefunden werden
            for link in links:
                link = re.sub('\\/url\\?q=',"", link['href'], count=1)  # GoogleResult Links beginnen mit "/url?q=". Der Teil wird entfernt
                sep = '&sa=U' # An jeden Link hängt Google noch ettliche Queries mit ran. Diese beginnen mit '&sa=U' und werden entfernt
                link = link.split(sep, -1)[0]
                linklist.append(link)
        return linklist
    except TypeError as e:
        print(e)
        return linklist

def google_searchandextract_without_api(domain):
    from urllib.request import Request, urlopen
    from urllib.parse import quote
    from bs4 import BeautifulSoup
    from lxml import html, etree
    googlequeue = []
    for link in extract(search(domain, STANDARD_KEYWORD)):
        googlequeue.append(link)
    return googlequeue
