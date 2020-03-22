from flask import Flask
from flask_cors import CORS
import sys

sys.path.append('../')

from review_analysis.utils.elastic_connector import Connector
from .controllers.ProductController import ProductController
from .controllers.GenerateDataController import GenerateDataController
from .controllers.DataController import DataController
from .controllers.ExperimentClusterController import ExperimentClusterController
from .controllers.ReviewExperimentController import ReviewController

app = Flask(__name__)
CORS(app)
es_con = Connector()
product_cnt = ProductController(es_con)
generate_cnt = GenerateDataController(es_con)
data_cnt = DataController(es_con)
experiment_cluster_cnt = ExperimentClusterController(es_con)
review_cnt = ReviewController(es_con)

from app import routes

if __name__ == '__main__':
    app.run(debug=True, port=8081, host='0.0.0.0')
