import tweepy
import pandas as pd
import string
import re
import nltk
import datetime
import pytz
import logging as lg

from time import time, sleep
from tzwhere import tzwhere
from nltk.stem import WordNetLemmatizer, SnowballStemmer
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from typing import List, Tuple, Dict
from countryinfo import CountryInfo
from translate import Translator
from transformers import pipeline
from flask import Flask, render_template, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import and_
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)
app.config.from_object('config')

db = SQLAlchemy(app)

class Content(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    hashtag = db.Column(db.String(200))
    summary = db.Column(db.String(4000))
    summary_preprocessed = db.Column(db.String(4000))
    date = db.Column(db.String(100))
    sentiment = db.Column(db.String(3))
    country = db.Column(db.String(200))

    def __init__(self, hashtag: str, summary: str, summary_preprocessed: str, date: str, sentiment: str, country: str) -> None:
        self.hashtag = hashtag
        self.summary = summary
        self.summary_preprocessed = summary_preprocessed
        self.date = date
        self.sentiment = sentiment
        self.country = country

def init_db():
    db.drop_all()
    db.create_all()
    lg.warning('Database initialized')

nltk.download('stopwords')
nltk.download('wordnet')
nltk.download('omw-1.4')

stopwords = stopwords.words('english')
porter_stemmer = SnowballStemmer(language='english')
wordnet_lemmatizer = WordNetLemmatizer()

ACCESS_TOKEN = '1554762533256527872-KYTjj68TGD7AATT81o3qQRN6wF2nt0'
ACCESS_SECRET = 'hekIoP51HHqdVH5D4wMZupQVJpWZZjXzx2saFd0s5pzAM'
CONSUMER_KEY = 'zataAuwEkWQEQBH9khGE4CWhQ'
CONSUMER_SECRET = 'xFzUMtNh169fhKjPFfr0vDULQoLsXEkcGoivwZf5HFwEHXQOma'
count_request = 1

auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
auth.set_access_token(ACCESS_TOKEN, ACCESS_SECRET)
api = tweepy.API(auth)

languages = ['af', 'sq', 'am', 'ar', 'hy', 'az', 'eu', 'be', 'bn', 'bs', 'bg', 'ca', 'ceb', 'ny', 'zh-cn', 'zh-tw', 'co', 'hr', 'cs', 'da', 'nl', 'en', 'eo', 'et', 'tl', 'fi', 'fr', 'fy', 'gl', 'ka', 'de', 'el', 'gu', 'ht', 'ha', 'haw', 'iw', 'he', 'hi', 'hmn', 'hu', 'is', 'ig', 'id', 'ga', 'it', 'ja', 'jw', 'kn', 'kk', 'km', 'ko', 'ku', 'ky', 'lo', 'la', 'lv', 'lt', 'lb', 'mk', 'mg', 'ms', 'ml', 'mt', 'mi', 'mr', 'mn', 'my', 'ne', 'no', 'or', 'ps', 'fa', 'pl', 'pt', 'pa', 'ro', 'ru', 'sm', 'gd', 'sr', 'st', 'sn', 'sd', 'si', 'sk', 'sl', 'so', 'es', 'su', 'sw', 'sv', 'tg', 'ta', 'tt', 'te', 'th', 'tr', 'tk', 'uk', 'ur', 'ug', 'uz', 'vi', 'cy', 'xh', 'yi', 'yo', 'zu']
countries = ['France', 'Germany', 'Italy', 'Japan', 'Spain', 'UK', 'USA']
data = {'b': 'France', 'a': 'France', 'pos': '1', 'neu': '1', 'neg': '0', 'cache': [], 'feed_message': "Votre fil d'actualité", "init": True}

emoji_pattern = re.compile("["
        u"\U0001F600-\U0001F64F"  # emoticons
        u"\U0001F300-\U0001F5FF"  # symbols & pictographs
        u"\U0001F680-\U0001F6FF"  # transport & map symbols
        u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
        u"\U00002500-\U00002BEF"  # chinese char
        u"\U00002702-\U000027B0"
        u"\U00002702-\U000027B0"
        u"\U000024C2-\U0001F251"
        u"\U0001f926-\U0001f937"
        u"\U00010000-\U0010ffff"
        u"\u2640-\u2642" 
        u"\u2600-\u2B55"
        u"\u200d"
        u"\u23cf"
        u"\u23e9"
        u"\u231a"
        u"\ufe0f"  # dingbats
        u"\u3030"
                      "]+", re.UNICODE)

summary_model = pipeline("summarization", model="facebook/bart-large-cnn")

sentiment_model = pipeline(model="finiteautomata/bertweet-base-sentiment-analysis")

translator_en = Translator(to_lang='en', from_lang='autodetect')
translator_fr = Translator(to_lang='fr', from_lang='autodetect')
translator_jp = Translator(to_lang='jp', from_lang='autodetect')
translator_de = Translator(to_lang='de', from_lang='autodetect')
translator_sp = Translator(to_lang='sp', from_lang='autodetect')

tzwhere_ = tzwhere.tzwhere()

class Info:

    def __init__(self, country: str) -> None:
        country = CountryInfo(country)
        language = country.languages()[0]
        capital = country.capital()
        location = country.capital_latlng()

        self.lat = location[0]
        self.lon = location[1]
        self.language = language if language in languages else 'en'
        self.capital = capital

def text_preprocessing(text: str):

    text_punctuation = "".join([i for i in text if i not in string.punctuation]) # remove punctuation
    text_lower = text_punctuation.lower() # lower
    text_tokenized = word_tokenize(text_lower) # tokenization
    text_stopwords = [i for i in text_tokenized if i not in stopwords] # stop words
    text_lemmatizer = [wordnet_lemmatizer.lemmatize(word) for word in text_stopwords] # lemmatizer

    return text_lemmatizer

def full_text_tweet(tweet):

    if tweet.truncated:

        return tweet.extended_tweet['full_text']  
    
    return tweet.text

def select_cache(cache: List[Tuple[str, str, str]], data: Dict[str, str]) -> List[Tuple[str, str, str]]:

    new_cache = []

    for i, text in enumerate(cache):

        add = False

        if text[1] == 'POS':

            if data['pos'] == '1':

                add = True

        if text[1] == 'NEU':

            if data['neu'] == '1':

                add = True

        if text[1] == 'NEG':

            if data['neg'] == '1':

                add = True
        
        if add:

            t = (i, text[0], text[1], text[2])
            new_cache.append(t)
        
    return new_cache

def reset_for_request(count_request, start_time):

    if count_request == 30:
        
        t = start_time - time()
        count_request = 1

        if t < 61:
            sleep(61 - t)

        start_time = time()

    else:

        count_request += 1

def harvest(db):

    print('Harvesting...')

    sleep(61)

    t=time()

    for country in countries:

        info = Info(country)
        available_loc = api.closest_trends(info.lat, info.lon)
        reset_for_request(count_request, start_time)
        trends = api.get_place_trends(available_loc[0]['woeid'])
        reset_for_request(count_request, start_time)
        hashtag_kept = []
        doc_kept = []
        doc_preprocessed_kept = []

        for trend in trends[0]['trends']:  

            hashtag = trend['name']

            text = [full_text_tweet(t) for t in api.search_30_day(
                        label='prod',
                        query=hashtag,
                        fromDate=(datetime.date.today() - datetime.timedelta(days=1)).strftime('%Y%m%d%H%M')
                    )]
            reset_for_request(count_request, start_time)

            doc = ''  
            for t in text[-25:]:

                tx = emoji_pattern.sub(r'', t)
                tx_translated = translator_en.translate(tx)
                doc += tx_translated
            
            raw_preprocessing = text_preprocessing(doc)
            q = db.session.query(Content.id).filter(Content.hashtag==hashtag)

            if db.session.query(q.exists()).scalar():

                content: Content = db.session.query(Content).filter(Content.hashtag==hashtag).order_by(Content.id.desc()).first()
                
                summary_preprocessed = set(content.summary_preprocessed.split(" "))
                tweet_preprocessed_set = set(raw_preprocessing)

                if len(summary_preprocessed.intersection(tweet_preprocessed_set)) < 10:

                    hashtag_kept.append(hashtag)
                    doc_kept.append(doc)
                    doc_preprocessed_kept.append(" ".join(raw_preprocessing))
            
            else:

                hashtag_kept.append(hashtag)
                doc_kept.append(doc)
                doc_preprocessed_kept.append(" ".join(raw_preprocessing))
        
        df_filter = pd.DataFrame(zip(hashtag_kept, doc_kept, doc_preprocessed_kept), columns=['hashtag', 'text', 'text preprocessed'])

        df_filter['summary'] = df_filter['text'].map(lambda x: summary_model(x, max_length=100)[0]['summary_text'])
        df_filter['sentiment'] = df_filter['summary'].map(lambda x: sentiment_model(x)[0]['label'])

        timezone_str = tzwhere_.tzNameAt(info.lat, info.lon)
        capital = info.capital

        if timezone_str is None:
            timezone_str = 'UTC'
            capital = 'London'

        tz = pytz.timezone(timezone_str)

        date = f" {datetime.datetime.now(tz).strftime('%H:%M:%S, %Y/%m/%d')} in ({capital})"

        for hashtag, summary, text_preprocessed, sentiment in zip(df_filter['hashtag'], df_filter['summary'], df_filter['text preprocessed'], df_filter['sentiment']):

            print(hashtag, summary, text_preprocessed, sentiment)
            db.session.add(Content(hashtag, summary, text_preprocessed, date, sentiment, country))
        
        db.session.commit()
    print('Harvesting done.')
    print(time()-t)

scheduler = BackgroundScheduler()
job = scheduler.add_job(func=harvest, trigger='interval', args=(db,), minutes=40, start_date=('2022-08-15 19:00:00'))
start_time = time()
scheduler.start()

def title(hashtag: str):

    if hashtag[0] == '#':

        hashtag = hashtag[1:]
    
    return hashtag[0].upper() + hashtag[1:]

def update_feed(db, data):

    country = data['a']
    contents: List[Content] = []

    if data['pos'] == '1':

        contents += db.session.query(Content).filter(and_(Content.country.like(country), Content.sentiment.like('POS'))).order_by(Content.id.desc()).all()

    if data['neu'] == '1':

        contents += db.session.query(Content).filter(and_(Content.country.like(country), Content.sentiment.like('NEU'))).order_by(Content.id.desc()).all()

    if data['neg'] == '1':

        contents += db.session.query(Content).filter(and_(Content.country.like(country), Content.sentiment.like('NEG'))).order_by(Content.id.desc()).all()

    contents = [(c.id, c.summary, c.sentiment, c.date, c.hashtag) for c in contents]
    contents = sorted(contents, key=lambda x: (-x[0], x[1], x[2], x[3], x[4]))
    contents: List[str] = [(i+1, c[1], c[2], c[3], title(c[4])) for i, c in enumerate(contents)]

    return contents if len(contents) < 100 else contents[:100]

@app.route('/')
@app.route('/index')
def index():

    data['init'] = True
    data['cache'] = update_feed(db, data)

    return render_template(
        'index.html',
        countries=countries,
        data=data
    )

@app.route('/change_params', methods=['GET'])
def change_params():

    data['init'] = False

    sentiment = request.args.get('sentiment', 'none')
    new_country = request.args.get('country', 'none')

    if sentiment == 'positive':

        data['pos'] = '0' if data['pos'] == '1' else '1'

    if sentiment == 'neutral':

        data['neu'] = '0' if data['neu'] == '1' else '1'

    if sentiment == 'negative':

        data['neg'] = '0' if data['neg'] == '1' else '1'
    
    if new_country != 'none':

        data['b'] = data['a']
        data['a'] = request.args.get('country')

    info = Info(data['a'])
    if info.language == 'en':
        data['feed_message'] = translator_en.translate("Your news feed")
    if info.language == 'fr':
        data['feed_message'] = translator_fr.translate("Your news feed")
    if info.language == 'de':
        data['feed_message'] = translator_de.translate("Your news feed")
    if info.language == 'sp':
        data['feed_message'] = translator_sp.translate("Your news feed")
    if info.language == 'jp':
        data['feed_message'] = translator_jp.translate("Your news feed")

    data['cache'] = update_feed(db, data)
    
    return jsonify(data), 200

@app.route('/load_feed', methods=['GET'])
def load_feed():

    data['init'] = False
    data['cache'] = update_feed(db, data)

    return jsonify(data), 200

