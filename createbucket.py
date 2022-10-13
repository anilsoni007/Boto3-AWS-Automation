
import boto3
#plz save the profile information in system using aws config tool
#profile_name is the name you have given for the user 
aws_mang_cons=boto3.session.Session(profile_name='ec2_wala')
s3_cons=aws_mang_cons.client(service_name='s3',region_name='us-east-1')
s3_cons.create_bucket(Bucket='myfirs-bucket-xx00899888')
print('your bucket is created successfully!!')
