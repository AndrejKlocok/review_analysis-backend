from app import app, es_con
from flask import jsonify, request


@app.route('/')
@app.route('/index')
def index():
    return "Hello, World!"


@app.route('/data/indexes_health', methods=['GET'])
def data_index_health():
    data, retcode = es_con.get_indexes_health()
    return jsonify(data)


@app.route('/data/breadcrumbs', methods=['GET'])
def data_breadcrumbs():
    data, retcode = es_con.get_product_breadcrums()
    return jsonify([data])


@app.route('/data/index_breadcrumbs', methods=['GET'])
def data_index_breadcrumbs():
    data, retcode = es_con.get_index_breadcrums()
    return jsonify([data])


@app.route('/product/', methods=['POST'])
def product_get():
    content = request.json
    category = content['category_name']
    data, retcode = es_con.get_category_products(category)
    return jsonify(data)
