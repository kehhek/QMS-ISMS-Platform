"""AWS: S3 bucket encryption + public-access checks — the two most
commonly-cited AWS controls in a SOC 2 / ISO 27001 audit. Uses boto3,
already a dependency for the platform's own S3 evidence storage backend
(see core/storage.py) — no new dependency needed.

config = {"bucket": "acme-prod-data", "region": "us-east-1"}
credentials = {"access_key_id": "...", "secret_access_key": "..."}
  (a read-only IAM user — s3:GetBucketEncryption, s3:GetPublicAccessBlock,
  s3:ListBucket — is all this ever needs; never write access.)
"""
from .base import CheckOutcome, IntegrationError


class AWSProvider:
    def _client(self, credentials, config):
        import boto3
        return boto3.client(
            's3',
            aws_access_key_id=credentials.get('access_key_id'),
            aws_secret_access_key=credentials.get('secret_access_key'),
            region_name=config.get('region') or 'us-east-1',
        )

    def test_connection(self, credentials, config):
        from botocore.exceptions import BotoCoreError, ClientError

        bucket = config.get('bucket')
        if not bucket:
            raise IntegrationError('An S3 bucket name is required.')
        client = self._client(credentials, config)
        try:
            client.head_bucket(Bucket=bucket)
        except (ClientError, BotoCoreError) as exc:
            raise IntegrationError(f'AWS rejected this request: {exc}')
        return {'connected_bucket': bucket}

    def run_checks(self, credentials, config):
        from botocore.exceptions import BotoCoreError, ClientError

        bucket = config.get('bucket')
        if not bucket:
            raise IntegrationError('This AWS integration needs a bucket configured.')
        client = self._client(credentials, config)

        encrypted = False
        try:
            resp = client.get_bucket_encryption(Bucket=bucket)
            rules = resp.get('ServerSideEncryptionConfiguration', {}).get('Rules', [])
            encrypted = len(rules) > 0
            encryption_detail = (
                f'{len(rules)} default encryption rule(s) configured on {bucket}.' if encrypted
                else f'No default encryption configured on {bucket}.'
            )
        except ClientError as exc:
            code = exc.response.get('Error', {}).get('Code')
            if code == 'ServerSideEncryptionConfigurationNotFoundError':
                encryption_detail = f'No default encryption configured on {bucket}.'
            else:
                raise IntegrationError(f'AWS error checking bucket encryption on {bucket}: {exc}')
        except BotoCoreError as exc:
            raise IntegrationError(f'AWS error checking bucket encryption on {bucket}: {exc}')

        public_blocked = False
        try:
            resp = client.get_public_access_block(Bucket=bucket)
            cfg = resp.get('PublicAccessBlockConfiguration', {})
            public_blocked = all(cfg.get(k) for k in (
                'BlockPublicAcls', 'IgnorePublicAcls', 'BlockPublicPolicy', 'RestrictPublicBuckets',
            ))
            access_detail = (
                f'Public access block is {"fully enabled" if public_blocked else "only partially enabled"} on {bucket}.'
            )
        except ClientError as exc:
            code = exc.response.get('Error', {}).get('Code')
            if code == 'NoSuchPublicAccessBlockConfiguration':
                access_detail = f'No public access block configuration exists on {bucket} — public access is not blocked.'
            else:
                raise IntegrationError(f'AWS error checking public access block on {bucket}: {exc}')
        except BotoCoreError as exc:
            raise IntegrationError(f'AWS error checking public access block on {bucket}: {exc}')

        return [
            CheckOutcome(
                key='bucket_encryption',
                label=f'Default encryption enabled on S3 bucket {bucket}',
                passed=encrypted,
                detail=encryption_detail,
                control_identifier='A.8.24',
            ),
            CheckOutcome(
                key='public_access_blocked',
                label=f'Public access blocked on S3 bucket {bucket}',
                passed=public_blocked,
                detail=access_detail,
                control_identifier='A.8.3',
            ),
        ]
