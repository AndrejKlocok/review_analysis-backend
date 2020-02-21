from flask import Flask
from flask_cors import CORS
import sys
sys.path.append('../')
from review_analysis.utils.elastic_connector import Connector


app = Flask(__name__)
CORS(app)
es_con = Connector()


from app import routes


if __name__ == '__main__':
    app.run(debug=True, port=8081)
