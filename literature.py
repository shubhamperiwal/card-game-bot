from sharedFunctions import Shared


class Literature:
    def __init__(self, shared, db):
        self.shared = shared
        self.db = db

    def beginLiterature(self, chatId, gameId, users):
        numUsers = len(users)
        self.shared.send_message("Begin Literature", chatId)
    

    