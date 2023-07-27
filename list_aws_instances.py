import boto3
aws_mang_cons=boto3.session.Session(profile_name='ec2_wala')
ec2_cons=aws_mang_cons.client(service_name='ec2',region_name='ap-south-1')
response=ec2_cons.describe_instances().get('Reservations')
for each in response:
    for each_id in each.get('Instances'):
        print(each_id.get('InstanceId'))
