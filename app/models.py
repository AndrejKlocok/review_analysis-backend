"""
This file contains implementation of User class

Author: xkloco00@stud.fit.vutbr.cz
"""

from werkzeug.security import generate_password_hash, check_password_hash

from flask_login import UserMixin


class User(UserMixin):
    _id = ''
    name = ''
    password_hash = ''
    level = ''

    def __init__(self, name, level, password):
        self.name = name
        self.level = level
        self.password_hash = generate_password_hash(password, method='sha256')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return dict(name=self.name, level=self.level)


