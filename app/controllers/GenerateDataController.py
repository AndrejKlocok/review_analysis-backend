"""
This file contains implementation of GenerateDataController class, which handles /generate/ endpoints. This class
provides API for dataset exporting with selectable formats.

Author: xkloco00@stud.fit.vutbr.cz
"""
import zipfile
import io
import sys

from review_analysis.utils.elastic_connector import Connector
from review_analysis.utils.generate_dataset import GeneratorController


class GenerateDataController:
    """
    Controller handles exporting data in generating tasks.
    """
    def __init__(self, con: Connector):
        """
        Constructor method takes elastic connector instance and creates instance of GeneratorController.
        :param con: instance of elastic connector
        """
        self.connector = con
        self.generator = GeneratorController(con)

    def generate_dataset(self, content: dict):
        """
        Export data according to content dictionary values.
        :param content:
        :return:
        """
        try:
            # perform generating task
            data = self.generator.generate(content)

            # if it is an error return concrete err
            if 'error' in data:
                return data, 400
            else:
                # else return zip file
                data_file = io.BytesIO()
                with zipfile.ZipFile(data_file, mode='w') as z:
                    for key, value in data.items():
                        z.writestr(key, ''.join(value))
                data_file.seek(0)

                return data_file, 200

        except Exception as e:
            print('GenerateDataController-generate_dataset: {}'.format(str(e)),file=sys.stderr)
            return {'error': str(e)}, 500
