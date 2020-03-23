from app import app, product_cnt, generate_cnt, data_cnt, experiment_cluster_cnt, review_cnt, user_cnt
from flask import jsonify, request, send_file, current_app
import jwt
from app.models import User
from datetime import datetime, timedelta
from functools import wraps


def token_required(f):
    @wraps(f)
    def _verify(*args, **kwargs):
        auth_headers = request.headers.get('Authorization', '').split()

        invalid_msg = {
            'message': 'Invalid token. Registeration and / or authentication required',
            'authenticated': False
        }
        expired_msg = {
            'message': 'Expired token. Reauthentication required.',
            'authenticated': False
        }

        if len(auth_headers) != 2:
            return jsonify(invalid_msg), 401

        try:
            token = auth_headers[1]
            data = jwt.decode(token, current_app.config['SECRET_KEY'])

            user = user_cnt.get_user(data['sub'])
            if not user:
                raise RuntimeError('User not found')
            return f(user, *args, **kwargs)
        except jwt.ExpiredSignatureError:
            return jsonify(expired_msg), 401 # 401 is Unauthorized HTTP status code
        except (jwt.InvalidTokenError, Exception) as e:
            print(e)
            return jsonify(invalid_msg), 401

    return _verify


@app.route('/')
@app.route('/index')
def index():
    return "Hello, World!"


@token_required
@app.route('/data/indexes_health', methods=['GET'])
def data_index_health():
    data, ret_code = data_cnt.get_indexes_health()
    return jsonify(data), ret_code


@token_required
@app.route('/data/breadcrumbs', methods=['GET'])
def data_breadcrumbs_full():
    data, ret_code = data_cnt.get_breadcrumbs()
    return jsonify([data]), ret_code


@token_required
@app.route('/product/', methods=['POST'])
def product_get():
    content = request.json
    data, ret_code = product_cnt.get_category_products(content)
    return jsonify(data), ret_code


@token_required
@app.route('/product/breadcrumbs', methods=['GET'])
def data_index_breadcrumbs():
    data, ret_code = product_cnt.get_breadcrumbs()
    return jsonify([data]), ret_code


@token_required
@app.route('/product/review', methods=['POST'])
def product_review_get():
    content = request.json
    print(content)
    data, ret_code = product_cnt.get_product_reviews(content)
    return jsonify(data), ret_code


@token_required
@app.route('/product/image', methods=['POST'])
def product_img_get():
    content = request.json
    url = content['url']
    data, ret_code = product_cnt.get_product_image_url(url)

    return jsonify(data), ret_code


@token_required
@app.route('/generate/data', methods=['POST'])
def generate_dataset():
    content = request.json

    data, ret_code = generate_cnt.generate_dataset(content)

    if ret_code == 200:
        return send_file(
            data,
            mimetype='application/zip',
            as_attachment=True,
            attachment_filename='data.zip'
        )
    else:
        return jsonify(data), ret_code


@token_required
@app.route('/experiment/review', methods=['POST'])
def experiment_review():
    content = request.json
    data, ret_code = review_cnt.get_review_experiment(content)

    return jsonify(data), ret_code


@token_required
@app.route('/experiment/sentence_pos_con', methods=['POST'])
def experiment_sentence_pos_con():
    content = request.json
    data, ret_code = review_cnt.get_sentence_polarity(content)

    return jsonify(data), ret_code


@token_required
@app.route('/experiment/text_rating', methods=['POST'])
def experiment_text_rating():
    content = request.json
    data, ret_code = review_cnt.get_text_rating(content)

    return jsonify(data), ret_code

@token_required
@app.route('/experiment/text_irrelevant', methods=['POST'])
def experiment_text_irrelevant():
    content = request.json
    data, ret_code = review_cnt.get_irrelevant(content)

    return jsonify(data), ret_code


@token_required
@app.route('/experiment/sentences', methods=['POST'])
def experiment_sentences():
    content = request.json
    print(content)
    data, retcode = experiment_cluster_cnt.get_experiment_sentences(content)
    return jsonify(data), retcode


@token_required
@app.route('/experiment/cluster', methods=['POST', 'GET', 'DELETE', 'PUT'])
def experiment_cluster():
    content = request.json
    print(content)
    if request.method == 'GET':
        data, ret_code = experiment_cluster_cnt.get_experiment()

    elif request.method == 'DELETE':
        data, ret_code = experiment_cluster_cnt.delete_experiment(content)

    elif request.method == 'PUT':
        data, ret_code = experiment_cluster_cnt.update_experiment_cluster_name(content)

    else:
        data, ret_code = experiment_cluster_cnt.cluster_similarity(content)

    return jsonify(data), ret_code


@token_required
@app.route('/experiment/cluster_merge', methods=['POST'])
def experiment_cluster_merge():
    content = request.json
    print(content)
    data, ret_code = experiment_cluster_cnt.cluster_merge(content)
    return jsonify(data), ret_code


@token_required
@app.route('/experiment/cluster/topic', methods=['PUT'])
def experiment_cluster_topic():
    content = request.json
    print(content)

    data, ret_code = experiment_cluster_cnt.update_experiment_cluster_topics(content)

    return jsonify(data), ret_code


@token_required
@app.route('/experiment/cluster_peek', methods=['POST'])
def experiment_cluster_peek():
    content = request.json

    data, retcode = experiment_cluster_cnt.peek_sentences(content)

    return jsonify(data), retcode


@app.route('/login/', methods=('POST',))
def login():
    data = request.get_json()
    user = user_cnt.authenticate(**data)

    if not user:
        return jsonify({ 'error': 'Invalid credentials', 'authenticated': False,
                         'error_code': 401}), 401

    token = jwt.encode({
        'sub': user.name,
        'iat':datetime.utcnow(),
        'exp': datetime.utcnow() + timedelta(minutes=30)},
        current_app.config['SECRET_KEY'])
    return jsonify({ 'token': token.decode('UTF-8'),
                     'user': user.to_dict()})


@app.route('/register/', methods=('POST',))
def register():
    data = request.get_json()
    user = user_cnt.create_user(data)
    return jsonify(user), 201
