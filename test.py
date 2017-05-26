import csv
import pickle
import train as tr # import sister file
import datetime as dt
import pandas as pd
import numpy as np
from sklearn.preprocessing import scale
import warnings
warnings.filterwarnings(action='ignore', category=UserWarning, module='gensim')
import gensim
from keras.models import model_from_json
import matplotlib.pyplot as plt
from collections import Counter

def get_tweet_data(name="tweets_output"):
    """
    returns a list of tuples, where each tuple contains tweet info
    """
    tweets = []
    file = "data/" + name + ".csv"
    with open(file, "r+", encoding = "ISO-8859-1") as f:
        next(f)
        reader = csv.reader(f)
        for line in reader:
            tweets.append((line[4], line[5]))       
    return tweets

def time_date_hour(timestamp):
    """
    partitions each datetime object to include up to hours
    """
    return dt.datetime.strptime(dt.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H'), "%Y-%m-%d %H")

def get_sentiment(tweets, tfidf, tweet_w2v, loaded_model):
    """
    returns a list of the sentiment value of each tweet in a search
    """
    df = pd.DataFrame({'Text':tweets})
    data = tr.postprocess(df)
    x_test = np.array(data.tokens)
    x_test = tr.labelize_tweets(x_test, 'TEST')
    if len(x_test) == 0:
        return []
    
    test_vecs_w2v = np.concatenate([tr.build_word_vector(z, 200, tweet_w2v, tfidf) for z in map(lambda x: x.words, x_test)])
    test_vecs_w2v = scale(test_vecs_w2v)
    
    # evaluate loaded model on test data
    loaded_model.compile(loss='binary_crossentropy', optimizer='rmsprop', metrics=['accuracy'])
    score = loaded_model.predict(test_vecs_w2v)
    
    sentiment = []
    # round values to contain only binary values (0/1)
    score_rounded = [round(x[0]) for x in score]
    for s in score_rounded:
        sentiment.append(s)
        
    return sentiment

def get_pos_neg(amount, sent):
    """
    returns the amount of positive and negative tweets for each partition (hour)
    """
    idx = 0
    y_neg, y_pos = [], []
    
    # each partition
    for p in amount.values():
        yp, yn = 0, 0
        # sentiment for each partition
        for s in range(idx, idx + p):
            if sent[s] == 1:
                yp += 1
            else:
                yn += 1
        y_pos.append(yp)
        y_neg.append(yn)
        idx += p
    
    return y_pos, y_neg

def main():
    """
    Produces sentiment graphs based on output files
    """
    print("Loading model...")
    # load all data only once
    tfidf = pickle.load(open("data/tfidf_data.pkl", "rb"))
    tweet_w2v = gensim.models.KeyedVectors.load_word2vec_format('data/tweet_w2v_model')
    
    # load json and create model
    json_file = open('data/model.json', 'r')
    loaded_model_json = json_file.read()
    json_file.close()
    loaded_model = model_from_json(loaded_model_json)
    
    # load weights into new model
    loaded_model.load_weights("data/model.h5")
    
    n = int(input("Number of files to analyze: "))
    colors = ['r', 'b', 'g', 'k', 'c', 'm']
    fig = plt.figure()
    plt.style.use('ggplot')
    
    for i in range(n):
        file = input("File #{}: ".format(i + 1))
        tweets_data = get_tweet_data(file)
        tweets = [i[0] for i in tweets_data]
        
        dates = np.array([time_date_hour(int(i[1])) for i in tweets_data])
        dates_ordered = dates[::-1]
        
        amount = Counter(dates_ordered)
        x_partition = [x for x in amount.keys()]
        x_partition.sort()
        y_sent = get_sentiment(tweets, tfidf, tweet_w2v, loaded_model)
        y_pos, y_neg = get_pos_neg(amount, y_sent)
        
        plt.xticks(rotation=45)
        plt.plot(x_partition, y_neg, colors[0], label='negative')
        plt.plot(x_partition, y_pos, colors[1], label='positive')
        print("Done with file #{}.".format(i + 1))
    
    print("Plotting...")
    fig.suptitle('Sentiment Analysis')
    plt.legend(loc = 'best')
    plt.xlabel('Date')
    plt.ylabel('Number of tweets')
    plt.show()
    fig.savefig('data/sentiment_analysis.jpg')

if __name__ == "__main__":
    main()