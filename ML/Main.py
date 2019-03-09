# coding=utf-8
from nltk.stem import PorterStemmer
from collections import Counter
from telebot import apihelper
from nltk import ngrams
import scipy.spatial
import pandas as pd
import collections
import numpy as np
import telebot
import math
import copy
import re
# Просто пишем "python Main.py" бот стартует
# http://www.gatherproxy.com/sockslist - хост и порт прокси можно найти на этом сайте и прибиндить в переменные ниже,
# они нужны для обхода юлокировок РКН. Прокси ингода мигрируют, поэтому их надо заменять.
# ip = '46.4.163.211'
# port = '1080'
#
# apihelper.proxy = {
#     'https': 'socks5://{}:{}'.format(ip, port)
# }

bot = telebot.TeleBot("578770490:AAEyZ9BNxgZs1c8hr6qPuyaAFRKfPWbBOi0")


@bot.message_handler(content_types=['text'])
def get_text_messages(message):
    if is_ascii(message.text):
            answer = get_answer(message.text)
            bot.send_message(message.from_user.id, answer)
    else:
        bot.send_message(message.from_user.id, "There are wrong symbols!")


def get_xlsx_column(file_name, sheet_name, column_name):
    xslx_file = pd.ExcelFile(file_name)
    parsed_xslx = xslx_file.parse(sheet_name)
    read_sentences = parsed_xslx[column_name]
    return read_sentences


def fill_lemmatized_sentences(read_sentences, lemmatized_sentences, porter, lemmatized_words):
    for readSentence in read_sentences:
        words_array = filter(None, re.split('\W+', readSentence.lower()))
        stemmed_sentence = []
        for word in words_array:
            stemmed_word = porter.stem(word).encode('UTF-8')
            lemmatized_words.append(str(stemmed_word, 'utf-8'))
            stemmed_sentence.append(str(stemmed_word, 'utf-8'))
        lemmatized_sentences.append(stemmed_sentence)


def is_ascii(s):
    return all(ord(c) < 128 for c in s)


def compute_tf(text):
    tf_text = collections.Counter(text)
    for i in tf_text:
        tf_text[i] = tf_text[i] / float(len(text))
    return tf_text


def compute_idf(word, corpus):
    return math.log10(len(corpus) / sum([1.0 for i in corpus if word in i]))


def compute_tf_idf(computed_tf, computed_idf):
    computed_tf_idf = collections.Counter()
    for lemmatized_word in computed_tf.keys():
        computed_tf_idf[lemmatized_word] = computed_tf[lemmatized_word] * computed_idf[lemmatized_word]
    return computed_tf_idf


def fill_vectors_array(lemmatized_sentences, vectors_array, empty_vector_of_words):
    for lemmatized_sentence in lemmatized_sentences:
        vector = copy.deepcopy(empty_vector_of_words)
        for word in lemmatized_sentence:
            if word in vector:
                vector[word] += 1
        vectors_array.append(vector.values())


def get_closest_sentence(main_sentence_number, vectors_array):
    min_value = 1
    for i, vector in enumerate(vectors_array):
        value = scipy.spatial.distance.cosine(list(vectors_array[main_sentence_number]), list(vectors_array[i]))
        if value < min_value and i != main_sentence_number:
            min_value = value


def fill_empty_vectors(n, read_sentences, empty_ngramms_vector, n_gramms_vectors_array):
    for read_sentence in read_sentences:
        vector = copy.deepcopy(empty_ngramms_vector)
        bigrams = ngrams(read_sentence, n)
        for bigram in bigrams:
            bigram_key = str()
            i = 0
            while i < n:
                bigram_key += bigram[i]
                i += 1
            vector[bigram_key] += 1
        n_gramms_vectors_array.append(vector.values())


def get_answer(message):
    global answer
    porter = PorterStemmer()
    lemmatized_sentences = []
    lemmatized_words = []
    file_name = "Moovies.xlsx"
    sheet_name = "Sheet1"
    read_answers = get_xlsx_column(file_name, sheet_name, "overview")
    fill_lemmatized_sentences(read_answers, lemmatized_sentences, porter, lemmatized_words)

    computed_tf = compute_tf(lemmatized_words)
    sorted_lemmatized_words_dictionary = Counter(sorted(lemmatized_words))

    computed_idf = collections.Counter()

    for lemmatized_word in sorted_lemmatized_words_dictionary.keys():
        computed_idf[lemmatized_word] = compute_idf(lemmatized_word, lemmatized_sentences)

    computed_tf_idf = compute_tf_idf(computed_tf, computed_idf)

    term_freq_dict = Counter(computed_tf_idf)

    Q1, Q2, Q3 = np.percentile(list(term_freq_dict.values()), [25, 50, 75])
    IQR = Q3 - Q1
    lower_inner_fence = Q1 - (1.5 * IQR)
    upper_inner_fence = Q3 + (1.5 * IQR)

    cleanedDictionary = dict()
    for tfidfScore in dict(computed_tf_idf).keys():
        if lower_inner_fence <= computed_tf[tfidfScore] <= upper_inner_fence:
            cleanedDictionary[tfidfScore] = computed_tf[tfidfScore]

    empty_vector_of_words = dict()
    for key in cleanedDictionary.keys():
        empty_vector_of_words[key] = 0
    vectors_array = []

    fill_vectors_array(lemmatized_sentences, vectors_array, empty_vector_of_words)

    read_questions = [message]

    lemmatized_question_sentences = []
    fill_lemmatized_sentences(read_questions, lemmatized_question_sentences, porter, lemmatized_words)

    question_vectors_array = []
    fill_vectors_array(lemmatized_question_sentences, question_vectors_array, empty_vector_of_words)

    min_value = 1
    j_val = 0
    for j, vector in enumerate(vectors_array):
        value = scipy.spatial.distance.cosine(list(question_vectors_array[0]), list(vectors_array[j]))
        if value < min_value:
            min_value = value
            j_val = j
        answer = read_answers[j_val]
        if min_value == 1:
            answer = "I don't know, how to answer("
    return answer

bot.polling(none_stop=True, interval=0)
