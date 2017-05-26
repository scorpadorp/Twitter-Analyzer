import re
import pandas as pd
pd.options.mode.chained_assignment = None
import numpy as np
import pickle
import string
import warnings
warnings.filterwarnings(action='ignore', category=UserWarning, module='gensim')
import gensim
from tqdm import tqdm
from nltk.tokenize import TweetTokenizer
from gensim.models.word2vec import Word2Vec
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import scale
from keras.models import Sequential
from keras.layers import Dense, Activation

def load_data():
    """
    reads both given training and testing files and pickles the dataframes
    """
    df_train = pd.read_csv('data/training.1600000.processed.noemoticon.csv', encoding = "ISO-8859-1", header=None)
    df_test = pd.read_csv('data/testdata.manual.2009.06.14.csv', encoding = "ISO-8859-1", header=None)
    
    header = ['Sentiment', 'ID', 'Date', 'Query', 'Sser', 'Text']    
    df_train.columns = header
    df_test.columns  = header
    
    df_train['Sentiment'] = df_train['Sentiment'].map({4:1, 0:0})
    df_test['Sentiment'] = df_test['Sentiment'].map({4:1, 0:0, 2:2})
    df_test[df_test != 2]
    
    # shuffle rows for better mixed distribution
    df_train = df_train.sample(frac=1).reset_index(drop=True)
    df_test  = df_test.sample(frac=1).reset_index(drop=True)
    
    df_train.drop(['ID','Date','Query','User'], axis=1, inplace=True)
    df_test.drop(['ID','Date','Query','User'], axis=1, inplace=True)
    
    df_train.to_pickle('data/df_training.pkl')
    df_test.to_pickle('data/df_test.pkl')
    print("Finished loading and pickling data")


def labelize_tweets(tweets, label_type):
    """
    labels each tweet as TRAIN or TEST
    """
    LabeledSentence = gensim.models.doc2vec.LabeledSentence
    labelized = []
    for i, v in tqdm(enumerate(tweets)):
        label = "{}_{}".format(label_type, i)
        labelized.append(LabeledSentence(v, [label]))
    return labelized

def postprocess(data):
    """
    Adds tokenized column to the given dataframe
    """
    tqdm.pandas(desc="progress-bar")
    data = data.head(len(data))
    data['tokens'] = data['Text'].progress_map(tokenize)
    data.reset_index(inplace=True)
    data.drop('index', inplace=True, axis=1)
    return data

def build_word_vector(tokens, size, tweet_w2v, tfidf):
    """
    creates an averaged tweet vector given a list of tweet tokens
    """
    vec = np.zeros(size).reshape((1, size))
    count = 0
    for word in tokens:
        try:
            vec += tweet_w2v[word].reshape((1, size)) * tfidf[word]
            count += 1.
        except KeyError: # handling the case where the token is not in corpus
            continue
    if count != 0:
        vec /= count
    return vec

def is_ascii(text):
    """ 
    returns a boolean to see if the word contains all ascii characters
    """
    return all(ord(char) < 128 for char in text)

def tokenize(tweet, n_gram=2):
    """
    preprocesses tweet using an n-gram analysis and returns a list of the tokenized words
    """
    tokenizer = TweetTokenizer()
    # get rid of links
    tweet = re.sub("(http|pic.twitter.com|instagram.com)\S*", '', tweet.lower())
    # get rid of #, but keep word
    tweet = re.sub("#", '', tweet)
    # get rid of words with mentions
    tweet = re.sub("@\S*", '', tweet)
    # create spaces after punctuation so words don't get stuck together
    tweet = tweet.replace('.','. ').replace('?','? ').replace('!','! ').replace('-','- ')
    # get rid of punctuation
    tweet = "".join(c for c in tweet if c not in string.punctuation)
    # get rid of words that only contain numbers
    tweet = re.sub("\s[0-9]+\s", " ", tweet) 
    # get rid of words containing non-ascii values
    L = tweet.split()
    for word in L:
        if not is_ascii(word):
            L.remove(word)
    tweet = ' '.join(L)
    
    tokens = tokenizer.tokenize(tweet)
    return tokens + ['-'.join(tokens[i:i+n_gram]) for i in range(len(tokens)-n_gram+1)]

def gen_nn(input_dim=200, width=32, depth=2):
    model = Sequential()
    model.add(Dense(32, activation='relu', input_dim=200))
    
    # add hidden layers
    for k in range(2, depth):
        model.add(Dense(output_dim=width))
        model.add(Activation('relu'))
    
    model.add(Dense(1, activation='sigmoid'))
    model.compile(optimizer='rmsprop', loss='binary_crossentropy', metrics=['accuracy'])
    return model

def main():
    """
    trains the data using word2vec using a 200-D vector for each word.
    trains model using keras and outputs saved movel in data folder
    """
    print("Training...")
    load_data()
    df = pd.read_pickle('data/df_training.pkl')
    df = postprocess(df)
    df_test = pd.read_pickle('data/df_test.pkl')
    df_test = df_test[df_test.Sentiment !=2] # get rid of neutral sentiment
    df_test = postprocess(df_test)
    
    x_train, y_train = df.tokens, df.Sentiment
    x_test, y_test = df_test.tokens, df_test.Sentiment
    x_train = labelize_tweets(x_train, 'TRAIN')
    x_test = labelize_tweets(x_test, 'TEST')
    
    tweet_w2v = Word2Vec(size=200, min_count=10)
    tweet_w2v.build_vocab([x.words for x in tqdm(x_train)])
    tweet_w2v.train([x.words for x in tqdm(x_train)], epochs=tweet_w2v.iter, 
                                     total_examples=tweet_w2v.corpus_count)
    tweet_w2v.wv.save_word2vec_format('data/tweet_w2v_model')
    
    print('building tf-idf matrix ...')
    vectorizer = TfidfVectorizer(analyzer=lambda x: x, min_df=10)
    vectorizer.fit_transform([x.words for x in x_train])
    tfidf = dict(zip(vectorizer.get_feature_names(), vectorizer.idf_))
    print('vocab size :', len(tfidf))
    pickle.dump(tfidf, open("data/tfidf_data.pkl", "wb"))
    
    train_vecs_w2v = np.concatenate([build_word_vector(z, 200, tweet_w2v, tfidf) for z in tqdm(map(lambda x: x.words, x_train))])
    train_vecs_w2v = scale(train_vecs_w2v)
    test_vecs_w2v = np.concatenate([build_word_vector(z, 200, tweet_w2v, tfidf) for z in tqdm(map(lambda x: x.words, x_test))])
    test_vecs_w2v = scale(test_vecs_w2v)
    
    # binary classifier with 1 hidden layer
    model = gen_nn()
    model.fit(train_vecs_w2v, y_train, epochs=10, batch_size=32, verbose=2)
    
    score = model.evaluate(test_vecs_w2v, y_test, batch_size=128, verbose=2)
    print("\nScore on test-data: {0:.2f}%".format(score[1]*100))
    
    # serialize model to JSON
    model_json = model.to_json()
    with open("data/model.json", "w") as json_file:
        json_file.write(model_json)
    
    # serialize weights to HDF5
    model.save_weights("data/model.h5")
    print("Saved model to disk")


if __name__ == "__main__":
    main()
    