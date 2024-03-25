import boto3
import logging
import os

# Setup logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def send_mail_with_attach_ses(sender, recipient, aws_region, subject, account_name, instances_missing_tags):
    ses = boto3.client('ses', region_name=aws_region)

    # Generate HTML content with table data
    table_html = "<html><head><br/>"
    table_html += "<style>"
    table_html += "table, th, td {"
    table_html += "border: 1px solid black;"
    table_html += "border-collapse: collapse;}"
    table_html += "th, td {"
    table_html += "padding: 5px;"
    table_html += "text-align: left;}"
    table_html += "</style>"
    table_html += "</head>"
    table_html += "<body><h3 style=color:#0000FF>Missing Compliant Tags in Resources Report - Account: " + str(
        account_name) + "</h3>"
    table_html += "<br>"
    table_html += "<table style=width:100%>"
    table_html += "<tr><th>Instance Name</th><th>EC2 Instance ID</th><th>Missing Tags </th></tr>"

    for instance_id, instance_data in instances_missing_tags.items():
        instance_name = instance_data['InstanceName']
        missing_tags = instance_data['MissingTags']
        # Format missing tags to display both key and value
        formatted_missing_tags = ', '.join([f"{tag['Key']}: {tag['Value']}" for tag in missing_tags])
        table_html += f"<tr><td>{instance_name}</td><td>{instance_id}</td><td>{formatted_missing_tags}</td></tr>"

    table_html += "</table></body></html>"

    # The email body for recipients with non-HTML email clients.
    body_text = "Hello,\r\nPlease find the attached file."

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

    account_number = sts.get_caller_identity()['Account']

    # Describe EC2 Instances
    ec2_instances = ec2.describe_instances()

    # Dictionary to store missing tags for each resource
    resources_missing_tags = {}

    for reservation in ec2_instances['Reservations']:
        for instance in reservation['Instances']:
            instance_id = instance['InstanceId']
            instance_name = [tag['Value'] for tag in instance['Tags'] if tag['Key'] == 'Name'][0]
            instance_state = instance['State']['Name']


            missing_tags = []
            tags = {tag['Key']: tag['Value'] for tag in instance.get('Tags', [])}

            # Check and delete 'Data Classification' or 'Data classification' tags if exist
            for key in ['Data Classification', 'Data classification']:
                if key in tags:
                    ec2.delete_tags(Resources=[instance_id], Tags=[{'Key': key}])

                    if instance_id not in resources_missing_tags:
                        resources_missing_tags[instance_id] = {
                            'InstanceName': instance_name,
                            'MissingTags': [{'Key': key, 'Value': tags[key]}]
                        }
                    else:
                        resources_missing_tags[instance_id]['MissingTags'].append({'Key': key, 'Value': tags[key]})

    if resources_missing_tags:
        # Send email with attachment using Amazon SES
        subject = "AWS Account " + str(account_number) + " Required Tags missing in Resources Report"
        sender = 'anilsoni1l.com'  # Replace with your sender email address
        recipient = 'anilsoni.com'  # Replace with recipient email address
        aws_region = os.environ['AWS_REGION']  # Get AWS region from Lambda environment
        send_mail_with_attach_ses(sender, recipient, aws_region, subject, account_number, resources_missing_tags)
    else:
        logger.info("No resources found with missing tags")

    return {
        'statusCode': 200,
        'body': 'Tags verification complete'
    }

