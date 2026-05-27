"""AWS provider package.

Houses every AWS service wrapper plus the boto3-specific shared machinery in
:mod:`cloud_relay.services.aws._core`. Each service has its own subpackage
(``secrets_manager``, ``s3``, ...). Adapters import services from here; library
consumers can import services directly.
"""
