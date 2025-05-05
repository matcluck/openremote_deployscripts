# openremote_deployscripts
Deployment scripts (along with backup and restore scripts) for OpenRemote

## Requirements
To install the required packages, please run:
```
pip install -r requirements.txt
```

These scripts have been tested on Windows 10 using Python 3.13.2

## deploy.py
Deploys an OpenRemote stack with the following features:
    - Checks if an existing OpenRemote stack is running before continuing
    - Includes functionality to restore from an OpenDeploy database backup
    - Supports a `--force` flag to destroy and recreate the stack without user confirmation
Deployment variables are set using the `config.json` file.

## backup.py
Creates a `.sql` backup file containing a dump of the following tables from the OpenDeploy database:
```
# List of tables to back up
tables = [
    "openremote.alarm",
    "openremote.alarm_asset_link",
    "openremote.asset",
    "openremote.asset_datapoint",
    "openremote.asset_predicted_datapoint",
    "openremote.asset_ruleset",
    "openremote.dashboard",
    "openremote.flyway_schema_history",
    "openremote.gateway_connection",
    "openremote.global_ruleset",
    "openremote.notification",
    "openremote.provisioning_config",
    "openremote.realm_ruleset",
    "openremote.spatial_ref_sys",
    "openremote.syslog_event",
    "openremote.user_asset_link",
    "topology.layer",
    "topology.topology"
]
```

The script prompts the user to select the OpenRemote Postgres container to create the backup from. Alternatively, the `--container` argument can be used to specify the Postgres DB container ID.

## restore.py
Restores an OpenRemote backup created with the `backup.py` script.

The script prompts the user to select the OpenRemote Postgres backup and the target container. Alternatively, the `--container` and `--backup` argument can be used to specify the Postgres DB container ID and the `.sql` backup file.