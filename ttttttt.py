import boto3
import logging
import os

# Setup logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def send_mail_with_attach_ses(sender, recipient, aws_region, subject, account_number, s3_missing_tags, failed_buckets):
    ses = boto3.client('ses', region_name=aws_region)

    # Generate HTML content with table data for missing tags
    missing_tags_html = generate_html_table(s3_missing_tags, "Missing Compliant Tags in Resources Report", account_number)

    # Generate HTML content with table data for failed buckets
    failed_buckets_html = generate_html_table(failed_buckets, "Failed to Update DataClassification Tags in Below Buckets", account_number)

    # Combine both tables in the email body
    body_html = missing_tags_html + "<br>" + failed_buckets_html

    # The email body for recipients with non-HTML email clients.
    body_text = "Hello,\r\nPlease find the attached file."

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

def generate_html_table(data, title, account_number):
    table_html = f"<html><head><br/>"
    table_html += "<style>"
    table_html += "table, th, td {"
    table_html += "border: 1px solid black;"
    table_html += "border-collapse: collapse;}"
    table_html += "th, td {"
    table_html += "padding: 5px;"
    table_html += "text-align: left;}"
    table_html += "</style>"
    table_html += "</head>"
    table_html += f"<body><h3 style=color:#0000FF>{title} - Account: {account_number}</h3>"
    table_html += "<br>"
    table_html += "<table style=width:100%>"
    table_html += "<tr><th>Resource</th><th>Resource Type</th><th>Tags</th></tr>"

    for item_name, item_data in data.items():
        resource_type = item_data['ResourceType']
        tags = item_data['Tags']
        table_html += f"<tr><td>{item_name}</td><td>{resource_type}</td><td>{', '.join(tags)}</td></tr>"

    table_html += "</table></body></html>"
    return table_html

def update_s3_tags(bucket_name, account_number, s3, existing_tags, failed_buckets):
    # Update 'DataClassification' tag
    existing_tags['DataClassification'] = 'Restricted' if account_number == '991323962418' else 'Internal'

    try:
        # Update tags for S3 bucket
        response = s3.put_bucket_tagging(
            Bucket=bucket_name,
            Tagging={'TagSet': [{'Key': key, 'Value': value} for key, value in existing_tags.items()]}
        )
        logger.info(f"Updated tags for bucket {bucket_name}")
    except s3.exceptions.ClientError as e:
        if e.response['Error']['Code'] == 'AccessDenied':
            logger.warning(f"Access Denied for bucket: {bucket_name}. Skipping...")
        else:
            logger.error(f"Failed to update tags for bucket: {bucket_name}. Error: {e}")
            failed_buckets[bucket_name] = {'ResourceType': 'S3 Bucket', 'Tags': list(existing_tags.keys())}

def lambda_handler(event, context):
    # Specify the correct region for the S3 client
    aws_region = 'us-west-2'

    s3 = boto3.client('s3', region_name=aws_region)
    client = boto3.client('sts')
    account_number = client.get_caller_identity()['Account']

    # List S3 buckets
    s3_buckets = s3.list_buckets()

    # Define the required tags with their acceptable values
    required_tags = [{'Key': 'DataClassification'}]

    # Dictionary to store missing tags for each resource
    s3_missing_tags = {}

    # Dictionary to store failed buckets
    failed_buckets = {}

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
            if current_value != ('Restricted' if account_number == '991323962418' else 'Internal'):
                # Update 'DataClassification' tag
                update_s3_tags(bucket_name, account_number, s3, tags, failed_buckets)
        else:
            # Create 'DataClassification' tag if it doesn't exist
            update_s3_tags(bucket_name, account_number, s3, tags, failed_buckets)

        for tag in required_tags:
            if tag['Key'] not in tags:
                missing_tags.append(tag['Key'])
            elif 'Values' in tag and tags[tag['Key']] not in tag['Values']:
                missing_tags.append(tag['Key'])

        if missing_tags:
            s3_missing_tags[bucket_name] = {'ResourceType': 'S3 Bucket', 'Tags': missing_tags}

    if s3_missing_tags or failed_buckets:
        # Send email with attachment using Amazon SES
        subject = f"AWS Account {account_number} Tags Verification Report"
        sender = 'anilsoni181@gmail.com'  # Replace with your sender email address
        recipient = 'anilsoni181@gmail.com'  # Replace with recipient email address
        send_mail_with_attach_ses(sender, recipient, aws_region, subject, account_number, s3_missing_tags, failed_buckets)
    else:
        logger.info("No resources found with missing tags")

    return {
        'statusCode': 200,
        'body': 'Tags verification complete'
    }
