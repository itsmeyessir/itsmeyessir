import requests
import os
import re
import json
from datetime import datetime, date

GITHUB_TOKEN = os.getenv('MY_PAT')
USERNAME = 'itsmeyessir'
SVG_PATHS = ['dark_mode.svg', 'light_mode.svg']
CACHE_PATH = 'loc_cache.json'

# GraphQL query for GitHub stats (all years for commit count)
graphql_query = '''
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    repositories(privacy: PUBLIC, first: 100) {
      totalCount
      nodes { name }
      pageInfo { hasNextPage endCursor }
    }
    contributionsCollection(from: $from, to: $to) {
      totalCommitContributions
      totalRepositoriesWithContributedCommits
      totalPullRequestContributions
      totalIssueContributions
      totalPullRequestReviewContributions
      totalRepositoryContributions
      totalRepositoriesWithContributedCommits
      totalRepositoriesWithContributedIssues
      totalRepositoriesWithContributedPullRequests
      totalRepositoriesWithContributedPullRequestReviews
      totalContributions
    }
    followers { totalCount }
    starredRepositories { totalCount }
    id
  }
}
'''

# GraphQL query for commits in a repo
def commits_query(repo, cursor=None):
    return {
        "query": '''
        query($owner: String!, $name: String!, $cursor: String) {
          repository(owner: $owner, name: $name) {
            defaultBranchRef {
              target {
                ... on Commit {
                  history(first: 100, after: $cursor) {
                    edges {
                      node {
                        author { user { login } }
                        additions
                        deletions
                      }
                    }
                    pageInfo { hasNextPage endCursor }
                  }
                }
              }
            }
          }
        }
        ''',
        "variables": {"owner": USERNAME, "name": repo, "cursor": cursor}
    }

def fetch_github_stats():
    if not GITHUB_TOKEN:
        print("[ERROR] MY_PAT is not set. Check your workflow secret name and value.")
        raise SystemExit(1)
    headers = {'Authorization': f'bearer {GITHUB_TOKEN}'}
    variables = {
        'login': USERNAME,
        'from': '2008-01-01T00:00:00Z',  # GitHub launch year, covers all years
        'to': datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
    }
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
    return data

def calculate_uptime():
    start_date = date(2022, 8, 16)
    today = date.today()
    delta = today - start_date
    years = delta.days // 365
    months = (delta.days % 365) // 30
    days = (delta.days % 365) % 30
    return f"{years} years, {months} months, {days} days"

def get_loc_for_repo(repo, headers, cache):
    # Use cache if available
    if repo in cache:
        return cache[repo]
    additions = 0
    deletions = 0
    cursor = None
    while True:
        q = commits_query(repo, cursor)
        r = requests.post('https://api.github.com/graphql', json=q, headers=headers)
        if r.status_code != 200:
            break
        history = r.json()['data']['repository']['defaultBranchRef']
        if not history:
            break
        history = history['target']['history']
        for edge in history['edges']:
            node = edge['node']
            if node['author'] and node['author']['user'] and node['author']['user']['login'] == USERNAME:
                additions += node['additions']
                deletions += node['deletions']
        if not history['pageInfo']['hasNextPage']:
            break
        cursor = history['pageInfo']['endCursor']
    cache[repo] = {'add': additions, 'del': deletions}
    return cache[repo]

def get_total_loc(repos, headers):
    # Load cache
    try:
        with open(CACHE_PATH, 'r') as f:
            cache = json.load(f)
    except Exception:
        cache = {}
    total_add = 0
    total_del = 0
    for repo in repos:
        loc = get_loc_for_repo(repo, headers, cache)
        total_add += loc['add']
        total_del += loc['del']
    # Save cache
    with open(CACHE_PATH, 'w') as f:
        json.dump(cache, f)
    return total_add, total_del

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
    data = fetch_github_stats()
    headers = {'Authorization': f'bearer {GITHUB_TOKEN}'}
    # Get all repo names (handle pagination if needed)
    repos = [repo['name'] for repo in data['repositories']['nodes']]
    total_add, total_del = get_total_loc(repos, headers)
    loc_count = total_add - total_del
    contribs = data['contributionsCollection']
    stats = {
        'repo_count': data['repositories']['totalCount'],
        'commit_count': contribs['totalCommitContributions'],
        'contrib_count': contribs['totalRepositoriesWithContributedCommits'],
        'star_count': data['starredRepositories']['totalCount'],
        'follower_count': data['followers']['totalCount'],
        'loc_count': loc_count,
        'loc_add': total_add,
        'loc_del': total_del,
        'total_contributions': contribs['totalContributions'],
        'pr_count': contribs['totalPullRequestContributions'],
        'issue_count': contribs['totalIssueContributions'],
        'review_count': contribs['totalPullRequestReviewContributions']
    }
    for svg_path in SVG_PATHS:
        update_svg(stats, svg_path)

if __name__ == '__main__':
    main()
