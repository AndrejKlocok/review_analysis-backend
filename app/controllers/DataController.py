from review_analysis.utils.elastic_connector import Connector

class DataController:
    def __init__(self, con: Connector):
        self.connector = con

    def get_indexes_health(self):
        return self.connector.get_indexes_health()

    def get_breadcrumbs(self):
        return self.connector.get_data_breadcrumbs()
