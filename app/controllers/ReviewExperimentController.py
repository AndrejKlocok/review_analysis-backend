from review_analysis.utils.elastic_connector import Connector
import warnings, sys, re
from nltk.tokenize import sent_tokenize
warnings.simplefilter(action='ignore', category=FutureWarning)

from review_analysis.clasification.bert_model import Bert_model
from review_analysis.utils.morpho_tagger import MorphoTagger


class ReviewController:
    def __init__(self, con: Connector):
        self.connector = con
        path = '/home/andrej/Documents/school/Diplomka/model/'
        self.re_int = re.compile(r'^[-+]?([1-9]\d*|0)$')
        self.tagger = MorphoTagger()
        self.tagger.load_tagger()
        self.pos_con_labels = ['+', '-']
        #self.pos_con_model = Bert_model(path+'bert_bipolar',
        #                                self.pos_con_labels)
        #self.pos_con_model.do_eval()
        #self.regression_model = Bert_model(path+'bert_regression', [])
        #self.regression_model.do_eval()

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

    def __merge_review_text(self, pos: list, con: list, summary: str):
        text = []
        text += [self.__clear_sentence(s) for s in pos]
        text += [self.__clear_sentence(s) for s in con]
        text += [summary]
        return ' '.join(text)

    def get_review_experiment(self, config):
        data = {
            'pos_labels': [],
            'con_labels': [],
            'rating': '',
            'summary_labels': [],
        }
        ret_code = 200
        try:

            review_text = self.__merge_review_text(config['pos'], config['con'], config['summary'])

            if review_text:
                _, rating = self.__eval_sentence(self.regression_model, review_text, useLabels=False)
                data['rating'] = '{:2.2f}%'.format(rating*100.0)
            else:
                raise ValueError('Empty review')

            for sentence in config['pos']:
                s, label = self.__eval_sentence(self.pos_con_model, sentence)
                data['pos_labels'].append({
                    'sentence':s,
                    'label': label
                })

            for sentence in config['con']:
                s, label = self.__eval_sentence(self.pos_con_model, sentence)
                data['con_labels'].append({
                    'sentence':s,
                    'label': label
                })

            if config['summary']:
                topic_words = []
                exp, code = self.connector.get_experiments_by_category(config['category'])
                exp = exp[0]
                for topic_d in (exp['topics_con']+exp['topics_pos']):
                    for topic_str in topic_d['topics']:
                        for topic in topic_str.split():
                            if topic not in topic_words:
                                topic_words.append(topic)

                for sentence in sent_tokenize(config['summary'], 'czech'):
                    sentence_out = []
                    s, label = self.__eval_sentence(self.pos_con_model, sentence)
                    sentence_pos_list = self.tagger.pos_tagging(s, False, False)
                    for sentence_wp_list in sentence_pos_list:
                        for wp in sentence_wp_list:
                            if wp.lemma in topic_words and wp.tag[0] in ['N']:
                                sentence_out.append('<b>'+wp.token+'</b>')
                            else:
                                sentence_out.append(wp.token)

                    sentence = ' '.join(sentence_out)
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
            _, data['polarity'] = self.__eval_sentence(self.pos_con_model, config['sentence'])

            return data, ret_code

        except Exception as e:
            print('ExperimentController-get_polarity_sentence: {}'.format(str(e)), file=sys.stderr)
            return {'error': str(e), 'error_code': 500}, 500

    def get_text_rating(self, config):
        data = {}
        ret_code = 200
        try:
            _, rating = self.__eval_sentence(self.regression_model, config['text'], useLabels=False)
            data['rating'] = '{:2.2f}%'.format(rating * 100.0)
            return data, ret_code

        except Exception as e:
            print('ExperimentController-get_polarity_sentence: {}'.format(str(e)), file=sys.stderr)
            return {'error': str(e), 'error_code': 500}, 500
