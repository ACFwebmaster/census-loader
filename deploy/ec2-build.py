
# AWS Crednetials file needs to exist in "/Users/hugh.saalmans/.aws/credentials"


import boto3
import logging
import os
import paramiko
import time

from datetime import datetime

logging.getLogger("paramiko").setLevel(logging.INFO)

AWS_FOLDER = "/Users/hugh.saalmans/.aws"
BLUEPRINT = "ubuntu_16_04_1"
BUILDID = "nano_1_2"
# KEY_PAIR_NAME = "Default"
AVAILABILITY_ZONE = "ap-southeast-2a"  # Sydney, AU

PEM_FILE = AWS_FOLDER + "/LightsailDefaultPrivateKey-ap-southeast-2.pem"

INSTANCE_NAME = "census_loader_instance"


def main():

    # # get AWS credentials (required to copy pg_dump files from S3)
    # aws_access_key_id = ""
    # aws_secret_access_key = ""
    # cred_array = open(AWS_FOLDER + "/credentials", 'r').read().split("\n")
    #
    # for line in cred_array:
    #     bits = line.split("=")
    #     if bits[0].lower() == "aws_access_key_id":
    #         aws_access_key_id = bits[1]
    #     if bits[0].lower() == "aws_secret_access_key":
    #         aws_secret_access_key = bits[1]

    # create lightsail client
    lightsail_client = boto3.client('lightsail')

    # blueprints = lightsail_client.get_blueprints()
    # for bp in blueprints['blueprints']:
    #     if bp['isActive']:
    #         print('{} : {}'.format(bp['blueprintId'], bp['description']))

    # bundles = lightsail_client.get_bundles(includeInactive=False)
    # for bundle in bundles['bundles']:
    #     for k, v in bundle.items():
    #         print('{} : {}'.format(k, v))

    # initial_script = "sudo export DEBIAN_FRONTEND=noninteractive\n" \
    #                  "sudo export AWS_ACCESS_KEY_ID={0}\n" \
    #                  "sudo export AWS_SECRET_ACCESS_KEY={1}"\
    #     .format(aws_access_key_id, aws_secret_access_key)

    response_dict = lightsail_client.create_instances(
        instanceNames=[INSTANCE_NAME],
        availabilityZone=AVAILABILITY_ZONE,
        blueprintId=BLUEPRINT,
        bundleId=BUILDID
        # userData=initial_script
    )
    logger.info(response_dict)

    # wait until instance is running
    instance_dict = get_lightsail_instance(lightsail_client, INSTANCE_NAME)

    while instance_dict["state"]["name"] != 'running':
        logger.info('Waiting 10 seconds... instance is %s' % instance_dict["state"]["name"])
        time.sleep(10)
        instance_dict = get_lightsail_instance(lightsail_client, INSTANCE_NAME)

    logger.info('Waiting 30 seconds... instance is booting')
    time.sleep(30)

    instance_ip = instance_dict["publicIpAddress"]
    logger.info("Public IP address: {0}".format(instance_ip))

    key = paramiko.RSAKey.from_private_key_file(PEM_FILE)
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    # Here 'ubuntu' is user name and 'instance_ip' is public IP of EC2
    ssh_client.connect(hostname=instance_ip, username="ubuntu", pkey=key)
    logger.info('Connected via SSH')

    # # try to silence annoying Debian message about not having a UI
    # cmd = "export DEBIAN_FRONTEND=noninteractive"
    # run_ssh_command(ssh_client, cmd)

    # cmd = "export DEBIAN_FRONTEND=noninteractive\n" \
    #       "export AWS_ACCESS_KEY_ID={0}\n" \
    #       "export AWS_SECRET_ACCESS_KEY={1}"\
    #     .format(aws_access_key_id, aws_secret_access_key)
    # run_ssh_command(ssh_client, cmd)

    # # add AWS credentials and config files
    # cmd = "mkdir ~/.aws"
    # run_ssh_command(ssh_client, cmd)
    #
    # aws_credentials = open(AWS_FOLDER + "/credentials", 'r').read()
    # cmd = "echo {0} > ~/.aws/credentials".format(aws_credentials)
    # run_ssh_command(ssh_client, cmd)
    #
    # aws_config = open(AWS_FOLDER + "/config", 'r').read()
    # cmd = "echo {0} > ~/.aws/config".format(aws_config)
    # run_ssh_command(ssh_client, cmd)

    # # update
    # cmd = "sudo apt-get update -y"
    # run_ssh_command(ssh_client, cmd)

    # # install AWS commands line tools and copy files from S3
    # cmd = "sudo pip3.5 install awscli"
    # run_ssh_command(ssh_client, cmd)

    # cmd = "sudo aws s3 cp s3://minus34.com/opendata/census-2016 ~/git/census-loader/data --recursive"
    # run_ssh_command(ssh_client, cmd)

    # # update
    # cmd = "sudo apt-get update -y"
    # run_ssh_command(ssh_client, cmd)

    # # set AWS keys for SSH
    # cmd = "export AWS_ACCESS_KEY_ID={0}".format(aws_access_key_id)
    # run_ssh_command(ssh_client, cmd)
    #
    # cmd = "export AWS_SECRET_ACCESS_KEY={0}".format(aws_secret_access_key)
    # run_ssh_command(ssh_client, cmd)

    # run each bash command
    bash_file = os.path.abspath(__file__).replace(".py", ".sh")
    bash_commands = open(bash_file, 'r').read().split("\n")

    for cmd in bash_commands:
        if cmd[:1] != "#" and cmd[:1].strip(" ") != "":  # ignore comments and blank lines
            run_ssh_command(ssh_client, cmd)

    ssh_client.close()

    return True


def get_lightsail_instance(lightsail_client, name):
    response = lightsail_client.get_instance(instanceName=name)

    return response["instance"]


def run_ssh_command(ssh_client, cmd):
    start_time = datetime.now()
    logger.info("START : {0} : {1}".format(start_time, cmd))

    stdin, stdout, stderr = ssh_client.exec_command(cmd)

    # for line in stdin.read().splitlines():
    #     logger.info(line)
    stdin.close()

    # too verbose - don't log
    # for line in stdout.read().splitlines():
    #     if line:
    #         logger.info(" {0} : OUTPUT : {1}".format(datetime.now() - start_time, line))
    stdout.close()

    for line in stderr.read().splitlines():
        if line:
            logger.warning(" {0} : ERROR : {1}".format(datetime.now() - start_time, line))
    stderr.close()

    # return True


if __name__ == '__main__':
    logger = logging.getLogger()

    # set logger
    log_file = os.path.abspath(__file__).replace(".py", ".log")
    logging.basicConfig(filename=log_file, level=logging.DEBUG, format="%(asctime)s %(message)s",
                        datefmt="%m/%d/%Y %I:%M:%S %p")

    # setup logger to write to screen as well as writing to log file
    # define a Handler which writes INFO messages or higher to the sys.stderr
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    # set a format which is simpler for console use
    formatter = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')
    # tell the handler to use this format
    console.setFormatter(formatter)
    # add the handler to the root logger
    logging.getLogger('').addHandler(console)

    logger.info("")
    logger.info("Start ec2-build")

    if main():
        logger.info("Finished successfully!")
    else:
        logger.fatal("Something bad happened!")

    logger.info("")
    logger.info("-------------------------------------------------------------------------------")