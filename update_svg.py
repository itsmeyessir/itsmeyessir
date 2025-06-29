import requests
import os
import re
from datetime import datetime, date

GITHUB_TOKEN = os.getenv('MY_PAT')
USERNAME = 'itsmeyessir'
SVG_PATHS = ['dark_mode.svg', 'light_mode.svg']

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
    if not GITHUB_TOKEN:
        print("[ERROR] MY_PAT is not set. Check your workflow secret name and value.")
        raise SystemExit(1)
    headers = {'Authorization': f'bearer {GITHUB_TOKEN}'}
    variables = {'login': USERNAME}
    response = requests.post(
        'https://api.github.com/graphql',
        json={'query': graphql_query, 'variables': variables},
        headers=headers
    )
    if response.status_code != 200:
        print(f"[ERROR] GitHub API returned status {response.status_code}")
        print(f"[ERROR] Response: {response.text}")
        raise SystemExit(1)
    data = response.json().get('data', {}).get('user')
    if not data:
        print(f"[ERROR] No user data returned. Full response: {response.text}")
        raise SystemExit(1)
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

def update_svg(stats, svg_path):
    with open(svg_path, 'r', encoding='utf-8') as f:
        svg = f.read()
    for key, value in stats.items():
        svg = re.sub(f'id="{key}">.*?<', f'id="{key}">{value}<', svg)
    # Update uptime
    uptime = calculate_uptime()
    svg = re.sub('id="uptime">.*?<', f'id="uptime">{uptime}<', svg)
    with open(svg_path, 'w', encoding='utf-8') as f:
        f.write(svg)

def main():
    print("Token present:", bool(GITHUB_TOKEN))
    stats = fetch_github_stats()
    for svg_path in SVG_PATHS:
        update_svg(stats, svg_path)

if __name__ == '__main__':
    main()
