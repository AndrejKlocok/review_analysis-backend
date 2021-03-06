"""
This file contains implementation of UserController class, which provides /login and /register endpoints. Class handles
user authentication and registration.

Author: xkloco00@stud.fit.vutbr.cz
"""

from werkzeug.security import check_password_hash

from .Controller import Controller
from app.models import User
import sys


class UserController(Controller):
    """
    Controller handles user authentication.
    """
    def create_user(self, content: dict):
        """
        Create new user, who's information are specified in content dictionary and index him to elasticsaerch.
        :param content:
        :return: user dict
        """
        ret_code = 200
        try:
            if content['name'] and content['password'] and content['level']:
                res = self.connector.index('users', content)
                self.connector.es.indices.refresh(index="users")
                data = self.connector.get_user_by_id(res['_id'])
                return data, ret_code
            else:
                return {'error': 'User model is not valid', 'error_code': 500}, 500

        except Exception as e:
            print('ExperimentController-create_user: {}'.format(str(e)), file=sys.stderr)
            return {'error': str(e), 'error_code': 500}, 500

    def get_user(self, name: str):
        """
        Get user by name.
        :param name:
        :return: user: User object
        """
        try:
            user_d = self.connector.get_user_by_name(name)
            user = User(user_d['name'], user_d['level'], user_d['password_hash'])
            user._id = user_d['_id']

            return user
        except Exception as e:
            print('ExperimentController-get_user: {}'.format(str(e)), file=sys.stderr)
            return None

    def authenticate(self, **kwargs):
        """
        Authenticate user.
        :param kwargs:
        :return: user: User object
        """
        name = kwargs.get('name')
        password = kwargs.get('password')

        if not name or not password:
            return None

        user = self.connector.get_user_by_name(name)

        if not user or not check_password_hash(user['password_hash'], password):
            return None

        u = User(user['name'], user['level'], user['password_hash'])
        u._id = user['_id']
        return u
