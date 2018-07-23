# -*- coding: utf-8 -*-

import requests
import argparse
import re

import vk_api
from vk_api import VkUpload
from vk_api.longpoll import VkLongPoll, VkEventType
from html.parser import HTMLParser


parser = argparse.ArgumentParser(description='bot.py')
parser.add_argument('-token')
opt = parser.parse_args()
token = opt.token


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
    dict_answers = {}
    for i in range(3):
        dict_answers[i] = len(req_json['results'][i]['answer'])

    answer_index = sorted(dict_answers.items(), key=lambda x: x[1])[0][0]

    answer = strip_tags(req_json['results'][answer_index]["answer"])
    answer = re.sub(r'http\S+', '', answer)
    return answer


def main():
    session = requests.Session()
    vk_session = vk_api.VkApi(token=token)
    vk = vk_session.get_api()
    upload = VkUpload(vk_session)  
    longpoll = VkLongPoll(vk_session)

    for event in longpoll.listen():
        if event.type == VkEventType.MESSAGE_NEW and event.to_me and event.text:
            print('id{}: "{}"'.format(event.user_id, event.text), end=' ')

            text = get_answer_from_mailru(event.text)

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