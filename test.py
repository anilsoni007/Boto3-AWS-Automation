import boto3
import logging
import os

# Setup logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def send_mail_with_attach_ses(sender, recipient, aws_region, subject, account_name, resources_missing_tags):
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
    table_html += "<tr><th>Resource Name</th><th>Resource ID</th><th>Missing Tags </th></tr>"

    for resource_id, resource_data in resources_missing_tags.items():
        resource_name = resource_data['ResourceName']
        missing_tags = resource_data['MissingTags']
        # Format missing tags to display both key and value
        formatted_missing_tags = ', '.join([f"{tag['Key']}: {tag['Value']}" for tag in missing_tags])
        table_html += f"<tr><td>{resource_name}</td><td>{resource_id}</td><td>{formatted_missing_tags}</td></tr>"

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
    efs = boto3.client('efs')
    sts = boto3.client('sts')

    account_number = sts.get_caller_identity()['Account']

    # Describe EFS File Systems
    efs_file_systems = efs.describe_file_systems()

    # Dictionary to store missing tags for each resource
    resources_missing_tags = {}

    for file_system in efs_file_systems['FileSystems']:
        file_system_id = file_system['FileSystemId']
        file_system_name = file_system_id  # EFS doesn't have a Name tag, using FileSystemId as name
        tags = {tag['Key']: tag['Value'] for tag in file_system.get('Tags', [])}

        # Check and delete 'Data Classification' or 'Data classification' tags if exist
        for key in ['Data Classification', 'Data classification']:
            if key in tags:
                efs.delete_tags(FileSystemId=file_system_id, Tags=[{'Key': key}])

                if file_system_id not in resources_missing_tags:
                    resources_missing_tags[file_system_id] = {
                        'ResourceName': file_system_name,
                        'MissingTags': [{'Key': key, 'Value': tags[key]}]
                    }
                else:
                    resources_missing_tags[file_system_id]['MissingTags'].append({'Key': key, 'Value': tags[key]})

    if resources_missing_tags:
        # Send email with attachment using Amazon SES
        subject = "AWS Account " + str(account_number) + " Required Tags missing in Resources Report"
        sender = 'anilsoni181@gmail.com'  # Replace with your sender email address
        recipient = 'anilsoni181@gmail.com'  # Replace with recipient email address
        aws_region = os.environ['AWS_REGION']  # Get AWS region from Lambda environment
        send_mail_with_attach_ses(sender, recipient, aws_region, subject, account_number, resources_missing_tags)
    else:
        logger.info("No resources found with missing tags")

    return {
        'statusCode': 200,
        'body': 'Tags verification complete'
    }

