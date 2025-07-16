import json
import os
from os import path


class DbManager:
    def __init__(self, cache_loc='cache.json'):
        self.cache_file = f'db/{cache_loc}'
        if not path.isdir('db'):
            os.mkdir('db')
        if not path.isfile(self.cache_file):
            open(self.cache_file, 'w').close()
            self.write_db({})

    def read_db(self):
        try:
            with open(self.cache_file, 'r') as file:
                data = json.load(file)
            return data
        except FileNotFoundError:
            print(f"File '{self.cache_file}' not found.", 'joblog')
            return None
        except json.JSONDecodeError:
            print(f"Error decoding JSON from '{self.cache_file}'.", 'joblog')
            return None

    def write_db(self, data):
        try:
            with open(self.cache_file, 'w') as file:
                json.dump(data, file)
            print(f"Data written to '{self.cache_file}' successfully.", 'joblog')
        except json.JSONDecodeError:
            print(f"Error writing JSON to '{self.cache_file}'.", 'joblog')
