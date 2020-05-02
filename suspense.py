import numpy as np

class Suspense:
    def __init__(self, shared, db):
        self.shared = shared
        self.db = db
    
    def decideSetWinner(self, currentSet, currentTurn, turns, gameId):
        firstCard = currentSet[0]

        lower_heart = 27
        upper_heart = 39
        heartCards = [x for x in currentSet if lower_heart <= x <= upper_heart]

        if(len(heartCards)==0):
            if(firstCard%13==0):
                firstCard-=1
            lower_suit = 13*int(firstCard/13)+1
            upper_suit = 13*int(firstCard/13)+13
            currSuitCards = [x for x in currentSet if lower_suit <= x <= upper_suit]
            highestCard = max(currSuitCards)
            userIndex = currentSet.index(highestCard)
        else:
            highestCard = max(heartCards)
            userIndex = currentSet.index(highestCard)

        userIndex = (userIndex+currentTurn)%len(turns)
        userId = turns[userIndex]
        firstName = self.db.getUser(userId)["first_name"]
        self.shared.sendMessageToAllPlayers(turns, "This set goes to "+firstName)

        # Add 1 set to user's score
        self.db.updateSetsInUserGame(gameId, userId)

        # clear current set
        self.db.updateValues("Game", "gameId", gameId, "currentSet", [])

        # Update current turn to winner
        self.db.updateValues("Game", "gameId", gameId, "currentTurn", userIndex)
        return firstName

    def calcScoreSuspense(self, goal, sets):
        return 11*goal + 10 if goal==sets else 0

    def endGameSuspense(self, gameId, turns):
        maxScore = 0
        winner = []
        text = "" 
        for userId in turns:
            user = self.db.getUser(userId)
            first_name = user["first_name"]
            userGame = self.db.getUserGame(gameId, userId)
            score = userGame["score"]
            if(score > maxScore):
                winner = [first_name]
                maxScore = score
            elif (score == maxScore):
                winner.append(first_name)
            text += "\n"+first_name+": "+str(score)
        self.shared.sendMessageToAllPlayers(turns, "The game has ended! The final scores are: "+text)
        keyboard = self.shared.build_keyboard(['/create'], False)
        self.shared.sendMessageToAllPlayers(turns, "The winner(s) is/are: "+(', '.join(winner)), keyboard)
        self.db.updateValues("Game", "gameId", gameId, "active", False)

    def endRound(self, gameId, turns, currentRound, currentTurn):
        numUsers = len(turns)
        currentRound+=1
        self.db.updateValues("Game", "gameId", gameId, "goals", [])
        self.db.updateValues("Game", "gameId", gameId, "currentRound", currentRound)
        self.db.updateValues("Game", "gameId", gameId, "currentTurn", currentTurn)
        # Uncomment this next one later
        scoresText = "Scores currently:" 
        # Calculate scores
        for i in range(numUsers):
            userId = turns[i]
            first_name = self.db.getUser(userId)["first_name"]
            userGame = self.db.getUserGame(gameId, userId)
            userGameId = userGame["userGameId"]
            userGoal = userGame["goal"]
            userSets = userGame["sets"]
            userScore = userGame["score"]
            scoreThisRound = self.calcScoreSuspense(userGoal, userSets)
            userScore += scoreThisRound
            self.shared.send_message("This round is over. ", userId)
            self.db.updateValues("UserGame", "userGameId", userGameId, "score", userScore)
            scoresText += "\n"+first_name+": "+str(userScore)
        self.shared.sendMessageToAllPlayers(turns, scoresText)

        if(currentRound-1 == int(52/len(turns))):
            self.endGameSuspense(gameId, turns)
            return True
        else:
            distributedCards = self.shared.distributeCards(numPeople = len(turns), currentRound=currentRound)

            goalList = []
            for i in range(len(distributedCards[0])+1):
                goalList.append("/goal "+str(i))
            keyboard = self.shared.build_keyboard(goalList, False)

            for i in range(numUsers):
                userId = turns[i]
                userGame = self.db.getUserGame(gameId, userId)
                userGameId = userGame["userGameId"]
                cardsForUser = sorted(distributedCards[i])
                text=""
                for cardId in cardsForUser:
                    text += self.shared.convertCardIDtoText(cardId)
                self.shared.send_message("New Round! \nYour cards: \n"+text, turns[i], keyboard)
                self.db.updateValues("UserGame", "userGameId", userGameId, "cards", cardsForUser)
                self.db.updateValues("UserGame", "userGameId", userGameId, "sets", 0)
                self.db.updateValues("UserGame", "userGameId", userGameId, "goal", -1)
            return False

    def playTurn(self, chatId, gameId, cardId, currentSet, userGameId, currentTurn, turns, cards, currentRound):
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
            winner = self.decideSetWinner(currentSet, currentTurn, turns, gameId)
            # Round is over. Compute round winner and redistribute cards
            if (len(cards)==0):
                endGame = self.endRound(gameId, turns, currentRound, currentTurn)
                if(not endGame):
                    self.shared.sendMessageToAllPlayers(turns, "It is "+winner+"'s turn now. Please set your goals.")
            else:
                self.shared.sendMessageToAllPlayers(turns, "It is "+winner+"'s turn now.")
        else:
            self.shared.sendMessageToAllPlayers(turns, "The next player is "+firstName+". Please play your turn by typing /turn or choosing a card")


    def suspenseSetGoal(self, gameId, userId, goal, turns, currentTurn, goals):
        # Set a goal
        # Extract game for which this is happening
        # Update DB with his goal
        # Add 1 to currentTurn
        # Send all users a message about the next user
        if(userId == turns[currentTurn]):
            userGame = self.db.getUserGame(gameId, userId)
            userGameId = userGame["userGameId"]
            self.db.updateValues("UserGame", "userGameId", userGameId, "goal", goal)
            goals.append(goal)
            self.db.updateValues("Game", "gameId", gameId, "goals", goals)
            if(len(goals) < len(turns)):
                currentTurn = self.shared.updateCurrentTurn(currentTurn, turns)
                firstName = self.db.getUser(turns[currentTurn])["first_name"]
                self.db.updateValues("Game", "gameId", gameId, "currentTurn", currentTurn)
                
                self.shared.sendMessageToAllPlayers(turns, "The goal set was "+str(goal))
                self.shared.sendMessageToAllPlayers(turns, "So far, the goals are "+(', '.join(map(str, goals))))
                self.shared.sendMessageToAllPlayers(turns, "The next player is "+firstName+". Please set a goal using /goal <yourGoal>")
            else:
                # Get whose turn it is
                currentTurn = int(np.argmax(goals))
                firstName = self.db.getUser(turns[currentTurn])["first_name"]
                self.db.updateValues("Game", "gameId", gameId, "currentTurn", currentTurn)
                self.shared.sendMessageToAllPlayers(turns, "The goal set was "+str(goal)+
                        "\nSo far, the goals are "+(', '.join(map(str, goals)))+
                        "\nAll goals are set. Begin playing")
                for userId in turns:
                    userGame = self.db.getUserGame(gameId, userId)
                    cards = userGame["cards"]
                    keyboard = self.shared.build_keyboard(cards)
                    self.shared.send_message("Click on the cards when it's your turn:", userId, keyboard)
                self.shared.sendMessageToAllPlayers(turns, "The player to begin is "+firstName+". Please play your turn by typing /turn or choosing a card")
                

            return ""
        else:
            return "Please play when it is your turn"


    def beginSuspense(self, chatId, gameId, users):
        numUsers = len(users)
        game = self.db.findDocument("Game", "gameId", gameId)
        started = game["started"]
        currentRound = game["currentRound"]
        if started: 
            self.shared.send_message("Game has begun already", chatId)
            return 

        self.shared.send_message("Begin Suspense", chatId)
        distributedCards = self.shared.distributeCards(numPeople=numUsers, currentRound=currentRound)

        turns = self.shared.decideTurns(users)
        self.db.updateValues("Game", "gameId", gameId, "started", True)
        self.db.updateValues("Game", "gameId", gameId, "turns", turns)
        self.db.updateValues("Game", "gameId", gameId, "currentTurn", 0)
        userNames = []
        for user in turns:
            userNames.append(self.db.getUser(user)["first_name"])
    
        message = "The order of turns is: "+(", ".join(userNames))+"\nIt is "+userNames[0]+"'s turn. Set a goal using /goal <yourGoal>"
        self.shared.sendMessageToAllPlayers(users, message)

        goalList = []
        for i in range(len(distributedCards[0])+1):
            goalList.append("/goal "+str(i))
        keyboard = self.shared.build_keyboard(goalList, False)

        for i in range(numUsers):
            cardsForUser = sorted(distributedCards[i])
            text=""
            for cardId in cardsForUser:
                text += self.shared.convertCardIDtoText(cardId)
            self.db.createUserGame(gameId, users[i], cardsForUser)
            self.shared.send_message("Your cards: \n"+text, users[i], keyboard)

    def showSets(self, gameId, users, chatId):
        text = "Sets: "
        for userId in users:
            first_name = self.db.getUser(userId)["first_name"]
            userGame = self.db.getUserGame(gameId, userId)
            goal = userGame["goal"]
            sets = userGame["sets"]
            text += "\n"+first_name+": "+str(sets)+" out of "+str(goal)
        self.shared.send_message(text, chatId)