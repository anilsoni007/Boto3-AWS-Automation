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
    table_html += "<tr><th>Resource ID</th><th>Resource Type</th><th>Missing Tags </th></tr>"

    for resource_id, resource_data in resources_missing_tags.items():
        resource_type = resource_data['ResourceType']
        missing_tags = resource_data['MissingTags']
        table_html += f"<tr><td>{resource_id}</td><td>{resource_type}</td><td>{', '.join(missing_tags)}</td></tr>"

    table_html += "</table></body></html>"

    # The email body
    body_text = "Tags have been updated for RDS clusters in AWS Account: " + str(account_name)

    # Send email using Amazon SES with HTML content
    response = ses.send_email(
        Source=sender,
        Destination={'ToAddresses': [recipient]},
        Message={
            'Subject': {'Data': subject},
            'Body': {
                'Html': {'Data': table_html},
                'Text': {'Data': body_text}
            }
        }
    )
    logger.info("Email notification sent after updating tags for RDS clusters")

def update_tags(resource_id, account_number, resource_type, rds):
    # Determine new_value based on account_number
    if account_number == '1234':
        new_value = 'Internal'
    elif account_number == '2345':
        new_value = 'Restricted'
    else:
        # Set a default value if the account number doesn't match any condition
        new_value = 'Default Value'

    # Update tags for RDS cluster
    response = rds.add_tags_to_resource(
        ResourceName=resource_id,
        Tags=[
            {
                'Key': 'DataClassification',
                'Value': new_value
            }
        ]
    )

def lambda_handler(event, context):
    rds = boto3.client('rds')
    sts = boto3.client('sts')

    account_number = sts.get_caller_identity()['Account']
    account_name = os.environ['AWS_ACCOUNT']
    aws_region = os.environ['AWS_REGION']
    sender = 'anilsoni181@gmail.com'  # Replace with your sender email address
    recipient = 'anilsoni181@gmail.com'  # Replace with recipient email address

    # Describe DB Clusters
    db_clusters = rds.describe_db_clusters()

    # Update tags for RDS clusters
    for db_cluster in db_clusters['DBClusters']:
        cluster_id = db_cluster['DBClusterIdentifier']
        cluster_status = db_cluster['Status']

        if cluster_status != 'available':
            continue

        # Update tags for RDS cluster
        update_tags(db_cluster['DBClusterArn'], account_number, 'RDS Cluster', rds)

    logger.info("Tags update complete for RDS clusters")

    # Send email notification
    subject = "Tags Updated for RDS Clusters in AWS Account: " + str(account_name)
    resources_missing_tags = {}  # Since all tags are updated, there are no missing tags
    send_mail_with_attach_ses(sender, recipient, aws_region, subject, account_name, resources_missing_tags)

    return {
        'statusCode': 200,
        'body': 'Tags update complete for RDS clusters'
    }
