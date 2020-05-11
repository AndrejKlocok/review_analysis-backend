from review_analysis.utils.elastic_connector import Connector


class Controller:
    """
    Base class for controllers.
    """
    def __init__(self, con: Connector):
        self.connector = con
