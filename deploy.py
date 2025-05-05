import os
import subprocess
import sys
import time
import json
import string
import secrets

# Define the current directory (where the script is located)
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
PYTHON_RESTORE_SCRIPT = os.path.join(SCRIPT_DIR, 'restore.py')
DOCKER_COMPOSE_FILE = os.path.join(SCRIPT_DIR, 'docker-compose.yml')
CONFIG_FILE = os.path.join(SCRIPT_DIR, 'config.json')



def generate_secure_password(length=16):
    """Generate a secure random alphanumeric password."""
    alphabet = string.ascii_letters + string.digits  # A-Z, a-z, 0-9 only
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def check_docker():
    print("Checking if Docker is installed and running...")
    try:
        subprocess.run(["docker", "--version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        subprocess.run(["docker", "info"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print("Docker is installed and running.")
    except subprocess.CalledProcessError:
        print("Docker is not installed or not running. Please install/start Docker to proceed.")
        sys.exit(1)


def check_docker_compose():
    print("Checking if Docker Compose is installed...")
    try:
        subprocess.run(["docker-compose", "--version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print("Docker Compose is installed.")
    except subprocess.CalledProcessError:
        print("Docker Compose is not installed. Please install Docker Compose to proceed.")
        sys.exit(1)


def check_python_docker_module():
    print("Checking if the Python Docker module is installed...")
    try:
        import docker
        print("Python Docker module is installed.")
    except ImportError:
        print("Python Docker module is not installed. Please install it using 'pip install docker'.")
        sys.exit(1)


def load_environment_variables():
    or_admin_password = None
    keycloak_password = None

    if os.path.exists(CONFIG_FILE):
        print(f"Loading environment variables from {CONFIG_FILE}...")
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)

            # Generate OR_ADMIN_PASSWORD if needed
            if not config.get("OR_ADMIN_PASSWORD"):
                or_admin_password = generate_secure_password()
                print("\n" + "*" * 50)
                print("* Generated secure OR_ADMIN_PASSWORD:")
                print(f"   {or_admin_password}")
                print("   **  Please record this password now — it will not be shown again.")
                print("*" * 50 + "\n")

            # Generate KEYCLOAK_ADMIN_PASSWORD if needed
            if not config.get("KEYCLOAK_ADMIN_PASSWORD"):
                keycloak_password = generate_secure_password()
                print("\n" + "*" * 50)
                print("* Generated secure KEYCLOAK_ADMIN_PASSWORD:")
                print(f"   {keycloak_password}")
                print("   **  Please record this password now — it will not be shown again.")
                print("*" * 50 + "\n")

            for key in config:
                if key == "OR_ADMIN_PASSWORD":
                    os.environ[key] = config[key] if config[key] else or_admin_password
                elif key == "KEYCLOAK_ADMIN_PASSWORD":
                    os.environ[key] = config[key] if config[key] else keycloak_password
                else:
                    os.environ[key] = config[key]

                # Mask password output
                if key in ["OR_ADMIN_PASSWORD", "KEYCLOAK_ADMIN_PASSWORD"]:
                    print(f"Set environment variable: {key}=********")
                else:
                    print(f"Set environment variable: {key}={os.environ[key]}")
    else:
        print(f"No config file found at {CONFIG_FILE}. Proceeding with defaults.")
        

def is_docker_compose_running():
    try:
        result = subprocess.run(
            ["docker-compose", "-p", "openremote", "-f", DOCKER_COMPOSE_FILE, "ps", "--services", "--filter", "status=running"],
            check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        running_services = result.stdout.decode().strip().splitlines()
        return len(running_services) > 0
    except subprocess.CalledProcessError:
        return False


def prompt_to_remove_stack():
    response = input("Docker Compose stack appears to be running. Do you want to stop and remove it before deploying a new stack? (y/N): ").strip().lower()
    if response == 'y':
        print("Removing existing Docker Compose stack...")
        subprocess.run(["docker-compose", "-p", "openremote", "-f", DOCKER_COMPOSE_FILE, "down"], check=True)
    else:
        print("Exiting without making changes.")
        sys.exit(0)


def start_docker_compose():
    print("Bringing up Docker Compose stack...")
    subprocess.run(["docker-compose", "-p", "openremote", "-f", DOCKER_COMPOSE_FILE, "up", "-d"], check=True)


def wait_for_containers():
    print("Waiting for containers to be fully up...")
    time.sleep(10)


def run_post_deployment_script():
    print("Running post-deployment tasks...")
    subprocess.run(["python", PYTHON_RESTORE_SCRIPT], check=True)
    print("Post-deployment tasks completed.")


def deploy(force=False):
    check_docker()
    check_docker_compose()
    check_python_docker_module()

    if is_docker_compose_running():
        if force:
            print("Docker Compose stack is running. Stopping and removing it before deploying new stack...")
            subprocess.run(["docker-compose", "-p", "openremote", "-f", DOCKER_COMPOSE_FILE, "down"], check=True)
        else:
            prompt_to_remove_stack()

    load_environment_variables()
    start_docker_compose()
    wait_for_containers()
    run_post_deployment_script()
    print("Deployment complete. Post-deployment tasks have been executed.")


if __name__ == "__main__":
    force_flag = "--force" in sys.argv
    deploy(force=force_flag)
