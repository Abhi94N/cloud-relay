"""cloud-relay: consolidated cloud service wrappers.

This package is primarily a *library* of framework-agnostic service modules
(under :mod:`cloud_relay.services`, currently AWS-only), with two thin adapters
layered on top:

* a Typer **CLI** (:mod:`cloud_relay.cli`) for operators and debugging, and
* a FastAPI **HTTP API** (:mod:`cloud_relay.api`) for non-Python consumers or
  when cloud access should sit behind a service boundary.

The package layout reserves room for additional cloud providers
(``services/gcp/``, ``services/azure/``, ...) behind the same shape; ``core/``
is intentionally provider-agnostic.

Import the library directly when calling from Python::

    from cloud_relay.services.aws._core import AwsSettings, ClientFactory
    from cloud_relay.services.aws.secrets_manager import (
        SecretsManagerService, GetSecretValueRequest,
    )
    factory = ClientFactory(AwsSettings(region="us-east-1"))
    svc = SecretsManagerService(factory)
    # svc.get_secret_value(GetSecretValueRequest(secret_id="my/secret"))
"""

__version__ = "0.1.0"
