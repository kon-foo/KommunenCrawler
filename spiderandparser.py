from urllib.request import urlopen, Request, HTTPError, quote
from urllib import parse, robotparser
from html.parser import HTMLParser
from lxml.html import fromstring
from contextlib import closing
import sys
import logging
import time
import posixpath

logger = logging.getLogger(__name__)

def getinhalt(charset, baseurl, link):
    """Lädt HTML- und PDF-Dateien herunter, ignoriert den Rest.
    Parst die Meta-Daten:
    Folgt 301-Redirects und 'http-equiv = refresh'-Redirects.
    Beachtet Meta-Angaben für Robots.
    """
    while True:
        try:
            response = urlopen(Request(quote(link, safe = ':/?=#&'), headers={'User-Agent': 'KommunenCrawler | https://github.com/elpunkt/KommunenCrawler/'}))
            timestamp = time.time()
        except HTTPError as e:
            logger.info('Keine Response oder Timeout\n(Link: {})'.format(link))
            return link, None, None, None, None
        if 'text/html' in response.getheader('Content-Type'):
            output = response.read()
            can_indexfollow = indexfollow(output)
            if can_indexfollow == -1:
                #logger.info('noindex in HTML-Meta\n(Link: {})'.format(link))
                return link, None, None, None, None
            redirection = fromstring(output).xpath("//meta[@http-equiv = 'refresh']/@content")
            if redirection:
                link = baseurl + redirection[0].split(";")[1].strip().replace("url=", "")
            else:
                try:
                    html_string = output.decode(charset)
                    return link, 'html', html_string, timestamp, can_indexfollow
                except Exception as e:
                    logger.info('Decoding Fehler, oder Timeout:', exc_info=True)
                    return link, None, None, None, None
        # elif 'application/pdf' in response.getheader('Content-Type'):
        #     path = parse.urlsplit(link).path
        #     filename = posixpath.basename(path)
        #     data = response.read()
        #     temppdf = 'tempData/downloads/{}.pdf'.format(filename)
        #     with open (temppdf, 'wb') as pdf:
        #         pdf.write(data)
        #     return link, 'pdf', temppdf, timestamp, None
        else:
            logger.info('Neither HTML nor PDF: {}'.format(link))
            return link, None, None, None, None

def indexfollow(meta):
    '''Meta name= 'robots' Parser.'''
    alleanweisungen = fromstring(meta).xpath("//meta[@name = 'robots']/@content")
    for anweisung in alleanweisungen:
        if 'noindex' in [x.strip() for x in anweisung.split(',')]:
            return -1
        elif 'nofollow' in [x.strip() for x in anweisung.split(',')]:
            return 0
    return 1


def check_if_filelink(link):
    '''Überprüft, auf gängige Dateiendungen.
    Wird genutzt, bevor ein Link zur Queue hinzugefügt wird.'''
    if link.endswith(('.exe','.zip','.doc', 'docx', '.jpg', '.jpeg', '.png', '.gif', '.xls', '.xlsx', '.ppt', '.pptx', '.vcf', '.asp')) == True:
        return True
    else:
        return False

''' Der folgende Code, bis zur erneuten Kennzeichnung stammt aus folgendem Projekt: https://github.com/buckyroberts/Spider/blob/master/link_finder.py
und ist Lizenzfrei verfügbar. Kleinere Änderungen wurden vorgenommen.'''

def get_domain_name(url):
    '''Extrahiert die Domain, um interne Links zu erkennen.'''
    try:
        results = get_sub_domain_name(url).split('.')
        return results[-2] + '.' + results[-1]
    except:
        return url

def get_sub_domain_name(url):
    try:
        return parse.urlparse(url).netloc
    except:
        return ''


class LinkFinder(HTMLParser):
    '''Findet alle Links.'''

    def __init__(self, base_url, page_url):
        super().__init__()
        self.base_url = base_url
        self.page_url = page_url
        self.links = set()

    def handle_starttag(self, tag, attrs):
        try:
            if tag == 'a':
                for (attribute, value) in attrs:
                    if attribute == 'href':
                        url = parse.urljoin(self.base_url, value)
                        self.links.add(url)
        except Exception as e:
            logger.warning('Fehler im Linkfinder.handle_starttag')

    def page_links(self):
        return self.links

    def error(self, message):
        pass

''' Ende des Codes von https://github.com/buckyroberts/Spider/blob/master/link_finder.py '''
