#!/usr/bin/env python
# -*- coding: utf-8 -*-
# PYTHON_ARGCOMPLETE_OK
# Copyright: (c) 2020, Abhijeet Kasurde (@Akasurde) <akasurde@redhat.com>
# MIT License (see LICENSE or https://opensource.org/licenses/MIT)

"""
Script that can be used to re-trigger the shippable RUNs

To trigger a PR CI run
    ./shippable_trigger_job.py -p 1234 --org ansible-collections --repo community.general -r
"""

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import click
import os
import sys
import requests

GITHUB_BASE_URL = "https://api.github.com"
SHIPPABLE_BASE_URL = "https://api.shippable.com/"


def create_github_session():
    token = None
    s = requests.Session()
    with open(os.path.join(os.path.expanduser("~"), '.github_api')) as file_:
        token = file_.read().rstrip("\n")

    if not token:
        sys.exit("Unable to read github api file")

    s.headers.update({'Authorization': 'token %s' % token})
    return s


class ShippableClient():
    def __init__(self):
        self.token = None
        self.session = None
        self.BASE_URL = SHIPPABLE_BASE_URL

    def read_shippable_api(self):
        with open(os.path.join(os.path.expanduser("~"), '.shippable_api')) as file_:
            self.token = file_.read().rstrip("\n")

    def create_shippable_session(self):
        self.session = requests.Session()

        self.session.headers.update({
            'Authorization': 'apiToken %s' % self.token,
            'Accept': "application/json"
        })

    def get_full_project(self, project_full_name=None):
        if not project_full_name:
            return []
        url = self.BASE_URL + 'projects?projectFullNames=%s' % project_full_name
        return self.session.get(url).json()

    def get_run_details(self, commit_sha=None):
        if not commit_sha:
            return []
        url = self.BASE_URL + 'runs?commitShas=%s' % commit_sha
        return self.session.get(url).json()

    def retry_run(self, run_id, project_full_name='', rerun_failed_only=True):
        project_id = self.get_full_project(project_full_name=project_full_name)
        if project_id:
            project_id = project_id[0]['id']
            new_build_url = self.BASE_URL + 'projects/%s/newBuild' % project_id
            run = self.session.post(
                new_build_url,
                json={
                    'isDebug': False,
                    'projectId': project_id,
                    'rerunFailedOnly': rerun_failed_only,
                    'runId': run_id
                }
            )
            return run

    def should_be_restarted(self, run):
        if run['totalTests'] == 0:
            print("Nothing has been run")
            return (True, False)
        url = self.BASE_URL + 'jobs?runIds={id}&status=failed,timeout,unstable'.format(**run)
        response = self.session.get(url).json()

        no_restart_patterns = [
            'fix conflicts and then commit the result.',
        ]

        needs_full_restart_patterns = [
            'Try re-running the entire matrix.',
        ]

        needs_restart_patterns = [
            'If the deploy key is not present in the repository, you can use the "Reset Project" button on the project settings page to restore it.',
            'OutOfMemoryException',
            'ERROR: 500: error: instance token not unique',
            'Failed to create vault token for this job.',
            'ERROR: Tests aborted after exceeding the',
            'ERROR: Failed transfer: ',
        ]
        for job in response:
            job_url = self.BASE_URL + 'jobs/{id}/consoles?download=true'.format(**job)
            content = self.session.get(job_url).content.decode()

            for i in no_restart_patterns:
                if i in content:
                    print('Pattern found: ' + i)
                    return (False, True)

            for i in needs_full_restart_patterns:
                if i in content:
                    print('Pattern found: ' + i)
                    return (True, False)

            for i in needs_restart_patterns:
                if i in content:
                    print('Pattern found: ' + i)
                    return (True, True)
        return (False, None)


@click.command()
@click.option('-p', '--pr')
@click.option('-d', '--debug', help='Debug', is_flag=True, default=False)
@click.option('-r', '--rerun', help='Retrigger successful job', is_flag=True, default=False)
@click.option('--org', help='Organization', default='ansible')
@click.option('--repo', help='Repo Name', default='ansible')
def main(pr, debug, rerun, org, repo):
    github_session = create_github_session()
    shippable = ShippableClient()
    shippable.read_shippable_api()
    shippable.create_shippable_session()
    project_full_name = '%s/%s' % (org, repo)
    pr_number = pr

    pr_url = GITHUB_BASE_URL + "/repos/%s/pulls/%s" % (project_full_name, pr_number)
    pr_obj = github_session.get(pr_url).json()
    if not pr_obj:
        sys.exit("Failed to get PR %s " % pr_number)
    statuses_url = pr_obj['statuses_url']

    statuses = github_session.get(statuses_url).json()
    shippable_statuses = [s for s in statuses if s['context'] == 'Shippable']
    current_shippable_status = shippable_statuses[0]

    if not rerun and current_shippable_status['state'] != 'failure':
        sys.exit("Give PR %s is not failed" % pr_number)
    sha = pr_obj['head']['sha']

    run_details = shippable.get_run_details(commit_sha=sha)
    current_run = run_details[0]
    if not current_run['endedAt']:
        sys.exit("Given job %s is still running..." % current_run['runNumber'])

    # shippable.should_be_restarted(current_run)
    new_run = shippable.retry_run(
        run_id=current_run['id'],
        project_full_name=project_full_name,
        rerun_failed_only=(not rerun),
    )

    new_job = new_run.json()
    print("New job triggered - %s/github/ansible/ansible/runs/%s/summary/console" %
          (SHIPPABLE_BASE_URL, new_job['runNumber']))


if __name__ == "__main__":
    main()
