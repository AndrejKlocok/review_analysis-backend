"""
This file contains implementation custom exceptions.

Author: xkloco00@stud.fit.vutbr.cz
"""


class WrongProperty(Exception):
    def __init__(self, message):
        super().__init__(message)
        self.message = message

    def __str__(self):
        return self.message
