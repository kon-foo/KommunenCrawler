# KommunenCrawler

**Work in progress**

Focussed WebCrawler to search and collect for unstructured, decentralized data on a specific topic. Content-based Relevance check for .html and .pdf documents via Taxonomie or scikit-learn document classification. Written in Python 3.5.2
Based on the Spider: https://github.com/buckyroberts/Spider by <a href="https://github.com/buckyroberts">Bucky Roberts</a>. Thanks mate!

Originally designed for crawling Websites of German Municipals and collecting data about informal citizien engagement.
This is my very first Python project. It might not be very Pythonic in some parts. It might not be 'best-practice'. I am grateful for any constructive feedback and contribution.

## Content:

1. Background & Concept
2. Used Non-Standard Libraries
3. Components & How to use
4. Next steps

## 1. Background and Concept

This Prototype is part of a Bachelor-Thesis with the purpose of collecting data about the effort of any german municipal in citizen engagement and participation. Starting with one or more given relevant pages (e.g. the first ten results of agoogle search for a relevant keyword, limited to the municipal website), the crawler will visit every link from every relevant page, and from every childpage of a relevant page. It stops at irrelevant child pages of irrelevant pages (see illustration 1). This restriction was was chosen to limit the crawl on relevant parts of the municipals website.
<figure style="float: right;">
  <img src="/img/crawling_path.png?raw=true" alt='crawling path' width="60%" />
  <figcaption>Illustration 1: Crawling path</figcaption>
</figure>

The relevance assesment is based on the cosine similarity of the Term-Frequency/Invert-Document-Frequency values of the trainings-dataset data test dcument.Jana Vembunarayanan provides an [easy to understand introduction](https://janav.wordpress.com/2013/10/27/tf-idf-and-cosine-similarity/) For each document an value between 0 and 1 is calculated. Documents with an relevance value, higher than 0.2 are labeled as relevant and saved to a database. 

## 2. Used Non-Standard Python Libraries
This Prototype was developed in Python 3.5.2
The following Non-Standard Libraries are required to run this Prototype:
* Required:
	* [sqlite3](https://docs.python.org/3/library/sqlite3.html) - For SQLLite database connection.
	* [logging](https://docs.python.org/3.5/library/logging.html) - Used for well.. logging.
	* [PyYAML 3.12](https://pypi.python.org/pypi/PyYAML/3.12) - Used for parsing the config-files
	* [boilerpipe-py3 1.2](https://pypi.python.org/pypi/boilerpipe-py3) - Getting rid of boilerplate content.
	* [scikit-learn 0.18.1](https://pypi.python.org/pypi/scikit-learn/0.18.1) - Used for the machine learning part.
	* [nltk 3.2.2](https://pypi.python.org/pypi/nltk/3.2.2) - Used for stemming
	* [pandas 0.19.2](https://pypi.python.org/pypi/pandas) - For CSV reading and Data handling

* Additional:
	* [google-api-python-client](https://github.com/google/google-api-python-client) - Can be used to automatically add google results for a specific keyword to the starting queue. API required.
	* [BeautifulSoup 4](https://pypi.python.org/pypi/beautifulsoup4) - Might be used to automatically add google results for a specific keyword to the starting queue without API. Disclaimer: This would violate their Terms and Conditions of Use and you really shouldn't do this!!!1
	* [lxml 3.4.0](https://pypi.python.org/pypi/lxml/3.4.0) - See BeautifulSoup 4.
	

## 3. Components & How to use
### First run:
0. Change configuration.yaml and logging.yaml to according to your needs.
	* You should definitely set the number of threads according to the capabilities of you system. 
1. Run main.py once, to create datastructures. 
2. Insert at least one entity to input database, including name, homepage, and unique identifier. 
3. Run main.py again for each crawl. 
4. Insert Unique when getting asked for gkz.
5. Create a starting queue:
	* Either uncomment 'queue = erstell_queue_quicklane(...)' or 'queue = erstelle_queue(...)' in main.py
	* When quicklane is chosen, the first ten search results for the standard keyword, as well as the homepage is added to the queue.
	* Elsewise you have more options:
	* You can insert links manually
	* You can add a list of Links. Use a .txt with one Link per Line. Put it in a folder 'Linklisten'. Enter filename when you are asked for it.
	* You can run a google search for as many keywords as you want. The first 10 results will be added to queue.
	* You can insert the already saved links from the output database to the queue (Useful, if you have changed the relevance criteria)
6. Wait for the process to finish. You can stopp and resume the crawl at any point.


### main.py
Initializes the Crawl:
Reads in the Configuration. Instanciates the RelevanceCheckerr. Sets up the datastructure. This includes creating an input and an output database. Creating folders for the queue-files, the list of crawled pages, the output-csv and a for downloading pdf-documents. Creates the starting queue, based on user settings. Starts the frontier.

### relevancechecker.py
Spider.py passes the HTML-document/ the pdf text to relevancecheck.runcheck(). The text of HTML-documents will be extracted, using a boilerpipe extractor. The text will than be preprocessed (Some word forms are replaced, stopwords will be removed, the documents gets tokenized (nltk word_tokenize), each token gets stemmed (nltk snowball GermanStemmer), words from the list of weighted words will be added twice to the stemmed words.) The tf/idf-value gets calculated by the TfidfVectorizer from scikit-learn, the cosine similarity gets calculated and will be pairwised compared to the value of each document in the trainings-dataset.

## 2. Next steps

	* Improve traindata, stoppword list and word weightings. 
	* Completing the documentation
	* ...


