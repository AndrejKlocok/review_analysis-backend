import sys, time
from collections import Counter

from review_analysis.utils.elastic_connector import Connector
from review_analysis.utils.morpho_tagger import MorphoTagger
from review_analysis.clasification.fasttext_model import FastTextModel, EmbeddingType, ClusterMethod

import warnings

warnings.filterwarnings("ignore", module="matplotlib")
from review_analysis.clasification.LDA_model import LDA_model


class ExperimentController:
    def __init__(self, con: Connector):
        self.connector = con
        self.tagger = MorphoTagger()
        self.tagger.load_tagger()
        self.fastTextModel = FastTextModel()

    def __get_sentences(self, rev_id: str, l: list, sen_type: str):
        sentences = []
        for index, sentence in enumerate(l):
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
                        '_id': rev_id,
                        'sentence': sentence,
                        'sentence_pos': sentence_list,
                        'index': index,
                        'type': sen_type
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

    def __cluster(self, sentences: list, config: dict, embedding_type: EmbeddingType, cluster_method: ClusterMethod):
        cluster = {
            'sentences_count': len(sentences),
            'clusters': [],
        }

        # temporary for positive reviews
        sentences_pos = [sentence['sentence_pos'] for sentence in sentences]
        #labels = self.fastTextModel.cluster_similarity(sentences_pos,pretrained=False, embedding=embedding_type,
        #                                              cluster=cluster_method, cluster_cnt=config['clusters_count'])
        import math, random
        labels = [math.floor(random.uniform(0, 7)) for _ in sentences_pos]
        cnt = Counter(labels)
        experiment_id = '1'

        clusters = {}
        for key, value in cnt.items():
            clusters[key] = {
                'cluster_number': key,
                'cluster_sentences_count': value,
                'sentences': [],
                'topics': [],
            }

        for index, label in enumerate(labels):
            sentences[index]['cluster_number'] = label
            sentences[index]['experiment_id'] = experiment_id
            clusters[label]['sentences'].append(sentences[index])

        lda = LDA_model(config['topics_per_cluster'])
        lda.load_sentences_from_api(clusters)

        for _, value in clusters.items():
            cluster['clusters'].append(value)

        return cluster

    def cluster_similarity(self, config: dict):
        start = time.time()
        data = {}
        ret_code = 200
        try:
            reviews = []
            sentences_pro = []
            sentences_con = []
            # TODO check config validity
            embedding_type = self.__get_embedding_type(config)
            cluster_method = self.__get_cluster_method(config)
            # get reviews
            for cat in config['categories']:
                cat_reviews, ret = self.connector.get_reviews_from_category(cat)
                if ret != 200:
                    return data, ret
                reviews += cat_reviews

            # create sentences pos cons
            for review in reviews:
                sentences_pro += self.__get_sentences(review['_id'], review['pros'], 'pros')
                sentences_con += self.__get_sentences(review['_id'], review['cons'], 'cons')

            data['pos'] = self.__cluster(sentences_pro, config, embedding_type, cluster_method)
            data['con'] = self.__cluster(sentences_con, config, embedding_type, cluster_method)

            print(time.time() - start)
            return data, ret_code

        except Exception as e:
            print('ExperimentController-cluster_similarity: {}'.format(str(e)), file=sys.stderr)
            return {'error': str(e)}, 500
