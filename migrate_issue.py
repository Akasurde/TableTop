import json
import os
import requests

from pathlib import Path

import click

from jinja2 import Environment, FileSystemLoader


BASE_URL = 'https://api.github.com'


@click.command()
@click.option('--src-org-name', help='Source Organization to use', default='ansible')
@click.option('--src-repo-name', help='Source Repository to use', default='ansible')
@click.option('--dest-org-name', help='Destination Organization to use', default='Akasurde')
@click.option('--dest-repo-name', help='Destination Repository to use', default='TableTop')
@click.option('-i', '--issue', help='Issue to migrate')
def main(src_org_name, src_repo_name, dest_org_name, dest_repo_name, issue):
    with open(os.path.expanduser('~/.github_api')) as f:
        pat = f.read().rstrip()
    
    gh_issue_api = f'{BASE_URL}/repos/{src_org_name}/{src_repo_name}/issues/{issue}'
    headers = {
        "Authorization": f'Bearer {pat}',
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    # Get Source Issue
    r = requests.get(
        gh_issue_api,
        headers=headers,
    )

    if not r.ok:
        print(f'Request Failed: {r.text}')

    # Issue Data
    issue_json = r.json()
    reporter = issue_json['user']['login']

    # Create a new issue at destination repo
    dest_repo_issue_url = f'{BASE_URL}/repos/{dest_org_name}/{dest_repo_name}/issues'
    dest_payload = {
        'title': issue_json['title'],
        'body': issue_json['body'],
    }

    r = requests.post(
        dest_repo_issue_url,
        headers=headers,
        data=json.dumps(dest_payload))

    if not r.ok:
        print(f'Request create a new issue at {dest_org_name}/{dest_repo_name}, Failed: {r.text}')

    dest_new_issue_url = r.json()['url']
    print(f"New issue created at {dest_new_issue_url}")
    dest_comment_payload = {
        'body': f'cc @{reporter}'
    }

    # Notify user 
    dest_new_issue_comment_url = dest_new_issue_url + '/comments'
    print(f'Commenting {dest_new_issue_comment_url}')
    r = requests.post(
        dest_new_issue_comment_url,
        headers=headers,
        data=json.dumps(dest_comment_payload)
    )

    if not r.ok:
        print(f'Failed to comment at {dest_new_issue_comment_url}, Failed: {r.text}')
    
    # Comment issue before closing 
    close_url = gh_issue_api
    close_issue_comment_url = close_url + '/comments'

    context = {
        'reporter': reporter,
        'dest_org_name': dest_org_name,
        'dest_repo_name': dest_repo_name,
        'dest_issue_url': dest_new_issue_url.replace('api.', '').replace('/repos', '')
    }
    src_issue_comment_template = "bug_wrong_repo.txt"
    environment = Environment(loader=FileSystemLoader(f"{os.path.dirname(os.path.realpath(__file__))}/templates/"))
    results_template = environment.get_template(src_issue_comment_template)
    closing_remark = str(results_template.render(context))
    close_comment_payload = {
        'body': closing_remark,
    }

    print(f'Commenting {close_issue_comment_url}')
    r = requests.post(
        close_issue_comment_url,
        headers=headers,
        data=json.dumps(close_comment_payload)
    )

    if not r.ok:
        print(f'Failed to comment at {close_issue_comment_url}, Failed: {r.text}')
    
    # Close origin issue
    closing_payload = {
        'state': 'closed',
        'state_reason': 'completed',
        'labels': ['bug', 'migrated_to_collection_repo'],
    }
    print(f'Closing {close_url}')
    r = requests.patch(
        close_url,
        headers=headers,
        data=json.dumps(closing_payload)
    )
    if not r.ok:
        print(f'Failed to close {close_url}, Request Failed: {r.text}')

    print(f'Locking {close_url}')
    lock_payload = {
        'lock_reason': 'resolved',
    }

    r = requests.put(
        close_url + '/lock',
        headers=headers,
        data=json.dumps(lock_payload)
    )
    if not r.ok:
        print(f'Failed to lock {close_url}, Request Failed: {r.text}')


if __name__ == '__main__':
    main()
