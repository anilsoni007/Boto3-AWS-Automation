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
    table_html += "<body><h3 style=color:#0000FF>Missing Required Tags in S3 Buckets Report - Account: " + str(
        account_name) + "</h3>"
    table_html += "<br>"
    table_html += "<table style=width:100%>"
    table_html += "<tr><th>Bucket Name</th><th>Missing Tags </th></tr>"

    for bucket_name, missing_tags in resources_missing_tags.items():
        formatted_missing_tags = ', '.join(missing_tags)
        table_html += f"<tr><td>{bucket_name}</td><td>{formatted_missing_tags}</td></tr>"

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
    s3 = boto3.client('s3')
    sts = boto3.client('sts')

    account_number = sts.get_caller_identity()['Account']

    # Describe S3 Buckets
    s3_buckets = s3.list_buckets()

    # Dictionary to store missing tags for each bucket
    buckets_missing_tags = {}

    for bucket in s3_buckets['Buckets']:
        bucket_name = bucket['Name']

        # Get bucket tags
        response = s3.get_bucket_tagging(Bucket=bucket_name)
        tags = {tag['Key']: tag['Value'] for tag in response.get('TagSet', [])}

        # Check for missing tags
        required_tags = ['Tag1', 'Tag2']  # Add your required tags here
        missing_tags = [tag for tag in required_tags if tag not in tags]

        if missing_tags:
            buckets_missing_tags[bucket_name] = missing_tags

    if buckets_missing_tags:
        # Send email with attachment using Amazon SES
        subject = f"AWS Account {account_number} Required Tags missing in S3 Buckets Report"
        sender = 'anilsoni181@gmail.com'  # Replace with your sender email address
        recipient = 'anilsoni181@gmail.com'  # Replace with recipient email address
        aws_region = os.environ['AWS_REGION']  # Get AWS region from Lambda environment
        send_mail_with_attach_ses(sender, recipient, aws_region, subject, account_number, buckets_missing_tags)
    else:
        logger.info("No S3 buckets found with missing tags")

    return {
        'statusCode': 200,
        'body': 'Tags verification complete'
    }

