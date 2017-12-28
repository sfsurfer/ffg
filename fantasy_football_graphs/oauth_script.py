from yahoo_oauth import OAuth2
import re
import xml.etree.ElementTree as ET
import os
import datetime, time
from models import Leagues

class YahooUser:
  def __init__(self, root):
    self.root = root
    self.team_names = [name.text for name in root.findall('.//name')[1:]]
    self.team_keys = [team_key.text for team_key in root.findall('.//team_key')]
    self.league_ids = [key.split('.')[2] for key in self.team_keys]
    self.league_keys = ['.'.join(key.split('.')[:3]) for key in self.team_keys]
    self.leagues = {}
    for league in self.league_keys:
        self.leagues[league] = {'name': ''}


class YahooController:
  def __init__(self):
    self.curr_week = None
    self.scoreboards = {}
    self.authenticate()
    self.get_teams_for_user()
    self.get_scoreboards_for_user()


  def authenticate(self):
    self.oauth = OAuth2(None, None, from_file='./secrets.json')

  def yapi_get(self, url):
    if not self.oauth:
        self.authenticate()
    if not self.oauth.token_is_valid():
      self.oauth.refresh_access_token()
    return self.oauth.session.get(url)

  def yxml(self, yxml):
    xml = re.sub(r' xmlns=[^>]+','',yxml)
    return ET.fromstring(xml)

  def get_teams_for_user(self):
    teams = self.yapi_get('https://fantasysports.yahooapis.com/fantasy/v2/users;use_login=1/games;game_keys=nfl/teams')
    self.user = YahooUser(self.yxml(teams.content))

  def get_leagues_for_user(self):
    self.league_names = []
    for key in self.user.league_keys:
      resp = self.yapi_get('https://fantasysports.yahooapis.com/fantasy/v2/leagues;league_keys=%s' % key)
      root = self.yxml(leagues.content)
      self.league_names.append(root.find('.//name'))

  def league_needs_update(self, league):
      now = datetime.datetime.now()
      print now.today().weekday()
      print league.modified.weekday()
      print #.get_weekday()
      # TODO: Check dates
      return True #False

  def calculate_luck(self, scoreboard):
      # TODO: Make meself an arogant algorithm
      return 1

  def get_current_week(self, league_key):
    if not self.curr_week:
      scoreboard_resp = self.yapi_get('https://fantasysports.yahooapis.com/fantasy/v2/league/%s/scoreboard' % league_key)
      scoreboard_xml = self.yxml(scoreboard_resp.content)

      weeks = set([w.text for w in scoreboard_xml.findall('.//week')])
      self.curr_week = weeks.pop()
    return self.curr_week

  def build_scoreboard_from_yahoo(self, league_key):
    league_resp = self.yapi_get('https://fantasysports.yahooapis.com/fantasy/v2/leagues;league_keys=%s' % league_key)
    league_root = self.yxml(league_resp.content)
    league_name = league_root.find('.//name').text

    curr_week = self.get_current_week(league_key)

    weekly_scores = {}
    for week in range(1, int(curr_week)):
      weekly_scores[week] = []
      resp = self.yapi_get('https://fantasysports.yahooapis.com/fantasy/v2/league/%s/scoreboard;week=%i' % (league_key,week))
      xml = self.yxml(resp.content)
      for matchup in xml.findall('.//matchup'):
        winner_team_key = matchup.find('winner_team_key').text
        print winner_team_key
        for t in matchup.findall('.//team'):
          team = {}
          team['key'] = t.find('team_key').text
          team['won'] = team['key'] == winner_team_key
          team['name'] = t.find('name').text
          team['points'] = t.find('team_points/total').text
          team['proj_points'] = t.find('team_projected_points/total').text
          weekly_scores[week].append(team)

    scoreboard = {
      'league_key': league_key,
      'name': league_name,
      'scoreboard': weekly_scores,
      'chart_data': self.get_chart_data(weekly_scores)
    }
    luck = self.calculate_luck(weekly_scores)
    now = datetime.datetime.now()
    t = Leagues(league_key=league_key,scoreboard=scoreboard,luck=luck,created=now,modified=now)
    t.save()
    return scoreboard

  def get_scoreboards_for_user(self):
    self.scoreboards = {}
    for league_key in self.user.league_keys:
      try:
        db_league = Leagues.objects.get(league_key=league_key)
        if self.league_needs_update(db_league):
          self.scoreboards[league_key] = self.build_scoreboard_from_yahoo(league_key)
        else:
          self.scoreboards[league_key] = db_league.scoreboard
      except Leagues.DoesNotExist:
        self.scoreboards[league_key] = self.build_scoreboard_from_yahoo(league_key)

  def get_chart_data(self, scores):
    chart_data = []
    team_data = {}
    for index,week in scores.iteritems():
      #week_no = 36 + index
      #i = time.asctime(time.strptime('2017 %i 2' % week_no, '%Y %U %w'))
      #print i
      for team in week:
        if not team['name'] in team_data:
          team_data[team['name']] = []
        team_data[team['name']].append([index, team['points']])
    for team, data in team_data.iteritems():
      chart_data.append({'name': team, 'data': data})
    return chart_data
