import boto3
aws_cons=boto3.session.Session(profile_name='ec2_wala')  # mention your aws profile name.
iam_cons=aws_cons.client(service_name='iam')  # the service console you wish to check.
response=iam_cons.list_users()

for each in response.get('Users'):
    print(each.get('UserName'))
