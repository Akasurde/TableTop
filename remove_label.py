import click
import requests
import os
from typing import Optional


BASE_URL = 'https://api.github.com'

@click.command()
@click.option(
    '--owner',
    '-o',
    required=True,
    help='The GitHub repository owner (e.g., "octocat").'
)
@click.option(
    '--repo',
    '-r',
    required=True,
    help='The GitHub repository name (e.g., "Spoon-Knife").'
)
@click.option(
    '--labels',
    required=True,
    help='Comma-separated list of labels to remove (e.g., "bug,enhancement").'
)
@click.option(
    '--token',
    envvar='GITHUB_TOKEN',
    help='Your GitHub Personal Access Token. Can be set via GITHUB_TOKEN environment variable.',
    hide_input=True # Hides input when typed in terminal for security
)
@click.option(
    '--dry-run',
    is_flag=True,
    default=False,
    help='If set, no changes will be made. Only shows what would happen.'
)
@click.option(
    '--issue-number',
    type=str,
    default=None,
    help='A Comma-separated list of specific issue or pull request numbers to target.'
)
def remove_github_labels(
    owner: str,
    repo: str,
    labels: str,
    token: str,
    dry_run: bool,
    issue_number: Optional[str],
) -> None:
    """
    Removes specific labels from GitHub Issues and Pull Requests.

    This script connects to GitHub using a Personal Access Token and allows
    you to specify a repository, a list of labels to remove, and optionally
    a specific issue/PR number.
    """
    if issue_number:
        issue_numbers = [int(issue) for issue in issue_number.split(',')]
    else:
        issue_numbers = []

    if dry_run:
        click.echo(click.style("DRY RUN MODE: No actual changes will be made.", fg='yellow'))

    click.echo(f"Attempting to remove labels from {owner}/{repo}...")
    if not token:
        with open(os.path.expanduser('~/.github_api')) as f:
            token = f.read().rstrip()
    
    items_processed = 0
    total_labels_removed = 0
    for issue in issue_numbers:
        click.echo(click.style(f"Processing issue: https://github.com/{owner}/{repo}/issues/{issue}", fg='green'))
        gh_issue_api = f'{BASE_URL}/repos/{owner}/{repo}/issues/{issue}'
        headers = {
            "Authorization": f'Bearer {token}',
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        # Get Issue
        r = requests.get(
            gh_issue_api,
            headers=headers,
        )

        if not r.ok:
            print(f'Request Failed: {r.text}')

        # Issue Data
        issue_json = r.json()
        reporter = issue_json['user']['login']
        remove_labels = [label['name'] for label in issue_json['labels']]
        click.echo(f"Reporter: {reporter} {remove_labels}")
        # Parse the labels to remove
        labels_to_remove = [label.strip() for label in labels.split(',') if label.strip()]
        if not labels_to_remove:
            click.echo(click.style("No valid labels provided to remove. Exiting.", fg='red'))
            return

        click.echo(f"Labels to target for removal: {', '.join(labels_to_remove)}")
        labels_removed_count = 0

        for label in labels_to_remove:
            if label in remove_labels:
                click.echo(f"Removing label: {label}")
                if not dry_run:
                    r = requests.delete(
                        f'{BASE_URL}/repos/{owner}/{repo}/issues/{issue}/labels/{label}',
                        headers=headers,
                    )
                    if not r.ok:
                        click.echo(click.style(f"Error removing label '{label}': {r.text}", fg='red'))
                        return
                    labels_removed_count += 1
        items_processed += 1
        click.echo(click.style(f"Removed {labels_removed_count} labels from issue/PR - https://github.com/{owner}/{repo}/issues/{issue}", fg='green'))
        total_labels_removed += labels_removed_count
    
    click.echo("="*80)
    click.echo("\n--- Summary ---")
    click.echo("="*80)
    if dry_run:
        click.echo(click.style(f"DRY RUN complete. Would have removed {total_labels_removed} labels from {items_processed} issues/PRs.", fg='yellow'))
    else:
        click.echo(click.style(f"Operation complete. Removed {total_labels_removed} labels from {items_processed} issues/PRs.", fg='green'))
    click.echo("="*80)

    
if __name__ == '__main__':
    remove_github_labels()
