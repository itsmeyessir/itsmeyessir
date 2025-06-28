import requests
import os
from datetime import datetime, date

GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
USERNAME = 'itsmeyessirski'
SVG_PATH = 'dark_mode.svg'

# GraphQL query for GitHub stats
graphql_query = '''
query($login: String!) {
  user(login: $login) {
    repositories(privacy: PUBLIC) { totalCount }
    contributionsCollection { contributionCalendar { totalContributions } }
    followers { totalCount }
    starredRepositories { totalCount }
    contributionsCollection {
      totalCommitContributions
      totalRepositoriesWithContributedCommits
    }
  }
}
'''

def fetch_github_stats():
    headers = {'Authorization': f'bearer {GITHUB_TOKEN}'}
    variables = {'login': USERNAME}
    response = requests.post(
        'https://api.github.com/graphql',
        json={'query': graphql_query, 'variables': variables},
        headers=headers
    )
    response.raise_for_status()
    data = response.json()['data']['user']
    return {
        'repo_count': data['repositories']['totalCount'],
        'commit_count': data['contributionsCollection']['totalCommitContributions'],
        'contrib_count': data['contributionsCollection']['totalRepositoriesWithContributedCommits'],
        'star_count': data['starredRepositories']['totalCount'],
        'follower_count': data['followers']['totalCount'],
        # 'loc_count', 'loc_add', 'loc_del' can be added with more advanced queries or static values
    }

def calculate_uptime():
    start_date = date(2022, 8, 16)
    today = date.today()
    delta = today - start_date
    years = delta.days // 365
    months = (delta.days % 365) // 30
    days = (delta.days % 365) % 30
    return f"{years} years, {months} months, {days} days"

def update_svg(stats):
    with open(SVG_PATH, 'r', encoding='utf-8') as f:
        svg = f.read()
    for key, value in stats.items():
        svg = svg.replace(f'id="{key}">0<', f'id="{key}">{value}<')
    # Update uptime
    uptime = calculate_uptime()
    svg = svg.replace('id="uptime">your uptime here<', f'id="uptime">{uptime}<')
    with open(SVG_PATH, 'w', encoding='utf-8') as f:
        f.write(svg)

def main():
    stats = fetch_github_stats()
    update_svg(stats)

if __name__ == '__main__':
    main()
