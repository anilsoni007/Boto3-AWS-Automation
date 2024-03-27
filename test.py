
import boto3
import logging
import os

# Setup logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def send_mail_with_attach_ses(sender, recipient, aws_region, subject, account_name, buckets_with_removed_tags):
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
    table_html += "<body><h3 style=color:#0000FF>S3 Buckets with Removed Tags Report - Account: " + str(
        account_name) + "</h3>"
    table_html += "<br>"
    table_html += "<table style=width:100%>"
    table_html += "<tr><th>Bucket Name</th><th>Removed Tags</th></tr>"

    for bucket_name, removed_tags in buckets_with_removed_tags.items():
        removed_tags_str = ', '.join([f"{tag['Key']}: {tag['Value']}" for tag in removed_tags])
        table_html += f"<tr><td>{bucket_name}</td><td>{removed_tags_str}</td></tr>"

    table_html += "</table></body></html>"

    # The email body for recipients with non-HTML email clients.
    body_text = "The following S3 buckets had tags 'Data Classification' or 'Data classification' removed:\n\n"
    for bucket_name, removed_tags in buckets_with_removed_tags.items():
        removed_tags_str = ', '.join([f"{tag['Key']}: {tag['Value']}" for tag in removed_tags])
        body_text += f"\nBucket Name: {bucket_name}\nRemoved Tags: {removed_tags_str}\n"

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
    logger.info("Email notification sent with removed tags report")

def lambda_handler(event, context):
    s3 = boto3.client('s3')
    sts = boto3.client('sts')

    account_number = sts.get_caller_identity()['Account']

    # Describe S3 Buckets
    s3_buckets = s3.list_buckets()

    # Dictionary to store buckets with removed tags
    buckets_with_removed_tags = {}

    for bucket in s3_buckets['Buckets']:
        bucket_name = bucket['Name']

        # Get bucket tags
        response = s3.get_bucket_tagging(Bucket=bucket_name)
        tags = {tag['Key']: tag['Value'] for tag in response.get('TagSet', [])}

        # Check for tags 'Data Classification' or 'Data classification'
        removed_tags = []
        for key in ['Data Classification', 'Data classification']:
            if key in tags:
                removed_tags.append({'Key': key, 'Value': tags[key]})
                # Delete the tag by updating the tags without the unwanted tag
                updated_tags = [{'Key': k, 'Value': v} for k, v in tags.items() if k.lower() != key.lower()]
                s3.put_bucket_tagging(Bucket=bucket_name, Tagging={'TagSet': updated_tags})

        if removed_tags:
            buckets_with_removed_tags[bucket_name] = removed_tags

    if buckets_with_removed_tags:
        # Send email with bucket names
        subject = f"AWS Account {account_number} - S3 Buckets with Removed Tags"
        sender = 'anilsoni181@gmail.com'  # Replace with your sender email address
        recipient = 'anilsoni181@gmail.com'  # Replace with recipient email address
        aws_region = os.environ['AWS_REGION']  # Get AWS region from Lambda environment
        send_mail_with_attach_ses(sender, recipient, aws_region, subject, account_number, buckets_with_removed_tags)
    else:
        logger.info("No S3 buckets found with 'Data Classification' or 'Data classification' tags")

    return {
        'statusCode': 200,
        'body': 'Tags verification complete'
    }
