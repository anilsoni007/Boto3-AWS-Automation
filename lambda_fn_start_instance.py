import boto3
def lambda_handler(event, context):
    ec2_cons=boto3.client(service_name='ec2',region_name='us-east-1')
    response=ec2_cons.describe_instances(Filters=[{'Name': 'tag:Env','Values': ['test']}]).get('Reservations')
    for each in response:
        for each_inst in each.get('Instances'):
            state=each_inst.get('State').get('Name')
            if state=='stopped':
                ec2_cons.start_instances(InstanceIds=[each_inst.get('InstanceId')])
