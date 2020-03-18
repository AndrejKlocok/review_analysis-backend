from urllib.request import urlopen
from bs4 import BeautifulSoup
import sys
from .Controller import Controller


class ProductController(Controller):

    def get_breadcrumbs(self):
        return self.connector.get_product_breadcrums()

    def get_category_products(self, category_name:str):
        return self.connector.get_category_products(category_name)

    def get_product_reviews(self, product_name:str):
        return self.connector.get_reviews_from_product(product_name)

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
