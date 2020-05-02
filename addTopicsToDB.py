import pymongo
import random
import numpy as np
import uuid
import pandas as pd

from pymongo import MongoClient
client = MongoClient()  

client = MongoClient("mongodb+srv://shubhamperiwal98:Shubham123@cluster0-rh4gz.gcp.mongodb.net/test")
db = client['CardGamesDB']
db_test = client['TestCardGamesDB']
topic_db = db['Topic']
topic_db_test = db_test['Topic']

df = pd.read_csv('Chameleon Topics.csv', index_col=0)

for index, row in df.iterrows():

    topic_db.insert_one({
        'topicId': uuid.uuid4().hex[:4],
        'topic': index,
        'words': list(row.values)
    })

    topic_db_test.insert_one({
        'topicId': uuid.uuid4().hex[:4],
        'topic': index,
        'words': list(row.values)
    })