import sys, time, warnings
from collections import Counter
from datetime import datetime, timezone

from review_analysis.utils.elastic_connector import Connector
from review_analysis.utils.morpho_tagger import MorphoTagger
from review_analysis.clasification.fasttext_model import FastTextModel, EmbeddingType, ClusterMethod, EmbeddingModel
from review_analysis.clasification.LDA_model import LDA_model

warnings.filterwarnings("ignore", module="matplotlib")


class ExperimentClusterController:
    """
    Controller class handles clustering related task, provides CRUD API for clusters, topics, sentences.
    """
    def __init__(self, con: Connector):
        self.connector = con
        self.tagger = MorphoTagger()
        self.tagger.load_tagger()
        self.fastTextModel = FastTextModel()

    def __get_sentences(self, rev: dict, sen_type: str):
        """
        Perform pos tagging on sentence list from review rev, specified by type of polarity sen_type.
        :param rev: review dictionary
        :param sen_type: type of sentences of review pros/cons
        :return: list of sentences dictionary: List[Dict[str, Union[list, int, str]]]
        """
        sentences = []
        for index, sentence in enumerate(rev[sen_type]):
            sentence_pos = self.tagger.pos_tagging(sentence, False)
            if not sentence_pos:
                continue
            # multi sentence
            if len(sentence_pos) > 1:
                pass
            else:
                # two or more words
                if len(sentence_pos[0]) > 1:
                    sentence_list = [wb.lemma for wb in sentence_pos[0]]
                    sentences.append({
                        'review_id': rev['_id'],
                        'sentence': sentence,
                        'sentence_pos': sentence_list,
                        'sentence_index': index,
                        'sentence_type': sen_type,
                        'product_name': rev['product_name'],
                        'category_name': rev['category']
                    })

        return sentences

    def __get_embedding_type(self, config: dict):
        """
        Convert embedding type string representation in config dict to enum value.
        :param config: configuration dict
        :return: enum: EmbeddingType
        """
        if config['embedding_method'] == 'fse_dist':
            embedding_type = EmbeddingType.distance_matrix
        elif config['embedding_method'] == 'fse_sim':
            embedding_type = EmbeddingType.similarity_matrix
        elif config['embedding_method'] == 'fse_vec':
            embedding_type = EmbeddingType.sentence_vectors
        else:
            raise KeyError('embedding_method')

        return embedding_type

    def __get_embedding_model(self, config: dict):
        """
        Convert embedding model string representation in config dict to enum value.
        :param config: configuration dict
        :return: enum:  EmbeddingModel
        """
        if config['embedding_model'] == 'FastText_pretrained':
            embedding_type = EmbeddingModel.fasttext_pretrained
        elif config['embedding_model'] == 'FastText_300d':
            embedding_type = EmbeddingModel.fasttext_300d
        else:
            raise KeyError('embedding_model')

        return embedding_type

    def __get_cluster_method(self, config: dict):
        """
        Convert clustering method string representation in config dict to enum value.
        :param config: configuration dict
        :return: enum: ClusterMethod
        """
        if config['cluster_method'] == 'kmeans':
            cluster = ClusterMethod.kmeans
        else:
            raise KeyError('cluster_method')

        return cluster

    def __cluster(self, sentences: list, clusters_count: int, topics_per_cluster: int,
                  embedding_type: EmbeddingType, cluster_method: ClusterMethod,
                  experiment_id: str, embedding_model: EmbeddingModel, sentence_type: str):
        """
        Perform clustering of sentences with given arguments.
        :param sentences: list of lemma sentences
        :param clusters_count: count of clusters
        :param topics_per_cluster: count of topics per cluster
        :param embedding_type:  type of embedding for sentences (text)
        :param cluster_method: type of clustering method
        :param experiment_id: ID of experiment
        :param embedding_model: type of embedding model, from which embedding will be generated
        :param sentence_type: type of sentences pos/con
        :return: touple of dictionary which represents list of clusters and salient words:
        Tuple[Dict[str, Union[int, list]], list]
        """
        cluster = {
            'sentences_count': len(sentences),
            'clusters': [],
        }
        # assign lemmas of sentence to each sentence
        sentences_pos = [sentence['sentence_pos'] for sentence in sentences]
        # perform clustering
        labels = self.fastTextModel.cluster_similarity(sentences_pos, embedding_model, embedding=embedding_type,
                                                       cluster=cluster_method, cluster_cnt=clusters_count)
        #import math, random
        #labels = [math.floor(random.uniform(0, 7)) for _ in sentences_pos]
        cnt = Counter(labels)

        # init clusters representation with meta data
        clusters = {}
        label_to_cluster_id = {}
        for key, value in cnt.items():
            cluster_meta = {
                'cluster_number': key,
                'cluster_sentences_count': value,
                'sentences': [],
                'topics': [],
                'experiment_id': experiment_id,
                'type': sentence_type
            }
            cluster_id = self.save_cluster_meta(cluster_meta)
            if not cluster_id:
                raise Exception('Cluster not saved')

            cluster_meta['cluster_id'] = cluster_id
            clusters[key] = cluster_meta
            label_to_cluster_id[key] = cluster_id

        # assign experiment data to each sentence
        for index, label in enumerate(labels):
            sentences[index]['cluster_number'] = label_to_cluster_id[label]
            sentences[index]['topic_number'] = 0
            sentences[index]['topic_id'] = ''
            sentences[index]['experiment_id'] = experiment_id
            clusters[label]['sentences'].append(sentences[index])

        # perform inner cluster information retrieval with LDA, get topics per cluster and salient words
        lda = LDA_model(topics_per_cluster)
        salient_words = lda.load_sentences_from_api(clusters, self.tagger)

        # assign topic information to each sentence
        for _, value in clusters.items():
            topic_to_id = {}
            cluster['clusters'].append(value)
            if not value['topics']:
                value['topics'] = ['topic_numb_0']

            # check for duplicate topic names
            if len(list(set(value['topics']))) != len(value['topics']):
                i = 0
                for topic in value['topics']:
                    topic = topic + '_' + str(i)

            # index topic
            for index, topic in enumerate(value['topics']):
                d = {
                    "experiment_id": experiment_id,
                    "cluster_number": value['cluster_id'],
                    "name": topic,
                    "topic_number": index,
                }
                topic_id = self.save_topic(d)
                if not topic_id:
                    raise Exception('Did not saved: {}'.format(str(d)))
                topic_to_id[index] = topic_id

            # update sentence meta data
            for sentence in value['sentences']:
                sentence['topic_id'] = topic_to_id[sentence['topic_number']]
                if not self.save_sentence(sentence):
                    print('Did not saved: {}'.format(sentence['sentence']), file=sys.stderr)

        self.connector.es.indices.refresh(index="experiment_sentence")
        self.connector.es.indices.refresh(index="experiment_topic")
        self.connector.es.indices.refresh(index="experiment_cluster")
        return cluster, salient_words

    def __get_reviews_sentences(self, category):
        """
        Get positive and negative sentences from domain category or product/shop.
        :param category: name of product/shop/category
        :return: touple of sentences: Tuple[list, list]
        """
        sentences_pro = []
        sentences_con = []

        reviews, ret = self.connector.get_reviews_from_category(category)

        # check if it is not product
        if ret == 404:
            reviews, ret = self.connector.get_reviews_from_product(category)

        # create sentences pos cons
        for review in reviews:
            sentences_pro += self.__get_sentences(review, 'pros')
            sentences_con += self.__get_sentences(review, 'cons')

        return sentences_pro, sentences_con

    def save_experiment(self, config: dict):
        """
        Index experiment into elasticsearch.
        :param config: experiment as dict
        :return: id of experiment: Optional[Any]
        """
        experiment = {
            "topics_per_cluster": config['topics_per_cluster'],
            "clusters_pos": [],
            "clusters_con": [],
            "cluster_method": config['cluster_method'],
            "embedding_method": config['embedding_method'],
            "embedding_model": config['embedding_model'],
            "category": config['category'],
            "date": datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S'),
        }
        res = self.connector.index('experiment', experiment)
        if res['result'] == 'created':
            return res['_id']
        return None

    def save_sentence(self, sentence: dict):
        """
        Index sentence into elasticsearch.
        :param sentence: sentence as dict
        :return: id of sentence: Optional[Any]
        """
        experiment_sentence = {
            "review_id": sentence['review_id'],
            "experiment_id": sentence['experiment_id'],
            "topic_number": sentence['topic_number'],
            "topic_id": sentence['topic_id'],
            "cluster_number": sentence['cluster_number'],
            "product_name": sentence['product_name'],
            "category_name": sentence['category_name'],
            "sentence": sentence['sentence'],
            "sentence_index": sentence['sentence_index'],
            "sentence_pos": sentence['sentence_pos'],
            "sentence_type": sentence['sentence_type'],
        }
        res = self.connector.index(index='experiment_sentence', doc=experiment_sentence)
        if res['result'] == 'created':
            return True
        return False

    def save_topic(self, topic_d: dict):
        """
        Index sentence into elasticsearch.
        :param topic_d: topic as dict
        :return: id of topic: Optional[Any]
        """
        experiment_topic = {
            "experiment_id": topic_d['experiment_id'],
            "cluster_number": topic_d['cluster_number'],
            "name": topic_d['name'],
            "topic_number": topic_d["topic_number"],
        }
        res = self.connector.index(index='experiment_topic', doc=experiment_topic)
        if res['result'] == 'created':
            return res['_id']
        return None

    def save_cluster_meta(self, cluster_d: dict):
        """
        Index cluster into elasticsearch.
        :param cluster_d: cluster as dict
        :return: id of cluster: Optional[Any]
        """
        cluster = {
            'experiment_id': cluster_d['experiment_id'],
            'type': cluster_d['type'],
            'cluster_name': 'cluster_' + str(cluster_d['cluster_number']),
            'cluster_number': cluster_d['cluster_number'],
        }

        res = self.connector.index(index='experiment_cluster', doc=cluster)

        if res['result'] == 'created':
            return res['_id']
        return None

    def get_experiment(self):
        """
        Get All experiments.
        :return: Union[Tuple[Any, Any], Tuple[Dict[str, Union[str, int]], int]]

        """
        try:
            data, ret_code = self.connector.get_experiments()

            return data, ret_code

        except Exception as e:
            print('ExperimentController-get_experiment: {}'.format(str(e)), file=sys.stderr)
            return {'error': str(e), 'error_code': 500}, 500

    def get_experiment_sentences(self, content: dict):
        """
        Get clustering  data for given category/shop/product.
        :param content: dictionary with category/shop/product name
        :return: experiment data: Union[Tuple[Dict[str, Dict[str, Any]], Any], Tuple[Dict[str, Union[str, int]], int]]
        """
        try:
            # if content['experiment_id']:
            data, ret_code = self.connector.get_experiments_by_category(content['category'])

            # 400 error
            if not data or ret_code != 200:
                # check for category experiment in case of product
                product = self.connector.get_product_by_name(content['category'])
                if product:
                    data, ret_code = self.connector.get_experiments_by_category(product['category'], content['category'])
                else:
                    raise ValueError('This category does not have any experiments')

            if len(data) > 1:
                raise Exception('More experiments for category')

            data = data[0]

            salient = list(set(data['sal_pos'] + data['sal_con']))

            output_d = {
                '_id': data['_id'],
                'pos': {
                    'sentences_count': data['pos_sentences'],
                    'clusters': data['clusters_pos'],
                    'sal_pos': data['sal_pos'],
                },
                'con': {
                    'sentences_count': data['con_sentences'],
                    'clusters': data['clusters_con'],
                    'sal_con': data['sal_con'],
                },
                'sal_pos': data['sal_pos'],
                'sal_con': data['sal_con'],
            }

            return output_d, ret_code

        except ValueError as e:
            print('ExperimentController-get_experiment_sentences: {}'.format(str(e)), file=sys.stderr)
            return {'error': str(e), 'error_code': 400}, 400

        except Exception as e:
            print('ExperimentController-get_experiment_sentences: {}'.format(str(e)), file=sys.stderr)
            return {'error': str(e), 'error_code': 500}, 500

    def delete_experiment(self, content: dict):
        """
        Remove experiment data, its clusters, topics and sentences from elasticsearch.
        :param content:
        :return: experiment list: Union[Tuple[Any, Any], Tuple[Dict[str, str], Any], Tuple[Dict[str, Union[str, int]], int]]
        """
        try:
            data, ret_code = self.connector.delete_experiment(content['experiment_id'])

            if ret_code == 200:
                data, ret_code = self.connector.get_experiments()
                return data, ret_code
            else:
                data = {
                    'error': 'Data not found',
                    'ret_code': ret_code,
                }
                return data, ret_code

        except Exception as e:
            print('ExperimentController-delete_experiment: {}'.format(str(e)), file=sys.stderr)
            return {'error': str(e), 'error_code': 500}, 500

    def update_experiment_cluster_name(self, content: dict):
        """
        Update experiments cluster name in elasticsearch.
        :param content:
        :return: elastic update dictionary
        """
        try:

            data, ret_code = self.connector.update_experiment_cluster_name(
                content['cluster_id'], content['cluster_name'])

            if ret_code == 200:
                return data, ret_code
            else:
                data = {
                    'error': 'Data not found',
                    'ret_code': ret_code,
                }
                return data, ret_code

        except Exception as e:
            print('ExperimentController-update_experiment_cluster_name: {}'.format(str(e)), file=sys.stderr)
            return {'error': str(e), 'error_code': 500}, 500

    def update_topic_name(self, content: dict):
        """
        Update the name of the topic.
        :param content:
        :return:
        """
        try:

            data, ret_code = self.connector.update_experiment_cluster_topic(
                content['topic_id'], content['topic_name'])

            if ret_code == 200:
                return data, ret_code
            else:
                data = {
                    'error': 'Data not found',
                    'ret_code': ret_code,
                }
                return data, ret_code

        except Exception as e:
            print('ExperimentController-update_topic_name: {}'.format(str(e)), file=sys.stderr)
            return {'error': str(e), 'error_code': 500}, 500

    def peek_sentences(self, config: dict):
        """
        Get informations about the count of pos/con sentences for clustering experiment.
        :param config:
        :return: sentences_count dictionary, return code
        """
        data = {}
        ret_code = 200
        try:
            if not config['category']:
                return None, 500
            #    raise WrongProperty('Empty categories')

            # create sentences pos cons
            sentences_pro, sentences_con = self.__get_reviews_sentences(config['category'])
            data['pos'] = {
                'sentences_count': len(sentences_pro)
            }
            data['con'] = {
                'sentences_count': len(sentences_con)
            }

            return data, ret_code

        except Exception as e:
            print('ExperimentController-peek_sentences: {}'.format(str(e)), file=sys.stderr)
            return {'error': str(e), 'error_code': 500}, 500

    def cluster_similarity(self, config: dict):
        """
        Perform text clustering according to configuration in config dictionary.
        :param config:
        :return: clustering data dictionary, return code
        """
        start = time.time()
        data = {}
        try:
            embedding_type = self.__get_embedding_type(config)
            cluster_method = self.__get_cluster_method(config)
            embedding_model = self.__get_embedding_model(config)

            if not config['category']:
                # raise WrongProperty('Empty category')
                raise KeyError('category not found')

            d_existing, r_c = self.connector.get_experiments_by_category(config['category'])
            if d_existing or r_c == 200:
                raise KeyError('Experiment already exists')

            # create sentences pos cons
            sentences_pro, sentences_con = self.__get_reviews_sentences(config['category'])

            experiment_id = self.save_experiment(config)
            if not experiment_id:
                raise Exception('Experiment was not saved')

            data['pos'], salient_pos = self.__cluster(sentences_pro, config['clusters_pos_count'],
                                                      config['topics_per_cluster'], embedding_type,
                                                      cluster_method, experiment_id, embedding_model,
                                                      'pos')
            data['con'], salient_con = self.__cluster(sentences_con, config['clusters_con_count'],
                                                      config['topics_per_cluster'], embedding_type,
                                                      cluster_method, experiment_id, embedding_model,
                                                      'con')

            res, ret_code = self.connector.update_experiment(
                experiment_id, salient_pos, salient_con,
            )
            if res['result'] != 'updated':
                raise Exception('Update of salient words failed')

            print(time.time() - start)
            return data, ret_code

        except KeyError as e:
            print('ExperimentController-cluster_similarity: {}'.format(str(e)), file=sys.stderr)
            return {'error': str(e), 'error_code': 400}, 400

        except Exception as e:
            print('ExperimentController-cluster_similarity: {}'.format(str(e)), file=sys.stderr)
            return {'error': str(e), 'error_code': 500}, 500

    def cluster_merge(self, config: dict):
        """
        Merge experiment cluster with its topics and sentences to another cluster.
        :param config:
        :return:
        """
        try:
            data, ret_code = self.connector.merge_experiment_cluster(config['cluster_from'], config['cluster_to'])
            return data, ret_code

        except Exception as e:
            print('ExperimentController-cluster_merge: {}'.format(str(e)), file=sys.stderr)
            return {'error': str(e), 'error_code': 500}, 500

    def update_sentence(self, config: dict):
        """
        Transfer sentence into another cluster or topic according to config dictionary.
        :param config:
        :return:
        """
        try:
            data, ret_code = self.connector.update_experiment_cluster_sentence(
                config['cluster_id'], config['sentence_id'],
                config['topic_number'], config['topic_id'])
            return data, ret_code

        except Exception as e:
            print('ExperimentController-sentence_change: {}'.format(str(e)), file=sys.stderr)
            return {'error': str(e), 'error_code': 500}, 500

    def create_cluster(self, config: dict):
        """
        Create empty cluster in experiment according to config dictionary.
        :param config:
        :return: dictionary with id of cluster, return code
        """
        try:
            cluster = {
                'experiment_id': config['experiment_id'],
                'type': config['type'],
                'cluster_name': config['cluster_name'],
                'cluster_number': config['cluster_number'],
            }

            res_cluster = self.connector.index(index='experiment_cluster', doc=cluster)
            if res_cluster['result'] != 'created':
                raise Exception('Cluster was not created')

            for index, topic in enumerate(config['topics']):
                d = {
                    "experiment_id": config['experiment_id'],
                    "cluster_number": res_cluster['_id'],
                    "name": topic,
                    "topic_number": index,
                }
                res_topic = self.save_topic(d)
                if not res_topic:
                    raise Exception('Topic: {} was not created'.format(topic))

            return {'experiment_id': res_cluster['_id']}, 200

        except Exception as e:
            print('ExperimentController-create_cluster: {}'.format(str(e)), file=sys.stderr)
            return {'error': str(e), 'error_code': 500}, 500

    def append_topics(self, config: dict):
        """
        Append new topic to cluster according to config dictionary.
        :param config:
        :return: dictionary with topic id, return code.
        """
        try:
            for index, topic in enumerate(config['topics']):
                d = {
                    "experiment_id": config['experiment_id'],
                    "cluster_number": config['cluster_number'],
                    "name": topic,
                    "topic_number": index,
                }
                res = self.save_topic(d)

                if not res:
                    raise Exception('Topic: {} was not created'.format(topic))

            return {'cluster_id': config['cluster_number']}, 200

        except Exception as e:
            print('ExperimentController-create_cluster: {}'.format(str(e)), file=sys.stderr)
            return {'error': str(e), 'error_code': 500}, 500

    def merge_topic(self, config: dict):
        """
        Merge topic identified by topic_from_id and its sentences to cluster identified by cluster_to_id and topic topic_to_id.
        :param config:
        :return:
        """

        try:
            data, ret_code = self.connector.update_experiment_cluster_sentences(
                config['topic_from_id'],
                config['cluster_to_id'], config['topic_to_number'], config['topic_to_id'])

            return data, ret_code

        except Exception as e:
            print('ExperimentController-create_cluster: {}'.format(str(e)), file=sys.stderr)
            return {'error': str(e), 'error_code': 500}, 500
