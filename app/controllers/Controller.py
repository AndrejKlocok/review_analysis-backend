from review_analysis.utils.elastic_connector import Connector


class Controller():
    def __init__(self, con: Connector):
        self.connector = con
