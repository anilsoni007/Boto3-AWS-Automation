import boto3
import logging
import os

# Setup logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def send_mail_with_attach_ses(sender, recipient, aws_region, subject, account_name, buckets_with_removed_tags, failed_buckets):
    ses = boto3.client('ses', region_name=aws_region)

    # Generate HTML content with tables for removed tags and failed buckets
    removed_tags_html = generate_table_html("S3 Buckets with Removed Tags", "Bucket Name", "Removed Tags", buckets_with_removed_tags)
    failed_buckets_html = generate_table_html("S3 Buckets with Permission Issues", "Bucket Name", "", failed_buckets)

    # The email body for recipients with non-HTML email clients.
    body_text = "The following S3 buckets had tags 'Data Classification' or 'Data classification' removed:\n\n"
    for bucket_name, removed_tags in buckets_with_removed_tags.items():
        removed_tags_str = ', '.join([f"{tag['Key']}: {tag['Value']}" for tag in removed_tags])
        body_text += f"\nBucket Name: {bucket_name}\nRemoved Tags: {removed_tags_str}\n"

    if failed_buckets:
        body_text += "\nThe following S3 buckets encountered permission issues while attempting to update tags:\n"
        body_text += "\n".join(failed_buckets)

    # The HTML body of the email.
    body_html = removed_tags_html + "<br><br>" + failed_buckets_html

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

def generate_table_html(heading, column1_header, column2_header, data):
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
    table_html += f"<body><h3 style=color:#0000FF>{heading}</h3>"
    table_html += "<br>"
    table_html += "<table style=width:100%>"
    table_html += f"<tr><th>{column1_header}</th><th>{column2_header}</th></tr>"

    for key, value in data.items():
        if column2_header:
            table_html += f"<tr><td>{key}</td><td>{value}</td></tr>"
        else:
            table_html += f"<tr><td>{value}</td></tr>"

    table_html += "</table></body></html>"
    return table_html

def lambda_handler(event, context):
    s3 = boto3.client('s3')
    sts = boto3.client('sts')

    account_number = sts.get_caller_identity()['Account']

    # Describe S3 Buckets
    s3_buckets = s3.list_buckets()

    # Dictionaries to store buckets with removed tags and failed buckets
    buckets_with_removed_tags = {}
    failed_buckets = {}

    for bucket in s3_buckets['Buckets']:
        bucket_name = bucket['Name']

        # Attempt to get bucket tags
        try:
            response = s3.get_bucket_tagging(Bucket=bucket_name)
            tags = {tag['Key']: tag['Value'] for tag in response.get('TagSet', [])}
        except Exception as e:
            logger.error(f"Failed to get tags for bucket {bucket_name}: {e}")
            failed_buckets[bucket_name] = "Failed to get tags due to permission issues"
            continue

        # Check for tags 'Data Classification' or 'Data classification'
        removed_tags = []
        for key in ['Data Classification', 'Data classification']:
            if key in tags:
                removed_tags.append({'Key': key, 'Value': tags[key]})
                # Delete the tag by updating the tags without the unwanted tag
                updated_tags = [{'Key': k, 'Value': v} for k, v in tags.items() if k.lower() != key.lower()]
                try:
                    s3.put_bucket_tagging(Bucket=bucket_name, Tagging={'TagSet': updated_tags})
                except Exception as e:
                    logger.error(f"Failed to update tags for bucket {bucket_name}: {e}")
                    failed_buckets[bucket_name] = "Failed to update tags due to permission issues"
                    continue

        if removed_tags:
            buckets_with_removed_tags[bucket_name] = removed_tags

    if buckets_with_removed_tags or failed_buckets:
        # Send email with bucket names and details
        subject = f"AWS Account {account_number} - S3 Buckets Tag Removal Report"
        sender = 'anilsoni181@gmail.com'  # Replace with your sender email address
        recipient = 'anilsoni181@gmail.com'  # Replace with recipient email address
        aws_region = os.environ['AWS_REGION']  # Get AWS region from Lambda environment
        send_mail_with_attach_ses(sender, recipient, aws_region, subject, account_number, buckets_with_removed_tags, failed_buckets)
    else:
        logger.info("No S3 buckets found with 'Data Classification' or 'Data classification' tags")

    return {
        'statusCode': 200,
        'body': 'Tags verification complete'
    }

