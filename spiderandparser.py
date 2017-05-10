from urllib.request import urlopen, Request, HTTPError, quote
from urllib import parse
from html.parser import HTMLParser
from lxml.html import fromstring
from contextlib import closing
import sys
import random
import string
import logging
import time

logger = logging.getLogger(__name__)

def getinhalt(charset, link):
    """Follow 301-Redirects and 'http-equiv = refresh'-Redirects """
    while True:
        print(link)
        print(quote(link, safe = ':/?=#&'))
        try:
            response = urlopen(Request(quote(link, safe = ':/?=#&'), headers={'User-Agent': 'KommunenCrawler | https://github.com/elpunkt/KommunenCrawler/'}))
            timestamp = time.time()
        except HTTPError as e:
            logger.info('Keine Response\n(Link: {}'.format(link))
            return None, None, None, None
        if 'text/html' in response.getheader('Content-Type'):
            output = response.read()
            redirection = fromstring(output).xpath("//meta[@http-equiv = 'refresh']/@content")
            if redirection:
                link = link + redirection[0].split(";")[1].strip().replace("url=", "")
            else:
                try:
                    html_string = output.decode(charset)
                    return link, 'html', html_string, timestamp
                except Exception as e:
                    logger.info('Decoding Fehler, oder Timeout:', exc_info=True)
                    return None, None, None, None
        elif 'application/pdf' in response.getheader('Content-Type'):
            data = response.read()
            uniqueidentifier = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(6))
            temppdf = 'tempData/downloads/temp_{}.pdf'.format(uniqueidentifier)
            with open (temppdf, 'wb') as pdf:
                pdf.write(data)
            return link, 'pdf', temppdf, timestamp
        else:
            logger.info('Neither HTML nor PDF: {}'.format(link))
            return None, None, None, None

# def getinhalt(charset, link):
#     try:
#         truelink,  = follow_redirect(link)
#         response = urlopen(Request(truelink, headers={'User-Agent': 'KommunenCrawler | https://github.com/elpunkt/KommunenCrawler/'}))
#         timestamp = time.time()
#     except HTTPError as e:
#         logger.info('Keine Response\n(Link: {}'.format(link))
#         return None, None, None, None
#     if 'text/html' in response.getheader('Content-Type'): # Checkt, ob ein gültiges HTML Dokument zurückkommt
#         try: # Probiert die beiden gängigen Codierungen aus. Muss noch anders gelöst werden.
#             html_bytes = response.read()
#             html_string = html_bytes.decode(charset)
#             return truelink, 'html', html_string, timestamp
#         except Exception as e:
#             logger.error('Decoding Fehler, oder Timeout:',exc_info=True)
#             return None, None, None, None
#     else:
#         try:
#             data = response.read()
#             uniqueidentifier = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(6))
#             temppdf = 'tempData/downloads/temp_{}.pdf'.format(uniqueidentifier)
#             with open (temppdf, 'wb') as pdf:
#                 pdf.write(data)
#             return truelink, 'pdf', temppdf, None
#         except Exception as e:
#             logger.warning('Fehler beim Versuch Datei zu laden.\nLink: {}'.format(link))
#             logger.warning('Fehler: \n{}'.format(e))
#             return None, None, None, None
#
# def follow_redirect(url):
#     """Follow 301-Redirects and 'http-equiv = refresh'-Redirects. Escape non-ASCII characters """
#     while True:
#         response = urlopen(Request(quote(url, safe = ':/?='), headers={'User-Agent': 'KommunenCrawler | https://github.com/elpunkt/KommunenCrawler/'}))
#         output = response.read()
#         redirection = fromstring(output).xpath("//meta[@http-equiv = 'refresh']/@content")
#         if redirection:
#             url = url + redirection[0].split(";")[1].strip().replace("url=", "")
#         else:
#             return url, output


def check_if_filelink(link):
    if link.endswith(('.exe','.zip','.doc', 'docx', '.jpg', '.jpeg', '.png', '.gif', '.xls', '.xlsx', '.ppt', '.pptx', '.vcf', '.asp')) == True:
        return True
    else:
        return False

## ''' Quelle https://github.com/buckyroberts/Spider/blob/master/link_finder.py '''

def get_domain_name(url):
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

    def __init__(self, base_url, page_url):
        super().__init__()
        self.base_url = base_url
        self.page_url = page_url
        self.links = set()

# Wenn HTMLParse feed() aufgerufen wird, wird diese Funktion ausgeführt. when it encounters an opening tag <a>
    def handle_starttag(self, tag, attrs): #attrs bekomm ich aus HTMLParser und kann damit weiterarbeiten
        try:
            if tag == 'a':
                for (attribute, value) in attrs:
                    if attribute == 'href':
                        url = parse.urljoin(self.base_url, value) #Komplette URLs werden beibehalten, relative URLs werden um die base_url ergänzt.
                        self.links.add(url)
        except Exception as e:
            logger.warning('Fehler im Linkfinder.handle_starttag')
            print(e)

    def page_links(self):
        return self.links

    def error(self, message):
        pass

## ''' Ende des Codes von https://github.com/buckyroberts/Spider/blob/master/link_finder.py '''
