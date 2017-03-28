import asyncio
from collections import defaultdict
from pprint import pprint

import aiohttp
import click


class PivotalFetcher:
  def __init__(self, token):
    self.token = token

  async def start_fetching(self, session, result_container):
    self.session = session
    self.result_container = result_container
    await self.fetch_projects()

  async def fetch_projects(self):
    resp = await self.session.get(
      'https://www.pivotaltracker.com/services/v5/projects',
      headers={'X-TrackerToken': self.token}
    )
    projects = await resp.json()
    await asyncio.wait(map(self.fetch_stories, projects))

  async def fetch_stories(self, project):
    print('fetching its stories:', project['id'])

    resp = await self.session.get(
      'https://www.pivotaltracker.com/services/v5/projects/{}/stories'.format(project['id']),
      headers={'X-TrackerToken': self.token}
    )
    stories = await resp.json()
    await asyncio.wait(map(self.fetch_owners, stories))

  async def fetch_owners(self, story):
    print('fetching its owners:', story['id'])

    resp = await self.session.get(
      'https://www.pivotaltracker.com/services/v5/projects/{}/stories/{}/owners'.format(story['project_id'], story['id']),
      headers={'X-TrackerToken': self.token}
    )
    owners = await resp.json()

    for owner in owners:
      self.result_container[owner['username']].append('https://www.pivotaltracker.com/story/show/{}'.format(story['id']))


