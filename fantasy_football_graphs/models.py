# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models
from django.contrib.postgres.fields import JSONField

# Create your models here.
class Leagues(models.Model):
    league_key = models.CharField(max_length=200)
    scoreboard = JSONField()
    luck = models.IntegerField()
    created = models.DateTimeField()
    modified = models.DateTimeField()

    def __str__(self):
        return self.team_key
