import boto3
import logging
import os

# Setup logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def send_mail_with_attach_ses(sender, recipient, aws_region, subject, account_number, s3_missing_tags):
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
        account_number) + "</h3>"
    table_html += "<br>"
    table_html += "<table style=width:100%>"
    table_html += "<tr><th>S3 Bucket</th><th>Resource Type</th><th>Missing Tags </th></tr>"

    for bucket_name, bucket_data in s3_missing_tags.items():
        resource_type = bucket_data['ResourceType']
        missing_tags = bucket_data['MissingTags']
        table_html += f"<tr><td>{bucket_name}</td><td>{resource_type}</td><td>{', '.join(missing_tags)}</td></tr>"

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

# def get_account_type(account_name):
#     # Extract account type from account name
#     if 'sandbox' in account_name.lower():
#         return 'Sandbox'
#     else:
#         return 'Other'

def update_s3_tags(bucket_name, account_number, s3):
    # Update 'DataClassification' tag based on account type
    if account_number == '991323962418':
        new_value = 'Restricted'
    else:
        new_value = 'Internal'

    # Update tags for S3 bucket
    response = s3.put_bucket_tagging(
        Bucket=bucket_name,
        Tagging={
            'TagSet': [
                {
                    'Key': 'DataClassification',
                    'Value': new_value
                }
            ]
        }
    )

def lambda_handler(event, context):
    s3 = boto3.client('s3')
    client = boto3.client('sts')
    account_number = client.get_caller_identity()['Account']

    if account_number == '991323962418':
        new_value = 'Restricted'
    else:
        new_value = 'Internal'

    #account_name = os.environ['AWS_ACCOUNT']

    # List S3 buckets
    s3_buckets = s3.list_buckets()

    # Define the required tags with their acceptable values
    required_tags = [
        {'Key': 'DataClassification'}
    ]

    # Dictionary to store missing tags for each resource
    resources_missing_tags = {}

    for bucket in s3_buckets['Buckets']:
        bucket_name = bucket['Name']

        try:
            # Get bucket tagging information
            tagging_response = s3.get_bucket_tagging(Bucket=bucket_name)
            tags = {tag['Key']: tag['Value'] for tag in tagging_response.get('TagSet', [])}
        except s3.exceptions.ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchTagSet':
                logger.warning(f"No tags set for bucket: {bucket_name}")
                tags = {}
            else:
                raise e

        missing_tags = []
        # Check if 'DataClassification' tag exists and update it if needed
        if 'DataClassification' in tags:
            current_value = tags['DataClassification']
            if current_value != new_value:
                update_s3_tags(bucket_name, account_number, s3)

            # account_type = get_account_type(account_name)
            # if account_type == 'Sandbox' and current_value != 'Internal':
            #     # Update tags for S3 bucket
            #     update_s3_tags(bucket_name, account_name, s3)
            # elif account_type != 'Sandbox' and current_value != 'Restricted':
            #     # Update tags for S3 bucket
            #     update_s3_tags(bucket_name, account_name, s3)
        else:
            # Create 'DataClassification' tag if it doesn't exist
            update_s3_tags(bucket_name, account_number, s3)

        for tag in required_tags:
            if tag['Key'] not in tags:
                missing_tags.append(tag['Key'])
            elif 'Values' in tag and tags[tag['Key']] not in tag['Values']:
                missing_tags.append(tag['Key'])

        if missing_tags:
            resources_missing_tags[bucket_name] = {
                'ResourceType': 'S3 Bucket',
                'MissingTags': missing_tags
            }

    if resources_missing_tags:
        # Send email with attachment using Amazon SES
        subject = "AWS Account " + str(account_number) + " Required Tags missing in Resources Report"
        sender = 'anilsoni181@gmail.com'  # Replace with your sender email address
        recipient = 'anilsoni181@gmail.com'  # Replace with recipient email address
        aws_region = os.environ['AWS_REGION']  # Get AWS region from Lambda environment
        send_mail_with_attach_ses(sender, recipient, aws_region, subject, account_number, resources_missing_tags)
    else:
                subject = "AWS Account " + str(account_number) + " Required Tags missing in Resources Report"
                sender = 'anilsoni181@gmail.com'  # Replace with your sender email address
                recipient = 'anilsoni181@gmail.com'  # Replace with recipient email address
                aws_region = os.environ['AWS_REGION']  # Get AWS region from Lambda environment
                send_mail_with_attach_ses(sender, recipient, aws_region, subject, account_number, {})

    return {
        'statusCode': 200,
        'body': 'Tags verification complete'
    }
