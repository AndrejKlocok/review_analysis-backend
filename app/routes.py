from app import app, product_cnt, generate_cnt, data_cnt, experiment_cnt
from flask import jsonify, request, send_file, abort


@app.route('/')
@app.route('/index')
def index():
    return "Hello, World!"


@app.route('/data/indexes_health', methods=['GET'])
def data_index_health():
    data, retcode = data_cnt.get_indexes_health()
    return jsonify(data)

@app.route('/data/breadcrumbs', methods=['GET'])
def data_breadcrumbs_full():
    data, retcode = data_cnt.get_breadcrumbs()
    return jsonify([data])


@app.route('/product/', methods=['POST'])
def product_get():
    content = request.json
    category = content['category_name']
    data, retcode = product_cnt.get_category_products(category)
    return jsonify(data)

@app.route('/product/breadcrumbs', methods=['GET'])
def data_index_breadcrumbs():
    data, retcode = product_cnt.get_breadcrumbs()
    return jsonify([data])


@app.route('/product/review', methods=['POST'])
def product_review_get():
    content = request.json
    product_name = content['product_name']
    data, retcode = product_cnt.get_product_reviews(product_name)
    return jsonify(data)


@app.route('/product/image', methods=['POST'])
def product_img_get():
    content = request.json
    url = content['url']
    data, ret_code = product_cnt.get_product_image_url(url)

    return jsonify(data)


@app.route('/generate/data', methods=['POST'])
def generate_dataset():
    content = request.json

    data, retcode = generate_cnt(content)
    # data = dataset_generator.generate(content)
    if retcode == 200:
        return send_file(
            data,
            mimetype='application/zip',
            as_attachment=True,
            attachment_filename='data.zip'
        )
    else:
        abort(retcode, data['error'])


@app.route('/experiment/cluster', methods=['POST'])
def experiment_cluster():
    content = request.json
    print(content)

    data, retcode = experiment_cnt.cluster_similarity(content)

    if retcode == 200:
        return jsonify(data)
    else:
        abort(retcode, data['error'])
