from sharedFunctions import Shared
import random 

class CardTrick:
    def __init__(self, shared, db):
        self.shared = shared
        self.db = db

    def beginCardTrick(self, chatId, gameId):
        game = self.db.findDocument("Game", "gameId", gameId)
        self.db.updateValues("Game", "gameId", gameId, "started", True)
        
        cards = list(range(2,50))
        keyboard = self.shared.build_keyboard(cards)
        self.shared.send_message("Choose a card", chatId, keyboard)

    def cardChosen(self, chatId, cardId):
        self.shared.send_message("Putting card back in deck", chatId)
        self.shared.send_message("Shuffling cards...", chatId)
        self.shared.send_message("Your card is "+self.shared.convertCardIDtoText(cardId), chatId)
        self.shared.send_message("Thank you for playing!", chatId)