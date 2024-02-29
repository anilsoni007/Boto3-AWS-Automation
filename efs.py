import boto3
import logging
import os

# Setup logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def send_mail_with_attach_ses(sender, recipient, aws_region, subject, account_name, efs_missing_tags):
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
    table_html += "<tr><th>EFS Name</th><th>Resource Type</th><th>Missing Tags </th></tr>"

    for resource_id, resource_data in efs_missing_tags.items():
        resource_type = resource_data['ResourceType']
        missing_tags = resource_data['MissingTags']
        table_html += f"<tr><td>{resource_id}</td><td>{resource_type}</td><td>{', '.join(missing_tags)}</td></tr>"

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

def get_account_type(account_name):
    # Extract account type from account name
    if 'sandbox' in account_name.lower():
        return 'Sandbox'
    else:
        return 'Other'

def update_tags(resource_id, account_name, resource_type, efs):
    account_type = get_account_type(account_name)
    # Update 'Data Classification' tag based on account type
    if account_type == 'Sandbox':
        new_value = 'Internal'
    else:
        new_value = 'Restricted'

    # Update tags for EFS instance
    response = efs.tag_resource(
        ResourceId=resource_id,
        Tags=[
            {
                'Key': 'DataClassification',
                'Value': new_value
            }
        ]
    )

def lambda_handler(event, context):
    efs = boto3.client('efs')

    account_name = os.environ['AWS_ACCOUNT']

    ############################# SPECIFIC EFS INSTANCE TEST ###############################
    specific_efs_id = "Filesystemid"
    #########################################################################################

    # Describe EFS File Systems
    efs_file_systems = efs.describe_file_systems()

    # Define the required tags with their acceptable values
    required_tags = [
        {'Key': 'DataClassification'}
    ]

    # Dictionary to store missing tags for each resource
    resources_missing_tags = {}

    for efs_file_system in efs_file_systems['FileSystems']:
        efs_id = efs_file_system['FileSystemId']
        efs_status = efs_file_system['LifeCycleState']

        ###################### FOR SPECIFIC INSTANCE #################################
        if efs_id != specific_efs_id:
            continue

        if efs_status != 'available':
            continue
        ################################################################################

        missing_tags = []
        tags_response = efs.describe_tags(FileSystemId=efs_id)
        tags = {tag['Key']: tag['Value'] for tag in tags_response['Tags']}

        # Check if 'DataClassification' tag exists and update it if needed
        if 'DataClassification' in tags:
            current_value = tags['DataClassification']
            account_type = get_account_type(account_name)
            if account_type == 'Sandbox' and current_value != 'Internal':
                # Delete existing tag
                efs.untag_resource(ResourceId=efs_id, TagKeys=['DataClassification'])
                # Update tags for EFS instance
                update_tags(efs_id, account_name, 'EFS Instance', efs)
            elif account_type != 'Sandbox' and current_value != 'Restricted':
                # Delete existing tag
                efs.untag_resource(ResourceId=efs_id, TagKeys=['DataClassification'])
                # Update tags for EFS instance
                update_tags(efs_id, account_name, 'EFS Instance', efs)
                    # Create 'Data Classification' tag if it doesn't exist
        else:
            update_tags(efs_id, account_name, 'EFS Instance', efs)

        for tag in required_tags:
            if tag['Key'] not in tags:
                missing_tags.append(tag['Key'])
            elif 'Values' in tag and tags[tag['Key']] not in tag['Values']:
                missing_tags.append(tag['Key'])

        if missing_tags:
            resources_missing_tags[efs_id] = {
                'ResourceType': 'EFS Instance',
                'MissingTags': missing_tags
            }
            ########################## Break loop after specific instance validation ##############
            break  # Exit the loop 
            #######################################################################################

    if resources_missing_tags:
        # Send email with attachment using Amazon SES
        subject = "AWS Account " + str(account_name) + " Required Tags missing in Resources Report"
        sender = 'anilsoni181@gmail.com'  # Replace with your sender email address
        recipient = 'anilsoni181@gmail.com'  # Replace with recipient email address
        aws_region = os.environ['AWS_REGION']  # Get AWS region from Lambda environment
        send_mail_with_attach_ses(sender, recipient, aws_region, subject, account_name, resources_missing_tags)
    else:
        logger.info("No resources found with missing tags")

    return {
        'statusCode': 200,
        'body': 'Tags verification complete'
    }

