from sharedFunctions import Shared
import random 

class BlackJack:
    def __init__(self, shared, db):
        self.shared = shared
        self.db = db

    def beginBlackJack(self, chatId, gameId, users):
        numUsers = len(users)
        game = self.db.findDocument("Game", "gameId", gameId)
        started = game["started"]
        if started: 
            self.shared.send_message("Game has begun already", chatId)
            return 

        self.shared.send_message("Begin Black Jack", chatId)

        distributedCards = self.shared.distributeCards(numPeople=numUsers)
        turns = self.shared.decideTurns(users)
        self.db.updateValues("Game", "gameId", gameId, "started", True)
        self.db.updateValues("Game", "gameId", gameId, "turns", turns)
        self.db.updateValues("Game", "gameId", gameId, "currentTurn", 0)
        userNames = []
        for user in turns:
            userNames.append(self.db.getUser(user)["first_name"])
    
        message = "The order of turns is: "+(", ".join(userNames))+"\nIt is "+userNames[0]+"'s turn now."
        self.shared.sendMessageToAllPlayers(users, message)

        cardsDistributed = []
        text = ""
        for i in range(numUsers):
            # Cz need to give only 2 per person
            cardsForUser = distributedCards[i][:2]
            cardsDistributed.extend(cardsForUser)
            text+="\n"+userNames[i]+": "
            for cardId in cardsForUser:
                text += self.shared.convertCardIDtoText(cardId)
            self.db.createUserGame(gameId, users[i], cardsForUser)

        dealerCard = self.getAdditionalCard(cardsDistributed)
        cardsDistributed.append(dealerCard)
        text += "\nDealer: "+self.shared.convertCardIDtoText(dealerCard)

        items = ['/hit', '/stand', '/show_dealer_cards', '/show_all_cards']
        keyboard = self.shared.build_keyboard(items, False)
        self.shared.sendMessageToAllPlayers(users, "All cards: "+text, keyboard)

        dealerCards = [dealerCard]
        self.db.updateValues("Game", "gameId", gameId, "cardsDistributed", cardsDistributed)
        self.db.updateValues("Game", "gameId", gameId, "dealerCards", dealerCards)
    
    def getAdditionalCard(self, cardsDistributed):
        all_cards = list(range(1, 53))
        for card in cardsDistributed:
            all_cards.remove(card)

        return (random.choice(all_cards))

    def showDealerCards(self, dealerCards, chatId):
        text = "Dealer Cards:\n"
        for cardId in dealerCards:
            text+=self.shared.convertCardIDtoText(cardId)
        self.shared.send_message(text, chatId)

    def showAllCards(self, gameId, users, chatId, dealerCards):
        text = "All cards:\n"
        for userId in users:
            userGame = self.db.getUserGame(gameId, userId)
            userCards = userGame["cards"]
            user = self.db.getUser(userId)
            first_name = user["first_name"]
            text += "\n"+first_name+": "
            for cardId in userCards:
                text+=self.shared.convertCardIDtoText(cardId)
        
        text += "\n\nDealer:"
        for cardId in dealerCards:
            text+=self.shared.convertCardIDtoText(cardId)
        self.shared.send_message(text, chatId)

    def calculatePoints(self, cards):
        nums = ['0', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
        points = 0
        for cardId in cards:
            cardId -= 1
            num = nums[cardId%13+1]
            if(cardId%13+1 < 10):
                points += int(num)
            elif(cardId%13+1 < 13):
                points += 10
            else:
                # It is an ace
                if(points > 10):
                    points += 1
                else:
                    points += 11
        return points

    def hitTurn(self, gameDict, chatId):
        cardsDistributed = gameDict["cardsDistributed"]
        gameId = gameDict["gameId"]
        users = gameDict["users"]
        turns = gameDict["turns"]
        currentTurn = gameDict["currentTurn"]
        if(turns[currentTurn] != chatId):
            self.shared.send_message("Please play on your own turn", chatId)
            return

        newCard = self.getAdditionalCard(cardsDistributed)
        cardsDistributed.append(newCard)
        self.db.updateValues("Game", "gameId", gameId, "cardsDistributed", cardsDistributed)

        items = ['/hit', '/stand', '/show_dealer_cards', '/show_all_cards']
        keyboard = self.shared.build_keyboard(items, False)

        self.shared.send_message("Your new card is: "+self.shared.convertCardIDtoText(newCard), chatId, keyboard)
        userGame = self.db.getUserGame(gameId, chatId)
        userCards = userGame["cards"]
        userGameId = userGame["userGameId"]
        userCards.append(newCard)
        user = self.db.getUser(chatId)
        first_name = user["first_name"]
        text = first_name+"'s cards: "
        for cardId in userCards:
            text+=self.shared.convertCardIDtoText(cardId)
        self.shared.sendMessageToAllPlayers(users, text)
        self.db.updateValues("UserGame", "userGameId", userGameId, "cards", userCards)

        points = self.calculatePoints(userCards)
        if(points > 21):
            self.db.updateValues("UserGame", "userGameId", userGameId, "points", points)
            self.userBust(gameDict, first_name, chatId)

    def userBust(self, gameDict, first_name, chatId):
        turns = gameDict["turns"]
        gameId = gameDict["gameId"]
        dealerCards = gameDict["dealerCards"]
        cardsDistributed = gameDict["cardsDistributed"]
        currentTurn = gameDict["currentTurn"]
        
        self.shared.sendMessageToAllPlayers(turns, first_name+" has exceeded 21.")
        
        self.standTurn(gameId, chatId, turns, currentTurn, dealerCards, cardsDistributed)

    def standTurn(self, gameId, chatId, turns, currentTurn, dealerCards, cardsDistributed):
        user = self.db.getUser(chatId)
        first_name = user["first_name"]
        userGame = self.db.getUserGame(gameId, chatId)
        userGameId = userGame["userGameId"]
        cards = userGame["cards"]
        if(turns[currentTurn] != chatId):
            self.shared.send_message("Please play on your own turn", chatId)
            return

        points = self.calculatePoints(cards)
        self.shared.sendMessageToAllPlayers(turns, first_name+"'s total is "+str(points))
        self.db.updateValues("UserGame", "userGameId", userGameId, "points", points)

        if(currentTurn == len(turns)-1):
            self.dealerTurn(gameId, turns, dealerCards, cardsDistributed)
        else:
            # next player turn
            currentTurn = self.shared.updateCurrentTurn(currentTurn, turns)
            user = self.db.getUser(turns[currentTurn])
            first_name = user["first_name"]
            self.db.updateValues("Game", "gameId", gameId, "currentTurn", currentTurn)
            self.shared.sendMessageToAllPlayers(turns, "It is "+first_name+"'s turn now.")

    def dealerTurn(self, gameId, turns, dealerCards, cardsDistributed):
        dealerPoints = self.calculatePoints(dealerCards)
        while(dealerPoints < 17):
            newCard = self.getAdditionalCard(cardsDistributed)
            cardsDistributed.append(newCard)
            self.db.updateValues("Game", "gameId", gameId, "cardsDistributed", cardsDistributed)
            dealerCards.append(dealerPoints)
            dealerPoints = self.calculatePoints(dealerCards)
        
        text = "Dealer cards:\n"
        for cardId in dealerCards:
            text += self.shared.convertCardIDtoText(cardId)
        text += "\nDealer Total: "+str(dealerPoints)

        if(dealerPoints > 21):
            text += "\nDealer has exceeded 21. BUSTED"
        self.db.updateValues("Game", "gameId", gameId, "dealerPoints", dealerPoints)
        self.shared.sendMessageToAllPlayers(turns, text)

        # Print current score
        text = "Current score:"
        for userId in turns:
            user = self.db.getUser(userId)
            first_name = user["first_name"]
            userGame = self.db.getUserGame(gameId, userId)
            userGameId = userGame["userGameId"]
            userPoints = userGame["points"]
            score = userGame["score"]
            if((userPoints > dealerPoints and userPoints<22) or (dealerPoints > 21)):
                score+=1
                self.db.updateValues("UserGame", "userGameId", userGameId, "score", score)
            elif(userPoints < dealerPoints):
                score-=1
                self.db.updateValues("UserGame", "userGameId", userGameId, "score", score)
            text+="\n"+first_name+": "+str(score)
        self.shared.sendMessageToAllPlayers(turns, text)

        self.beginRound(gameId, turns)

    def beginRound(self, gameId, turns):
        numUsers = len(turns)
        distributedCards = self.shared.distributeCards(numPeople=len(turns))
        self.db.updateValues("Game", "gameId", gameId, "currentTurn", 0)

        userNames = []
        for user in turns:
            userNames.append(self.db.getUser(user)["first_name"])
    
        cardsDistributed = []
        text = ""
        for i in range(numUsers):
            # Cz need to give only 2 per person
            cardsForUser = distributedCards[i][:2]
            cardsDistributed.extend(cardsForUser)
            text+="\n"+userNames[i]+": "
            for cardId in cardsForUser:
                text += self.shared.convertCardIDtoText(cardId)
            userGame = self.db.getUserGame(gameId, turns[i])
            userGameId = userGame["userGameId"]
            self.db.updateValues("UserGame", "userGameId", userGameId, "cards", cardsForUser)

        dealerCard = self.getAdditionalCard(cardsDistributed)
        cardsDistributed.append(dealerCard)
        text += "\nDealer: "+self.shared.convertCardIDtoText(dealerCard)
        self.shared.sendMessageToAllPlayers(turns, "All cards: "+text)

        dealerCards = [dealerCard]
        self.db.updateValues("Game", "gameId", gameId, "cardsDistributed", cardsDistributed)
        self.db.updateValues("Game", "gameId", gameId, "dealerCards", dealerCards)

        user = self.db.getUser(turns[0])
        first_name = user["first_name"]
        items = ['/hit', '/stand', '/show_dealer_cards', '/show_all_cards']
        keyboard = self.shared.build_keyboard(items, False)
        self.shared.sendMessageToAllPlayers(turns, "It is "+first_name+"'s turn now.", keyboard)
    
    def endGameBlackJack(self, gameId, turns):
        self.shared.sendMessageToAllPlayers(turns, "The game has ended")

        text = "Final scores:"
        winner = []
        maxScore = -999
        for userId in turns:
            user = self.db.getUser(userId)
            first_name = user["first_name"]
            userGame = self.db.getUserGame(gameId, userId)
            userGameId = userGame["userGameId"]
            score = userGame["score"]
            if(score > maxScore):
                winner = [first_name]
                maxScore = score
            elif(score == maxScore):
                winner.append(first_name)
            text+="\n"+first_name+": "+str(score)
        text += "\nThe winner(s) is/are "+(', '.join(winner))

        items = ["/create"]
        keyboard = self.shared.build_keyboard(items, False)
        self.shared.sendMessageToAllPlayers(turns, text, keyboard)