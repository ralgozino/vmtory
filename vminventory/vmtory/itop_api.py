#!/usr/bin/python

from django.conf import settings
import urllib.request as request
import json


VERSION = "0.1.0"


def encode_special_characters(text):
    text = text.replace("%", "%25")
    return text


def make_data(ticket):

    payload = {
                "operation": 'core/create',
                "comment": 'Generado desde vmtory',
                'class': 'UserRequest',
                "output_fields": 'id, friendlyname',
                "fields": {
                    "org_id": 'SELECT Organization WHERE name = "YOUR_ORG"',
                    "caller_id": 'SELECT Person JOIN User ON User.contactid = Person.id WHERE login="%s"' % ticket['username'],
                    "service_id": 'SELECT Service WHERE id = 2',
                    "servicesubcategory_id": 'SELECT ServiceSubcategory WHERE id = %s' % ticket['subcategory'],
                    "title": ticket['title'].replace('&', '%26'),
                    "description": ticket['description'].replace('&', '%26'),
                }
    }

    data = 'auth_user=' + settings.ITOP_USERNAME + '&auth_pwd=' + settings.ITOP_PASSWORD + "&json_data=" + json.dumps(payload)
    return data


def request(data):
    url = settings.ITOP_API_URL
    req = request.Request(url, data.encode('utf-8'))
    response = request.urlopen(req)
    return json.loads(response.read().decode('utf-8'))


def create_ticket(ticket):
    data = make_data(ticket)
    response = request(data)
    return response
