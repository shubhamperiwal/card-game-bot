import pymongo
from pymongo import MongoClient
import uuid
from credentials import default_level

class DBHelper:
    def __init__(self, dbname, mongodb_uri):
        self.client = MongoClient(mongodb_uri)
        self.dbname = dbname

    def setup(self):
        
        self.db = self.client[self.dbname]
        self.cards_db = self.db['Card']
        self.users_db = self.db['User']
        self.games_db = self.db['Game']
        self.messages_db = self.db['Message']
        self.user_game_db = self.db['UserGame']
        self.topics_db = self.db['Topic']

    def addMessageToDB(self, message_id, text, sender):
        first_name = ""
        username = "" 
        if("first_name" in sender):
            first_name = sender["first_name"]
        if("username" in sender):
            username = sender["username"]
        message = {
            "message_id": message_id,
            "text": text,
            "first_name": first_name,
            "username": username
        }
        self.messages_db.insert_one(message)

    def findUser(self, chatId):
        return self.users_db.find_one({"chatId": chatId})

    
    def createGame(self, gameType, chatId):
        game = {
            "gameId": uuid.uuid4().hex[:4],
            "users": [],
            "messages": [],
            "gameType": gameType,
            "active": True,
            "turns": [],
            "currentTurn": 0,
            "goals": [],
            "currentSet": [],
            "currentRound": 1,
            "started": False,
            "cardsDistributed": [], #BlackJack
            "dealerCards": [],  #BlackJack
            "dealerPoints": 0, #BlackJack
            "level": default_level, #WordJumble
            "currentWord": "", #WordJumble
            "currentTopic": "", #Chameleon
            "cham_player": "" #Chameleon
        }
        game_oid = self.games_db.insert_one(game).inserted_id
        game_id = self.games_db.find_one({"_id": game_oid})["gameId"]
        return game_id

    def getActiveGame(self, userId):
        game = self.games_db.find( { "users": userId, "active" : True } )
        gameId = gameType = cham_player = chosenWord = ""
        users = turns = currentTurn = goals = currentSet = votes = []
        topics = messages = cardsDistributed = dealerCards = clues = []

        currentRound = 1

        for x in game:
            gameId = x["gameId"]
            users = x["users"]
            gameType = x["gameType"]
            turns = x["turns"]
            currentTurn = x["currentTurn"]
            currentRound = x["currentRound"]
            if "goals" in x:
                goals = x["goals"]
            if "currentSet" in x:
                currentSet = x["currentSet"]
            if "topics" in x:
                currentSet = x["topics"]
            if "messages" in x:
                messages = x["messages"]
            if "cardsDistributed" in x:
                cardsDistributed = x["cardsDistributed"]
            if "dealerCards" in x:
                dealerCards = x["dealerCards"]
            if "clues" in x:
                clues = x["clues"]
            if "votes" in x:
                votes = x["votes"]
            if "cham_player" in x:
                cham_player = x["cham_player"]
            if "chosen_word" in x:
                chosen_word = x["chosen_word"]
            

        gameDict = {
            "gameId": gameId,
            "users": users,
            "gameType": gameType,
            "turns": turns,
            "currentTurn": currentTurn,
            "goals": goals,
            "currentSet": currentSet,
            "currentRound": currentRound,
            "topics": topics,
            "cardsDistributed": cardsDistributed,
            "dealerCards": dealerCards,
            "clues": clues,
            "votes": votes,
            "cham_player": cham_player
        }
        return gameDict

    def deactivateOtherGames(self, chatId):
        self.games_db.update_many( filter={ "users": { "$all" : [chatId] } }, update={"$set": {'active': False}})

    def addUserToGame(self, gameId, userId, first_name):
        addUserCommand = { "$push": { "users":  userId} }

        # check if user is already in game
        game = self.games_db.find_one({"gameId": gameId})
        if(game is None):
            return False, "Incorret code"
        users = game["users"]
        if(game["started"]):
            return False, "Game has started already. Cannot join now"
        if(len(users) == 6):
            return False, "There are already 6 users in game. Please create a new game or wait for me to be advance enough to allow deletion of users from game"
        if(userId in users):
            return False, "User is already added to game"
        # Deactivate all other games of that user
        self.deactivateOtherGames(userId)

        self.games_db.update_one(self.games_db.find_one({"gameId": gameId}), addUserCommand)
        return True, first_name+" has joined the game. Waiting for everyone to join..."

    def addUserToDB(self, chatId, sender):
        first_name = ""
        last_name = ""
        username = ""
        if "first_name" in sender:
            first_name = sender["first_name"]
        if "last_name" in sender:
            last_name = sender["last_name"]
        if "username" in sender:
            username = sender["username"]
        

        user = {
            'cards': [],
            'numGames': 0,
            'chatId': chatId,
            'username': username,
            'first_name': first_name,
            'last_name': last_name
        }
        user_id = self.users_db.insert_one(user)
        return user_id

    def getUser(self, userId):
        return self.users_db.find_one({"chatId": userId})

    def updateValues(self, dbName, fieldId, docId, field, value):
        dbToUpdate = self.db[dbName]
        dbToUpdate.update_one(dbToUpdate.find_one({fieldId: docId}), {"$set": {field: value}})

    def findDocument(self, dbName, fieldId, docId):
        dbToFind = self.db[dbName]
        return dbToFind.find_one({fieldId: docId})

    def createUserGame(self, gameId, userId, cardsForUser=[], firstName=""):
        userGame = {
            "userGameId": uuid.uuid4().hex[:4],
            "gameId": gameId,
            "userId": userId,
            "first_name": firstName,
            "cards": cardsForUser,
            "goal": -1,
            "sets": 0,
            "score": 0,
            "points": 0, #blackJack
            "isChameleon": False, #Chameleon
            "clue": "", #Chameleon
            "vote": "", #Chameleon
             
        }

        self.user_game_db.insert_one(userGame)

    def getUserGame(self, gameId, userId):
        return self.user_game_db.find_one({"gameId": gameId, "userId": userId})

    def updateSetsInUserGame(self, gameId, userId):
        userGame = self.getUserGame(gameId, userId)
        userGameId = userGame["userGameId"]
        return self.user_game_db.update({ "userGameId": userGameId },{ "$inc": { "sets": 1}})
    
    def updateScoreInUserGame(self, gameId, userId, points):
        userGame = self.getUserGame(gameId, userId)
        userGameId = userGame["userGameId"]
        return self.user_game_db.update({ "userGameId": userGameId },{ "$inc": { "score": points}})

    def updateCurrentRound(self, gameId):
        return self.games_db.update({ "gameId": gameId },{ "$inc": { "currentRound": 1}})


#------------- Chameleon begins
    def getAllTopics(self):
        all_topic_docs = self.topics_db.find({})
        all_topic_list = []
        for topic in all_topic_docs:
            all_topic_list.append(topic['topic'])

        return all_topic_list
        