from .Controller import Controller

class DataController(Controller):

    def get_indexes_health(self):
        return self.connector.get_indexes_health()

    def get_breadcrumbs(self):
        return self.connector.get_data_breadcrumbs()
