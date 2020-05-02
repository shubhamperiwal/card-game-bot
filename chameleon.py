from sharedFunctions import Shared
import random 

class Chameleon:
    def __init__(self, shared, db):
        self.shared = shared
        self.db = db
        # points chameleon gets if he is not caught or other players get if they catch chameleon
        self.winningPrize = 500
        # points chameleon gets if he guesses the word correctly.
        self.chamGuessPrize = 300
        # points a player loses if he is voted incorrectly or if he votes incorrectly
        self.wrongVotePenalty = -100

    def selectTopic(self, chatId, gameId, users):
        numUsers = len(users)
        game = self.db.findDocument("Game", "gameId", gameId)
        started = game["started"]
        if started: 
            self.shared.send_message("Game has begun already", chatId)
            return 

        self.db.updateValues("Game", "gameId", gameId, "started", True)
        self.newRound(users, gameId)

    def newRound(self, users, gameId):

        game = self.db.findDocument("Game", "gameId", gameId)
        currentRound = game["currentRound"]
        if(currentRound > 1):
            #Reset values
            self.db.updateValues("Game", "gameId", gameId, "clues", [])
            self.db.updateValues("Game", "gameId", gameId, "votes", [])
            for user in users:
                userGame = self.db.getUserGame(gameId, user)
                userGameId = userGame["userGameId"]
                self.db.updateValues("UserGame", "userGameId", userGameId, "clue", "")
                self.db.updateValues("UserGame", "userGameId", userGameId, "vote", "")


        all_topics = self.db.getAllTopics()
        all_topics_str = '\n '.join(all_topics)
        all_topics = ["/topic "+x for x in all_topics]
        self.shared.sendMessageToAllPlayers(users, "Begin new Round of Chameleon. Creator must now select topic from these options: \n"+all_topics_str)
        
        keyboard = self.shared.build_keyboard(all_topics, False)
        self.shared.send_message("Please select topic", users[0], keyboard)


    def beginChameleon(self, chatId, gameId, users, topic):
        all_words = self.db.findDocument("Topic", "topic", topic)["words"]
        all_words_str = "\n".join(all_words)
        self.shared.sendMessageToAllPlayers(users, "The words are:\n"+all_words_str)

        cham_player = random.choice(users)
        rest_users = users.copy()
        rest_users.remove(cham_player)
        chosen_word = random.choice(all_words)
        
        self.shared.sendMessageToAllPlayers(rest_users, "The word is: "+chosen_word)
        self.shared.send_message("You are the chameleon", cham_player)

        turns = self.shared.decideTurns(users)
        self.db.updateValues("Game", "gameId", gameId, "cham_player", cham_player)
        self.db.updateValues("Game", "gameId", gameId, "currentTopic", topic)
        self.db.updateValues("Game", "gameId", gameId, "currentWord", chosen_word)
        self.db.updateValues("Game", "gameId", gameId, "turns", turns)
        self.db.updateValues("Game", "gameId", gameId, "currentTurn", 0)
        userNames = []
        for user in turns:
            firstName = self.db.getUser(user)["first_name"]
            userNames.append(firstName)
            self.db.createUserGame(gameId, user, [], firstName)
    
        message = "The order of turns is: "+(", ".join(userNames))+"\nIt is "+userNames[0]+"'s turn. Please enter your /clue <your clue>."
        self.shared.sendMessageToAllPlayers(users, message)
            

    def addClue(self, userId, gameId, users, clue, turns, currentTurn, clues):
        if(userId == turns[currentTurn]):
            userGame = self.db.getUserGame(gameId, userId)
            userGameId = userGame["userGameId"]
            self.db.updateValues("UserGame", "userGameId", userGameId, "clue", clue)
            clues.append(clue)
            self.db.updateValues("Game", "gameId", gameId, "clues", clues)

            clues_str = "The clues are:\n"
            for userId in turns:
                userGame = self.db.getUserGame(gameId, userId)
                user_name = userGame["first_name"]
                user_clue = userGame["clue"]
                if(len(user_clue) > 0):
                    clues_str += "\n"+user_name+": "+user_clue

            if(len(clues) < len(turns)):
                currentTurn = self.shared.updateCurrentTurn(currentTurn, turns)
                firstName = self.db.getUser(turns[currentTurn])["first_name"]
                self.db.updateValues("Game", "gameId", gameId, "currentTurn", currentTurn)
                
                self.shared.sendMessageToAllPlayers(turns, clues_str)
                self.shared.sendMessageToAllPlayers(turns, "The next player is "+firstName+". Please give your clue using /clue <yourClue>")
            else:
                # People need to vote now.
                self.shared.sendMessageToAllPlayers(turns, clues_str)
                vote_users = ["/vote "+self.db.getUser(user)["first_name"] for user in users]
                keyboard = self.shared.build_keyboard(vote_users, False)

                currentTurn = self.shared.updateCurrentTurn(currentTurn, turns)
                firstName = self.db.getUser(turns[currentTurn])["first_name"]
                self.db.updateValues("Game", "gameId", gameId, "currentTurn", currentTurn)

                self.shared.sendMessageToAllPlayers(users, "Begin voting now. The player to begin voting is "+firstName, keyboard)
        else:
            self.shared.send_message("Please play when it is your turn", userId)
        
    def addVote(self, userId, gameId, users, vote, turns, currentTurn, votes, cham_player):
        if(userId == turns[currentTurn]):
            userGame = self.db.getUserGame(gameId, userId)
            userGameId = userGame["userGameId"]
            voted_userId = self.db.findDocument("User", "first_name", vote)["chatId"]

            # If voted incorrectly, then penalise
            if(voted_userId != cham_player):
                self.db.updateScoreInUserGame(gameId, voted_userId, self.wrongVotePenalty)
                if(userId != cham_player):
                    self.db.updateScoreInUserGame(gameId, userId, self.wrongVotePenalty)
            self.db.updateValues("UserGame", "userGameId", userGameId, "vote", vote)
            votes.append(vote)
            self.db.updateValues("Game", "gameId", gameId, "votes", votes)

            votes_dict = {x:votes.count(x) for x in votes}

            votes_str = "The votes are:\n"
            for key, value in votes_dict.items():
                votes_str += "\n"+key+": "+str(value)

            if(len(votes) < len(turns)):
                currentTurn = self.shared.updateCurrentTurn(currentTurn, turns)
                firstName = self.db.getUser(turns[currentTurn])["first_name"]
                self.db.updateValues("Game", "gameId", gameId, "currentTurn", currentTurn)
                
                self.shared.sendMessageToAllPlayers(turns, "The vote was given to "+vote)
                self.shared.sendMessageToAllPlayers(turns, votes_str)
                self.shared.sendMessageToAllPlayers(turns, "The next player is "+firstName+". Please give your vote using /vote <yourVote>")
            else:
                # End Round. Calculate scores. Chameleon select word
                self.shared.sendMessageToAllPlayers(turns, "The vote was given to "+vote)
                self.shared.sendMessageToAllPlayers(turns, votes_str)
                self.endRound(users, votes, cham_player, gameId, votes_dict)
        else:
            self.shared.send_message("Please play when it is your turn", userId)

    def endRound(self, users, votes, cham_player, gameId, votes_dict):

        # Check if Chameleon got the most votes.
        most_voted_firstName = max(set(votes), key=votes.count)
        most_voted_userId = self.db.findDocument("User", "first_name", most_voted_firstName)["chatId"]

        dict_values = list(votes_dict.values())
        most_votes = max(dict_values)

        self.db.updateCurrentRound(gameId)

        # If there is just a single majority user.
        if(cham_player == most_voted_userId and dict_values.count(most_votes) == 1):
            self.shared.sendMessageToAllPlayers(users, "Players Won! \nIt was "+self.db.getUser(cham_player)["first_name"]+"\nNow chameleon will try to select the correct word")

            rest_users = users.copy()
            rest_users.remove(cham_player)
            for user in rest_users:
                # Give rest of the users 500 if they select chameleon correctly
                self.db.updateScoreInUserGame(gameId, user, self.winningPrize)

            # Now chameleon will try to select word
            topic = self.db.findDocument("Game", "gameId", gameId)["currentTopic"]
            words = self.db.findDocument("Topic", "topic", topic)["words"]

            words_key = ["/select "+word for word in words]
            keyboard = self.shared.build_keyboard(words_key, False)
            self.shared.send_message("Please try to select the correct word: ", cham_player, keyboard)
        else:
            self.shared.sendMessageToAllPlayers(users, "Chameleon Won! \nIt was "+self.db.getUser(cham_player)["first_name"])
            # Give user 500 if he wins chameleon
            self.db.updateScoreInUserGame(gameId, cham_player, self.winningPrize)
            self.printScores(gameId, users)
            self.newRound(users, gameId)
        
    def chameleonSelectWord(self, userId, chosenWord, users, gameId):
        game = self.db.findDocument("Game", "gameId", gameId)
        currentWord = game["currentWord"]
        currentRound = game["currentRound"]
        
        if(chosenWord==currentWord):
            self.shared.sendMessageToAllPlayers(users, "Chameleon has selected the word correctly!")
            self.db.updateScoreInUserGame(gameId, userId, self.chamGuessPrize)
        else:
            self.shared.sendMessageToAllPlayers(users, "Chameleon has NOT selected the word correctly!")
        
        self.printScores(gameId, users)
        self.newRound(users, gameId)

    def printScores(self, gameId, users):
        scores_text = "\nCurrent scores:"
        for user in users:
            userGame = self.db.getUserGame(gameId, user)
            first_name = userGame["first_name"]
            score = userGame["score"]
            scores_text += "\n"+first_name+": "+str(score)

        self.shared.sendMessageToAllPlayers(users, scores_text)

    def endGameChameleon(self, gameId, turns):
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




