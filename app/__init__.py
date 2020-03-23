from flask import Flask
from flask_cors import CORS
import sys, secrets

sys.path.append('../')

from review_analysis.utils.elastic_connector import Connector
from .controllers.ProductController import ProductController
from .controllers.GenerateDataController import GenerateDataController
from .controllers.DataController import DataController
from .controllers.ExperimentClusterController import ExperimentClusterController
from .controllers.ReviewExperimentController import ReviewController
from .controllers.UserController import UserController

app = Flask(__name__)
CORS(app)

app.config['SECRET_KEY'] = secrets.token_urlsafe(32)

es_con = Connector()
product_cnt = ProductController(es_con)
generate_cnt = GenerateDataController(es_con)
data_cnt = DataController(es_con)
experiment_cluster_cnt = ExperimentClusterController(es_con)
review_cnt = ReviewController(es_con)
user_cnt = UserController(es_con)

from app import routes

if __name__ == '__main__':
    app.run(debug=True, port=8081, host='0.0.0.0')
