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
