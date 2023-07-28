import boto3
aws_mang_cons=boto3.session.Session(profile_name='ec2_wala')
vols_cons=aws_mang_cons.client(service_name='ec2',region_name='ap-south-1')
response=vols_cons.describe_volumes(Filters=[{'Name': 'tag-key', 'Values' : ['Name']}]).get('Volumes')
#print(response)

for each in response:
    #print(each.get('VolumeId'))
    vols_cons.delete_volume(VolumeId=each.get('VolumeId'))
