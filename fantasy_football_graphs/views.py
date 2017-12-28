# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.http import HttpResponse
from django.shortcuts import render
from django.template import loader
from oauth_script import YahooController

# Create your views here.
def index(request):
    template = loader.get_template('ffg/index.html')
    return HttpResponse(template.render({},request))

def oauth(request):
    o = YahooController()
    o.authenticate()
    template = loader.get_template('ffg/select_league.html')
    return HttpResponse(template.render({'scoreboards': o.scoreboards}, request))

def graph(request):
    o = YahooController()
    o.authenticate()
    template = loader.get_template('ffg/score_graphs.html')
    return HttpResponse(template.render({'scoreboards': o.scoreboards}), request)

def processing(request):
    return HttpResponse("Processing...")
