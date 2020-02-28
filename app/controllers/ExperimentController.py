import sys

from review_analysis.utils.elastic_connector import Connector
from review_analysis.utils.morpho_tagger import MorphoTagger
from review_analysis.clasification.fasttext_model import FastTextModel, EmbeddingType, ClusterMethod

class ExperimentController:
    def __init__(self, con: Connector):
        self.connector = con
        self.tagger = MorphoTagger()
        self.tagger.load_tagger()
        self.fastTextModel = FastTextModel()

    def __get_sentences(self, rev_id: str, l: list, sen_type: str):
        sentences = []
        for index, sentence  in enumerate(l):
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

    def cluster_similarity(self, config: dict):
        data = {}
        ret_code = 200
        #try:
        reviews = []
        sentences_pro = []
        sentences_con = []
        # TODO check config validity
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

        data['pos'] = {
            'sentences_count': len(sentences_pro),
        }
        data['con'] = {
            'sentences_count': len(sentences_con),
        }

        if config['embedding_method'] == 'sent2vec_dist':
            self.fastTextModel.cluster_similarity_matrix()
        else:
            pass


        #except Exception as e:
        #    print('ExperimentController-cluster_similarity: {}'.format(str(e)), file=sys.stderr)
        #    return {'error': str(e)}, 500
