import boto3
import logging
import os


# Setup logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def send_mail_with_attach_ses(sender, recipient, aws_region, subject, account_name, missing_resources):
    ses = boto3.client('ses', region_name=aws_region)
    
    # Generate HTML content with table data
    table_html = "<html><head><br/>"
    table_html += "<style>"
    table_html +=  "table, th, td {"
    table_html += "border: 1px solid black;"
    table_html += "border-collapse: collapse;}"
    table_html += "th, td {"
    table_html += "padding: 5px;"
    table_html += "text-align: left;}"
    table_html += "</style>"
    table_html += "</head>"
    table_html += "<body><h3 style=color:#0000FF>Missing Compliant Tags in RDS Instances and Clusters Report - Account: " + str(account_name) + "</h3>"
    table_html += "<br>"
    table_html += "<table style=width:100%>"
    table_html += "<tr><th>Resource ID</th><th>Name</th><th>Missing Tags </th></tr>"
    
    for resource_id, resource_data in missing_resources.items():
        name = resource_data.get('Name', 'N/A')
        missing_tags = resource_data['MissingTags']
        table_html += f"<tr><td>{resource_id}</td><td>{name}</td><td>{', '.join(missing_tags)}</td></tr>"
    
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
    rds = boto3.client('rds')
    sts = boto3.client('sts')
    account_name = sts.get_caller_identity()['Account']
    required_tags = [
        {'Key': 'Name'},
        {'Key': 'Owner', 'Values': ['Anil']},
        {'Key': 'Project', 'Values': ['Chanakya', 'Chanakya-chemicals']}
    ]
    missing_resources = {}
    
    # Check RDS Instances
    instances = rds.describe_db_instances()
    for instance in instances['DBInstances']:
        instance_id = instance['DBInstanceIdentifier']
        instance_name = instance['DBInstanceIdentifier']
        tags = {tag['Key']: tag['Value'] for tag in instance.get('TagList', [])}
        missing_tags = []
        for tag in required_tags:
            if tag['Key'] not in tags:
                missing_tags.append(tag['Key'])
            elif 'Values' in tag and tags[tag['Key']] not in tag['Values']:
                missing_tags.append(tag['Key'])
        if missing_tags:
            missing_resources[instance_id] = {'Name': instance_name, 'MissingTags': missing_tags}
    
    # Check RDS Clusters
    clusters = rds.describe_db_clusters()
    for cluster in clusters['DBClusters']:
        cluster_id = cluster['DBClusterIdentifier']
        cluster_name = cluster['DBClusterIdentifier']
        tags = {tag['Key']: tag['Value'] for tag in cluster.get('TagList', [])}
        missing_tags = []
        for tag in required_tags:
            if tag['Key'] not in tags:
                missing_tags.append(tag['Key'])
            elif 'Values' in tag and tags[tag['Key']] not in tag['Values']:
                missing_tags.append(tag['Key'])
        if missing_tags:
            missing_resources[cluster_id] = {'Name': cluster_name, 'MissingTags': missing_tags}
    
    if missing_resources:
        subject = "AWS ACCOUNT  " + str(account_name) + "  Required tags missing in RDS instances and clusters Report"
        sender = 'anilsoni181@gmail.com'
        recipient = 'anilsoni181@gmail.com'
        aws_region = os.environ['AWS_REGION']
        send_mail_with_attach_ses(sender, recipient, aws_region, subject, account_name, missing_resources)
    else:
        logger.info("No instances or clusters found with the missing required tags")
    
    return {
        'statusCode': 200,
        'body': 'Tags validation completed'
    }

