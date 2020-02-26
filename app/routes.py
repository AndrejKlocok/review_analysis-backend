from app import app, es_con, dataset_generator
from flask import jsonify, request, send_file, abort
from urllib.request import urlopen
from bs4 import BeautifulSoup
import sys
import zipfile
import io


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

@app.route('/product/review', methods=['POST'])
def product_review_get():
    content = request.json
    product_name = content['product_name']
    data, retcode = es_con.get_reviews_from_product(product_name)
    return jsonify(data)

@app.route('/product/image', methods=['POST'])
def product_img_get():
    content = request.json
    url = content['url']
    data = {}
    ret_code = 200
    try:
        xml = BeautifulSoup(urlopen(url), 'lxml')
        src = xml.find('td').find('img').get('src')

        data['src'] = src

    except AttributeError as e:
        print(e, file=sys.stderr)
        ret_code = 404
    except Exception as e:
        print(e, file=sys.stderr)
        ret_code = 500
    finally:
        return jsonify(data)

@app.route('/generate/data', methods=['POST'])
def generate_dataset():
    content = request.json

    data = dataset_generator.generate(content)

    if 'error' in data:
        abort(400, data['error'])
    else:
        data_file = io.BytesIO()
        with zipfile.ZipFile(data_file, mode='w') as z:
            for key, value in data.items():
                z.writestr(key, ''.join(value))
        data_file.seek(0)

        return send_file(
            data_file,
            mimetype='application/zip',
            as_attachment=True,
            attachment_filename='data.zip'
        )
