import docker
import time
import logging
from datetime import datetime, timedelta

# This is a script that kills longrunning docker containers

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def parse_docker_timestamp(timestamp_str):
    try:
        # Docker timestamps are in ISO 8601 format
        return datetime.fromisoformat(timestamp_str).replace(tzinfo=None)
        # return datetime.strptime(timestamp_str, "%Y-%m-%dT%H:%M:%S.%fZ")
    except ValueError:
        # If the above fails, try without microseconds
        return datetime.strptime(timestamp_str, "%Y-%m-%dT%H:%M:%SZ")

def kill_long_running_containers(max_runtime_minutes=35):
    client = docker.from_env()
    logger.info(f"Starting Docker container monitor. Max runtime set to {max_runtime_minutes} minutes.")
    
    while True:
        try:
            containers = client.containers.list()
            current_time = datetime.now()
            logger.info(f"Checking {len(containers)} running containers at {current_time}")
            
            for container in containers:
                try:
                    container_start_time_str = container.attrs['State']['StartedAt']
                    container_start_time = parse_docker_timestamp(container_start_time_str)
                    runtime = current_time - container_start_time

                    
                    logger.info(f"Container {container.name} running for {runtime}")
                    
                    if runtime > timedelta(minutes=max_runtime_minutes):
                        logger.warning(f"Killing container {container.name} (runtime: {runtime})")
                        try:
                            container.kill()
                            logger.info(f"Successfully killed container {container.name}")
                        except Exception as e:
                            logger.error(f"Failed to kill container {container.name}. Error: {str(e)}")
                    else:
                        logger.debug(f"Container {container.name} within runtime limit ({runtime})")
                except KeyError as e:
                    logger.error(f"Failed to process container {container.name}. Missing key: {str(e)}")
                except Exception as e:
                    logger.error(f"Unexpected error processing container {container.name}: {str(e)}")
            
            logger.info("Sleeping for 60 seconds before next check")
            time.sleep(60)
        except docker.errors.APIError as e:
            logger.error(f"Docker API error: {str(e)}")
            time.sleep(60)  # Wait before retrying
        except Exception as e:
            logger.critical(f"Unexpected error occurred: {str(e)}")
            time.sleep(60)  # Wait before retrying

if __name__ == "__main__":
    try:
        kill_long_running_containers()
    except KeyboardInterrupt:
        logger.info("Script terminated by user")
    except Exception as e:
        logger.critical(f"Unexpected error occurred: {str(e)}")