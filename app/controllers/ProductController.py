from urllib.request import urlopen
from bs4 import BeautifulSoup
import sys
from .Controller import Controller


class ProductController(Controller):

    def get_breadcrumbs(self):
        return self.connector.get_product_breadcrums()

    def get_category_products(self, content: dict):
        category = content['category_name']
        if category == 'shop':
            return self.connector.get_shops()
        else:
            return self.connector.get_category_products(category)

    def get_product_reviews(self, content: dict):
        if content['domain'] == 'shop':
            return self.connector.get_reviews_from_shop(content['name'])
        else:
            return self.connector.get_reviews_from_product(content['name'])

    def get_product_image_url(self, product_url:str):
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
