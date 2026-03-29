from django.db import models


class HaulerDispatchRow(models.Model):
    """
    Index for autonomous haulers: one row per ObjectDB id in the dispatch pool.
    Queried with next_run__lte=now ORDER BY next_run LIMIT N for large fleets.
    """

    objectdb_id = models.PositiveIntegerField(primary_key=True)
    next_run = models.DateTimeField()

    class Meta:
        db_table = "world_hauler_dispatch"
        indexes = [
            models.Index(fields=["next_run"]),
        ]
