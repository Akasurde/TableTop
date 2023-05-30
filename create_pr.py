#!/usr/bin/env python

import os
import sys

import click

from git import Repo
from git.exc import InvalidGitRepositoryError


@click.command()
@click.option('-o', '--org-name', help='Organization to use', default='ansible')
@click.option('-p', '--src-path', help='Path to source code', default=os.getcwd())
@click.option('-r', '--repo-name', help='Repository to use', default='ansible')
def main(repo_name, org_name, src_path):
    git_repo = None
    origin_name = 'origin'
    try:
        git_repo = Repo(src_path)
    except InvalidGitRepositoryError as e:
        sys.exit(f'{src_path} is not a valid git repository')

    try:
        origin = git_repo.remote(origin_name)
    except ValueError as e:
        sys.exit(f'{e} for the {src_path}')
    origin.push()
    # print(git_repo.remotes)
    # print(repo_name, org_name)


if __name__ == '__main__':
    main()
