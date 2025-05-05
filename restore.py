import docker
import os
import sys
import argparse

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

    print("Select the PostgreSQL container to restore the OpenRemote DB backup to:")
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


def display_backup_file_menu():
    """
    Display a menu to select a backup file from the current directory.
    """
    print("Select a backup file:")
    backup_files = [f for f in os.listdir('.') if f.endswith('.sql')]
    
    if not backup_files:
        print("No .sql backup files found.")
        return None

    for i, backup_file in enumerate(backup_files):
        print(f"{i + 1}. {backup_file}")

    try:
        selection = int(input(f"Enter a number (1-{len(backup_files)}): "))
        if 1 <= selection <= len(backup_files):
            return backup_files[selection - 1]
        else:
            print("Invalid selection.")
            return None
    except ValueError:
        print("Please enter a valid number.")
        return None


def restore_postgres_container(container_name, dbname, user, password, backup_file):
    """
    Restore a backup to the PostgreSQL container.
    """
    client = docker.from_env()  # Connect to Docker engine
    container = client.containers.get(container_name)

    # Copy the backup file into the container
    with open(backup_file, 'rb') as f:
        container.put_archive('/tmp', f)

    # Set environment variables for password
    env = {"PGPASSWORD": password}
    
    # Restore the database from the backup
    container.exec_run(f"psql -U {user} -d {dbname} -f /tmp/{backup_file}", environment=env)

    print(f"Restore completed from {backup_file}")


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
    parser = argparse.ArgumentParser(description="Restore PostgreSQL backup")
    parser.add_argument('--container', type=str, help='Name of the container to restore to')
    parser.add_argument('--backup', type=str, help='Backup file to restore from')
    return parser.parse_args()


def main():
    # Parse command line arguments
    args = parse_arguments()

    # If no container or backup file is provided via arguments, interactively prompt the user
    container_name = args.container or None
    backup_file = args.backup or None

    if not backup_file:
        # Display the backup file menu if needed
        backup_file = display_backup_file_menu()

    if not container_name:
        # Find all PostgreSQL containers
        containers = find_postgres_containers()

        # Display the container menu if needed
        container_name = display_container_menu(containers)    

    if container_name and backup_file:
        print(f"Selected container: {container_name}")
        print(f"Selected backup file: {backup_file}")
        
        # Retrieve environment variables from the PostgreSQL container
        env_vars = get_postgres_env_variables(container_name)
        dbname = env_vars.get("POSTGRES_DB", "postgres")
        user = env_vars.get("POSTGRES_USER", "postgres")
        password = env_vars.get("POSTGRES_PASSWORD", "")
        
        # Perform restore from the backup file
        restore_postgres_container(container_name, dbname, user, password, backup_file)
        
    else:
        print("Either container or backup file was not selected. Exiting.")


if __name__ == "__main__":
    main()
