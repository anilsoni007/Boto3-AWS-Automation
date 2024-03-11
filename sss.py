import boto3
import logging
import os

# Setup logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def send_mail_with_attach_ses(sender, recipient, aws_region, subject, account_number, s3_missing_tags, updated_buckets, failed_buckets):
    ses = boto3.client('ses', region_name=aws_region)

    # Generate HTML content with table data for missing tags
    missing_tags_table_html = "<table style=width:100%>"

    for bucket_name, bucket_data in s3_missing_tags.items():
        resource_type = bucket_data['ResourceType']
        missing_tags = bucket_data['MissingTags']
        missing_tags_table_html += f"<tr><td>{bucket_name}</td><td>{resource_type}</td><td>{', '.join(missing_tags)}</td></tr>"

    missing_tags_table_html += "</table>"

    # Generate HTML content with table data for updated buckets
    updated_buckets_table_html = "<table style=width:100%>"
    updated_buckets_table_html += "<tr><th>S3 Bucket</th><th>Tags Updated</th></tr>"

    for bucket_name, updated_tag_value in updated_buckets.items():
        updated_buckets_table_html += f"<tr><td>{bucket_name}</td><td>{updated_tag_value}</td></tr>"

    updated_buckets_table_html += "</table>"

    # Generate HTML content with table data for failed buckets
    failed_buckets_table_html = "<table style=width:100%>"
    failed_buckets_table_html += "<tr><th>S3 Bucket</th><th>Failed to Update Tags</th></tr>"

    for bucket_name in failed_buckets:
        failed_buckets_table_html += f"<tr><td>{bucket_name}</td><td>Access Denied</td></tr>"

    failed_buckets_table_html += "</table>"

    #headline for failed buckets
    failed_buckets_headline = "<h3 style='color:red;'> Failed to update DataClassification tags in below buckets </h3>"

    # Combine all tables
    combined_table_html = missing_tags_table_html + "<br/><br/>" + updated_buckets_table_html + "<br/><br/>" + failed_buckets_headline + failed_buckets_table_html

    # The email body for recipients with non-HTML email clients.
    body_text = "Hello,\r\nPlease find the attached file."

    # The HTML body of the email.
    body_html = "<html><head><br/>"
    body_html += "<style>"
    body_html += "table, th, td {"
    body_html += "border: 1px solid black;"
    body_html += "border-collapse: collapse;}"
    body_html += "th, td {"
    body_html += "padding: 5px;"
    body_html += "text-align: left;}"
    body_html += "</style>"
    body_html += "</head>"
    body_html += "<body><h3 style=color:#0000FF>Missing Compliant Tags in Resources Report - Account: " + str(
        account_number) + "</h3>"
    body_html += "<br>"
    body_html += combined_table_html
    body_html += "</body></html>"

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

def update_s3_tags(bucket_name, account_number, s3, existing_tags, updated_buckets, failed_buckets):
    # Update 'DataClassification' tag
    updated_tag_value = 'Restricted' if account_number == '991323962418' else 'Internal'
    existing_tags['DataClassification'] = updated_tag_value

    try:
        # Update tags for S3 bucket
        response = s3.put_bucket_tagging(
            Bucket=bucket_name,
            Tagging={'TagSet': [{'Key': key, 'Value': value} for key, value in existing_tags.items()]}
        )
        
        updated_buckets[bucket_name] = updated_tag_value
        logger.info(f"Updated tags for bucket {bucket_name}")
    except s3.exceptions.ClientError as e:
        if e.response['Error']['Code'] == 'AccessDenied':
            logger.warning(f"Access Denied for bucket: {bucket_name}. Skipping...")
            failed_buckets.append(bucket_name)
        else:
            raise e

def lambda_handler(event, context):
    aws_region = os.environ['AWS_REGION']
    s3 = boto3.client('s3')
    client = boto3.client('sts',region_name=aws_region)
    account_number = client.get_caller_identity()['Account']

    # Check if the Lambda function has permission to list buckets
    try:
        s3.list_buckets()
    except s3.exceptions.ClientError as e:
        if e.response['Error']['Code'] == 'AccessDenied':
            logger.error("Lambda function does not have permission to list buckets. Exiting...")
            return {
                'statusCode': 403,
                'body': 'Lambda function does not have permission to list buckets.'
            }
        else:
            raise e

    # List S3 buckets
    s3_buckets = s3.list_buckets()

    # Define the required tags with their acceptable values
    required_tags = [
        {'Key': 'DataClassification'}
    ]

    # Dictionary to store missing tags for each resource
    resources_missing_tags = {}

    # Lists to store updated and failed buckets
    updated_buckets = {}
    failed_buckets = []

    for bucket in s3_buckets['Buckets']:
        bucket_name = bucket['Name']

        try:
            # Get bucket tagging information
            tagging_response = s3.get_bucket_tagging(Bucket=bucket_name)
            tags = {tag['Key']: tag['Value'] for tag in tagging_response.get('TagSet', [])}

            # Get bucket ownership controls
            s3.get_bucket_ownership_controls(Bucket=bucket_name)
        except s3.exceptions.ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchTagSet':
                logger.warning(f"No tags set for bucket: {bucket_name}")
                tags = {}
            elif e.response['Error']['Code'] == 'AccessDenied':
                logger.warning(f"Access Denied for bucket: {bucket_name}. Skipping...")
                failed_buckets.append(bucket_name)
                continue  # Skip processing this bucket
            elif e.response['Error']['Code'] == 'NoSuchBucketOwnershipControls':
                logger.warning(f"No bucket ownership controls set for bucket: {bucket_name}")
                failed_buckets.append(bucket_name)
                continue  # Skip processing this bucket
            else:
                logger.error(f"Failed to retrieve bucket ownership controls for bucket: {bucket_name}. Skipping...")
                failed_buckets.append(bucket_name)
                continue  # Skip processing this bucket

        missing_tags = []
        # Check if 'DataClassification' tag exists and update it if needed
        if 'DataClassification' in tags:
            current_value = tags['DataClassification']
            if current_value != ('Restricted' if account_number == '991323962418' else 'Internal'):
                # Update 'DataClassification' tag
                update_s3_tags(bucket_name, account_number, s3, tags, updated_buckets, failed_buckets)
        else:
            # Create 'DataClassification' tag if it doesn't exist
            update_s3_tags(bucket_name, account_number, s3, tags, updated_buckets, failed_buckets)

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

    # Retry updating tags for buckets that previously failed
    for failed_bucket in failed_buckets:
        try:
            # Get bucket tagging information
            tagging_response = s3.get_bucket_tagging(Bucket=failed_bucket)
            tags = {tag['Key']: tag['Value'] for tag in tagging_response.get('TagSet', [])}

            # Update 'DataClassification' tag
            update_s3_tags(failed_bucket, account_number, s3, tags, updated_buckets, failed_buckets)
        except s3.exceptions.ClientError as e:
            if e.response['Error']['Code'] == 'AccessDenied':
                logger.warning(f"Access Denied for bucket: {failed_bucket}. Skipping...")
            else:
                logger.error(f"Failed to update tags for bucket: {failed_bucket}. Skipping...")
                failed_buckets.append(failed_bucket)

    if updated_buckets or failed_buckets:
        # Send email with attachment using Amazon SES
        subject = "AWS Account " + str(account_number) + " Required Tags missing in Resources Report"
        sender = 'anilsoni181@gmail.com'  # Replace with your sender email address
        recipient = 'anilsoni181@gmail.com'  # Replace with recipient email address
        aws_region = os.environ['AWS_REGION']  # Get AWS region from Lambda environment
        send_mail_with_attach_ses(sender, recipient, aws_region, subject, account_number, resources_missing_tags,
                                  updated_buckets, failed_buckets)
    else:
        logger.info("No resources found with missing tags")

    return {
        'statusCode': 200,
        'body': 'Tags verification complete'
    }
