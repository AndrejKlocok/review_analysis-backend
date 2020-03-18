import sys, time, warnings
from collections import Counter
from datetime import datetime, timezone

from review_analysis.utils.elastic_connector import Connector
from review_analysis.utils.morpho_tagger import MorphoTagger
from review_analysis.clasification.fasttext_model import FastTextModel, EmbeddingType, ClusterMethod
from review_analysis.clasification.LDA_model import LDA_model

# from app.utils.Exceptions import WrongProperty

warnings.filterwarnings("ignore", module="matplotlib")


class ExperimentClusterController:
    def __init__(self, con: Connector):
        self.connector = con
        self.tagger = MorphoTagger()
        self.tagger.load_tagger()
        self.fastTextModel = FastTextModel()

    def __get_sentences(self, rev: dict, sen_type: str):
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
        if config['embedding_method'] == 'sent2vec_dist':
            embedding_type = EmbeddingType.distance_matrix
        elif config['embedding_method'] == 'sent2vec_sim':
            embedding_type = EmbeddingType.similarity_matrix
        elif config['embedding_method'] == 'sent2vec_vec':
            embedding_type = EmbeddingType.sentence_vectors
        else:
            raise KeyError('embedding_method')

        return embedding_type

    def __get_cluster_method(self, config: dict):
        if config['cluster_method'] == 'kmeans':
            cluster = ClusterMethod.kmeans
        else:
            raise KeyError('cluster_method')

        return cluster

    def __cluster(self, sentences: list, clusters_count: int, topics_per_cluster: int,
                  embedding_type: EmbeddingType, cluster_method: ClusterMethod,
                  experiment_id: str, doSave: bool, sentence_type: str):
        cluster = {
            'sentences_count': len(sentences),
            'clusters': [],
        }

        sentences_pos = [sentence['sentence_pos'] for sentence in sentences]
        labels = self.fastTextModel.cluster_similarity(sentences_pos, pretrained=False, embedding=embedding_type,
                                                       cluster=cluster_method, cluster_cnt=clusters_count)
        #import math, random
        #labels = [math.floor(random.uniform(0, 7)) for _ in sentences_pos]
        cnt = Counter(labels)

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

        for index, label in enumerate(labels):
            sentences[index]['cluster_number'] = label_to_cluster_id[label]
            sentences[index]['topic_number'] = 0
            sentences[index]['experiment_id'] = experiment_id
            clusters[label]['sentences'].append(sentences[index])

        lda = LDA_model(topics_per_cluster)
        salient_words = lda.load_sentences_from_api(clusters, self.tagger)

        for _, value in clusters.items():
            cluster['clusters'].append(value)
            if value['topics']:
                res, ret_code = self.connector.update_experiment_cluster_topics(value['cluster_id'], value['topics'])
                if res['result'] != 'updated':
                    raise Exception('Update of topics failed')

            for sentence in value['sentences']:
                if not self.save_sentence(sentence):
                    print('Did not saved: {}'.format(sentence['sentence']), file=sys.stderr)

        self.connector.es.indices.refresh(index="experiment_sentence")
        return cluster, salient_words

    def __get_reviews_sentences(self, category):
        sentences_pro = []
        sentences_con = []

        reviews, ret = self.connector.get_reviews_from_category(category)
        # if ret != 200:
        #    raise WrongProperty('No reviews found for category: {}'.format(cat))

        # create sentences pos cons
        for review in reviews:
            sentences_pro += self.__get_sentences(review, 'pros')
            sentences_con += self.__get_sentences(review, 'cons')

        return sentences_pro, sentences_con

    def save_experiment(self, config: dict, pos_cnt: int, con_cnt: int):
        experiment = {
            "topics_per_cluster": config['topics_per_cluster'],
            "clusters_pos_count": config['clusters_pos_count'],
            "clusters_pos": [],
            "clusters_con": [],
            "clusters_con_count": config['clusters_con_count'],
            "cluster_method": config['cluster_method'],
            "embedding_method": config['embedding_method'],
            "category": config['category'],
            "date": datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S'),
            "pos_sentences": pos_cnt,
            "con_sentences": con_cnt,

        }
        res = self.connector.index('experiment', experiment)
        if res['result'] == 'created':
            return res['_id']
        return None

    def save_sentence(self, sentence: dict):
        experiment_sentence = {
            "review_id": sentence['review_id'],
            "experiment_id": sentence['experiment_id'],
            "cluster_number": sentence['cluster_number'],
            "product_name": sentence['product_name'],
            "category_name": sentence['category_name'],
            "topic_number": sentence['topic_number'],
            "sentence": sentence['sentence'],
            "sentence_index": sentence['sentence_index'],
            "sentence_pos": sentence['sentence_pos'],
            "sentence_type": sentence['sentence_type'],
        }
        res = self.connector.index(index='experiment_sentence', doc=experiment_sentence)
        if res['result'] == 'created':
            return True
        return False

    def save_cluster_meta(self, cluster_d: dict):
        cluster = {
            'experiment_id': cluster_d['experiment_id'],
            'type': cluster_d['type'],
            'cluster_name': 'cluster_' + str(cluster_d['cluster_number']),
            'cluster_number': cluster_d['cluster_number'],
            'topics': cluster_d['topics'],
            'cluster_sentences_count': cluster_d['cluster_sentences_count'],
        }

        res = self.connector.index(index='experiment_cluster', doc=cluster)

        if res['result'] == 'created':
            return res['_id']
        return None

    def get_experiment(self):
        try:
            data, ret_code = self.connector.get_experiments()

            return data, ret_code

        except Exception as e:
            print('ExperimentController-get_experiment: {}'.format(str(e)), file=sys.stderr)
            return {'error': str(e), 'error_code': 500}, 500

    def get_experiment_sentences(self, content):
        try:
            # if content['experiment_id']:
            data, ret_code = self.connector.get_experiments_by_category(content['category'])

            # 400 error
            if not data or ret_code != 200:
                raise ValueError('This category does not have any experiments')

            if len(data) > 1:
                raise Exception('More experiments for category')

            data = data[0]

            output_d = {
                'pos': {
                    'sentences_count': data['pos_sentences'],
                    'clusters': data['clusters_pos'],
                    'sal_pos': data['sal_pos'],
                },
                'con': {
                    'sentences_count': data['con_sentences'],
                    'clusters': data['clusters_con'],
                    'sal_con': data['sal_con'],
                }
            }

            return output_d, ret_code

        except ValueError as e:
            print('ExperimentController-get_experiment_sentences: {}'.format(str(e)), file=sys.stderr)
            return {'error': str(e), 'error_code': 400}, 400

        except Exception as e:
            print('ExperimentController-get_experiment_sentences: {}'.format(str(e)), file=sys.stderr)
            return {'error': str(e), 'error_code': 500}, 500

    def delete_experiment(self, content):
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

    def update_experiment_cluster_name(self, content):
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

    def update_experiment_cluster_topics(self, content):
        try:

            data, ret_code = self.connector.update_experiment_cluster_topics(
                content['cluster_id'], content['topics'])

            if ret_code == 200:
                return data, ret_code
            else:
                data = {
                    'error': 'Data not found',
                    'ret_code': ret_code,
                }
                return data, ret_code

        except Exception as e:
            print('ExperimentController-update_experiment_cluster_topics: {}'.format(str(e)), file=sys.stderr)
            return {'error': str(e), 'error_code': 500}, 500

    def peek_sentences(self, config: dict):
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

        # except WrongProperty as e:
        #    print('ExperimentController-cluster_similarity: {}'.format(str(e)), file=sys.stderr)
        #    return {'error': str(e), 'error_code': 400}, 400

        except Exception as e:
            print('ExperimentController-cluster_similarity: {}'.format(str(e)), file=sys.stderr)
            return {'error': str(e), 'error_code': 500}, 500

    def cluster_similarity(self, config: dict):
        start = time.time()
        data = {}
        ret_code = 200
        try:
            # TODO check already done experiments
            # TODO check config validity
            embedding_type = self.__get_embedding_type(config)
            cluster_method = self.__get_cluster_method(config)
            if not config['category']:
                # raise WrongProperty('Empty category')
                return None, 500

            # create sentences pos cons
            sentences_pro, sentences_con = self.__get_reviews_sentences(config['category'])

            experiment_id = '1'
            if config['save_data']:
                experiment_id = self.save_experiment(config, len(sentences_pro), len(sentences_con))
                if not experiment_id:
                    raise Exception('Experiment was not saved')

            data['pos'], salient_pos = self.__cluster(sentences_pro, config['clusters_pos_count'],
                                                      config['topics_per_cluster'], embedding_type,
                                                      cluster_method, experiment_id, config['save_data'],
                                                      'pos')
            data['con'], salient_con = self.__cluster(sentences_con, config['clusters_con_count'],
                                                      config['topics_per_cluster'], embedding_type,
                                                      cluster_method, experiment_id, config['save_data'],
                                                      'con')

            res, ret_code = self.connector.update_experiment(
                experiment_id, salient_pos, salient_con,
            )
            if res['result'] != 'updated':
                raise Exception('Update of salient words failed')

            print(time.time() - start)
            return data, ret_code

        # except WrongProperty as e:
        #    print('ExperimentController-cluster_similarity: {}'.format(str(e)), file=sys.stderr)
        #    return {'error': str(e), 'error_code': 400}, 400

        except KeyError as e:
            print('ExperimentController-cluster_similarity: {}'.format(str(e)), file=sys.stderr)
            return {'error': str(e), 'error_code': 400}, 400

        except Exception as e:
            print('ExperimentController-cluster_similarity: {}'.format(str(e)), file=sys.stderr)
            return {'error': str(e), 'error_code': 500}, 500
