from collections import defaultdict
from pprint import pprint

import click
from github import Github
import requests


class AssigneesChecker:
  def __init__(self):
    self.assignees = defaultdict(list)

  def fetch_github(self, username, password):
    for repo in Github(username, password).get_organization('glucoseinc').get_repos():
      for issue in repo.get_issues():
        for assignee in issue.assignees:
          self.assignees[assignee.login].append((issue.title, issue.html_url))

  def fetch_pivotal(self, token):
    projects = requests.get(
      'https://www.pivotaltracker.com/services/v5/projects',
      headers={'X-TrackerToken': token}
    ).json()
    for project in projects:
      stories = requests.get(
        'https://www.pivotaltracker.com/services/v5/projects/{}/stories'.format(project['id']),
        headers={'X-TrackerToken': token}
      ).json()
      for story in stories:
        owners = requests.get(
          'https://www.pivotaltracker.com/services/v5/projects/{}/stories/{}/owners'.format(project['id'], story['id']),
          headers={'X-TrackerToken': token}
        ).json()
        for owner in owners:
          self.assignees[owner['username']].append('https://www.pivotaltracker.com/story/show/{}'.format(story['id']))


@click.command()
@click.option('--github-user', type=click.STRING, required=True)  # of GitHub
@click.option('--github-pass', prompt=True, hide_input=True, required=True)
@click.option('--pivotal-token', type=click.STRING)  # can be taken from pivotaltracker.com/profile
def main(github_user, github_pass, pivotal_token):
  checker = AssigneesChecker()
  checker.fetch_github(github_user, github_pass)
  checker.fetch_pivotal(pivotal_token)
  pprint(checker.assignees)


if __name__ == '__main__':
    main()
