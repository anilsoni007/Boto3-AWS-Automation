import boto3
import os
import logging

# Setup logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def send_mail_with_attach_ses(sender, recipient, aws_region, subject, table_data):
    ses = boto3.client('ses', region_name=aws_region)
    
    # Generate HTML content with table data
    table_html = "<html><body>"
    table_html += "<h2>Missing Tags Report</h2>"
    table_html += "<table border='1'><tr><th>Bucket Name</th><th>Missing Tags</th></tr>"
    
    for bucket_name, missing_tags in table_data.items():
        table_html += f"<tr><td>{bucket_name}</td><td>{', '.join(missing_tags)}</td></tr>"
    
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
    s3_client = boto3.client('s3')
    
    # Define the required tags with their acceptable values
    required_tags = {
        'Tag1': 'Value1',
        'Tag2': 'Value2',
        'Tag3': 'Value3'
    }
    
    # Dictionary to store missing tags for each bucket
    buckets_missing_tags = {}
    
    # Get all S3 buckets
    response = s3_client.list_buckets()
    buckets = response['Buckets']
    
    for bucket in buckets:
        bucket_name = bucket['Name']
        try:
            # Get tags assigned to the S3 bucket
            tags = s3_client.get_bucket_tagging(Bucket=bucket_name)['TagSet']
            
            missing_tags = []
            for tag_key, tag_value in required_tags.items():
                if {'Key': tag_key, 'Value': tag_value} not in tags:
                    missing_tags.append(tag_key)
            
            if missing_tags:
                buckets_missing_tags[bucket_name] = missing_tags
        except s3_client.exceptions.NoSuchTagSet:
            # If there are no tags assigned to the bucket
            buckets_missing_tags[bucket_name] = list(required_tags.keys())
        except Exception as e:
            logger.error(f"Error checking tags for bucket {bucket_name}: {e}")
    
    if buckets_missing_tags:
        # Send email with attachment using Amazon SES
        subject = "Missing Tags Report for S3 Buckets"
        sender = 'xxxx@gmail.com'  # Replace with your sender email address
        recipient = 'xxxxx@gmail.com'  # Replace with recipient email address
        aws_region = 'ap-south-1'  # Replace with your AWS region
        send_mail_with_attach_ses(sender, recipient, aws_region, subject, buckets_missing_tags)
    else:
        logger.info("No S3 buckets found with missing tags")

    return {
        'statusCode': 200,
        'body': 'Tags verification complete'
    }
