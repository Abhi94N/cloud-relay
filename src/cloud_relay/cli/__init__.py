"""Typer CLI adapter.

A thin command-line surface over the service library, intended for operators
and debugging. Commands parse arguments, call a service method, and render the
result through :mod:`cloud_relay.cli.output`. The CLI depends only on
:mod:`cloud_relay.services` and :mod:`cloud_relay.core`; it never imports from
:mod:`cloud_relay.api`.
"""
