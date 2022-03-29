
"""
Create, Monitor and Launch a public-facing web server in the Amazon Cloud
Automated Cloud Services CA1
"""
import boto3
import subprocess
import os
import time
from os import listdir
from botocore.exceptions import ClientError

#boto3 clients

ec2 = boto3.resource('ec2')
ec2_client = boto3.client('ec2')
s3 = boto3.resource("s3")
s3_client = boto3.client('s3')

# constant variables - change the version to avoid name duplication errors
version = 'ca1-01'

bucket_name = 'acs-testing-bucket-30.03.21-' + version
keypair_name = 'pair-of-keys-' + version
sg_name = 'a-sg-group-' + version

file_name = 'bog.jpg'
keypair_full_name = keypair_name + '.pem'

def create_keypair():
    outfile = open(keypair_full_name, 'w')
    key_pair = ec2.create_key_pair(KeyName=keypair_name)

    # change permissions of keypair to read only access for owner
    new_permit_cmd = 'chmod 400 ' + keypair_full_name
    try:
        subprocess.run(new_permit_cmd, check=True, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print('permissions for keypair have been updated')
    except Exception as error:
        print ('Exception thrown : ' + str(error))

    # create new keypair file
    try:
        KeyPairOut = str(key_pair.key_material)
        print(KeyPairOut)
        outfile.write(KeyPairOut)
    except Exception as error:
        print ('Exception thrown : ' + str(error))

def delete_keypair():
    keypair_name = input("Enter a key pair name: ")
    try:
        os.remove(keypair_full_name)
        print('Deleted : ' + keypair_full_name)
    except Exception as error:
        print ('Exception thrown : ' + str(error))

def delete_all_keypairs():
    folder_name = os.getcwd()
    try:
        for file_name in listdir(folder_name):
            if file_name.endswith('.pem'):
                os.remove(folder_name + '/' + file_name)
        print('Deleted all key pairs in project directory')
    except Exception as error:
        print ('Exception thrown : ' + str(error))

def create_instance(sg_id):
    img_url = 'https://' + bucket_name + '.s3-eu-west-1.amazonaws.com/bog.jpg'  #  img_url e.g.  https://acs-ca1-peter-bucket-test.s3-eu-west-1.amazonaws.com/bog.jpg
    user_data = """
    #!/bin/bash
    yum update -y
    yum install httpd -y
    systemctl enable httpd
    systemctl start httpd
    echo "<h5>This web-page is hosted on a Linux EC2 Instance running Apache webserver</h5>" >> /var/www/html/index.html
    echo "<img src="{}">" >> /var/www/html/index.html
    """.format(img_url)

    instance = ec2.create_instances(
        ImageId='ami-079d9017cb651564d',
        MinCount=1,        MaxCount=1,
        InstanceType='t2.micro',
        KeyName=keypair_name,
        SecurityGroupIds=[sg_id],
        UserData=user_data
    )
    print('waiting for instance status: running ....')
    instance[0].wait_until_running()
    instance_id = instance[0].id
    current_instance = list(ec2.instances.filter(InstanceIds=[instance_id]))
    instance_ip = current_instance[0].public_ip_address

    print('EC2 instance status : running')
    print('Instance Id: ' + instance_id)
    print('Instance IP: ' + instance_ip)
    print('Keypair name: ' + keypair_name + '.pem')

    # give web server time to start
    print('waiting for apache to install ....')
    time.sleep(120)
    print('apache installed')

    host_name = ' ec2-user@' + instance_ip

    # ssh into ec2 instance - having issues
    """
    error-message: subprocess.CalledProcessError: Command 'ssh -i pair-of-keys-test-8.pem ec2-user@54.171.112.59 -o StrictHostKeyChecking=no'
    returned non-zero exit status 255
    I tried manually pasting 'ssh -i pair-of-keys-test-8.pem ec2-user@54.171.112.59 -o StrictHostKeyChecking=no' into a terminal window and
    I was brought to the instance immediately. ?
    """
    cmd = 'ssh -i ' + keypair_full_name + host_name + ' -o StrictHostKeyChecking=no'
    ssh_process = subprocess.run(cmd, check=True, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # send web-server status checking script - having issues
    ssh_process = subprocess.Popen(['ssh', '-i', keypair_full_name, host_name],
                                  stdin=subprocess.PIPE, stdout=subprocess.PIPE)

    # run web-server status checking script - having issues
    cmd = 'python'
    subprocess.call('python', 'Check_Webserver/check_webserver.py', check=True, shell=True)

def create_security_group():
    try:
        response = ec2_client.create_security_group(
        Description='ACS CA1 Security Group',
        GroupName=sg_name,
        VpcId='vpc-34c7234d',
        DryRun=False
        )
        print(response)
        print(sg_name + ' has been created')
        apply_security_group_rules(sg_name)
        sg_id = response['GroupId']
        print(sg_id)
        return sg_id
    except ClientError as error:
        print ('Boto3 exception thrown in create_security_group: \n' + str(error))

def apply_security_group_rules(sg_name):
    try:
        ec2_client.authorize_security_group_ingress(
        GroupName=sg_name,
        IpPermissions=[
            {'IpProtocol': 'TCP',
            'FromPort': 22,
            'ToPort': 22,
            'IpRanges': [{'CidrIp': '0.0.0.0/0'}]},
            {'IpProtocol': 'TCP',
            'FromPort': 80,
            'ToPort': 80,
            'IpRanges': [{'CidrIp': '0.0.0.0/0'}]},
            {'IpProtocol': 'TCP',
            'FromPort': 443,
            'ToPort': 443,
            'IpRanges': [{'CidrIp': '0.0.0.0/0'}]}
        ],
        )
        print('Web-server inbound rules have been applied to ' + sg_name)
    except ClientError as error:
        print ('Boto3 exception thrown in apply_security_group_rules: \n' + str(error))

def list_security_group_names():
    security_groups = ec2.security_groups.all()
    security_group_names = []
    for sg in security_groups:
        name = sg.group_name
        security_group_names.append(name)
        print(name)
    return security_group_names

def delete_all_security_groups():
    for sg_name in list_security_group_names():
        try:
            response = ec2_client.delete_security_group(
            GroupName = sg_name
            )
            print(response)
        except ClientError as error:
            print ('Boto3 exception thrown in delete_all_security_groups:\n' + str(error))

def create_bucket():
    try:
        response = s3.create_bucket(Bucket=bucket_name,
        CreateBucketConfiguration={'LocationConstraint': 'eu-west-1'})
        print (response)
        return bucket_name
    except ClientError as error:
        print ('Boto3 exception thrown in create_bucket: ' + str(error))

def put_bucket(bucket_name):
    try:
        response = s3_client.upload_file(file_name, bucket_name, file_name, ExtraArgs={'ACL': 'public-read'})
        print(file_name + ' successfully uploaded to bucket ' + bucket_name)
    except ClientError as error:
        print ('Exception thrown in put_bucket:\n' + str(error))

def delete_bucket_contents():
    bucket_name = input("Enter a bucket name: ")
    bucket = s3.Bucket(bucket_name)
    for key in bucket.objects.all():
        try:
            response = key.delete()
            print (response)
        except Exception as error:
            print (error)

def delete_bucket():
    bucket_name = input("Enter a bucket name: ")
    bucket = s3.Bucket(bucket_name)
    try:
        response = bucket.delete()
        print(response)
    except Exception as error:
        print(error)

def terminate_all_ec2_instances():
    try:
        instances = ec2.instances.all()
        for instance in instances:
            instance = ec2.Instance(instance.id)
            response = instance.terminate()
            print(response)
    except Exception as error:
        print ('Exception thrown in terminate_all_ec2_instances: \n' + str(error))

def launch_new_ec2_instance():
    bucket_name = create_bucket()
    put_bucket(bucket_name)
    create_keypair()
    sg_id = create_security_group()
    create_instance(sg_id)

def main():
    menu = {
        '1' : launch_new_ec2_instance,  # running no errors
        '2' : terminate_all_ec2_instances,  # running no errors
        '3' : create_keypair,    # running no errors
        '4' : delete_keypair,    # running no errors
        '5' : delete_all_keypairs,  # running no errors
        '6' : create_bucket,    # running no errors
        '7' : delete_bucket,    # running no errors
        '8' : put_bucket,   # running no errors
        '9' : delete_bucket_contents,   # running no errors
        '10' : create_security_group,   # running no errors
        '11' : list_security_group_names,   # running no errors
        '12' : delete_all_security_groups,   # running no errors
    }

    # menu options in console and accept console input as selection
    print(' - - - - - - - - - - - -\nBOTO3 AWS AUTOMATION MENU\n - - - - - - - - - - - -')

    while True:
        print('acs-ca1 functionality:\nchoose menu option 1\n - - - - - - - - - - - -')
        for key in menu:
            print(key, '->', menu[key].__name__)
        selection = input("Select a menu item: ")
        menu[selection]()

if __name__ == "__main__":
    main()
