from flask import Flask
from flask_cors import CORS
from flask_restx import Api
import sys, secrets

sys.path.append('../')

from review_analysis.utils.elastic_connector import Connector
from .controllers.ProductController import ProductController
from .controllers.GenerateDataController import GenerateDataController
from .controllers.DataController import DataController
from .controllers.ExperimentClusterController import ExperimentClusterController
from .controllers.ReviewExperimentController import ReviewController
from .controllers.UserController import UserController

flask_app = Flask(__name__)
CORS(flask_app)

flask_app.config['SECRET_KEY'] = secrets.token_urlsafe(32)
app = Api(app=flask_app,
          version="1.0",
          title="Review analysys back end",
          description="Provides API interface to review analysis system.",
          api_spec_url='/swagger',
          contact='xkloco00@stud.fit.vutbr.cz'
          )

es_con = Connector()
generate_cnt = GenerateDataController(es_con)
data_cnt = DataController(es_con)
experiment_cluster_cnt = ExperimentClusterController(es_con)
review_cnt = ReviewController(es_con)
product_cnt = ProductController(es_con)
user_cnt = UserController(es_con)

from app import routes


