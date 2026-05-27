"""Cloud service wrappers, grouped by provider.

Each provider has its own subpackage (``aws``, and later ``gcp``, ``azure``,
...). A provider package owns its SDK-specific machinery in ``_core/`` (client
factory, settings, base class, error translator) and exposes one subpackage
per service.

Every service is **framework-agnostic**: it imports only its cloud SDK,
Pydantic, and :mod:`cloud_relay.core`. Nothing here imports FastAPI, Typer,
or Rich, so services are reusable from the library, the API, the CLI,
notebooks, or scripts alike.
"""
