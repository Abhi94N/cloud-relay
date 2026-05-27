"""Base class shared by every AWS service wrapper.

:class:`BaseService` removes per-service constructor boilerplate and enforces a
single contract: every concrete AWS service declares the boto3 service name it
wraps via the ``service_name`` class attribute. The matching client is resolved
from the injected :class:`~cloud_relay.services.aws._core.auth.ClientFactory`
exactly once, at construction.

Future cloud packages should define their own analogous base (e.g.
``services/gcp/_core/service.py``) since GCP and Azure use entirely different
client objects; there is no single cross-cloud base worth abstracting today.
"""

from cloud_relay.services.aws._core.auth import ClientFactory


class BaseService:
    """Base for all AWS service wrappers.

    Concrete subclasses MUST set the class attribute :attr:`service_name` to the
    boto3 service identifier (for example ``"secretsmanager"`` or ``"s3"``).
    Subclasses then implement operation methods that call ``self._client`` and
    translate botocore errors via
    :func:`cloud_relay.services.aws._core.errors.translate_error`.

    Attributes:
        service_name: boto3 service identifier; must be set by subclasses.
    """

    service_name: str

    def __init__(self, factory: ClientFactory) -> None:
        """Resolve and store the boto3 client for this service.

        Args:
            factory: The client factory the service draws its client from.

        Raises:
            NotImplementedError: If the subclass did not set ``service_name``.
        """
        if not getattr(self, "service_name", None):
            raise NotImplementedError(
                f"{type(self).__name__} must define a `service_name` class attribute"
            )
        self._factory = factory
        self._client = factory.client(self.service_name)
