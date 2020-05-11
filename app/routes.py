from app import app, product_cnt, generate_cnt, data_cnt, experiment_cluster_cnt, review_cnt, user_cnt
from flask import request, send_file, current_app
from flask_restx import Resource, fields, marshal, marshal_with
import jwt
from datetime import datetime, timedelta
from functools import wraps
from .models import User

# name spaces
data_ns = app.namespace('data', description='Handles non essential data')
product_ns = app.namespace('product', description='Handles product/shop and review extraction from elastic')
generate_ns = app.namespace('generate', description='Exporting of data from elasticsearch with various options')
experiment_ns = app.namespace('experiment', description='Clustering of similar sentences with given embedding method')
login_ns = app.namespace('login', description='User authentication')
register_ns = app.namespace('register', description='User authentication')

actualization_statistic_model = app.model('actualization_statistic_model',
                                          {
                                              'category': fields.String(required=True,
                                                                        description="Product category")
                                          })
product_model = app.model('product_model',
                          {
                              'category_name': fields.String(required=True,
                                                             description="Product category")
                          })
product_review_model = app.model('product_review_model',
                                 {
                                     'name': fields.String(required=True,
                                                           description="Name of the product or shop"),
                                     'domain': fields.String(required=True,
                                                             description="Domain of the product or shop")
                                 })
product_url_model = app.model('product_url_model',
                              {
                                  'url': fields.String(required=True,
                                                       description="Url of product")
                              })

generate_data_model = app.model('generate_data_model',
                                {
                                    'model_type': fields.String(required=True,
                                                                description="Type of output model"),
                                    'categories': fields.List(required=True,
                                                              description="Product categories, from which the data "
                                                                          "will be generated",
                                                              cls_or_instance=fields.String),
                                    'sentence_type': fields.String(required=True,
                                                                   description="Type of sentence"),
                                    'task_type': fields.String(required=True,
                                                               description="Type of generation task"),
                                    'equal': fields.Boolean(required=True,
                                                            description="Equal dataset for all classes"),
                                    'sentence_min_len': fields.String(required=True,
                                                                      description="Sentence minimum length"),
                                    'sentence_max_len': fields.String(required=True,
                                                                      description="Sentence maximum length"),
                                })

experiment_review_model = app.model('experiment_review_model',
                                    {
                                        '_id': fields.String(required=True,
                                                             description="ID of review"),
                                        'category': fields.String(required=True,
                                                                  description="Subcategory of review")
                                    })

experiment_demo_pos_con_model = app.model('experiment_demo_pos_con_model',
                                          {
                                              'model_type': fields.String(required=True,
                                                                          description="Type of the model"),
                                              'sentence': fields.String(required=True,
                                                                        description="Sentence to be evaluated")
                                          })

experiment_demo_model = app.model('experiment_demo_model',
                                  {
                                      'sentence': fields.String(required=True,
                                                                description="Sentence to be evaluated")
                                  })

experiment_sentence_model = app.model('experiment_sentence_model',
                                      {
                                          'category': fields.String(required=True,
                                                                    description="Category or products name")
                                      })

experiment_model = app.model('experiment_cluster_model',
                             {
                                 'category': fields.String(required=True,
                                                           description="Category or products name"),
                                 'embedding_method': fields.String(required=True,
                                                                   description="Type of calculating sentence embeddings"),
                                 'embedding_model': fields.String(required=True,
                                                                  description="Model for word embeddings"),
                                 'cluster_method': fields.String(required=True,
                                                                 description="Name of clustering algorithm"),
                                 'clusters_pos_count': fields.Integer(required=True,
                                                                      description="Count of positive clusters"),
                                 'clusters_con_count': fields.Integer(required=True,
                                                                      description="Count of negative clusters"),
                                 'topics_per_cluster': fields.Integer(required=True,
                                                                      description="Count of topics per cluster")
                             })

experiment_delete_model = app.model('experiment_delete_model',
                                    {
                                        'experiment_id': fields.String(required=True,
                                                                       description="ID of experiment")
                                    })

experiment_update_model = app.model('experiment_update_model',
                                    {
                                        'cluster_id': fields.String(required=True,
                                                                    description="ID of experiments cluster"),
                                        'cluster_name': fields.String(required=True,
                                                                      description="New name for cluster")
                                    })

experiment_cluster_merge_model = app.model('experiment_cluster_merge_model',
                                           {
                                               'cluster_from': fields.String(required=True,
                                                                             description="ID of experiments cluster"),
                                               'cluster_to': fields.String(required=True,
                                                                           description="New name for cluster")
                                           })

experiment_cluster_model = app.model('experiment_cluster_model',
                                     {
                                         'experiment_id': fields.String(required=True,
                                                                        description="ID of experiment"),
                                         'type': fields.String(required=True,
                                                               description="Type of cluster"),
                                         'cluster_name': fields.String(required=True,
                                                                       description="The name of the cluster"),
                                         'cluster_number': fields.Integer(required=True,
                                                                          description="Number of cluster")
                                     })

experiment_update_sentence_model = app.model('experiment_update_sentence_model',
                                             {
                                                 'cluster_id': fields.String(required=True,
                                                                             description="ID of experiments cluster"),
                                                 'sentence_id': fields.String(required=True,
                                                                              description="ID of sentence"),
                                                 'topic_number': fields.String(required=True,
                                                                               description="Number of topic"),
                                                 'topic_id': fields.String(required=True,
                                                                           description="ID of topic")
                                             })

experiment_cluster_topic_model = app.model('experiment_cluster_topic_model',
                                           {
                                               'experiment_id': fields.String(required=True,
                                                                              description="ID of experiment"),
                                               'cluster_number': fields.String(required=True,
                                                                               description="ID of cluster"),
                                               'topics': fields.List(required=True,
                                                                     description="List of topics to be appended",
                                                                     cls_or_instance=fields.String)

                                           })

experiment_topic_update_model = app.model('experiment_topic_update_model',
                                          {
                                              'topic_id': fields.String(required=True,
                                                                        description="ID of topic"),
                                              'topic_name': fields.String(required=True,
                                                                          description="Name of topic")

                                          })

experiment_topic_merge_model = app.model('experiment_topic_merge_model',
                                         {
                                             'topic_from_id': fields.String(required=True,
                                                                            description="ID of topic that will be merged"),
                                             'cluster_to_id': fields.String(required=True,
                                                                            description="Id of destination cluster"),
                                             'topic_to_number': fields.String(required=True,
                                                                              description="Number of destination topic"),
                                             'topic_to_id': fields.String(required=True,
                                                                          description="ID of destination topic")

                                         })

experiment_peek_model = app.model('experiment_peek_model',
                                  {
                                      'category': fields.String(required=True,
                                                                description="The name of category or product")
                                  })

login_user_model = app.model('login_user_model',
                             {
                                 'name': fields.String(required=True,
                                                       description="The name of user"),
                                 'password': fields.String(required=True,
                                                           description="The hash of password of user")
                             })

register_user_model = app.model('register_user_model',
                                {
                                    'name': fields.String(required=True,
                                                          description="The name of user"),
                                    'password': fields.String(required=True,
                                                              description="The hash of password of user"),
                                    'level': fields.String(required=True,
                                                           description="The rights level")
                                })


def token_required(f):
    """
    Authentication wrapper for every endpoint, expects token in header.
    :param f: end-point handler
    """

    @wraps(f)
    def _verify(*args, **kwargs):
        token = None

        invalid_msg = {
            'error': 'Invalid token. Registration and / or authentication required',
            'authenticated': False,
            'error_code': 401
        }
        expired_msg = {
            'error': 'Expired token. Re-authentication required.',
            'authenticated': False,
            'error_code': 401
        }
        if 'Authorization' in request.headers:
            token = request.headers['Authorization']

        if not token:
            return invalid_msg, 401

        try:
            data = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])

            user = user_cnt.get_user(data['sub'])

            if not user:
                raise RuntimeError('User not found')
            return f(*args, **kwargs)
        except jwt.ExpiredSignatureError:
            return expired_msg, 401
        except (jwt.InvalidTokenError, Exception) as e:
            print(e)
            return invalid_msg, 401

    return _verify


@data_ns.route('/indexes_health')
class IndexesHealth(Resource):
    @token_required
    def get(self):
        """
        Get health of used indexes from elasticsearch api.
        """

        data, ret_code = data_cnt.get_indexes_health()
        return data, ret_code


@data_ns.route('/breadcrumbs')
class BreadcrumbsFull(Resource):
    @token_required
    def get(self):
        """
        Get full breadcrumb path of all products.
        """
        data, ret_code = data_cnt.get_breadcrumbs()
        return [data], ret_code


@data_ns.route('/actualization_statistics')
class ActualizationStatistics(Resource):
    @app.expect(actualization_statistic_model)
    @token_required
    def post(self):
        """
        Get statistics about regular review crawl.
        """
        category = request.json['category']
        data, ret_code = data_cnt.get_actualization_statistics(category)
        return data, ret_code


@product_ns.route('/')
class Product(Resource):
    @app.expect(product_model)
    @token_required
    def post(self):
        """
        Get list of products from products domain subcategory or shop.
        """
        category = request.json['category_name']
        data, ret_code = product_cnt.get_category_products(category)
        return data, ret_code


@product_ns.route('/breadcrumbs')
class ProductBreadcrumbs(Resource):
    @token_required
    def get(self):
        """
        Get simplified breadcrumbs of domain and subcategory for products as a tree.
        """
        data, ret_code = product_cnt.get_breadcrumbs()
        return [data], ret_code


@product_ns.route('/review')
class ProductReviews(Resource):
    @app.expect(product_review_model)
    @token_required
    def post(self):
        """
        Return list of product reviews.
        """
        content = request.json
        data, ret_code = product_cnt.get_product_reviews(content)
        return data, ret_code


@product_ns.route('/image')
class ProductImg(Resource):
    @app.expect(product_url_model)
    @token_required
    def post(self):
        """
        Get url of products picture from heureka site.
        """
        content = request.json
        url = content['url']
        data, ret_code = product_cnt.get_product_image_url(url)

        return data, ret_code


@product_ns.route('/statistics')
class ProductStatistics(Resource):
    @app.expect(product_review_model)
    @token_required
    def post(self):
        """
        Get statistics of product like AVG rating/recommendations, graph of review count during time.
        """
        content = request.json
        data, ret_code = product_cnt.get_statistics(content)

        return data, ret_code


@generate_ns.route('/data')
class GenerateDataset(Resource):
    @app.expect(generate_data_model)
    @token_required
    def post(self):
        """
        Export dataset according to given arguments, returns a zip file.
        """
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
            return data, ret_code


@experiment_ns.route('/review')
class ExperimentReview(Resource):
    @app.expect(experiment_review_model)
    @token_required
    def post(self):
        """
        Evaluate review by all available bert models (bipolar, review rating) and mark salient words.
        """
        content = request.json
        data, ret_code = review_cnt.get_review_experiment(content)

        return data, ret_code


@experiment_ns.route('/sentence_pos_con')
class ExperimentSentencePosCon(Resource):
    @app.expect(experiment_demo_pos_con_model)
    @token_required
    def post(self):
        """
        Evaluate sentence or text by given bipolar bert model.
        """
        content = request.json
        data, ret_code = review_cnt.get_sentence_polarity(content)

        return data, ret_code


@experiment_ns.route('/text_rating')
class ExperimentTextRating(Resource):
    @app.expect(experiment_demo_model)
    @token_required
    def post(self):
        """
        Evaluate sentence/text by regression bert model.
        """
        content = request.json
        data, ret_code = review_cnt.get_text_rating(content)

        return data, ret_code


# @app.route('/experiment/text_irrelevant', methods=['POST'])
@experiment_ns.route('/text_irrelevant')
class ExperimentTextIrrelevant(Resource):
    @app.expect(experiment_demo_model)
    @token_required
    def post(self):
        """
        Evaluate sentence/text by irrelevant SVM model with uSIF weighting scheme as sentence embeddings.
        """
        content = request.json
        data, ret_code = review_cnt.get_irrelevant(content)

        return data, ret_code


@experiment_ns.route('/sentences')
class ExperimentSentences(Resource):
    @app.expect(experiment_sentence_model)
    @token_required
    def post(self):
        """
        Return representation of clustering algorithm with clusters, topics and sentences.
        """
        content = request.json
        data, ret_code = experiment_cluster_cnt.get_experiment_sentences(content)
        return data, ret_code


@experiment_ns.route('/')
class Experiment(Resource):

    @token_required
    def get(self):
        """
        Get list of all clustering experiments.
        """
        data, ret_code = experiment_cluster_cnt.get_experiment()
        return data, ret_code

    @app.expect(experiment_model)
    @token_required
    def post(self):
        """
        Perform clustering experiment according to given data.
        """
        content = request.json
        data, ret_code = experiment_cluster_cnt.cluster_similarity(content)

        return data, ret_code

    @app.expect(experiment_delete_model)
    @token_required
    def delete(self):
        """
        Remove data about experiment.
        """
        content = request.json
        data, ret_code = experiment_cluster_cnt.delete_experiment(content)
        return data, ret_code


@experiment_ns.route('/cluster_merge')
class ExperimentClusterMerge(Resource):
    @app.expect(experiment_cluster_merge_model)
    @token_required
    def post(self):
        """
        Merge one cluster "from" to cluster "to".
        """
        content = request.json
        data, ret_code = experiment_cluster_cnt.cluster_merge(content)
        return data, ret_code


@experiment_ns.route('/cluster')
class ExperimentCluster(Resource):
    @app.expect(experiment_cluster_model)
    @token_required
    def post(self):
        """
        Create new cluster in experiment.
        """
        content = request.json
        data, ret_code = experiment_cluster_cnt.create_cluster(content)
        return data, ret_code

    @app.expect(experiment_update_model)
    @token_required
    def put(self):
        """
        Update cluster name in experiment.
        """
        content = request.json
        data, ret_code = experiment_cluster_cnt.update_experiment_cluster_name(content)
        return data, ret_code


@experiment_ns.route('/sentence')
class ExperimentSentence(Resource):
    @app.expect(experiment_update_sentence_model)
    @token_required
    def put(self):
        """
        Transfer sentence to another cluster or topic within experiment.
        """
        content = request.json
        data, ret_code = experiment_cluster_cnt.update_sentence(content)
        return data, ret_code


@experiment_ns.route('/experiment_cluster_topics')
class ExperimentClusterTopics(Resource):
    @app.expect(experiment_cluster_topic_model)
    @token_required
    def put(self):
        """
        Append new topics to cluster.
        """
        content = request.json
        data, ret_code = experiment_cluster_cnt.append_topics(content)
        return data, ret_code


@experiment_ns.route('/topic')
class ExperimentTopic(Resource):
    @app.expect(experiment_topic_update_model)
    @token_required
    def put(self):
        """
        Update the name of the topic.
        """
        content = request.json
        data, ret_code = experiment_cluster_cnt.update_topic_name(content)

        return data, ret_code

    @app.expect(experiment_topic_merge_model)
    @token_required
    def post(self):
        """
        Merge topic to another clusters topic with its sentences.
        """
        content = request.json
        data, ret_code = experiment_cluster_cnt.merge_topic(content)

        return data, ret_code


@experiment_ns.route('/cluster_peek')
class ExperimentClusterPeek(Resource):
    @app.expect(experiment_peek_model)
    @token_required
    def post(self):
        """
        Peek sentences count, that will be the subject of the experiment.
        """
        content = request.json
        data, ret_code = experiment_cluster_cnt.peek_sentences(content)

        return data, ret_code


@login_ns.route('/')
class Login(Resource):
    @app.expect(login_user_model)
    def post(self):
        """
        User login to review analysis.
        """
        data = request.json
        user = user_cnt.authenticate(**data)

        if not user:
            return {'error': 'Invalid credentials', 'authenticated': False,
                    'error_code': 401}, 401

        token = jwt.encode({
            'sub': user.name,
            'iat': datetime.utcnow(),
            'exp': datetime.utcnow() + timedelta(minutes=90)},
            current_app.config['SECRET_KEY'],
            algorithm='HS256')
        return {'token': token.decode('UTF-8'),
                'user': user.to_dict()}


@register_ns.route('/')
class Register(Resource):
    @app.expect(register_user_model)
    def post(self):
        """
        Register new user to review analysis.
        """
        data = request.json
        user = user_cnt.create_user(data)
        return user, 201
