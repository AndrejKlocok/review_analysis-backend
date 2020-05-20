"""
This file contains implementation of ReviewController class, which handles few /experiment/ endpoints:
    /experiment/review
    /experiment/sentence_pos_con
    /experiment/text_rating
    /experiment/text_irrelevant
This class uses trained models to perform analysis right on the requests.

Author: xkloco00@stud.fit.vutbr.cz
"""
from review_analysis.utils.elastic_connector import Connector
import warnings, sys, re
from nltk.tokenize import sent_tokenize

warnings.simplefilter(action='ignore', category=FutureWarning)

from review_analysis.clasification.bert_model import Bert_model
from review_analysis.clasification.SVM_model import SVM_Classifier
from review_analysis.utils.morpho_tagger import MorphoTagger


class ReviewController:
    """
    Controller handles text/review analysis. Provides handlers for review analysis with bipolar bert models, prediction
    of reviews rating and marking of salient words within sentence. Also single methods for bipolar analysis, irrelevant
    review analysis and text rating.
    """

    def __init__(self, con: Connector):
        """
        Constructor method takes elastic connector instance. Initializes morphological tagger and domain bipolar bert
        models, text rating prediction model, irrelevant model.
        :param con: instance of elastic connector
        """
        self.connector = con
        path = '../model/'

        self.re_int = re.compile(r'^[-+]?([1-9]\d*|0)$')
        self.tagger = MorphoTagger()
        self.tagger.load_tagger(path='../model/czech-morfflex-pdt-161115-no_dia-pos_only.tagger')
        self.pos_con_labels = ['0', '1']
        self.irrelevant_model = SVM_Classifier('../model/')
        self.irrelevant_model.load_models()
        self.pos_con_model = Bert_model(path + 'bert_bipolar',
                                        self.pos_con_labels)
        self.pos_con_model.do_eval()

        self.regression_model = Bert_model(path + 'bert_regression', [])
        self.regression_model.do_eval()
        self.model_d = self._load_models(path, self.pos_con_labels)
        self.model_d['general'] = self.pos_con_model

    def _load_models(self, path: str, labels: list):
        """
        Load all bipolar models located in path.
        :param path: path to models
        :param labels: used labels
        :return:
        """
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
        for value in indexes:
            d[value] = Bert_model(path + 'bert_bipolar_domain/' + value, labels)
            d[value].do_eval()

        return d

    def __clear_sentence(self, sentence: str) -> str:
        """
        Clear text by capitalizing, removing multiple dots and tabs.
        :param sentence:
        :return:
        """
        sentence = sentence.strip().capitalize()
        sentence = re.sub(r'\.{2,}', "", sentence)
        sentence = re.sub(r'\t+', ' ', sentence)
        if sentence[-1] != '.':
            sentence += '.'

        return sentence

    def __eval_sentence(self, model: Bert_model, sentence: str, useLabels: bool = True):
        """
        Evaluate sentence with bipolar model.
        :param model: Bert bipolar model
        :param sentence: list of sentences
        :param useLabels: use labels (not in regression task)
        :return: text, label
        """
        sentence = self.__clear_sentence(sentence)
        return sentence, model.eval_example('a', sentence, useLabels)

    def merge_review_text(self, pos: list, con: list, summary: str):
        """
        Merge text from pros, cons and summary section into one.
        :param pos:
        :param con:
        :param summary:
        :return:
        """
        text = []
        text += [self.__clear_sentence(s) for s in pos]
        text += [self.__clear_sentence(s) for s in con]
        text += [summary]
        return ' '.join(text)

    def __salient(self, s: str, salient: list):
        """
        Mark salient words in salient list.
        :param s:
        :param salient:
        :return:
        """
        sentence_out = []
        # get list of WordPos {lemma, tag, token}
        sentence_pos_list = self.tagger.pos_tagging(s, False, False)
        # find salient words in wordpos list and mark them
        for sentence_wp_list in sentence_pos_list:
            for wp in sentence_wp_list:
                if wp.lemma in salient and wp.tag[0] in ['N']:
                    sentence_out.append('<b>' + wp.token + '</b>')
                else:
                    sentence_out.append(wp.token)
        sentence = ' '.join(sentence_out)
        return sentence

    def __round_percentage(self, number: float):
        """
        Round percentage of float number [0,1] to integer.
        :param number:
        :return: int
        """
        return round(round(number * 100.0, -1))

    def get_review_experiment(self, config):
        """
        Perform analysis on review object according to config dictionary. Analysis consists of bipolar
         models analysis, rating analysis, salient words marking.
        :param config:
        :return: analysed review dictionary, return code
        """
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

            # not all reviews are processed with rating prediction model
            if 'rating_model' not in review:
                review_text = self.merge_review_text(review['pros'], review['cons'], review['summary'])
                if review_text:
                    _, rating = self.__eval_sentence(self.regression_model, review_text, useLabels=False)

                    rating = self.__round_percentage(rating)
                    data['rating_model'] = '{}%'.format(rating)
                else:
                    raise KeyError('Empty review')
            else:
                data['rating_model'] = review['rating_model']

            # marking of salient words from experiment of products subcategory or shop.
            exp, _ = self.connector.get_experiments_by_category(config['category'])
            topic_words = []
            if exp:
                exp = exp[0]
                topic_words = exp['sal_con'] + exp['sal_pos']

            # evaluate each sentence of review pros section with general bipolar model, mark salient  words
            for sentence in review['pros']:
                s, label = self.__eval_sentence(self.pos_con_model, sentence)
                if topic_words:
                    s = self.__salient(s, topic_words)
                data['pos_labels'].append({
                    'sentence': s,
                    'label': label
                })
            # evaluate each sentence of review cons section with general bipolar model, mark salient  words
            for sentence in review['cons']:
                s, label = self.__eval_sentence(self.pos_con_model, sentence)
                if topic_words:
                    s = self.__salient(s, topic_words)
                data['con_labels'].append({
                    'sentence': s,
                    'label': label
                })

            # pos model is evaluation of sentence by all domain models
            # if exists copy it
            if 'pos_model' in review:
                data['pos_model'] = review['pos_model']
            else:
                # else evaluate each sentence of pros section with all domain models
                for sentence in review['pros']:
                    model_review = []

                    for category, model in self.model_d.items():
                        s, label = self.__eval_sentence(model, sentence)
                        model_review.append([label, category + '_model'])

                    data['pos_model'].append(model_review)

            # con model is the same as pos_model but for negative sentences
            if 'con_model' in review:
                data['con_model'] = review['con_model']
            else:
                # evaluate each sentence of cons section with all domain models
                for sentence in review['cons']:
                    model_review = []

                    for category, model in self.model_d.items():
                        s, label = self.__eval_sentence(model, sentence)
                        model_review.append([label, category + '_model'])

                    data['con_model'].append(model_review)
            # for summary section evaluate each sentence it with general bipolar model and mark all salient words
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

        except KeyError as e:
            print('ExperimentController-get_review_experiment: {}'.format(str(e)), file=sys.stderr)
            return {'error': str(e), 'error_code': 404}, 404

        except ValueError as e:
            print('ExperimentController-get_review_experiment: {}'.format(str(e)), file=sys.stderr)
            return {'error': str(e), 'error_code': 400}, 400

        except Exception as e:
            print('ExperimentController-get_review_experiment: {}'.format(str(e)), file=sys.stderr)
            return {'error': str(e), 'error_code': 500}, 500

    def get_sentence_polarity(self, config):
        """
        Evaluate polarity of text by bipolar model according to config dict.
        :param config:
        :return: dict representing result of evaluation, return code
        """
        data = {}
        ret_code = 200
        try:
            try:
                model = self.model_d[config['model_type']]
                data['model_type'] = config['model_type']
            # wrong model name -> use general
            except Exception as e:
                print('ExperimentController-get_polarity_sentence: {}'.format(str(e)), file=sys.stderr)
                model = self.model_d['general']
                data['model_type'] = 'general'

            _, data['polarity'] = self.__eval_sentence(model, config['sentence'])

            return data, ret_code

        except Exception as e:
            print('ExperimentController-get_polarity_sentence: {}'.format(str(e)), file=sys.stderr)
            return {'error': str(e), 'error_code': 500}, 500

    def get_text_rating(self, config):
        """
        Evaluate rating of text with bert prediction model.
        :param config:
        :return: dict representing result of evaluation, return code
        """
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
        """
        Evaluate text for irrelevant sentences with SVM model and uSIF sentence embeddings.
        :param config:
        :return: dict representing result of evaluation, return code
        """
        data = {}
        ret_code = 200
        try:
            label_str = self.irrelevant_model.eval_example(config['text'])
            data['label'] = label_str
            return data, ret_code

        except Exception as e:
            print('ExperimentController-get_irrelevant: {}'.format(str(e)), file=sys.stderr)
            return {'error': str(e), 'error_code': 500}, 500
