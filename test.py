import boto3
import logging
import os

# Setup logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def check_missing_tags(ec2_client):
    missing_tags_instances = []
    
    # Get all EC2 instances
    response = ec2_client.describe_instances()
    
    for reservation in response['Reservations']:
        for instance in reservation['Instances']:
            instance_id = instance['InstanceId']
            instance_name = None
            instance_tags = instance.get('Tags', [])
            
            # Get the instance name from tags
            for tag in instance_tags:
                if tag['Key'] == 'Name':
                    instance_name = tag['Value']
                    break
            
            missing_tags = []
            # Check if the instance has the required tags
            required_tags = {'DataC': 'internal'}  # Required tags
            for key, value in required_tags.items():
                tag_found = False
                for tag in instance_tags:
                    if tag['Key'] == key and tag['Value'] == value:
                        tag_found = True
                        break
                if not tag_found:
                    missing_tags.append(f"{key}:{value}")
            
            # If instance has missing tags, add it to the list
            if missing_tags:
                missing_tags_instances.append({
                    'InstanceId': instance_id,
                    'Name': instance_name,
                    'MissingTags': missing_tags
                })
    
    return missing_tags_instances

def send_mail_with_attach_ses(sender, recipient, aws_region, subject, account_number, instances_missing_tags):
    ses = boto3.client('ses', region_name=aws_region)
    
    # Generate HTML content with instances missing required tags
    table_html = "<html><head><br/>"
    table_html += "<style>"
    table_html +=  "table, th, td {"
    table_html += "border: 1px solid black;"
    table_html += "border-collapse: collapse;}"
    table_html += "th, td {"
    table_html += "padding: 5px;"
    table_html += "text-align: left;}"
    table_html += "</style>"
    table_html += "</head>"
    table_html += "<body><h3 style=color:#0000FF>EC2 Instances Missing Required Tags Report - Account: " + str(account_number) + "</h3>"
    table_html += "<br>"
    table_html += "<table style=width:100%>"
    table_html += "<tr><th>Instance ID</th><th>Name</th><th>Missing Tags</th></tr>"
    
    for instance in instances_missing_tags:
        instance_id = instance['InstanceId']
        instance_name = instance['Name']
        missing_tags = ', '.join(instance['MissingTags'])
        table_html += f"<tr><td>{instance_id}</td><td>{instance_name}</td><td>{missing_tags}</td></tr>"
    
    table_html += "</table></body></html>"

    # Send email using SES
    try:
        response = ses.send_email(
            Source=sender,
            Destination={'ToAddresses': [recipient]},
            Message={
                'Subject': {'Data': subject},
                'Body': {'Html': {'Data': table_html}}
            }
        )
        logger.info("Email sent successfully: %s", response)
    except Exception as e:
        logger.error("Failed to send email: %s", e)

def lambda_handler(event, context):
    account_number = event.get('account_number')
    
    # Create EC2 client
    ec2_client = boto3.client('ec2', region_name=os.environ['AWS_REGION'])
    
    # Check for instances with missing tags
    instances_missing_tags = check_missing_tags(ec2_client)

    if instances_missing_tags:
        # Send email with instances missing required tags
        subject = "AWS Account " + str(account_number) + " EC2 Instances Missing Required Tags Report"
        sender = 'anilsoni181@gmail.com'  # Replace with your sender email address
        recipient = 'anilsoni181@gmail.com'  # Replace with recipient email address
        aws_region = os.environ['AWS_REGION']  # Get AWS region from Lambda environment
        send_mail_with_attach_ses(sender, recipient, aws_region, subject, account_number, instances_missing_tags)
    else:
        logger.info("No EC2 instances found with missing tags")

    return {
        'statusCode': 200,
        'body': 'Tags verification complete'
    }
