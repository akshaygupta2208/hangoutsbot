from datetime import datetime
import json
import os
import re
import time
from urllib.parse import urlencode
from bs4 import BeautifulSoup
from elasticsearch_dsl import DocType, Date, Integer, Keyword, String
from elasticsearch_dsl.connections import connections
from selenium import webdriver
import elasticsearch
import elasticsearch_dsl
import requests
from sys import argv

# Define a default Elasticsearch client
connections.create_connection(hosts=['localhost'])
user_agent = 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.9.0.7) Gecko/2009021910 Firefox/3.0.7'
params ={'User-Agent': user_agent}
class Question(DocType):
    title = String()
    body = elasticsearch_dsl.CustomField

    class Meta:
        index = 'quora'

    def save(self, ** kwargs):
        return super(Question, self).save(** kwargs)


def get_linked_questions(soup):
    global question_list
    for link in soup.find_all('a'):
        # print link.get('class')
        if(link.get('class') != None and 'question_link' in link.get('class') and 'unanswered' not in link.get('href')):
            if link.get('href') not in question_list:
                question_list[link.get('href')] = False


def fetch_question(question):
    global question_list
    print (question)
    r = requests.get("https://www.quora.com" + question)
    status_code = r.status_code
    print (status_code)
    body = []
    soup = BeautifulSoup(r.text, 'lxml')
    # soup = BeautifulSoup(aa, 'lxml')
    votes = 0
    for answerdiv in soup.find_all('div'):
        ans_data = {}

        if(answerdiv.get('class') != None and 'AnswerBase' in answerdiv.get('class')):
            for votespan in answerdiv.find_all('a'):
                if(votespan.get('class') != None and 'AnswerVoterListModalLink' in votespan.get('class')):
                    votes = votespan.get_text().split('Upvotes')[0].strip()
        if(answerdiv.get('id') != None and 'answer_content' in answerdiv.get('id')):
            # print answerdiv.get_text()
            body.append({'answer': answerdiv.get_text(), 'votes': votes})
            votes = 0

    # AnswerVoterListModalLink
    if(len(body) > 0):
        # print json.dumps({"answers": body}, sort_keys=True, indent=4)
        article = Question(meta={'id': question.replace('/', '')},
                           title=question.replace('/', '').replace('-', ' '), body=body)
        print (article.save())
    get_linked_questions(soup)


Question.init()
question_list = {}
def update_kb(query):
    fetch_question(query)
    while(len(question_list) > 0):
        for que in question_list:
            if (question_list[que] == False):
                question_list[que] = True
                r = requests.head(
                    "http://localhost:9200/quora/question" + que)
                status_code = r.status_code
                if status_code == 200:
                    continue
                next_question = que
                break
        fetch_question(next_question)
        
def search_questions(query):
    try:
        print ("https://www.quora.com/search?q=" + query.strip().replace(" ", "-"))
        r = requests.get("https://www.quora.com/search?q=" + query.strip().replace(" ", "-"),headers=params)
        status_code = r.status_code
        print (status_code)
        soup = BeautifulSoup(r.text, 'lxml')
        for answerdiv in soup.find_all('a'):
            
            #print (answerdiv.get('class'))
            if (answerdiv.get('class') != None and 'question_link' in answerdiv.get('class')):
                print(answerdiv.get('href'))
                if 'unanswered' not in answerdiv.get('href'):
                    update_kb(answerdiv.get('href'))
    except Exception as e:
        pass
#search_questions("bahubali is a super star")
#update_kb("What-happened-to-King-Arthur")
