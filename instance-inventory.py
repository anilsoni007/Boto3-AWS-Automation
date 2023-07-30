import boto3
import csv
aws_mang_Cons=boto3.session.Session(profile_name='ec2_wala')
ec2_cons=aws_mang_Cons.client(service_name='ec2', region_name='ap-south-1')
file=open('myinventory.csv','w',newline='')
content=csv.writer(file)
content.writerow(['S.No.', 'AMI','Instace-Id', 'Instance-Type', 'Availability-Zone', 'Arch', 'State'])
response=ec2_cons.describe_instances()
counting=1
for each in response.get('Reservations'):
     for each_instance in each.get('Instances'):
          print(counting,each_instance.get('ImageId'), each_instance.get('InstanceId'),each_instance.get('InstanceType'),each_instance.get('Placement').get('AvailabilityZone'), each_instance.get('Architecture'),each_instance.get('State').get('Name'))
          content.writerow([counting,each_instance.get('ImageId'), each_instance.get('InstanceId'),each_instance.get('InstanceType'),each_instance.get('Placement').get('AvailabilityZone'), each_instance.get('Architecture'),each_instance.get('State').get('Name')])
          counting=counting+1
file.close()
