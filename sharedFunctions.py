import json
import requests
import urllib
from emoji import emojize
import random

class Shared:

    def __init__(self, URL, db):
        self.URL = URL
        self.db = db

    def get_url(self, url):
        response = requests.get(url)
        content = response.content.decode("utf8")
        return content


    def get_json_from_url(self, url):
        content = self.get_url(url)
        js = json.loads(content)
        return js

    def build_keyboard(self, items, isCards=True):
        if(isCards):
            start = 0
            if(len(items)%2==1):
                keyboard = [[self.convertCardIDtoText(items[0], True)]]
                start = 1
            else:
                keyboard = []
            for i in range(start, len(items)-1, 2):
                row = [self.convertCardIDtoText(items[i], True), self.convertCardIDtoText(items[i+1], True)]
                keyboard.append(row)
        else:
            if(len(items) < 5):
                keyboard = [[item] for item in items]
            else:
                start = 0
                if(len(items)%2==1):
                    keyboard = [[items[0]]]
                    start = 1
                else:
                    keyboard = []
                for i in range(start, len(items)-1, 2):
                    row = [items[i], items[i+1]]
                    keyboard.append(row)
        reply_markup = {"keyboard":keyboard, "one_time_keyboard": True}
        return json.dumps(reply_markup)

    def send_message(self, text, chat_id, reply_markup=None):
        text = urllib.parse.quote_plus(text)
        url = self.URL + "sendMessage?text={}&chat_id={}&parse_mode=Markdown".format(text, chat_id)
        if reply_markup:
            url += "&reply_markup={}".format(reply_markup)
        self.get_url(url)

    def sendMessageToAllPlayers(self, users, message, keyboard=None):
        for user in users:
            self.send_message(message, user, keyboard)

    def convertCardIDtoText(self, cardId, keyboard=False):
        cardId -= 1
        nums = ['', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
        num = nums[cardId%13+1]
        suit = int(cardId/13)+1
        emoji = None
        if(suit==1):
            emoji = emojize(":diamond_suit:", use_aliases=True)
        elif(suit==2):
            emoji = emojize(":club_suit:", use_aliases=True)
        elif(suit==3):
            emoji = emojize(":heart_suit:", use_aliases=True)
        elif(suit==4):
            emoji = emojize(":spade_suit:", use_aliases=True)

        if(not keyboard):
            return emoji+" "+str(num)+" | "
        else:
            return "| "+emoji+" "+str(num)+" | "

    def convertTextToCardId(self, suitNum, num):
        return suitNum*13 + num

    def distributeCards(self, numPeople=6, currentRound=1):
        ys = list(range(1, 53))
        random.shuffle(ys)
        removable_cards = [1, 14, 27, 40]

        # Remove all 2s accordingly
        for i in range(52 % numPeople):
            ys.remove(removable_cards[i])

        ys = ys[:len(ys)-(numPeople*(currentRound-1))]

        size = len(ys) // numPeople
        distributedCards = []
        for i in range(numPeople):
            distributedCards.append(ys[i*size:(i+1)*size])
        return distributedCards

    def decideTurns(self, users):
        random.shuffle(users)
        return users

    def updateCurrentTurn(self, currentTurn, users):
        if(currentTurn < len(users)-1):
            return currentTurn+1
        else:
            return 0
    
    def showScores(self, gameId, users, chatId):
        text = "Scores: "
        for userId in users:
            first_name = self.db.getUser(userId)["first_name"]
            userGame = self.db.getUserGame(gameId, userId)
            score = userGame["score"]
            text += "\n"+first_name+": "+str(score)
        self.send_message(text, chatId)

    def isLegalTurn(self, gameId, chatId, currentSet, cardId, cards):
        if(len(currentSet)==0):
            return True
        firstCard = currentSet[0]
        if(firstCard%13==0):
            firstCard-=1
        lower_suit = 13*int(firstCard/13)+1
        upper_suit = 13*int(firstCard/13)+13
        currentSuit = int(firstCard/13)+1
        
        cardId -= 1 
        playedSuit = int(cardId/13)+1

        if(currentSuit == playedSuit):
            return True
        
        currentSuitCardsInDeck = [i for i in cards if lower_suit <= i <= upper_suit]

        return len(currentSuitCardsInDeck) == 0




