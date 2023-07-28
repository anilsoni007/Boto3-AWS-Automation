import boto3
import sys
aws_mng_cons=boto3.session.Session(profile_name='ec2_wala')
ec2_cons=aws_mng_cons.client(service_name='ec2')

print('this is menu driven script to perform listed operations on an EC2 instance')
print("""
          1 Start
          2 Stop
          3 Terminate
          4 Exit
          """)
option=int(input('Enter your selected option plz: '))
if option==1:
        instance_id=input(('plz enter the instance id: '))
        print('===================starting the Ec2 instance===================')
        my_inst_obj=ec2_cons.start_instances(InstanceIds=[instance_id])
elif option==2:
        instance_id=input(('plz enter the instance id: '))
        print('======================stopping the EC2 instance=================')
        my_inst_obj=ec2_cons.stop_instances(InstanceIds=[instance_id])
elif option==3:
        instance_id=input(('plz enter the instance id: '))
        print('=========================Terminating the EC2 instances=============')
        my_inst_obj=ec2_cons.terminate_instances(InstanceIds=[instance_id])

elif option==4:
        print('exiting the script....')
        sys.exit()
else:
        print(f'plz select the valid options')
