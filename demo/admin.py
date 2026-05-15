"""Wire healthdatamodel's unregistered admin classes into the demo project.

The upstream package exposes ``RecordAdmin`` / ``WorkoutAdmin`` /
``WearableConnectionAdmin`` as classes but doesn't call ``admin.site.register``
itself — that lets each consumer decide whether to expose these in their own
admin. The demo registers them so you can browse synced data at
``/admin/healthdatamodel/record/`` and friends.
"""

from django.contrib import admin
from healthdatamodel.admin import (
    DataSourceRankingAdmin,
    RecordAdmin,
    WearableConnectionAdmin,
    WorkoutAdmin,
    WorkoutMetadataEntryAdmin,
)
from healthdatamodel.models import (
    DataSourceRanking,
    Record,
    WearableConnection,
    Workout,
    WorkoutMetadataEntry,
)

admin.site.register(Record, RecordAdmin)
admin.site.register(Workout, WorkoutAdmin)
admin.site.register(WorkoutMetadataEntry, WorkoutMetadataEntryAdmin)
admin.site.register(WearableConnection, WearableConnectionAdmin)
admin.site.register(DataSourceRanking, DataSourceRankingAdmin)
