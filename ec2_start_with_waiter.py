import boto3
aws_mg_cons = boto3.session.Session(profile_name='ec2')   # mention the aws profile name
ec2_Cons = aws_mg_cons.client(service_name='ec2',region_name='ap-south-1')    # mention the region name in which you want the ec2 service to be started...
ins_to_start=str(input('plz enter the instance id to start: '))
starting=ec2_Cons.start_instances(InstanceIds=[ins_to_start])
print(f'**************plz wait while ur instance is getting started......!***********')
waiter = ec2_Cons.get_waiter('instance_running')
waiter.wait(InstanceIds=[ins_to_start])
print(f'')
print(f'**************now the instance is started and in running state....!**********')
