from sharedFunctions import Shared


class Hearts:
    def __init__(self, shared, db):
        self.shared = shared
        self.db = db

    def beginHearts(self, chatId, gameId, users):
        numUsers = len(users)
        game = self.db.findDocument("Game", "gameId", gameId)
        started = game["started"]
        if started: 
            self.shared.send_message("Game has begun already", chatId)
            return 

        self.shared.send_message("Begin Hearts", chatId)
        distributedCards = self.shared.distributeCards(numPeople=numUsers)

        low_clubs = 14
        if(52%numUsers > 1):
            low_clubs = 15
        
        low_clubs_user = -1
        
        for i in range(numUsers):
            cardsForUser = sorted(distributedCards[i])
            text=""
            for cardId in cardsForUser:
                text += self.shared.convertCardIDtoText(cardId)

            if(low_clubs in cardsForUser):
                low_clubs_user = users[i]    
            
            keyboard = self.shared.build_keyboard(cardsForUser)
            self.db.createUserGame(gameId, users[i], cardsForUser)
            self.shared.send_message("Your cards: \n"+text, users[i], keyboard)
        
        starter = low_clubs_user

        users.remove(starter)
        turns = [starter]+users
        self.db.updateValues("Game", "gameId", gameId, "turns", turns)
        self.db.updateValues("Game", "gameId", gameId, "started", True)
        self.db.updateValues("Game", "gameId", gameId, "currentTurn", 0)
        
        userNames = []
        for user in turns:
            userNames.append(self.db.getUser(user)["first_name"])
    
        message = "The order of turns is: "+(", ".join(userNames))+"\nIt is "+userNames[0]+"'s turn. Select a card to play"
        self.shared.sendMessageToAllPlayers(turns, message)

    def playTurn(self, chatId, gameId, cardId, currentSet, userGameId, currentTurn, turns, cards):
        # Check if user is correct
        # Add to current set in games
        # Message all users about the card
        # Message all users the current set
        # remove card from user's keyboard
        # update currentTurn
        # If this is the last user then deduce winner
        if(turns[currentTurn] != chatId):
            self.shared.send_message("Please play on your own turn", chatId)
            return
        
        currentSet.append(cardId)
        self.db.updateValues("Game", "gameId", gameId, "currentSet", currentSet)

        user = self.db.getUser(chatId)
        userName = user['first_name']
        self.shared.sendMessageToAllPlayers(turns, userName+" played "+self.shared.convertCardIDtoText(cardId))

        text=""
        for card in currentSet:
            text += self.shared.convertCardIDtoText(card)
        self.shared.sendMessageToAllPlayers(turns, "Current Set: "+text)

        if(cardId not in cards):
            print("Card ID not in cards: \nCardId: ", cardId, "\nCards: ", cards)
            return
        cards.remove(cardId)
        self.db.updateValues("UserGame", "userGameId", userGameId, "cards", cards)
        keyboard = self.shared.build_keyboard(cards)
        self.shared.send_message("Cards updated", chatId, keyboard)

        currentTurn = self.shared.updateCurrentTurn(currentTurn, turns)
        self.db.updateValues("Game", "gameId", gameId, "currentTurn", currentTurn)

        firstName = self.db.getUser(turns[currentTurn])["first_name"]

        if (len(currentSet) == len(turns)):
            # Round is over. Compute round winner and redistribute cards
            winner = self.decideSetWinner(currentSet, currentTurn, turns, gameId)
            if (len(cards)==0):
                endGame = self.endRound(gameId, turns, currentTurn)
                if(endGame):
                    self.endGameHearts(gameId)
            else:
                self.shared.sendMessageToAllPlayers(turns, "It is "+winner+"'s turn now.")
        else:
            self.shared.sendMessageToAllPlayers(turns, "The next player is "+firstName+". Please play your turn by typing /turn or choosing a card")

    def calculatePointsInSet(self, currentSet):
        points = 0
        for cardId in currentSet:
            if(cardId >= 27 and cardId <= 39):
                points += 1
            elif(cardId==50):
                points += 13
        return points

    def decideSetWinner(self, currentSet, currentTurn, turns, gameId):
        firstCard = currentSet[0]
        if(firstCard%13==0):
            firstCard-=1
        lower_suit = 13*int(firstCard/13)+1
        upper_suit = 13*int(firstCard/13)+13
        currSuitCards = [x for x in currentSet if lower_suit <= x <= upper_suit]
        highestCard = max(currSuitCards)
        userIndex = currentSet.index(highestCard)
        userIndex = (userIndex+currentTurn)%len(turns)
        userId = turns[userIndex]
        firstName = self.db.getUser(userId)["first_name"]
        self.shared.sendMessageToAllPlayers(turns, "This set goes to "+firstName)

        # Add 1 set to user
        self.db.updateSetsInUserGame(gameId, userId)

        # Update points of the user
        points = self.calculatePointsInSet(currentSet)
        self.db.updateScoreInUserGame(gameId, userId, points)

        # clear current set
        self.db.updateValues("Game", "gameId", gameId, "currentSet", [])

        # Update current turn to winner
        self.db.updateValues("Game", "gameId", gameId, "currentTurn", userIndex)
        return firstName

    def endRound(self, gameId, turns, currentTurn):
        numUsers = len(turns)        
        scoresText = "Scores currently:" 
        
        endGame = False
        # Calculate scores
        for i in range(numUsers):
            userId = turns[i]
            first_name = self.db.getUser(userId)["first_name"]
            userGame = self.db.getUserGame(gameId, userId)
            userGameId = userGame["userGameId"]
            userGoal = userGame["goal"]
            userSets = userGame["sets"]
            userPoints = userGame["score"]
            if(userSets == 0):
                userPoints -= 5
                self.db.updateValues("UserGame", "userGameId", userGameId, "score", userPoints)

            if(userPoints > 50):
                endGame = True
            self.shared.send_message("This round is over. ", userId)
            
            scoresText += "\n"+first_name+": "+str(userPoints)
        self.shared.sendMessageToAllPlayers(turns, scoresText)
        distributedCards = self.shared.distributeCards(numPeople = len(turns))

        low_clubs = 14
        if(52%numUsers > 1):
            low_clubs = 15
        
        low_clubs_user = -1

        for i in range(numUsers):
            userId = turns[i]
            userGame = self.db.getUserGame(gameId, userId)
            userGameId = userGame["userGameId"]
            cardsForUser = sorted(distributedCards[i])
            text=""
            for cardId in cardsForUser:
                text += self.shared.convertCardIDtoText(cardId)

            if(low_clubs in cardsForUser):
                low_clubs_user = userId

            keyboard = self.shared.build_keyboard(cardsForUser)
            self.shared.send_message("New Round! \nYour cards: \n"+text, turns[i], keyboard)
            self.db.updateValues("UserGame", "userGameId", userGameId, "cards", cardsForUser)
            self.db.updateValues("UserGame", "userGameId", userGameId, "sets", 0)

        starter = low_clubs_user

        currentTurn = turns.index(starter)
        self.db.updateValues("Game", "gameId", gameId, "currentTurn", currentTurn)
        user = self.db.getUser(turns[currentTurn])
        first_name = user["first_name"]
        message = "\nIt is "+first_name+"'s turn. Select a card to play"
        self.shared.sendMessageToAllPlayers(turns, message)
        
        return endGame
    
    def endGameHearts(self, gameId, turns):
        minScore = 1000
        winner = []
        text = "" 
        for userId in turns:
            user = self.db.getUser(userId)
            first_name = user["first_name"]
            userGame = self.db.getUserGame(gameId, userId)
            score = userGame["score"]
            if(score < minScore):
                winner = [first_name]
                minScore = score
            elif (score == minScore):
                winner.append(first_name)
            text += "\n"+first_name+": "+str(score)
        self.shared.sendMessageToAllPlayers(turns, "The game has ended! The final scores are: "+text)
        keyboard = self.shared.build_keyboard(['/create'], False)
        self.shared.sendMessageToAllPlayers(turns, "The winner(s) is/are: "+(', '.join(winner)), keyboard)
        self.db.updateValues("Game", "gameId", gameId, "active", False)


    

    