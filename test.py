
import boto3
import logging
import os

# Setup logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def send_mail_with_attach_ses(sender, recipient, aws_region, subject, account_name, missing_resources):
    ses = boto3.client('ses', region_name=aws_region)
    
    # Generate HTML content with table data
    table_html = """
    <html>
        <head>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    color: white;
                    background-color: black;
                }}
                h3 {{
                    color: #333333;
                    font-size: 25px;
                    text-align: center;
                    background-color: yellow;
                    padding: 10px;
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin-top: 20px;
                }}
                th, td {{
                    border: 1px solid white;
                    padding: 8px;
                    text-align: left;
                }}
                th {{
                    background-color: #FF0000; /* Red */
                    color: white;
                }}
                tr:nth-child(even) {{
                    background-color: #555555;
                }}
            </style>
        </head>
        <body>
            <h3>Missing Compliant Tags in Amazon EFS Resources Report - Account: {account_name}</h3>
            <table>
                <tr>
                    <th style="border: 1px solid white; padding: 8px; text-align: left; background-color: #FF0000; color: white;">Resource ID</th>
                    <th style="border: 1px solid white; padding: 8px; text-align: left; background-color: #FF0000; color: white;">Name</th>
                    <th style="border: 1px solid white; padding: 8px; text-align: left; background-color: #FF0000; color: white;">Missing Tags</th>
                </tr>
    """.format(account_name=account_name)

    for resource_id, resource_data in missing_resources.items():
        name = resource_data.get('Name', 'N/A')
        missing_tags = ', '.join(resource_data['MissingTags'])
        table_html += f"""<tr>
                            <td style="border: 1px solid white; padding: 8px; text-align: left;">{resource_id}</td>
                            <td style="border: 1px solid white; padding: 8px; text-align: left;">{name}</td>
                            <td style="border: 1px solid white; padding: 8px; text-align: left;">{missing_tags}</td>
                          </tr>"""

    table_html += """
            </table>
        </body>
    </html>
    """

    # The email body for recipients with non-HTML email clients.
    body_text = "Hello,\r\nPlease find the missing tags report for Amazon EFS resources attached."

    # The HTML body of the email.
    body_html = table_html
    
    # Send email using Amazon SES
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
    efs = boto3.client('efs')
    sts = boto3.client('sts')
    account_name = sts.get_caller_identity()['Account']
    required_tags = [
        {'Key': 'Name'},
        {'Key': 'Owner', 'Values': ['Anil']},
        {'Key': 'Project', 'Values': ['Chanakya', 'Chanakya-chemicals']}
    ]
    missing_resources = {}
    
    # Check EFS File Systems
    file_systems = efs.describe_file_systems()
    for file_system in file_systems['FileSystems']:
        file_system_id = file_system['FileSystemId']
        file_system_name = [tag['Value'] for tag in file_system['Tags'] if tag['Key'] == 'Name']
        tags = {tag['Key']: tag['Value'] for tag in file_system.get('Tags', [])}
        missing_tags = []
        for tag in required_tags:
            if tag['Key'] not in tags:
                missing_tags.append(tag['Key'])
            elif 'Values' in tag and tags[tag['Key']] not in tag['Values']:
                missing_tags.append(tag['Key'])
        if missing_tags:
            missing_resources[file_system_id] = {'Name': file_system_name[0] if file_system_name else 'N/A', 'MissingTags': missing_tags}
    
    if missing_resources:
        subject = "AWS ACCOUNT " + str(account_name) + " Required tags missing in Amazon EFS Resources Report"
        sender = 'anilsoni181@gmail.com'
        recipient = 'anilsoni181@gmail.com'
        aws_region = os.environ['AWS_REGION']
        send_mail_with_attach_ses(sender, recipient, aws_region, subject, account_name, missing_resources)
    else:
        logger.info("No EFS file systems found with the missing required tags")
    
    return {
        'statusCode': 200,
        'body': 'Tags validation completed'
    }
