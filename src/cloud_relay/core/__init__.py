"""Cloud-neutral cross-cutting infrastructure.

Contains the shared configuration base (:mod:`cloud_relay.core.config`), the
domain exception hierarchy (:mod:`cloud_relay.core.errors`), and logging setup
(:mod:`cloud_relay.core.logging`).

This package is provider-agnostic: it imports nothing from boto3, google-cloud,
azure-sdk, or any cloud SDK. Provider-specific machinery (client factories,
SDK error translation, per-cloud settings) lives under
``cloud_relay.services.<provider>._core``.
"""
