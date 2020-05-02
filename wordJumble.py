from sharedFunctions import Shared
import random 

class WordJumble:
    def __init__(self, shared, db):
        self.shared = shared
        self.db = db

    def beginWordJumble(self, chatId, gameId, users):
        numUsers = len(users)
        game = self.db.findDocument("Game", "gameId", gameId)
        started = game["started"]
        if started: 
            self.shared.send_message("Game has begun already", chatId)
            return 

        self.shared.send_message("Begin Word Jumble", chatId)

        currentLevel = game["level"]
        currentLevelWords = self.db.findDocument("Word", "length", currentLevel)["words"]
        currentWord = random.choice(currentLevelWords).lower()
        jumbledWord = self.get_jumble_word(currentWord)

        turns = self.shared.decideTurns(users)
        self.db.updateValues("Game", "gameId", gameId, "started", True)
        self.db.updateValues("Game", "gameId", gameId, "currentWord", currentWord)

        message = "The jumbled word is "+jumbledWord
        self.shared.sendMessageToAllPlayers(users, message)

    def get_jumble_word(self, word):
        l = list(word)
        random.shuffle(l)
        return ''.join(l)