import boto3
import os
import logging

# Setup logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def send_mail_with_attach_ses(sender, recipient, aws_region, subject, account_name, table_data):
    ses = boto3.client('ses', region_name=aws_region)
    
    # Generate HTML content with table data
    table_html = "<html><body>"
    table_html += "<h2>Missing Tags Report - Account: " + str(account_name) + "</h2>"
    table_html += "<table border='1'><tr><th>Instance ID</th><th>Name</th><th>Missing Tags</th></tr>"
    
    for instance_id, instance_data in table_data.items():
        name = instance_data.get('Name', 'N/A')
        missing_tags = instance_data['MissingTags']
        table_html += f"<tr><td>{instance_id}</td><td>{name}</td><td>{', '.join(missing_tags)}</td></tr>"
    
    table_html += "</table></body></html>"
    
    # The email body for recipients with non-HTML email clients.
    body_text = f"Hello,\r\nPlease find the attached file for the Missing Tags Report in AWS account: {account_name} - Region: {aws_region}."

    # The HTML body of the email.
    body_html = table_html
    
    # Send email using Amazon SES with attachment
    response = ses.send_email(
        Source=sender,
        Destination={'ToAddresses': [recipient]},
        Message={
            'Subject': {'Data': subject},
            'Body': {
                'Text': {'Data': body_text},
                'Html': {'Data': body_html}
            }
        }
    )
    logger.info("Email notification sent with missing tags report")

def lambda_handler(event, context):
    ec2 = boto3.client('ec2')
    sts = boto3.client('sts')
    
    # Get AWS account ID and region
    account_id = sts.get_caller_identity()['Account']
    region = os.environ['AWS_REGION']
    account_name = os.environ['AWS_ACCOUNT']
    
    # Define the required tags with their acceptable values
    required_tags = [
        {'Key': 'Name'},  # Check if the tag key 'Name' is present
        {'Key': 'Environment', 'Values': ['dev', 'prod', 'staging', 'sandbox']},
        {'Key': 'Owner'},
        {'Key': 'Exposure', 'Values': ['Internal', 'External']},
        {'Key': 'Data Classification'},
        {'Key': 'Business Criticality'}
    ]
    
    # Dictionary to store missing tags for each instance
    instances_missing_tags = {}
    
    # Get all EC2 instances
    instances = ec2.describe_instances()
    
    for reservation in instances['Reservations']:
        for instance in reservation['Instances']:
            instance_id = instance['InstanceId']
            instance_name = [tag['Value'] for tag in instance['Tags'] if tag['Key'] == 'Name']
            tags = {tag['Key']: tag.get('Value') for tag in instance.get('Tags', [])}
            missing_tags = []
            
            for tag in required_tags:
                if 'Values' in tag:
                    # Check if the tag key is present and has one of the specified values
                    if tag['Key'] not in tags or tags[tag['Key']] not in tag['Values']:
                        missing_tags.append(tag['Key'])
                else:
                    # Check if the tag key is present
                    if tag['Key'] not in tags:
                        missing_tags.append(tag['Key'])
            
            if missing_tags:
                instances_missing_tags[instance_id] = {'Name': instance_name[0] if instance_name else 'N/A', 'MissingTags': missing_tags}
    
    if instances_missing_tags:
        # Send email with attachment using Amazon SES
        subject = "Missing Tags Report for EC2 Instances"
        sender = 'anilssdsdssdss@gmail.com'  # Replace with your sender email address
        recipient = 'anisdsss1@gmail.com'  # Replace with recipient email address
        aws_region = os.environ['AWS_REGION']  # Get AWS region from Lambda environment
        send_mail_with_attach_ses(sender, recipient, aws_region, subject, account_name, instances_missing_tags)
    else:
        logger.info("No instances found with missing tags")

    return {
        'statusCode': 200,
        'body': 'Tags verification complete'
    }
