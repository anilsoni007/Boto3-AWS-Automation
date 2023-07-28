import boto3
aws_mang_cons=boto3.session.Session(profile_name='ec2_wala')
ec2_cons=aws_mang_cons.client(service_name='ec2')
response=ec2_cons.start_instances(InstanceIds=['i-0a9df30642009cbab'])
print(f'waiting for your instances to be started.....')
waiter=ec2_cons.get_waiter('instance_running')
waiter.wait(InstanceIds=['i-0a9df30642009cbab'])
print(f'======now your instance is up and running..=========')
