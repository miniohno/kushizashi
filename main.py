import asyncio
from collections import defaultdict
from pprint import pprint

import aiohttp
import click


class PivotalFetcher:
  def __init__(self, token):
    self.headers = {'X-TrackerToken': token}

  async def start_fetching(self, session, result_container):
    self.session = session
    self.result_container = result_container
    await self.fetch_projects()

  async def fetch_projects(self):
    resp = await self.session.get(
      'https://www.pivotaltracker.com/services/v5/projects',
      headers=self.headers
    )
    projects = await resp.json()
    await asyncio.wait(map(self.fetch_stories, projects))

  async def fetch_stories(self, project):
    print('fetching its stories:', project['id'])

    resp = await self.session.get(
      'https://www.pivotaltracker.com/services/v5/projects/{}/stories'.format(project['id']),
      headers=self.headers
    )
    stories = await resp.json()
    await asyncio.wait(map(self.fetch_owners, stories))

  async def fetch_owners(self, story):
    print('fetching its owners:', story['id'])

    resp = await self.session.get(
      'https://www.pivotaltracker.com/services/v5/projects/{}/stories/{}/owners'.format(story['project_id'], story['id']),
      headers=self.headers
    )
    owners = await resp.json()

    for owner in owners:
      self.result_container[owner['username']].append('https://www.pivotaltracker.com/story/show/{}'.format(story['id']))


class GitHubFetcher:
  def __init__(self, token):
    self.headers = {'Authorization': 'token ' + token}

  async def start_fetching(self, session, result_container):
    self.session = session
    self.result_container = result_container
    await self.fetch_repositories()

  async def fetch_repositories(self):
    resp = await self.session.get(
      'https://api.github.com/orgs/glucoseinc/repos',
      headers=self.headers
    )
    repositories = await resp.json()
    await asyncio.wait(map(self.fetch_issues, repositories))

  async def fetch_issues(self, repository):
    print('fetching its issues:', repository['id'])

    resp = await self.session.get(
      repository['issues_url'].replace('{/number}', ''),
      headers=self.headers
    )
    issues = await resp.json()

    for issue in issues:
      for assignee in issue['assignees']:
        self.result_container[assignee['login']].append(issue['html_url'])


async def fetch_parallelly(*fetchers):
  result_container = defaultdict(list)

  async with aiohttp.ClientSession() as session:
    await asyncio.wait([
      fetcher.start_fetching(session, result_container)
      for fetcher in fetchers
    ])

  return dict(result_container)


@click.command()
@click.option('--github-token', type=click.STRING, required=True)  # can be taken from github.com/settings/tokens
@click.option('--pivotal-token', type=click.STRING, required=True)  # can be taken from pivotaltracker.com/profile
def main(github_token, pivotal_token):
  github = GitHubFetcher(github_token)
  pivotal = PivotalFetcher(pivotal_token)

  assignees = asyncio.get_event_loop().run_until_complete(fetch_parallelly(github, pivotal))
  pprint(assignees)


if __name__ == '__main__':
  main()
