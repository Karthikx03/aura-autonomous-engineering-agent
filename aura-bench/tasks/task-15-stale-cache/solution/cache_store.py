class UserStore:
    def __init__(self):
        self._data = {}
        self._cache = {}

    def set_user(self, user_id, name):
        self._data[user_id] = name
        self._cache[user_id] = name

    def get_user(self, user_id):
        if user_id in self._cache:
            return self._cache[user_id]
        value = self._data.get(user_id)
        self._cache[user_id] = value
        return value
