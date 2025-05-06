import docker
import os
import sys
import tarfile
import io
import argparse
import logging
import time

# Setup logging
logging.basicConfig(
    filename=f"{str(int(time.time()))}-restore.log",
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def log(message):
    print(message)
    logging.info(message)

def log_error(message):
    print(message, file=sys.stderr)
    logging.error(message)

def log_output(result):
    stdout = result.output[0].decode() if result.output[0] else ''
    stderr = result.output[1].decode() if result.output[1] else ''

    if stdout:
        log("STDOUT:\n" + stdout)
    if stderr:
        log_error("STDERR:\n" + stderr)

    if result.exit_code != 0:
        log_error(f"Command failed with exit code {result.exit_code}")

def find_postgres_containers():
    client = docker.from_env()
    containers = client.containers.list(all=True)
    return [c for c in containers if 'postgres' in c.name]

def display_container_menu(containers):
    if not containers:
        log("No PostgreSQL containers found.")
        return None
    log("Select the PostgreSQL container:")
    for i, container in enumerate(containers):
        print(f"{i + 1}. {container.name}")
    try:
        selection = int(input(f"Enter a number (1-{len(containers)}): "))
        if 1 <= selection <= len(containers):
            return containers[selection - 1].name
    except ValueError:
        pass
    log_error("Invalid selection.")
    return None

def display_backup_file_menu():
    files = [f for f in os.listdir('.') if f.endswith('.bak')]
    if not files:
        log("No .bak backup files found.")
        return None
    log("Select a backup file:")
    for i, f in enumerate(files):
        print(f"{i + 1}. {f}")
    try:
        selection = int(input(f"Enter a number (1-{len(files)}): "))
        if 1 <= selection <= len(files):
            return files[selection - 1]
    except ValueError:
        pass
    log_error("Invalid selection.")
    return None

def copy_backup_to_container(container, backup_file):
    log(f"Copying backup file '{backup_file}' to container...")
    with open(backup_file, 'rb') as f:
        data = f.read()
    file_tarstream = io.BytesIO()
    with tarfile.open(fileobj=file_tarstream, mode='w') as tar:
        tarinfo = tarfile.TarInfo(name=os.path.basename(backup_file))
        tarinfo.size = len(data)
        tar.addfile(tarinfo, io.BytesIO(data))
    file_tarstream.seek(0)
    container.put_archive('/tmp', file_tarstream)
    log("Backup file copied to /tmp inside container.")

def run_psql(container, cmd, env):
    log(f"Running SQL command: {cmd}")
    result = container.exec_run(f"psql -U postgres -d openremote -c \"{cmd}\"", environment=env, demux=True)
    log_output(result)
    return result

def disconnect_all_connections(container):
    log("Disconnecting all active connections to the 'openremote' database...")
    disconnect_sql = """
        SELECT pg_terminate_backend(pid)
        FROM pg_stat_activity
        WHERE datname = 'openremote' AND pid <> pg_backend_pid();
    """
    result = run_psql(container, disconnect_sql, {})
    if result.exit_code != 0:
        log_error("Failed to disconnect all active connections.")
    else:
        log("All active connections disconnected.")

def restore_database(container, backup_file, env):
    disconnect_all_connections(container)

    log("Dropping existing 'openremote' database...")
    drop_result = container.exec_run("dropdb openremote", environment=env, demux=True)
    log_output(drop_result)

    log("Creating new 'openremote' database...")
    create_result = container.exec_run("createdb openremote", environment=env, demux=True)
    log_output(create_result)

    run_psql(container, "CREATE EXTENSION IF NOT EXISTS postgis;", env)
    run_psql(container, "CREATE EXTENSION IF NOT EXISTS timescaledb;", env)
    run_psql(container, "SELECT timescaledb_pre_restore();", env)

    log("Running pg_restore...")
    result = container.exec_run(
        f"pg_restore -Fc --verbose -U postgres -d openremote /tmp/{os.path.basename(backup_file)}",
        environment=env,
        demux=True
    )
    log_output(result)

    run_psql(container, "SELECT timescaledb_post_restore();", env)

    if result.exit_code != 0:
        log_error("Restore failed.")
    else:
        log("Database restored successfully.")

def get_postgres_env(container):
    env_vars = container.attrs['Config']['Env']
    return {e.split('=')[0]: e.split('=')[1] for e in env_vars if '=' in e and e.startswith("POSTGRES_")}

def parse_arguments():
    parser = argparse.ArgumentParser(description="Restore OpenRemote PostgreSQL DB")
    parser.add_argument('--container', help='PostgreSQL Docker container name')
    parser.add_argument('--backup', help='Path to .bak backup file')
    return parser.parse_args()

def main():
    args = parse_arguments()
    container_name = args.container or display_container_menu(find_postgres_containers())
    backup_file = args.backup or display_backup_file_menu()

    if not container_name or not backup_file:
        log_error("Both container and backup file are required.")
        return

    client = docker.from_env()
    container = client.containers.get(container_name)
    env_vars = get_postgres_env(container)
    password = env_vars.get("POSTGRES_PASSWORD", "")

    env = {"PGPASSWORD": password}

    log(f"Using container: {container_name}")
    log(f"Using backup file: {backup_file}")

    copy_backup_to_container(container, backup_file)
    restore_database(container, backup_file, env)

if __name__ == "__main__":
    main()
