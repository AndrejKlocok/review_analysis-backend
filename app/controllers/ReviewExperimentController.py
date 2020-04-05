from review_analysis.utils.elastic_connector import Connector
import warnings, sys, re
from nltk.tokenize import sent_tokenize
warnings.simplefilter(action='ignore', category=FutureWarning)

from review_analysis.clasification.bert_model import Bert_model
from review_analysis.clasification.SVM_model import SVM_Classifier
from review_analysis.utils.morpho_tagger import MorphoTagger


class ReviewController:
    def __init__(self, con: Connector):
        self.connector = con
        path = '/home/andrej/Documents/school/Diplomka/model/'
        #path = '/mnt/data/xkloco00_a18/model/'
        #path = '/tmp/xkloco00/athena18/model/'
        self.re_int = re.compile(r'^[-+]?([1-9]\d*|0)$')
        self.tagger = MorphoTagger()
        self.tagger.load_tagger()
        self.pos_con_labels = ['0', '1']
        #self.irrelevant_model = SVM_Classifier()
        #self.irrelevant_model.load_models()
        self.pos_con_model = Bert_model(path+'bert_bipolar',
                                        self.pos_con_labels)
        self.pos_con_model.do_eval()

        self.regression_model = Bert_model(path+'bert_regression', [])
        self.regression_model.do_eval()
        self.model_d = self._load_models(path, self.pos_con_labels)
        self.model_d['general'] = self.pos_con_model

    def _load_models(self, path, labels):
        d = {
        }
        indexes = [
            'elektronika',
            'bile_zbozi',
            'dum_a_zahrada',
            'chovatelstvi',
            'auto-moto',
            'detske_zbozi',
            'obleceni_a_moda',
            'filmy_knihy_hry',
            'kosmetika_a_zdravi',
            'sport',
            'hobby',
            'jidlo_a_napoje',
            'stavebniny',
            'sexualni_a_eroticke_pomucky',
        ]
        #for value in indexes:
        #    d[value] = Bert_model(path + 'bert_bipolar_domain/' + value, labels)
        #    d[value].do_eval()

        return d

    def __clear_sentence(self, sentence: str) -> str:
        sentence = sentence.strip().capitalize()
        sentence = re.sub(r'\.{2,}', "", sentence)
        sentence = re.sub(r'\t+', ' ', sentence)
        if sentence[-1] != '.':
            sentence += '.'

        return sentence

    def __eval_sentence(self, model: Bert_model, sentence: str, useLabels=True):
        sentence = self.__clear_sentence(sentence)
        return sentence, model.eval_example('a', sentence, useLabels)

    def merge_review_text(self, pos: list, con: list, summary: str):
        text = []
        text += [self.__clear_sentence(s) for s in pos]
        text += [self.__clear_sentence(s) for s in con]
        text += [summary]
        return ' '.join(text)

    def __salient(self, s, salient):
        sentence_out = []
        sentence_pos_list = self.tagger.pos_tagging(s, False, False)
        for sentence_wp_list in sentence_pos_list:
            for wp in sentence_wp_list:
                if wp.lemma in salient and wp.tag[0] in ['N']:
                    sentence_out.append('<b>' + wp.token + '</b>')
                else:
                    sentence_out.append(wp.token)
        sentence = ' '.join(sentence_out)
        return sentence

    def __round_percentage(self, number):
        return round(round(number*100.0, -1))

    def get_review_experiment(self, config):
        data = {
            'pos_model': [],
            'con_model': [],
            'pos_labels': [],
            'con_labels': [],
            'rating_model': '',
            'summary_labels': [],
        }
        ret_code = 200
        try:
            review = self.connector.get_review_by_id(config['_id'], config['category'])
            if not review:
                raise ValueError('Review was not found')

            # not all reviews are processed with rating predictor model
            if 'rating_model' not in review:
                review_text = self.merge_review_text(review['pros'], review['cons'], review['summary'])
                if review_text:
                    _, rating = self.__eval_sentence(self.regression_model, review_text, useLabels=False)

                    rating = self.__round_percentage(rating)
                    data['rating_model'] = '{}%'.format(rating)
                else:
                    raise ValueError('Empty review')
            else:
                data['rating_model'] = review['rating_model']

            exp, _ = self.connector.get_experiments_by_category(config['category'])
            topic_words = []
            if exp:
                exp = exp[0]
                topic_words = exp['sal_con'] + exp['sal_pos']

            for sentence in review['pros']:
                s, label = self.__eval_sentence(self.pos_con_model, sentence)
                if topic_words:
                    s = self.__salient(s, topic_words)
                data['pos_labels'].append({
                    'sentence':s,
                    'label': label
                })

            for sentence in review['cons']:
                s, label = self.__eval_sentence(self.pos_con_model, sentence)
                if topic_words:
                    s = self.__salient(s, topic_words)
                data['con_labels'].append({
                    'sentence':s,
                    'label': label
                })

            # pos model exists
            if 'pos_model' in review:
                data['pos_model'] = review['pos_model']
            else:
                for sentence in review['pros']:
                    model_review = []

                    for category, model in self.model_d.items():
                        s, label = self.__eval_sentence(model, sentence)
                        model_review.append([label, category + '_model'])

                    data['pos_model'].append(model_review)

            # con model exists
            if 'con_model' in review:
                data['con_model'] = review['con_model']
            else:
                for sentence in review['cons']:
                    model_review = []

                    for category, model in self.model_d.items():
                        s, label = self.__eval_sentence(model, sentence)
                        model_review.append([s, label, category + '_model'])

                    data['con_model'].append(model_review)

            if review['summary']:
                for sentence in sent_tokenize(review['summary'], 'czech'):
                    sentence, label = self.__eval_sentence(self.pos_con_model, sentence)
                    if topic_words:
                        sentence = self.__salient(sentence, topic_words)

                    data['summary_labels'].append({
                        'sentence': sentence,
                        'label': label
                    })

            return data, ret_code

        except ValueError as e:
            print('ExperimentController-get_review_experiment: {}'.format(str(e)), file=sys.stderr)
            return {'error': str(e), 'error_code': 400}, 400

        except Exception as e:
            print('ExperimentController-get_review_experiment: {}'.format(str(e)), file=sys.stderr)
            return {'error': str(e), 'error_code': 500}, 500

    def get_sentence_polarity(self, config):
        data = {}
        ret_code = 200
        try:
            try:
                model = self.model_d['model_type']
            # wrong model name -> use general
            except Exception as e:
                model = self.model_d['general']

            _, data['polarity'] = self.__eval_sentence(model, config['sentence'])

            return data, ret_code

        except Exception as e:
            print('ExperimentController-get_polarity_sentence: {}'.format(str(e)), file=sys.stderr)
            return {'error': str(e), 'error_code': 500}, 500

    def get_text_rating(self, config):
        data = {}
        ret_code = 200
        try:
            _, rating = self.__eval_sentence(self.regression_model, config['text'], useLabels=False)
            data['rating_f'] = rating
            data['rating'] = self.__round_percentage(rating)

            return data, ret_code

        except Exception as e:
            print('ExperimentController-get_text_rating: {}'.format(str(e)), file=sys.stderr)
            return {'error': str(e), 'error_code': 500}, 500

    def get_irrelevant(self, config):
        data = {}
        ret_code = 200
        try:
            label_str = self.irrelevant_model.eval_example(config['text'])
            data['label'] = label_str
            return data, ret_code

        except Exception as e:
            print('ExperimentController-get_irrelevant: {}'.format(str(e)), file=sys.stderr)
            return {'error': str(e), 'error_code': 500}, 500
