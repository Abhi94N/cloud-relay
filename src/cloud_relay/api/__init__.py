"""FastAPI HTTP adapter.

A thin HTTP surface over the service library, for non-Python consumers or when
cloud access should sit behind a service boundary. Routes parse the request,
call a single (synchronous) service method via ``run_in_threadpool`` so the
event loop is never blocked, and return a typed model. Error-to-HTTP mapping
is handled centrally in :mod:`cloud_relay.api.main`. The API depends only on
:mod:`cloud_relay.services` and :mod:`cloud_relay.core`; it never imports the CLI.

Routes are namespaced by provider (``/aws/...``, later ``/gcp/...`` etc.).
"""
