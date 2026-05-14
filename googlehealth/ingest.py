"""Map Google Health API payloads onto django-healthdatamodel records.

Public entry points will call ``healthdatamodel.ingest.ingest_records`` and
``healthdatamodel.schemas.RecordInput`` / ``WorkoutInput``; this module is the
only place that knows about the Google Health response shape.
"""
