import time
from dbhelper import DBHelper
from credentials import bot_token, mongoDB_uri, dbName, test_bot_token, test_dbName
import sys
from chameleon import Chameleon
from sharedFunctions import Shared
from suspense import Suspense
from hearts import Hearts
from blackJack import BlackJack
from wordJumble import WordJumble
from cardTrick import CardTrick

TOKEN = bot_token
DBNAME = dbName
if(len(sys.argv) > 1):
    # running the test bot
    TOKEN = test_bot_token
    DBNAME = test_dbName

mongoDB_uri = mongoDB_uri
URL = "https://api.telegram.org/bot{}/".format(TOKEN)

db = DBHelper(DBNAME, mongoDB_uri)
shared = Shared(URL, db)
suspense = Suspense(shared, db)
hearts = Hearts(shared, db)
blackJack = BlackJack(shared, db)
wordJumble = WordJumble(shared, db)
cardTrick = CardTrick(shared, db)
chameleon = Chameleon(shared, db)

available_games = ["Suspense", "Hearts", "BlackJack", "Chameleon", "CardTrick"]
suits = ['','Diamonds', 'Clubs', 'Hearts', 'Spades']
suitEmojis = ["♦", "♣", "♥", "♠"]
nums = ['', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']

# Add a function that calculates the highest ID of all the updates we receive from getUpdates.
def get_last_update_id(updates):
    update_ids = []
    for update in updates["result"]:
        update_ids.append(int(update["update_id"]))
    return max(update_ids)

def get_last_chat_id_and_text(updates):
    num_updates = len(updates["result"])
    last_update = num_updates - 1
    text = updates["result"][last_update]["message"]["text"]
    chat_id = updates["result"][last_update]["message"]["chat"]["id"]
    return (text, chat_id)

def handle_group(update):
    message = update["message"]
    chatId = update["message"]["chat"]["id"]
    shared.send_message("Please create a game on private chat and send join code to your friends", chatId)

def handle_private(update):
    message = update["message"]
    chatId = update["message"]["chat"]["id"]
    message_id = message["message_id"]
    text = ""
    if "text" in message:
        text = message["text"]
    else:
        shared.send_message("Please send a text - one of the commands", chatId)
        return    
    sender = message["from"]

    # If it's not a card selected from keyboard, then add to DB
    if text.count("|") < 1:
        db.addMessageToDB(message_id, text, sender)

    # If user not in DB, add user
    if(db.findUser(chatId) is None):
        username = ""
        if("username" in sender):
            username = sender["username"]
        # Notify me whenever a new user joins
        shared.send_message("New user: "+username, 144552242)
        db.addUserToDB(chatId, sender)

    gameId = "" 
    if text == "/start":
        shared.send_message("Welcome to Card Games Bot. Please use /create to create a new game.", chatId)

    if "/create" in text:
        if(len(text.split())==1):
            keyboard = shared.build_keyboard(available_games, False)
            shared.send_message("Please select the game you want to create: ", chatId, keyboard)
        else:
            text = text.split()[1]
            
    if text in available_games:
        if(text=="Suspense"):
            gameId = db.createGame(text, chatId)
            shared.send_message("Game of Suspense created. Your friends can send '/join"+gameId+"' to CalCardsBot and join the game", chatId)
            db.addUserToGame(gameId, chatId, sender["first_name"])
        elif(text=="Hearts"):
            gameId = db.createGame(text, chatId)
            shared.send_message("Game of Hearts created. Your friends can send '/join"+gameId+"' to CalCardsBot and join the game", chatId)
            db.addUserToGame(gameId, chatId, sender["first_name"])
        elif(text=="BlackJack"):
            gameId = db.createGame(text, chatId)
            shared.send_message("Game of BlackJack created. Your friends can send '/join"+gameId+"' to CalCardsBot and join the game.", chatId)
            db.addUserToGame(gameId, chatId, sender["first_name"])
        elif(text=="WordJumble"):
            shared.send_message("Word Jumble is under construction. Please try the others", chatId)
            # gameId = db.createGame(text, chatId)
            # shared.send_message("Game of Word Jumble created. Your friends can send '/join"+gameId+"' to the bot and join the game. Or you can start by yourself.", chatId)
            # db.addUserToGame(gameId, chatId, sender["first_name"])
        elif(text=="Chameleon"):
            gameId = db.createGame(text, chatId)
            shared.send_message("Game of Chameleon created. Your friends can send '/join"+gameId+"' to CalCardsBot and join the game.", chatId)
            db.addUserToGame(gameId, chatId, sender["first_name"])
        elif(text=="CardTrick"):
            gameId = db.createGame(text, chatId)
            shared.send_message("Card trick begins.", chatId)
            db.addUserToGame(gameId, chatId, sender["first_name"])
            cardTrick.beginCardTrick(chatId, gameId)

    if "/join" in text:
        gameId = text[5:]
        if(len(gameId) == 4):
            done, mess = db.addUserToGame(gameId, chatId, sender["first_name"])
            if(done):
                users = db.findDocument("Game", "gameId", gameId)["users"]
                keyboard = shared.build_keyboard(["/start_game"], False)
                shared.sendMessageToAllPlayers(users, mess, keyboard)
            else:
                shared.send_message(mess, chatId)
        else:
            shared.send_message("Incorrect game ID attached to /join", chatId)

    elif "/start_game" in text:
        gameDict = db.getActiveGame(chatId)
        gameId = gameDict["gameId"]
        users = gameDict["users"]
        gameType = gameDict["gameType"]
        
        if(gameType == "BlackJack"):
            blackJack.beginBlackJack(chatId, gameId, users)
        elif(gameType == "WordJumble"):
            wordJumble.beginWordJumble(chatId, gameId, users)
        elif(len(users)==1):
            shared.send_message("Let other users join as well. ", chatId)
        else:
            if(gameType == "Suspense"):
                suspense.beginSuspense(chatId, gameId, users)
            elif(gameType == "Hearts"):
                hearts.beginHearts(chatId, gameId, users)
            elif(gameType == "Chameleon"):
                chameleon.selectTopic(chatId, gameId, users)

    elif "/goal" in text:
        if(len(text.split())==1):
            shared.send_message("Please enter your goal", chatId)
        else:
            goal = text.split()[1]
            if(not goal.isdigit()):
                shared.send_message("Please enter only a number as your goal", chatId)
            else:
                goal = int(goal)
                gameDict = db.getActiveGame(chatId)
                gameId = gameDict["gameId"]
                turns = gameDict["turns"]
                currentTurn = gameDict["currentTurn"]
                goals = gameDict["goals"]
                result = suspense.suspenseSetGoal(gameId, chatId, goal, turns, currentTurn, goals)
                shared.send_message(result, chatId)

    elif "/topic" in text:
        if(len(text.split())==1):
            shared.send_message("Please enter your topic", chatId)
        else:
            topic = text[7:]
            gameDict = db.getActiveGame(chatId)
            gameId = gameDict["gameId"]
            users = gameDict["users"]
            chameleon.beginChameleon(chatId, gameId, users, topic)

    elif "/clue" in text:
        if(len(text.split())==1):
            shared.send_message("Please enter your clue", chatId)
        else:
            clue = text[6:]
            gameDict = db.getActiveGame(chatId)
            gameId = gameDict["gameId"]
            users = gameDict["users"]
            clues = gameDict["clues"]
            currentTurn = gameDict["currentTurn"]
            turns = gameDict["turns"]
            chameleon.addClue(chatId, gameId, users, clue, turns, currentTurn, clues)

    elif "/vote" in text:
        if(len(text.split())==1):
            shared.send_message("Please enter the name of the person you want to vote", chatId)
        else:
            vote = text.split()[1]
            gameDict = db.getActiveGame(chatId)
            gameId = gameDict["gameId"]
            users = gameDict["users"]
            votes = gameDict["votes"]
            currentTurn = gameDict["currentTurn"]
            turns = gameDict["turns"]
            cham_player = gameDict["cham_player"]
            chameleon.addVote(chatId, gameId, users, vote, turns, currentTurn, votes, cham_player)

    elif "/help" in text:
        shared.send_message("Please use /create to start a new game and then send the join link to your friends to join", chatId)

    elif "/end" in text:
        gameDict = db.getActiveGame(chatId)
        gameId = gameDict["gameId"]
        turns = gameDict["turns"]
        gameType = gameDict["gameType"]
        if(gameType=="Suspense"):
            suspense.endGameSuspense(gameId, turns)
        elif(gameType=="Hearts"):
            hearts.endGameHearts(gameId, turns)
        elif(gameType=="BlackJack"):
            blackJack.endGameBlackJack(gameId, turns)
        elif(gameType=="Chameleon"):
            chameleon.endGameChameleon(gameId, turns)

    elif "/select" in text:
        gameDict = db.getActiveGame(chatId)
        gameId = gameDict["gameId"]
        chosenWord = text[8:]
        users = gameDict["users"]
        chameleon.chameleonSelectWord(chatId, chosenWord, users, gameId)

    elif "/rules" in text:
        rules = "For rules on how to play the games: contact Mohit Poddar on 65 9867 3855."
        shared.send_message(rules, chatId)

    elif "/show_sets" in text:
        gameDict = db.getActiveGame(chatId)
        gameId = gameDict["gameId"]
        users = gameDict["users"]
        suspense.showSets(gameId, users, chatId)

    elif "/show_scores" in text:
        gameDict = db.getActiveGame(chatId)
        gameId = gameDict["gameId"]
        users = gameDict["users"]
        gameType = gameDict["gameType"]
        shared.showScores(gameId, users, chatId)

    elif "/show_dealer_cards" in text:
        gameDict = db.getActiveGame(chatId)
        gameId = gameDict["gameId"]
        dealerCards = gameDict["dealerCards"]
        blackJack.showDealerCards(dealerCards, chatId)

    elif "/show_all_cards" in text:
        gameDict = db.getActiveGame(chatId)
        gameId = gameDict["gameId"]
        users = gameDict["users"]
        dealerCards = gameDict["dealerCards"]
        blackJack.showAllCards(gameId, users, chatId, dealerCards)

    
    elif "/hit" in text:
        gameDict = db.getActiveGame(chatId)
        blackJack.hitTurn(gameDict, chatId)

    elif "/stand" in text:
        gameDict = db.getActiveGame(chatId)
        gameId = gameDict["gameId"]
        users = gameDict["users"]
        currentTurn = gameDict["currentTurn"]
        dealerCards = gameDict["dealerCards"]
        cardsDistributed = gameDict["cardsDistributed"]
        blackJack.standTurn(gameId, chatId, users, currentTurn, dealerCards, cardsDistributed)

    # just play turn
    elif "/turn" in text:
        gameDict = db.getActiveGame(chatId)
        gameId = gameDict["gameId"]
        userGame = db.getUserGame(gameId, chatId)
        cards = userGame["cards"]
        if(gameType=="BlackJack"):
            items = [['/hit', '/stand'], ['/show_dealer_cards', '/show_scores']]
            keyboard = shared.build_keyboard(items, False) 
            shared.send_message("Please choose your turn", chatId, keyboard)
        else:
            keyboard = shared.build_keyboard(cards)
            shared.send_message("Please select the card to play", chatId, keyboard)

    # Value chosen from keyboard
    if text.count("|") > 1:
        gameDict = db.getActiveGame(chatId)
        gameId = gameDict["gameId"]
        turns = gameDict["turns"]
        currentTurn = gameDict["currentTurn"]
        currentSet = gameDict["currentSet"]
        currentRound = gameDict["currentRound"]
        goals = gameDict["goals"]
        turns = gameDict["turns"]
        gameType = gameDict["gameType"]
        if(gameType=="Suspense"):
            if(len(goals) < len(turns)):
                shared.send_message("Please let everyone set goals before playing your turn", chatId)
                return

            textList = text.split()
            suitNum = suitEmojis.index(textList[1])
            num = nums.index(textList[2])
            cardId = suitNum*13 + num

            userGame = db.getUserGame(gameId, chatId)
            cards = userGame["cards"]
            userGameId = userGame["userGameId"]

            if(shared.isLegalTurn(gameId, chatId, currentSet, cardId, cards)):
                suspense.playTurn(chatId, gameId, cardId, currentSet, userGameId, currentTurn, turns, cards, currentRound)
            else:
                shared.send_message("Playing this card is not allowed. Don't try to cheat", chatId)

        elif(gameType=="Hearts"):
            textList = text.split()
            suitNum = suitEmojis.index(textList[1])
            num = nums.index(textList[2])
            cardId = suitNum*13 + num

            userGame = db.getUserGame(gameId, chatId)
            cards = userGame["cards"]
            userGameId = userGame["userGameId"]

            if(shared.isLegalTurn(gameId, chatId, currentSet, cardId, cards)):
                hearts.playTurn(chatId, gameId, cardId, currentSet, userGameId, currentTurn, turns, cards)
            else:
                shared.send_message("Playing this card is not allowed. Don't try to cheat", chatId)

        elif gameType == "CardTrick":
            textList = text.split()
            suitNum = suitEmojis.index(textList[1])
            num = nums.index(textList[2])
            cardId = suitNum*13 + num
            cardTrick.cardChosen(chatId, cardId)

def handle_updates(updates):
    for update in updates["result"]:
        message = update["message"]
        chatType = message["chat"]["type"]
        if(chatType=="private"):
            handle_private(update)
        elif(chatType=="group"):
            handle_group(update)

def get_updates(offset=None):
    url = URL + "getUpdates?timeout=100"
    if offset:
        url += "&offset={}".format(offset)
    js = shared.get_json_from_url(url)
    return js

def main():

    # Won't setup if db already exists
    db.setup()
    last_update_id = None
    while True:
        updates = get_updates(last_update_id)
        if "result" in updates and len(updates["result"]) > 0:
            last_update_id = get_last_update_id(updates) + 1
            handle_updates(updates)
        time.sleep(0.5)


if __name__ == '__main__':
    main()