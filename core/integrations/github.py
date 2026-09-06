"""GitHub: branch protection checks — the two things a change-management
control review asks about most often. Uses urllib (stdlib) rather than
adding `requests` as a new dependency; GitHub's REST API needs nothing
requests would meaningfully simplify for two GET calls.

config = {"owner": "acme-corp", "repo": "backend", "branch": "main"}
  ("branch" optional, defaults to "main")
credentials = {"token": "<a GitHub personal access token with repo scope>"}
"""
import json
import urllib.error
import urllib.request

from .base import CheckOutcome, IntegrationError

API_BASE = 'https://api.github.com'


class GitHubProvider:
    def _get(self, path, token):
        req = urllib.request.Request(
            f'{API_BASE}{path}',
            headers={
                'Authorization': f'Bearer {token}',
                'Accept': 'application/vnd.github+json',
                'User-Agent': 'qms-isms-platform',
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.status, json.loads(resp.read() or b'{}')
        except urllib.error.HTTPError as exc:
            try:
                body = json.loads(exc.read() or b'{}')
            except (ValueError, TypeError):
                body = {}
            return exc.code, body
        except urllib.error.URLError as exc:
            raise IntegrationError(f'Could not reach GitHub: {exc.reason}')

    def test_connection(self, credentials, config):
        token = credentials.get('token')
        if not token:
            raise IntegrationError('A GitHub personal access token is required.')
        status, body = self._get('/user', token)
        if status != 200:
            raise IntegrationError(f'GitHub rejected this token: {body.get("message", status)}')
        return {'connected_as': body.get('login')}

    def run_checks(self, credentials, config):
        token = credentials.get('token')
        owner = config.get('owner')
        repo = config.get('repo')
        branch = config.get('branch') or 'main'
        if not (token and owner and repo):
            raise IntegrationError('This GitHub integration needs a token, owner, and repo configured.')

        status, branch_data = self._get(f'/repos/{owner}/{repo}/branches/{branch}', token)
        if status == 404:
            raise IntegrationError(f'Branch "{branch}" not found on {owner}/{repo} — check the integration config.')
        if status != 200:
            raise IntegrationError(f'GitHub error fetching branch info: {branch_data.get("message", status)}')

        protected = bool(branch_data.get('protected'))
        outcomes = [
            CheckOutcome(
                key='branch_protection',
                label=f'Branch protection enabled on {owner}/{repo}@{branch}',
                passed=protected,
                detail=f'GitHub reports protected={protected} for {owner}/{repo}@{branch}.',
                control_identifier='A.8.32',
            ),
        ]

        required_reviews = False
        review_detail = (
            f'{owner}/{repo}@{branch} is not protected at all, so no review requirement can be in effect.'
        )
        if protected:
            pr_status, pr_data = self._get(f'/repos/{owner}/{repo}/branches/{branch}/protection', token)
            if pr_status == 200:
                required_reviews = bool(pr_data.get('required_pull_request_reviews'))
                review_detail = (
                    f'required_pull_request_reviews is '
                    f'{"configured" if required_reviews else "not configured"} on {owner}/{repo}@{branch}.'
                )
            elif pr_status == 403:
                review_detail = (
                    'This token does not have admin access on the repo, so the protection rules '
                    '(including the review requirement) could not be read.'
                )
            else:
                review_detail = f'GitHub error reading protection rules: {pr_data.get("message", pr_status)}'

        outcomes.append(CheckOutcome(
            key='required_reviews',
            label=f'Pull request review required before merge on {owner}/{repo}@{branch}',
            passed=required_reviews,
            detail=review_detail,
            control_identifier='A.8.25',
        ))
        return outcomes
