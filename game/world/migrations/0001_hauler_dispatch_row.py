# Generated manually for world.HaulerDispatchRow

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="HaulerDispatchRow",
            fields=[
                ("objectdb_id", models.PositiveIntegerField(primary_key=True, serialize=False)),
                ("next_run", models.DateTimeField()),
            ],
            options={
                "db_table": "world_hauler_dispatch",
            },
        ),
        migrations.AddIndex(
            model_name="haulerdispatchrow",
            index=models.Index(fields=["next_run"], name="world_haul_disp_next_run_idx"),
        ),
    ]
