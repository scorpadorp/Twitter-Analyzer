# Twitter-Analyzer
Scrapes tweets and downloads them to perform sentiment analysis

## tweet_scrape.py
keyword args:
search="any search criteria"
since="yyyy-mm-dd"
until="yyyy-mm-dd"
who="username"
tweets=number (-1 for all; limit is 1 million)
db=True/False (save to database)
geo=True/False (get location of user; VERY slow)
lang="en" (language code, 2-letters long, to only search for)
o="tweets_output" (name of output file)

You only need search to have a valid query.


## train.py
Trains the data in the data folder. This is not needed to run unless you want modify the parameters. If so, only run once.

## test.py
Requires input of file (from tweet_scrape.py) and returns a graph of the number of pos/neg tweets vs time

Let me know if you want additional features I can add.