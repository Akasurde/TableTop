import json
import os
import requests
import sys

from pathlib import Path

import click

from git import Repo
from git.exc import InvalidGitRepositoryError
from jinja2 import Environment, FileSystemLoader


BASE_URL = 'https://api.github.com'


@click.command()
@click.option('-b', '--base-branch', help='Base Branch name', default='devel')
@click.option('-o', '--org-name', help='Organization to use', default='ansible')
@click.option('-p', '--src-path', help='Path to source code', default=os.getcwd())
@click.option('-r', '--repo-name', help='Repository to use', default='ansible')
@click.option('--push-branch', help='Push branch to origin before creating a pull request', is_flag=True, default=False)
@click.option('--bugfix', help='Bugfix', is_flag=True, default=True)
@click.option('--docs', help='Bugfix', is_flag=True, default=False)
@click.option('--feature', help='Bugfix', is_flag=True, default=False)
@click.option('--tests', help='Bugfix', is_flag=True, default=False)
def main(repo_name, org_name, src_path, push_branch, base_branch, bugfix, docs, feature, tests):
    git_repo = None
    origin_name = 'origin'
    try:
        git_repo = Repo(src_path)
    except InvalidGitRepositoryError as e:
        sys.exit(f'{src_path} is not a valid git repository: {e}')

    try:
        origin = git_repo.remote(origin_name)
    except ValueError as e:
        sys.exit(f'{e} for the {src_path}')

    current_branch = git_repo.active_branch
    if push_branch:
        print(f'Pushing changes to {current_branch}...')
        origin.push(current_branch)
    else:
        print(f'Assuming changes from {current_branch} already pushed to {origin_name}')

    with open(os.path.expanduser('~/.github_api')) as f:
        pat = f.read().rstrip()

    current_commit = git_repo.head.commit
    file_changed = []
    for path in current_commit.diff('HEAD~1'):
        file_changed.append(path.b_path)

    pr_description = current_commit.message.split("\n")[2:-1]

    context = {
        'description': pr_description,
        'bugfix': bugfix,
        'docs': docs,
        'tests': tests,
        'feature': feature,
        'files_changed': file_changed,
    }

    pr_template = "pull_request_template.txt"
    environment = Environment(loader=FileSystemLoader(f"{os.path.dirname(os.path.realpath(__file__))}/templates/"))
    results_template = environment.get_template(pr_template)

    print(str(results_template.render(context)))
    breakpoint()
    create_pull_request(
        org_name,
        repo_name,  # repo_name
        current_commit.summary,  # title
        str(results_template.render(context)),  # description
        "Akasurde:%s" % current_branch.name,  # head_branch
        base_branch,  # base_branch
        pat,  # git_token
    )


def list_paths(root_tree, path=Path(".")):
    for blob in root_tree.blobs:
        yield path / blob.name
    for tree in root_tree.trees:
        yield from list_paths(tree, path / tree.name)


def create_pull_request(project_name, repo_name, title, description, head_branch, base_branch, git_token):
    """Creates the pull request for the head_branch against the base_branch"""
    git_pulls_api = f'{BASE_URL}/repos/{project_name}/{repo_name}/pulls'
    headers = {
        "Authorization": f'Bearer {git_token}',
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    payload = {
        "title": title,
        "body": description,
        "head": head_branch,
        "base": base_branch,
    }

    r = requests.post(
        git_pulls_api,
        headers=headers,
        data=json.dumps(payload))

    if not r.ok:
        print(f'Request Failed: {r.text}')


if __name__ == '__main__':
    main()
