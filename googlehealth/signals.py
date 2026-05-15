"""Django signals emitted by the webhook receiver.

``notification_received`` fires for every authenticated, non-verification POST
to the receiver view. Connect a handler to drive ingest:

.. code-block:: python

    from django.dispatch import receiver
    from googlehealth.signals import notification_received
    from googlehealth.webhooks import process_notification

    @receiver(notification_received)
    def on_notification(sender, payload, **kwargs):
        process_notification(payload)  # or hand off to celery / etc.

Sender is ``None`` (signal is namespace-only). The ``payload`` keyword carries
the parsed JSON body exactly as Google sent it.
"""

import django.dispatch

notification_received = django.dispatch.Signal()
