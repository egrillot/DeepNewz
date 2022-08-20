import tweepy
import string
import re
import datetime
import pytz
import logging as lg
import twint

from time import time
from tzwhere import tzwhere
from typing import List, Tuple, Dict
from transformers import pipeline, MarianTokenizer, AutoModelForSeq2SeqLM, AutoTokenizer
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
    url = db.Column(db.String(4000))

    def __init__(self, hashtag: str, summary: str, summary_preprocessed: str, date: str, sentiment: str, country: str, url: str) -> None:
        self.hashtag = hashtag
        self.summary = summary
        self.summary_preprocessed = summary_preprocessed
        self.date = date
        self.sentiment = sentiment
        self.country = country
        self.url = url

def init_db(app):
    db.init_app(app)
    db.drop_all()
    db.create_all()
    lg.warning('Database initialized')

ACCESS_TOKEN = '1554762533256527872-KYTjj68TGD7AATT81o3qQRN6wF2nt0'
ACCESS_SECRET = 'hekIoP51HHqdVH5D4wMZupQVJpWZZjXzx2saFd0s5pzAM'
CONSUMER_KEY = 'zataAuwEkWQEQBH9khGE4CWhQ'
CONSUMER_SECRET = 'xFzUMtNh169fhKjPFfr0vDULQoLsXEkcGoivwZf5HFwEHXQOma'

auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
auth.set_access_token(ACCESS_TOKEN, ACCESS_SECRET)
api = tweepy.API(auth)

countries = ['France', 'Japan', 'UK', 'USA']
coordinates = {
    'France': {
        'Paris': {
            'lat': 48.856613,
            'lon': 2.352222
        },
        'Marseille': {
            'lat': 43.296482,
            'lon': 5.369780
        },
        'Lille': {
            'lat': 50.629250,
            'lon': 3.057256
        },
        'Bordeaux': {
            'lat': 44.837788,
            'lon': -0.579180
        },
        'Lyon': {
            'lat': 45.764042,
            'lon': 4.835659
        }
    },
    'Japan': {
        'Sapporo': {
            'lat': 43.066666,
            'lon': 141.350006
        },
        'Tokyo': {
            'lat': 35.652832,
            'lon': 139.839478
        },
        'Nagoya': {
            'lat': 35.18147,
            'lon': 136.90641
        },
        'Hiroshima': {
            'lat': 34.383331,
            'lon': 132.449997
        },
        'Fukuoka ': {
            'lat': 33.590355,
            'lon': 130.401716
        }
    },
    'UK': {
        'London': {
            'lat': 51.509865,
            'lon': -0.118092
        },
        'Birmingham': {
            'lat': 52.489471,
            'lon': -1.898575
        },
        'Manchester': {
            'lat': 53.48095,
            'lon': -2.23743
        },
        'Glasgow': {
            'lat': 55.860916,
            'lon': -4.251433
        },
        'Belfast': {
            'lat': 54.597285,
            'lon': -5.93012
        }
    },
    'USA': {
        'Washington': {
            'lat': 47.751076,
            'lon': -120.740135
        },
        'New York': {
            'lat': 40.730610,
            'lon': -73.935242
        },
        'Chicago': {
            'lat': 41.881832,
            'lon': -87.623177
        },
        'Los Angeles': {
            'lat': 34.052235,
            'lon': -118.243683
        },
        'Dallas': {
            'lat': 32.779167,
            'lon': -96.808891
        },
        'Las Vegas': {
            'lat': 36.114704,
            'lon': -115.201462
        }
    }
}

data = {'b': 'France', 'a': 'France', 'pos': '1', 'neu': '1', 'neg': '0', 'cache': [], 'feed_message': "Votre fil d'actualité", "init": True}
mname_fr_en = 'Helsinki-NLP/opus-mt-fr-en'
mname_ja_en = 'Helsinki-NLP/opus-mt-ja-en'

tokenizer_fr_en = MarianTokenizer.from_pretrained(mname_fr_en)
model_fr_en = AutoModelForSeq2SeqLM.from_pretrained(mname_fr_en)

tokenizer_ja_en = MarianTokenizer.from_pretrained(mname_ja_en)
model_ja_en = AutoModelForSeq2SeqLM.from_pretrained(mname_ja_en)

global current_hashtag
current_hashtag = {datetime.datetime.today().weekday(): []}

def reset_daily_hashtag(current_hashtag):

    if datetime.datetime.today().weekday() != list(current_hashtag.keys())[0]:

        current_hashtag = {datetime.datetime.today().weekday(): []}

def translate(text, lang):

    if lang == 'fr':

        tokenizer = tokenizer_fr_en
        model = model_fr_en
    
    elif lang == 'ja':

        tokenizer = tokenizer_ja_en
        model = model_ja_en
    
    elif lang == 'en':

        return text
    
    else:

        return

    input_ids = tokenizer.encode(text, return_tensors="pt")
    outputs = model.generate(input_ids)
    decoded = tokenizer.decode(outputs[0], skip_special_tokens=True)

    return decoded

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

sum_tokenizer = AutoTokenizer.from_pretrained("facebook/bart-large-cnn")
sum_model = AutoModelForSeq2SeqLM.from_pretrained("facebook/bart-large-cnn")

def summarize(text):

    inputs = sum_tokenizer([text], max_length=1024, return_tensors='pt', truncation=True)
    # Generate Summary
    summary_ids = sum_model.generate(inputs['input_ids'], max_length=100)
    return [sum_tokenizer.decode(g, skip_special_tokens=True, clean_up_tokenization_spaces=False) for g in summary_ids][0]

sentiment_model = pipeline(model="finiteautomata/bertweet-base-sentiment-analysis")

tzwhere_ = tzwhere.tzwhere()

def text_preprocessing(text: str):

    text_punctuation = "".join([i for i in text if i not in string.punctuation]) # remove punctuation
    text_lower = text_punctuation.lower() # lower
    text_tokenized = text_lower.split(" ") # tokenization

    return text_tokenized

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

def get_trend(trend):

    return trend if trend[0] == "#" else "#" + trend 

def get_tweets(trend): #80s

    #configuration
    config = twint.Config()
    config.Search = get_trend(trend)
    config.Limit = 3200
    config.Since = (datetime.date.today() - datetime.timedelta(hours=3)).strftime('%Y-%m-%d %H:%M:%S')
    config.Store_object = True
    config.Hide_output = True
    #running search
    twint.run.Search(config)

    tweets_as_objects = twint.output.tweets_list

    return [(t.tweet, t.lang) for t in tweets_as_objects][-25:] 

def harvest(db):

    print('Harvesting...')

    start_time=time()

    reset_daily_hashtag(current_hashtag)

    for country in countries:

        for city, coordinate in coordinates[country].items():
            
            lat = coordinate['lat']
            lon = coordinate['lon']
            available_loc = api.closest_trends(lat, lon)
            trends = api.get_place_trends(available_loc[0]['woeid'])
            print(city, trends[0]['trends'])
            for trend in trends[0]['trends']:  
                print(trend, current_hashtag)
                hashtag = trend['name']
                url = trend['url']

                if hashtag not in list(current_hashtag.values()):

                    current_hashtag[list(current_hashtag.keys())[0]].append(hashtag)
                    text_lang = get_tweets(hashtag)
                    print('yo')
                    if len(text_lang) != 0:

                        doc = ''  
                        for t in text_lang:

                            tx = emoji_pattern.sub(r'', t[0])
                            tx_translated = translate(tx, t[1])
                            doc += tx_translated if tx_translated is not None else ''
                        
                        raw_preprocessing = text_preprocessing(doc)
                        q = db.session.query(Content.id).filter(Content.hashtag==hashtag)

                        if db.session.query(q.exists()).scalar():

                            content: Content = db.session.query(Content).filter(Content.hashtag==hashtag).order_by(Content.id.desc()).first()
                            
                            summary_preprocessed = set(content.summary_preprocessed.split(" "))
                            tweet_preprocessed_set = set(raw_preprocessing)

                            if len(summary_preprocessed.intersection(tweet_preprocessed_set)) < 10:

                                summary = summarize(doc)
                                sentiment = sentiment_model(summary)[0]['label']

                                timezone_str = tzwhere_.tzNameAt(lat, lon)

                                if timezone_str is None:
                                    timezone_str = 'UTC'
                                    city = 'London'

                                tz = pytz.timezone(timezone_str)

                                date = f" {datetime.datetime.now(tz).strftime('%H:%M:%S, %Y/%m/%d')} in ({city})"
                                db.session.add(Content(hashtag, summary, " ".join(raw_preprocessing), date, sentiment, country, url))
                                db.session.commit()
                        
                        else:

                            summary = summarize(doc)
                            sentiment = sentiment_model(summary)[0]['label']

                            timezone_str = tzwhere_.tzNameAt(lat, lon)

                            if timezone_str is None:
                                timezone_str = 'UTC'
                                city = 'London'

                            tz = pytz.timezone(timezone_str)

                            date = f" {datetime.datetime.now(tz).strftime('%H:%M:%S, %Y/%m/%d')} in ({city})"
                            db.session.add(Content(hashtag, summary, " ".join(raw_preprocessing), date, sentiment, country, url))
                            db.session.commit()

    print('Harvesting done.')
    print(time()-start_time)

scheduler = BackgroundScheduler()
job = scheduler.add_job(func=harvest, trigger='interval', args=(db,), minutes=15, misfire_grace_time=1)
scheduler.start()

def title(hashtag: str):

    if hashtag[0] == '#':

        hashtag = hashtag[1:]
    
    return hashtag[0].upper() + hashtag[1:]

def update_feed(db, data):

    country = data['a']
    lat = list(coordinates[country].values())[0]['lat']
    lon = list(coordinates[country].values())[0]['lon']
    contents: List[Content] = []
    d = datetime.datetime.now(pytz.timezone(tzwhere_.tzNameAt(lat, lon))).strftime('%Y/%m/%d')
    
    if data['pos'] == '1':

        contents += db.session.query(Content).filter(and_(Content.country.like(country), Content.sentiment.like('POS'))).order_by(Content.id.desc()).all()

    if data['neu'] == '1':

        contents += db.session.query(Content).filter(and_(Content.country.like(country), Content.sentiment.like('NEU'))).order_by(Content.id.desc()).all()

    if data['neg'] == '1':

        contents += db.session.query(Content).filter(and_(Content.country.like(country), Content.sentiment.like('NEG'))).order_by(Content.id.desc()).all()

    contents = [(c.id, c.summary, c.sentiment, c.date, c.hashtag, c.url) for c in contents if d in c.date]
    contents = sorted(contents, key=lambda x: (-x[0], x[1], x[2], x[3], x[4], x[5]))
    contents: List[str] = [(i+1, c[1], c[2], c[3], title(c[4]), c[5]) for i, c in enumerate(contents)]

    return contents

@app.route('/')
@app.route('/index')
def index():

    data['init'] = True
    data['cache'] = update_feed(db ,data)

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

    if data['a'] == 'UK' or data['a'] == 'USA':
        data['feed_message'] = "Your news feed"
    if data['a'] == 'France':
        data['feed_message'] = "Votre fil d'actualité"
    if data['a'] == 'Japan':
        data['feed_message'] = "あなたのニュースフィード"

    data['cache'] = update_feed(db ,data)
    
    return jsonify(data), 200

@app.route('/load_feed', methods=['GET'])
def load_feed():

    data['init'] = False
    data['cache'] = update_feed(db ,data)

    return jsonify(data), 200

