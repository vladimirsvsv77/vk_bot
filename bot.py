# -*- coding: utf-8 -*-

import requests
import argparse
import re
import redis

import vk_api
from vk_api import VkUpload
from vk_api.longpoll import VkLongPoll, VkEventType
from html.parser import HTMLParser


parser = argparse.ArgumentParser(description='bot.py')
parser.add_argument('-token')
opt = parser.parse_args()
token = opt.token


sentences = ['Добрый день! Меня зовут Вера, подскажите, пожалуйста, находитесь ли вы в поиске работы? Ответьте, пожалуйста, да или нет.', 
'Мы предлагаем официальное трудоустройство, уровень заработной платы от 100 000 рублей. Офис в центре Москвы, дружный коллектив. Скажите, интересна ли вам эта вакансия? Ответьте, пожалуйста, да или нет.',
'Благодарю за ответы, в ближайшее время с вами свяжется наш менеджер по подбору персонала']
negative = 'Извините, пожалуйста, за беспокойство. Хорошего дня!'


r_server = redis.StrictRedis(host='localhost', port=6379, db=0)


class MLStripper(HTMLParser):
    def __init__(self):
        self.reset()
        self.strict = False
        self.convert_charrefs= True
        self.fed = []
    def handle_data(self, d):
        self.fed.append(d)
    def get_data(self):
        return ''.join(self.fed)


def strip_tags(html):
    s = MLStripper()
    s.feed(html)
    return s.get_data()


def get_answer_from_mailru(question):
    req_json = requests.get('https://go.mail.ru/answer_json?q=' + question).json()
    try:
        answer = strip_tags(req_json['results'][0]["answer"])
        answer = re.sub(r'http\S+', '', answer)
    except:
        answer = 'у меня нет ответа на этот вопрос'
    return answer


def get_next_sentence(user_id, text):
    sentence_index = int(r_server.get(user_id))
    if 'да' in text or sentence_index == 0:
        text = sentences[sentence_index]
        if sentence_index == len(sentences) - 1:
            r_server.set(user_id, 0)
        else:
            r_server.set(user_id, sentence_index + 1)
    elif 'нет' in text:
        text = negative
        r_server.set(user_id, 0)
    else:
        text = "Извините, я не поняла ответ. Ответьте, пожалуйста, да или нет."

    return text


def main():
    session = requests.Session()
    vk_session = vk_api.VkApi(token=token)
    vk = vk_session.get_api()
    upload = VkUpload(vk_session)  
    longpoll = VkLongPoll(vk_session)

    for event in longpoll.listen():
        if event.type == VkEventType.MESSAGE_NEW and event.to_me and event.text:
            print('id{}: "{}"'.format(event.user_id, event.text), end=' ')

            # text = get_answer_from_mailru(event.text)
            if r_server.get(event.user_id) is None:
                r_server.set(event.user_id, 0)
                text = sentences[0]
            else:
                text = get_next_sentence(event.user_id, event.text.strip().lower())

            if not text:
                vk.messages.send(
                    user_id=event.user_id,
                    message='No results'
                )
                print('no results')
                continue

            vk.messages.send(
                user_id=event.user_id,
                message=text
            )


if __name__ == '__main__':
    main()