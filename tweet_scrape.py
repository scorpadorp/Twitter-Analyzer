#  -*- coding: utf-8 -*-
import urllib, re
import fire
import time
import json
import datetime as dt
import sqlite3
from pyquery import PyQuery

class Tweet():
    def __init__(self):
        self.author_id = None
        self.day = None
        self.geo = None
        self.hashtags = None
        self.id = None
        self.lang = None
        self.likes = None
        self.mentions = None
        self.name = None
        self.permalink = None
        self.replies = None
        self.retweets = None
        self.text = None
        self.time = None
        self.timestamp = None
        self.urls = None
        self.username = None
        self.user_url = None

class TweetHandler():
    def __init__(self, base_url, url_data, max_tweets=100, db=False, geo=False, lang_to_filter=None, out="tweets_output"):
        self.results = []
        self.max_tweets = max_tweets
        self.min_pos = ''
        self.geo_filter = geo
        self.lang_to_filter = lang_to_filter
        self.base_url = base_url
        self.url_data = url_data
        self.under_limit = True
        self.to_db = db
        self.url = None
        self.output_file = out

    def update_url(self):
        self.url = self.base_url % (urllib.parse.quote(self.url_data), self.min_pos)

    def gather_tweet_info(self, tweets):
        for tweet_html in tweets:
            tweet_info = PyQuery(tweet_html)
            tweet = Tweet()
            if len(self.results) >= self.max_tweets:
                return False

            tweet.lang = tweet_info("p.TweetTextSize").attr("lang")
            if self.lang_to_filter != None and self.lang_to_filter != tweet.lang:
                continue
            
            tweet.name = tweet_info("div")[0].attrib['data-name']
            tweet.username = tweet_info("div")[0].attrib['data-screen-name']
            text = re.sub(r"\s+", " ", tweet_info("p.js-tweet-text").text())
            text = text.replace('# ', '#').replace('@ ', '@').replace(':// ', '://')
            text = re.sub("http.*(?<=\…)", "", text)
            tweet.text = re.sub("(http|pic.twitter.com|instagram.com)\S*", '', text)
            tweet.replies = int(re.findall('[0-9]+', tweet_info("span.ProfileTweet-actionCountForAria")[0].text)[0])
            tweet.retweets = int(re.findall('[0-9]+', tweet_info("span.ProfileTweet-actionCountForAria")[1].text)[0])
            tweet.likes = int(re.findall('[0-9]+', tweet_info("span.ProfileTweet-actionCountForAria")[2].text)[0])
            tweet.timestamp = int(tweet_info("span.js-short-timestamp").attr("data-time"))
            datetime = dt.datetime.fromtimestamp(tweet.timestamp)
            tweet.day = dt.datetime.strftime(datetime, '%m'+'/'+'%d'+'/'+'%Y')
            tweet.time = dt.datetime.strftime(datetime, '%H'+':'+'%M'+':'+'%S')
            tweet.id = tweet_info.attr("data-tweet-id")
            tweet.author_id = int(tweet_info("a.js-user-profile-link").attr("data-user-id"))
            tweet.permalink = 'https://twitter.com' + tweet_info.attr("data-permalink-path")
            tweet.user_url = "https://twitter.com/" + tweet.username
            tweet.mentions = " ".join(re.compile('(@\\w*)').findall(tweet.text))
            tweet.hashtags = " ".join(re.compile('(#\\w*)').findall(tweet.text))
            urls = []
            for url in tweet_info("a"):
                try:
                    urls.append((url.attrib["data-expanded-url"]))
                except KeyError:
                    pass
            tweet.urls = ", ".join(urls)
            # TODO: load GEODATE on google to see if location is real
            # THE FOLLOWING IS AN EXPENSIVE OPERATION!
            if self.geo_filter:
                for t in self.results:
                    if tweet.username == t.username:
                        tweet.geo = t.geo
                else:
                    c = urllib.request.build_opener()
                    user_agent = "Mozilla/5.0 (Windows NT 6.1; Win64; x64)"
                    headers = [('User-Agent', user_agent)]
                    c.addheaders = headers
                    try:
                        r = c.open(tweet.user_url).read()
                        soup = PyQuery(r)
                        tweet.geo = soup("span.ProfileHeaderCard-locationText").text()
                    except urllib.error.HTTPError as e:
                        print("The server couldn't fulfill the request (error code {})".format(e.code))

            # check for duplicates
            for t in self.results:
                if tweet.id == t.id:
                    break
            else:
                self.results.append(tweet)
                size = len(manager.results)
                if size % 100 == 0 and size < self.max_tweets:
                    print("So far: {} tweets".format(size))

        return True

    def download_to_file(self):
        file = "data/" + self.output_file + ".csv"
        with open(file, "w+", encoding = "utf-8") as f:
            f.write("")
            f.write("{}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}".format(
                    "day",  "time", "name", "username", "text", "timestamp", "likes", "replies",
                    "retweets", "hashtags", "mentions", "language", "urls",
                    "permalink", "id", "author_id", "user_url", "geo"))
            for tweet in self.results:
                f.write("\n{}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}".format(
                        tweet.day, tweet.time, re.sub(","," ", tweet.name), #only if csv file
                        tweet.username, re.sub(","," ", tweet.text), #only if csv file
                        tweet.timestamp, tweet.likes, tweet.replies, tweet.retweets, tweet.hashtags,
                        tweet.mentions, tweet.lang, tweet.urls, tweet.permalink, tweet.id,
                        tweet.author_id, tweet.user_url, tweet.geo))

    def download_to_db(self):
        # TODO: add option to append to existing table (in case of big data)
        file = "data/" + self.output_file + ".sqlite"
        conn = sqlite3.connect(file)
        cur = conn.cursor()
        cur.executescript('''
        DROP TABLE IF EXISTS Tweets;
        CREATE TABLE Tweets (
            id  INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
            username TEXT NOT NULL, name TEXT, text TEXT, timestamp TEXT, day TEXT, time TEXT,
            geo TEXT, hashtags TEXT, likes INTEGER, replies INTEGER, retweets INTEGER,
            mentions TEXT, language TEXT, permalink TEXT NOT NULL, urls TEXT,
            post_id INTEGER UNIQUE, author_id INTEGER, user_url TEXT NOT NULL
        );''')
        for tweet in self.results:
            cur.execute('''INSERT INTO Tweets (username, name, text, timestamp, day, time, geo, hashtags,
                        likes, replies, retweets, mentions, language, permalink,
                        urls, post_id, author_id, user_url)
                    VALUES ( ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ? )''',
                    (tweet.username, tweet.name, tweet.text, tweet.timestamp, tweet.day, tweet.time,
                     tweet.geo, tweet.hashtags, tweet.likes, tweet.replies,
                     tweet.retweets, tweet.mentions, tweet.lang, tweet.permalink, tweet.urls,
                     tweet.id, tweet.author_id, tweet.user_url) )
            conn.commit()

def arg_builder(search=None, since=None, until=None, who=None, tweets=100,
                db=False, geo=False, lang=None, o="tweets_output"):
    base_url = "https://twitter.com/i/search/timeline?f=tweets&q=%s&src=typd&max_position=%s"
    url_data = ''
    if who != None:
        url_data += ' from:' + who
    if since != None:
        since = since.replace('/','-')
        url_data += ' since:' + since
    if until != None:
        until = until.replace('/','-')
        url_data += ' until:' + until
    if search != None:
        url_data += ' ' + search
    if tweets == -1:
        tweets = 10**6 # arbitrary value so this doesn't run for eternity
    return TweetHandler(base_url, url_data, tweets, db, geo, lang, o)

if __name__ == '__main__':
    start = time.time()
    manager = fire.Fire(arg_builder)
    
    # each pass loads a page (20 tweets)
    while manager.under_limit: 
        manager.update_url()
        
        try:
            conn = urllib.request.build_opener()
            user_agent = "Mozilla/5.0 (Windows NT 6.1; Win64; x64)"
#            headers = [('User-Agent', user_agent)]
            headers = [
			         ('Host', "twitter.com"),
			         ('User-Agent', "Mozilla/5.0 (Windows NT 6.1; Win64; x64)"),
			         ('Accept', "application/json, text/javascript, */*; q=0.01"),
			         ('Accept-Language', "de,en-US;q=0.7,en;q=0.3"),
			         ('X-Requested-With', "XMLHttpRequest"),
			         ('Referer', manager.url),
			         ('Connection', "keep-alive")
		               ]
            conn.addheaders = headers
            response = conn.open(manager.url).read()
            data = json.loads(response.decode())
            manager.min_pos = data["min_position"]
        except:
            print("Unknown error. Retrying...")

        try:
            tweets = PyQuery(data["items_html"])("div.js-stream-tweet")
        except:
            print("No more tweets left with that search criteria.")
            break
        manager.gather_tweet_info(tweets)
        manager.under_limit = manager.gather_tweet_info(tweets)

    if manager.to_db:
        manager.download_to_db()
        print('Done. Extracted {} tweets into file "data\\{}.sqlite"'.format(len(manager.results), manager.output_file))
    else:
        manager.download_to_file()
        print('Done. Extracted {} tweets into file "data\\{}.csv"'.format(len(manager.results), manager.output_file))
    print("Time: {0:.2f} seconds".format(time.time() - start))
