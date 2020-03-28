from .Controller import Controller
import sys, datetime


class DataController(Controller):

    def get_indexes_health(self):
        return self.connector.get_indexes_health()

    def get_breadcrumbs(self):
        return self.connector.get_data_breadcrumbs()

    def get_actualization_statistics(self, content):
        try:
            data = {
                'review_count': [],
                'affected_products': [],
                'new_products': [],
                'new_product_reviews': []
            }
            dates_d = {}

            actualization_list, ret_code = self.connector.get_actualization_by_category(content['category'])
            for actualization in actualization_list:
                date_obj = datetime.datetime.strptime(actualization['date'], "%d. %B %Y")
                date_str = str(date_obj.date())

                dates_d[date_str] = actualization

            for key, value in sorted( dates_d.items() ):
                data['review_count'].append([key, value['review_count']])
                data['affected_products'].append([key, value['affected_products']])
                data['new_products'].append([key, value['new_products']])
                data['new_product_reviews'].append([key, value['new_product_reviews']])

            return data, ret_code

        except Exception as e:
            print("[DataController-get_actualization_statistics] Error: " + str(e), file=sys.stderr)
            return {'error': str(e), 'error_code': 400}, 400
