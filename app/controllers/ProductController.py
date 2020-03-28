from urllib.request import urlopen
from bs4 import BeautifulSoup
import sys
from review_analysis.utils.elastic_connector import Connector


class ProductController:
    def __init__(self, con: Connector):
        self.connector = con

    def get_breadcrumbs(self):
        return self.connector.get_product_breadcrums()

    def get_category_products(self, content: dict):
        category = content['category_name']
        if category == 'shop':
            return self.connector.get_shops()
        else:
            return self.connector.get_category_products(category)

    def get_product_reviews(self, content: dict):
        try:
            if content['domain'] == 'shop':
                reviews, code = self.connector.get_reviews_from_shop(content['name'], True)
            else:
                reviews, code = self.connector.get_reviews_from_product(content['name'])

            for review in reviews:
                if 'rating_model' in review:
                    review['rating_diff'] = int(review['rating'][:-1]) - int(review['rating_model'][:-1])
                else:
                    review['rating_diff'] = 0

            return reviews, code

        except Exception as e:
            print('ExperimentController-get_product_reviews: {}'.format(str(e)), file=sys.stderr)
            return {'error': str(e), 'error_code': 500}, 500

    def get_product_image_url(self, product_url: str):
        data = {}
        ret_code = 200
        try:
            xml = BeautifulSoup(urlopen(product_url), 'lxml')
            src = xml.find('td').find('img').get('src')

            data['src'] = src

        except AttributeError as e:
            print(e, file=sys.stderr)
            ret_code = 404
        except Exception as e:
            print(e, file=sys.stderr)
            ret_code = 500
        finally:
            return data, ret_code

    def get_statistics(self, content: dict):
        try:
            data = {}
            ret_code = 200
            if content['domain'] == 'shop':
                reviews, _ = self.connector.get_reviews_from_shop(content['name'])
            else:
                reviews, _ = self.connector.get_reviews_from_product(content['name'])

            if not reviews:
                raise Exception('Item {} does not have any reviews'.format(content['name']))

            sum_rating = 0
            sum_recommends = 0
            dates_d = {}
            for review in reviews:
                try:
                    sum_rating += int(review['rating'][:-1])
                    date_str = '-'.join(review['date'].split('-')[:2])+'-01'

                    if date_str not in dates_d:
                        dates_d[date_str] = {
                               'month': ' '.join(review['date_str'].split()[1:]),
                                'cnt': 0
                        }
                    dates_d[date_str]['cnt'] += 1
                    if review['recommends'] == 'YES':
                        sum_recommends += 1

                except Exception as e:
                    # some reviews has empty ratings...
                    pass

            avg_rating = sum_rating / len(reviews)
            avg_recommends = sum_recommends / len(reviews)

            review_dates = []
            for key, value in sorted( dates_d.items() ):
                review_dates.append([value['month'], value['cnt']])

            data['avg_rating'] = '{:.2f}%'.format(avg_rating)
            data['avg_recommends'] = '{:.2f}%'.format(avg_recommends*100)
            data['review_dates'] = review_dates

            return data, ret_code

        except Exception as e:
            print('ExperimentController-get_experiment_sentences: {}'.format(str(e)), file=sys.stderr)
            return {'error': str(e), 'error_code': 500}, 500
