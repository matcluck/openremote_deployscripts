import docker
import os
import sys
import argparse
import time
import subprocess

def find_postgres_containers():
    """
    Find all PostgreSQL containers that have 'postgres' in their name.
    """
    client = docker.from_env()  # Connect to Docker engine
    containers = client.containers.list(all=True)
    
    # Filter containers that have 'postgres' in their name
    postgres_containers = [container for container in containers if 'postgres' in container.name]

    return postgres_containers


def display_container_menu(containers):
    """
    Display a menu of available containers to choose from.
    """
    if not containers:
        print("No PostgreSQL containers found.")
        return None

    print("Select the PostgreSQL container for OpenRemote to create a backup:")
    for i, container in enumerate(containers):
        print(f"{i + 1}. {container.name}")
    
    try:
        selection = int(input(f"Enter a number (1-{len(containers)}): "))
        if 1 <= selection <= len(containers):
            return containers[selection - 1].name
        else:
            print("Invalid selection.")
            return None
    except ValueError:
        print("Please enter a valid number.")
        return None

def copy_from_container(container_name, container_path, host_path):
    subprocess.run([
        "docker", "cp",
        f"{container_name}:{container_path}",
        host_path
    ], check=True)

def backup_postgres_container(container_name, dbname, user, password, backup_file):
    """
    Back up the entire PostgreSQL database.
    """
    client = docker.from_env()  # Connect to Docker engine
    container = client.containers.get(container_name)

    # Construct the pg_dump command for the entire database
    dump_command = f"pg_dump -U {user} -d {dbname} -Fc -f /tmp/{backup_file}"

    # Set environment variables for password
    env = {"PGPASSWORD": password}
    
    # Execute the pg_dump command inside the container
    container.exec_run(dump_command, environment=env)

    # Copy the backup file from the container to the host
    copy_from_container(container_name,f"/tmp/{backup_file}",backup_file)
    print(f"Backup completed and saved to {backup_file}")


def get_postgres_env_variables(container_name):
    """
    Retrieve PostgreSQL environment variables from the specified container.
    """
    client = docker.from_env()
    container = client.containers.get(container_name)
    
    # Fetch the container's environment variables (if available)
    env_vars = container.attrs['Config']['Env']
    
    # Find specific environment variables related to PostgreSQL
    postgres_env = {}
    for var in env_vars:
        if var.startswith("POSTGRES_"):
            key, value = var.split("=", 1)
            postgres_env[key] = value
            
    return postgres_env


def parse_arguments():
    """
    Parse command-line arguments.
    """
    parser = argparse.ArgumentParser(description="Backup PostgreSQL database")
    parser.add_argument('--container', type=str, help='Name or ID of the container to back up from')
    return parser.parse_args()


def main():
    # Parse command line arguments
    args = parse_arguments()

    # If no container is provided via arguments, interactively prompt the user
    container_name = args.container or None

    if not container_name:
        # Find all PostgreSQL containers
        containers = find_postgres_containers()

        # Display the container menu if needed
        container_name = display_container_menu(containers)

    if container_name:
        print(f"Selected container: {container_name}")
        
        # Retrieve environment variables from the PostgreSQL container
        env_vars = get_postgres_env_variables(container_name)
        dbname = env_vars.get("POSTGRES_DB", "postgres")
        user = env_vars.get("POSTGRES_USER", "postgres")
        password = env_vars.get("POSTGRES_PASSWORD", "")
        
        # Perform backup (back up the entire database)
        backup_file = f"{str(int(time.time()))}-openremote.bak"
        backup_postgres_container(container_name, dbname, user, password, backup_file)
        
    else:
        print("No PostgreSQL container selected. Exiting.")


if __name__ == "__main__":
    main()
