import asyncio
from collections import defaultdict
import itertools
from pprint import pprint

import aiohttp
import click


SAME_PERSON = {
  'tanigawa': 'oblique1121',
  'manabumatsuura': 'm-matsuura'
}


class BaseFetcher:
  async def start_fetching(self, session, result_container):
    self.session = session
    self.result_container = result_container

  def register(self, assignee, value):
    self.result_container[SAME_PERSON.get(assignee, assignee)].append(value)


class PivotalFetcher(BaseFetcher):
  def __init__(self, token):
    self.headers = {'X-TrackerToken': token}

  async def start_fetching(self, *args):
    await super().start_fetching(*args)

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
      headers=self.headers,
      params={'limit': 10000, 'filter': '-state:accepted'}
    )
    stories = await resp.json()
    await asyncio.wait([self.fetch_owners(project, story) for story in stories])

  async def fetch_owners(self, project, story):
    print('fetching its owners:', story['id'])

    resp = await self.session.get(
      'https://www.pivotaltracker.com/services/v5/projects/{}/stories/{}/owners'.format(story['project_id'], story['id']),
      headers=self.headers
    )
    owners = await resp.json()

    for owner in owners:
      self.register(
        owner['username'],
        (project['name'], story['name'], 'https://www.pivotaltracker.com/story/show/{}'.format(story['id']))
      )


class GitHubFetcher(BaseFetcher):
  def __init__(self, token):
    self.headers = {'Authorization': 'token ' + token}

  async def start_fetching(self, *args):
    await super().start_fetching(*args)

    repositories = await self.fetch_all_pages('https://api.github.com/orgs/glucoseinc/repos')
    await asyncio.wait(map(self.fetch_issues, repositories))

  async def fetch_issues(self, repository):
    print('fetching its issues:', repository['id'])

    issues = await self.fetch_all_pages(repository['issues_url'].replace('{/number}', ''))

    for issue in issues:
      for assignee in issue['assignees']:
        self.register(assignee['login'], (repository['name'], issue['title'], issue['html_url']))

  async def fetch_all_pages(self, url):
    per_page = 100
    fetched = []

    for page in itertools.count(1):
      resp = await self.session.get(url, headers=self.headers, params={'page': page, 'per_page': per_page})
      decoded = await resp.json()
      fetched += decoded

      if per_page > len(decoded):
        return fetched


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
