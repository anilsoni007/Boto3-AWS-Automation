import boto3
aws_mang_cons=boto3.session.Session(profile_name='ec2_wala')
vols_cons=aws_mang_cons.client(service_name='ec2',region_name='ap-south-1')
response=vols_cons.describe_volumes(Filters=[{'Name': 'status', 'Values':['in-use']}])
for each in response.get('Volumes'):
    print(each.get('VolumeId'))
