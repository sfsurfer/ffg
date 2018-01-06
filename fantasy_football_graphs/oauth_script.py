from yahoo_oauth import OAuth2
import re
import xml.etree.ElementTree as ET
import os
import datetime, time, pytz
from yahoo_user import YahooUser
from models import Leagues
from logger import Logger


from os import access, R_OK
from os.path import isfile

class YahooController():
  def __init__(self):
    self.curr_week = {}
    self.curr_week_sb = {}
    self.league_end_dates = {}
    self.season = '2017'
    self.scoreboards = {}
    self.logger = Logger()
    self.logger.set_level(Logger.INFO)
    self.init_secrets()
    self.authenticate()
    self.get_teams_for_user()
    self.get_scoreboards_for_user()

  def init_secrets(self):
    secrets_file = './secrets.json'
    if not isfile(secrets_file) or not access(secrets_file,R_OK):
      if 'YAHOO_KEY' in os.environ and 'YAHOO_SECRET' in os.environ:
        f = open(secrets_file, 'w')
        f.write("""
{
    "consumer_key": "%s",
    "consumer_secret": "%s"
}
        """ % (os.environ['YAHOO_KEY'],os.environ['YAHOO_SECRET']))
      else:
        self.logger.log("Must have 'YAHOO_KEY' and 'YAHOO_SECRET' environment variables set!", Logger.ERROR)

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
    teams = self.yapi_get('https://fantasysports.yahooapis.com/fantasy/v2/users;use_login=1/games;game_keys=nfl;season=%s/teams' % self.season)
    self.user = YahooUser(self.yxml(teams.content))

  def ydate_to_datetime(self, date):
    date_format = "%Y-%m-%d"
    return datetime.datetime.strptime(date,date_format)

  def league_needs_update(self, league, league_key):
    update_time_delta = datetime.timedelta(days=1)
    update_date = self.get_week_completion_date(league_key) + update_time_delta
    if league.modified > self.get_league_end_date(league_key) or league.modified > update_date:
      return False
    elif datetime.datetime.now() > update_date:
      return True
    else:
      return False

  def get_week_completion_date(self, league_key):
    sb = self.get_current_week_scoreboard(league_key)
    return max([self.ydate_to_datetime(e.text) for e in sb.findall('.//week_end')]).replace(tzinfo=pytz.utc)

  def get_league_end_date(self, league_key):
    sb = self.get_current_week_scoreboard(league_key)
    return self.ydate_to_datetime(sb.find('.//end_date').text).replace(tzinfo=pytz.utc)

  def week_completed(self, league_key):
    return datetime.date.now() > self.get_week_completion_date(league_key)

  def calculate_luck(self, scoreboard):
    # TODO: Make meself an arogant algorithm
    return 1

  def get_current_week_scoreboard(self, league_key):
    if league_key not in self.curr_week_sb:
      scoreboard_resp = self.yapi_get('https://fantasysports.yahooapis.com/fantasy/v2/league/%s/scoreboard' % league_key)
      self.curr_week_sb[league_key] = self.yxml(scoreboard_resp.content)
    return self.curr_week_sb[league_key]

  def get_current_week(self, league_key):
    if league_key not in  self.curr_week:
      scoreboard_xml = self.get_current_week_scoreboard(league_key)
      weeks = set([w.text for w in scoreboard_xml.findall('.//week')])
      self.curr_week[league_key] = weeks.pop()
    return self.curr_week[league_key]

  def build_scoreboard_from_yahoo(self, league_key):
    league_resp = self.yapi_get('https://fantasysports.yahooapis.com/fantasy/v2/leagues;league_keys=%s' % league_key)
    league_root = self.yxml(league_resp.content)
    league_name = self.xml_find(league_root,'.//name')

    curr_week = int(self.get_current_week(league_key))
    range_end = curr_week + 1 if self.week_completed else curr_week

    weekly_scores = {}
    for week in range(1, int(range_end)):
      weekly_scores[week] = []
      resp = self.yapi_get('https://fantasysports.yahooapis.com/fantasy/v2/league/%s/scoreboard;week=%i' % (league_key,week))
      xml = self.yxml(resp.content)
      for matchup in xml.findall('.//matchup'):
        winner_team_key = self.xml_find(matchup,'winner_team_key')
        for t in matchup.findall('.//team'):
          team = {}
          team['key'] = self.xml_find(t,'team_key')
          team['won'] = team['key'] == winner_team_key
          team['name'] = self.xml_find(t,'name')
          team['points'] = self.xml_find(t,'team_points/total')
          team['proj_points'] = self.xml_find(t,'team_projected_points/total')
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
        if self.league_needs_update(db_league, league_key):
          self.scoreboards[league_key] = self.build_scoreboard_from_yahoo(league_key)
        else:
          self.scoreboards[league_key] = db_league.scoreboard
      except Leagues.DoesNotExist:
        self.scoreboards[league_key] = self.build_scoreboard_from_yahoo(league_key)

  def get_chart_data(self, scores):
    chart_data = []
    team_data = {}
    for index,week in scores.iteritems():
      for team in week:
        if not team['name'] in team_data:
          team_data[team['name']] = []
        team_data[team['name']].append([index, team['points']])
      for on_bye in [t for t in team_data if t not in [w['name'] for w in week]]:
        team_data[on_bye].append([index, None])
    for team, data in team_data.iteritems():
      chart_data.append({'name': team, 'connectNulls': True, 'data': data})
    self.logger.log(chart_data, Logger.DEBUG)
    return chart_data

  def xml_find(self, xml, tag):
    r = xml.find(tag)
    if r != None:
      resp = r.text
    else:
      self.logger.log("Failed to find tag %s, setting to empty string" % tag, Logger.WARNING)
      resp = ''
    return resp
