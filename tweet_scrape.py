#  -*- coding: utf-8 -*-
import urllib, re
#import fire
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
        self.urls = None
        self.username = None
        self.user_url = None

class TweetManager():
    def __init__(self, max_tweets=100, geo = False, filt=False, lang_filter = 'en'):
        self.results = []
        self.max_tweets = max_tweets
        self.geo_filter = geo
        self.filter = filt
        self.lang_filter = lang_filter
        self.considered = 0
    def gather_tweet_info(self, tweets):
        for tweet_html in tweets:
            self.considered += 1
            tweet_info = PyQuery(tweet_html)
            tweet = Tweet()
            if len(self.results) >= max_tweets:
                return False     
            
            tweet.lang = tweet_info("p.TweetTextSize").attr("lang")
            if self.filter and tweet.lang != self.lang_filter:
                continue
            
            tweet.name = tweet_info("span.FullNameGroup").text()
            if "\u200f" in tweet.name: #check for verified symbol
                pos = tweet.name.find("\u200f")                
                tweet.name = tweet.name[:pos - 1]
            tweet.username = tweet_info("span.username").text()[2:]
            tweet.text = re.sub(r"\s+", " ", tweet_info("p.js-tweet-text").text().replace('# ', '#').replace('@ ', '@'))
            tweet.replies = int(re.findall('[0-9]+', tweet_info("span.ProfileTweet-actionCountForAria")[0].text)[0])
            tweet.retweets = int(re.findall('[0-9]+', tweet_info("span.ProfileTweet-actionCountForAria")[1].text)[0])
            tweet.likes = int(re.findall('[0-9]+', tweet_info("span.ProfileTweet-actionCountForAria")[2].text)[0])
            full_date = int(tweet_info("span.js-short-timestamp").attr("data-time"))
            date = dt.datetime.fromtimestamp(full_date)
            tweet.day = dt.datetime.strftime(date, '%m'+'/'+'%d'+'/'+'%Y')
            tweet.time = dt.datetime.strftime(date, '%H'+':'+'%M'+':'+'%S')
            tweet.id = tweet_info.attr("data-tweet-id")
            tweet.author_id = int(tweet_info("a.js-user-profile-link").attr("data-user-id")) 
            permalink = tweet_info.attr("data-permalink-path")
            tweet.permalink = 'https://twitter.com' + permalink
            tweet.user_url = "https://twitter.com/" + tweet.username
            tweet.mentions = " ".join(re.compile('(@\\w*)').findall(tweet.text))
            tweet.hashtags = " ".join(re.compile('(#\\w*)').findall(tweet.text))
            urls = []
            for link in tweet_info("a"):
                try:
                    urls.append((link.attrib["data-expanded-url"]))
                except KeyError:
                    pass        
            tweet.urls = ",".join(urls)
            
            # check for duplicates
            bypass = False
            for t in self.results:
                if tweet.id == t.id:
                    bypass = True
                    break
            if bypass:
                continue
            # TODO: load GEODATE on google to see if location is real
            # EXPENSIVE OPERATION! if name is already in list (or database), skip
            if self.geo_filter:
                #TODO: check if username already in db
                if True:
                    pass
                else:
                    c = urllib.request.build_opener()
                    c.addheaders = [('User-Agent', 'Mozilla/5.0')]
                    try:
                        r = c.open(tweet.user_url).read()
                        soup = PyQuery(r)
                        tweet.geo = soup("span.ProfileHeaderCard-locationText").text() 
                    except:
                        print("Bad Request")   
            self.results.append(tweet)
            
        return True
    
    def download_to_file(self):
        with open("tweets_output.csv", "w+", encoding = "utf-8") as f:
            f.write("{}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}\n".format(
                    "day",  "time", "name", "username", "text", "likes", "replies",
                    "retweets", "hashtags", "mentions", "language", "urls", 
                    "permalink", "id", "author_id", "user_url", "geo\n"))
            for tweet in self.results:
                f.write("{}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}\n".format(
                        tweet.day, tweet.time, re.sub(","," ", tweet.name), #only if csv file
                        tweet.username, re.sub(","," ", tweet.text), #only if csv file
                        tweet.likes, tweet.replies, tweet.retweets, tweet.hashtags, 
                        tweet.mentions, tweet.lang, tweet.urls, tweet.permalink, tweet.id, 
                        tweet.author_id, tweet.user_url, tweet.geo))
    
    def download_to_db(self):
        # TODO: add option to append to existing table (in case of big data)
        conn = sqlite3.connect('tweets_output.sqlite')
        cur = conn.cursor()
        cur.executescript('''
        DROP TABLE IF EXISTS Tweets;
        CREATE TABLE Tweets (
            id  INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
            username TEXT NOT NULL,
            name TEXT,
            text TEXT,
            day TEXT,
            time TEXT,
            geo TEXT,
            hashtags TEXT,            
            likes INTEGER,
            replies INTEGER,
            retweets INTEGER,
            mentions TEXT,
            language TEXT,
            permalink TEXT NOT NULL,            
            urls TEXT,
            post_id INTEGER,
            author_id INTEGER,
            user_url TEXT NOT NULL
        );''')
        for tweet in self.results:
            cur.execute('''INSERT INTO Tweets (username, name, text, day, time, geo, hashtags,
                        likes, replies, retweets, mentions, language, permalink,
                        urls, post_id, author_id, user_url) 
                    VALUES ( ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ? )''',
                    (tweet.username, tweet.name, tweet.text, tweet.day, tweet.time,
                     tweet.geo, tweet.hashtags, tweet.likes, tweet.replies, 
                     tweet.retweets, tweet.mentions, tweet.lang, tweet.permalink, tweet.urls,
                     tweet.id, tweet.author_id, tweet.user_url) )
            conn.commit()

under_limit = True
max_tweets = 104
to_file = False
user = False
date = True
geo_filter = False
lang_filter = False
min_pos = ''
base_url = "https://twitter.com/i/search/timeline?f=tweets&q=%s&src=typd&max_position=%s"
url_data = ''
lang = 'en'
if user:
    url_data += ' from:' + 'ABC'
if date:
    url_data += ' since:' + '2015-01-01'
    url_data += ' until:' + '2016-01-01'
url_data += ' ' + '#zika'
manager = TweetManager(max_tweets, geo_filter, lang_filter, lang)

if __name__ == '__main__':
    while under_limit: #each pass loads a page (20 tweets)
        url = base_url % (urllib.parse.quote(url_data), min_pos)
        print(url)
        try:
            conn = urllib.request.build_opener()
            conn.addheaders = [('User-Agent', 'Mozilla/5.0')]
            response = conn.open(url).read()
            data = json.loads(response.decode())
            min_pos = data["min_position"]
        except:
            print("Unknown error")
        
        try:
            tweets = PyQuery(data["items_html"])("div.js-stream-tweet")
        except:
            print("Loaded all tweets before limit reached")
            break
        
        manager.gather_tweet_info(tweets)      
        under_limit = manager.gather_tweet_info(tweets)
    
    if to_file:    
        print('Done. Data located in file "tweets_output.csv"')
        manager.download_to_file()
    else:
        print('Done. Data located in file "tweets_output.sqlite"')
        manager.download_to_db()

