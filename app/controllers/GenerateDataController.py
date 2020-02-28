import zipfile
import io
import sys

from review_analysis.utils.elastic_connector import Connector
from review_analysis.utils.generate_dataset import GeneratorController


class GenerateDataController:
    def __init__(self, con: Connector):
        self.connector = con
        self.generator = GeneratorController(con)

    def generate_dataset(self, content: dict):
        try:
            data = self.generator.generate(content)

            if 'error' in data:
                return data, 400
            else:
                data_file = io.BytesIO()
                with zipfile.ZipFile(data_file, mode='w') as z:
                    for key, value in data.items():
                        z.writestr(key, ''.join(value))
                data_file.seek(0)

                return data_file, 200

        except Exception as e:
            print('GenerateDataController-generate_dataset: {}'.format(str(e)),file=sys.stderr)
            return {'error': str(e)}, 500
