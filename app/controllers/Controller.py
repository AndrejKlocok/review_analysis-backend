"""
This file contains base class for API Controller.

Author: xkloco00@stud.fit.vutbr.cz
"""
from review_analysis.utils.elastic_connector import Connector


class Controller:
    """
    Base class for controllers.
    """
    def __init__(self, con: Connector):
        """
        Constructor method takes elastic connector instance.
        :param con: instance of elastic connector
        """
        self.connector = con
