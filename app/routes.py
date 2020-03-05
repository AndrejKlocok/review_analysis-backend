from app import app, product_cnt, generate_cnt, data_cnt, experiment_cnt
from flask import jsonify, request, send_file, abort


@app.route('/')
@app.route('/index')
def index():
    return "Hello, World!"


@app.route('/data/indexes_health', methods=['GET'])
def data_index_health():
    data, retcode = data_cnt.get_indexes_health()
    return jsonify(data), retcode


@app.route('/data/breadcrumbs', methods=['GET'])
def data_breadcrumbs_full():
    data, retcode = data_cnt.get_breadcrumbs()
    return jsonify([data]), retcode


@app.route('/product/', methods=['POST'])
def product_get():
    content = request.json
    category = content['category_name']
    data, retcode = product_cnt.get_category_products(category)
    return jsonify(data), retcode


@app.route('/product/breadcrumbs', methods=['GET'])
def data_index_breadcrumbs():
    data, retcode = product_cnt.get_breadcrumbs()
    return jsonify([data]), retcode


@app.route('/product/review', methods=['POST'])
def product_review_get():
    content = request.json
    product_name = content['product_name']
    data, retcode = product_cnt.get_product_reviews(product_name)
    return jsonify(data), retcode


@app.route('/product/image', methods=['POST'])
def product_img_get():
    content = request.json
    url = content['url']
    data, ret_code = product_cnt.get_product_image_url(url)

    return jsonify(data), ret_code


@app.route('/generate/data', methods=['POST'])
def generate_dataset():
    content = request.json

    data, ret_code = generate_cnt.generate_dataset(content)
    # data = dataset_generator.generate(content)
    if ret_code == 200:
        return send_file(
            data,
            mimetype='application/zip',
            as_attachment=True,
            attachment_filename='data.zip'
        )
    else:
        return jsonify(data), ret_code


@app.route('/experiment/', methods=['GET', 'DELETE'])
def experiment():
    if request.method == 'GET':
        data, retcode = experiment_cnt.get_experiment()
    else:  # request.method == 'POST':
        content = request.json
        print(content)
        data, retcode = experiment_cnt.delete_experiment(content)
    return jsonify(data), retcode


@app.route('/experiment/sentences', methods=['POST'])
def experiment_sentences():
    content = request.json
    print(content)
    data, retcode = experiment_cnt.get_experiment_sentences(content)
    return jsonify(data), retcode


@app.route('/experiment/cluster', methods=['POST'])
def experiment_cluster():
    content = request.json
    print(content)

    data, retcode = experiment_cnt.cluster_similarity(content)

    return jsonify(data), retcode


@app.route('/experiment/cluster_peek', methods=['POST'])
def experiment_cluster_peek():
    content = request.json

    data, retcode = experiment_cnt.peek_sentences(content)

    return jsonify(data), retcode
