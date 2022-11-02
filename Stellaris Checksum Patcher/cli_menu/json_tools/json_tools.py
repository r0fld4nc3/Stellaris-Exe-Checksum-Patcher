import os
import json

# 3rd-party
from . import dict_tools as dt

class JsonTools:
    def load(self, os_path=None) -> dict:
        pass
    
    def write(self, os_path=None) -> bool:
        pass
    
    def print(self, dict_to_print, indent=2) -> str:
        pass
    
    def get_from_key(self, key) -> None:
        pass
    
    def get_from_value(self, value) -> None:
        pass
    
    def set_key_value(self, dictionary, key, value) -> None:
        pass
    
    def remove_entry(self, dictionary, key) -> None:
        pass