import boto3
import logging
import os

# Setup logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def send_mail_with_attach_ses(sender, recipient, aws_region, subject, account_name, table_data):
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
            <h3>Missing Compliant Tags in EC2s Report - Account: {account_name}</h3>
            <table>
                <tr>
                    <th style="border: 1px solid white; padding: 8px; text-align: left; background-color: #FF0000; color: white;">Instance ID</th>
                    <th style="border: 1px solid white; padding: 8px; text-align: left; background-color: #FF0000; color: white;">Name</th>
                    <th style="border: 1px solid white; padding: 8px; text-align: left; background-color: #FF0000; color: white;">Missing Tags</th>
                </tr>
    """.format(account_name=account_name)

    for instance_id, instance_data in table_data.items():
        name = instance_data.get('Name', 'N/A')
        missing_tags = ', '.join(instance_data['MissingTags'])
        table_html += f"""<tr>
                            <td style="border: 1px solid white; padding: 8px; text-align: left;">{instance_id}</td>
                            <td style="border: 1px solid white; padding: 8px; text-align: left;">{name}</td>
                            <td style="border: 1px solid white; padding: 8px; text-align: left;">{missing_tags}</td>
                          </tr>"""

    table_html += """
            </table>
        </body>
    </html>
    """

    # The email body for recipients with non-HTML email clients.
    body_text = "Hello,\r\nPlease find the missing tags report for EC2 instances attached."

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
    ec2 = boto3.client('ec2')
    sts = boto3.client('sts')
    account_name = sts.get_caller_identity()['Account']
    required_tags = [
        {'Key': 'Name'},
        {'Key': 'Owner', 'Values': ['Anil']},
        {'Key': 'Project', 'Values': ['Chanakya', 'Chanakya-chemicals']}
    ]
    instance_missing_tags = {}
    instances = ec2.describe_instances()
    
    for reservation in instances['Reservations']:
        for instance in reservation['Instances']:
            instance_id = instance['InstanceId']
            instance_name = [tag['Value'] for tag in instance['Tags'] if tag['Key'] == 'Name']
            tags = {tag['Key']: tag.get('Value') for tag in instance.get('Tags', [])}
            missing_tags = []
            for tag in required_tags:
                if tag['Key'] not in tags:
                    missing_tags.append(tag['Key'])
                elif 'Values' in tag and tags[tag['Key']] not in tag['Values']:
                    missing_tags.append(tag['Key'])
            if missing_tags:
                instance_missing_tags[instance_id] = {'Name': instance_name[0] if instance_name else 'N/A', 'MissingTags': missing_tags}

    if instance_missing_tags:
        subject = "AWS ACCOUNT " + str(account_name) + " Required tags missing in EC2 instances Report"
        sender = 'anilsoni181@gmail.com'
        recipient = 'anilsoni181@gmail.com'
        aws_region = os.environ['AWS_REGION']
        send_mail_with_attach_ses(sender, recipient, aws_region, subject, account_name, instance_missing_tags)
    else:
        logger.info("No instances found with the missing required tags")
    
    return {
        'statuscode': 200,
        'body': 'Tags validation completed'
    }

