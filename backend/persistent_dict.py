import pickle
import os

class PersistentDict:
    def __init__(self, filename='cache.pkl'):
        self.filename = filename
        self.load()

    def load(self):
        if os.path.exists(self.filename):
            with open(self.filename, 'rb') as f:
                self.data = pickle.load(f)
        else:
            self.data = {}

    def save(self):
        with open(self.filename, 'wb') as f:
            pickle.dump(self.data, f)

    def __setitem__(self, key, value):
        self.data[key] = value
        self.save()

    def __getitem__(self, key):
        if key in self.data:
            return self.data[key]
        else:
            raise KeyError(f"Key '{key}' not found in cache")

    def __contains__(self, key):
        return key in self.data

    def __delitem__(self, key):
        if key in self.data:
            del self.data[key]
            self.save()
        else:
            raise KeyError(f"Key '{key}' not found in cache")
