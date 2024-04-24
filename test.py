import boto3
import logging
import os

# Setup logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def get_lambda_functions(lambda_client):
    lambda_functions = []
    response = lambda_client.list_functions()
    for function in response['Functions']:
        lambda_function = {
            'Name': function['FunctionName'],
            'Runtime': function['Runtime'],
            'CompatibleUpgradableVersion': function.get('CompatibleUpgradableRuntime', 'N/A'),
            'Description': function.get('Description', 'N/A')
        }
        lambda_functions.append(lambda_function)
    return lambda_functions

def generate_html_table(lambda_functions):
    table_html = "<html><head><br/>"
    table_html += "<style>"
    table_html += "table {border-collapse: collapse;width: 100%;}"
    table_html += "th, td {border: 1px solid #dddddd;text-align: left;padding: 8px;}"
    table_html += "th {background-color: #f2f2f2;}"
    table_html += "</style>"
    table_html += "</head>"
    table_html += "<body>"
    table_html += "<h2>Available Lambda Functions</h2>"
    table_html += "<table>"
    table_html += "<tr><th>Function Name</th><th>Runtime</th><th>Compatible/Upgradable Version</th><th>Description</th></tr>"
    for function in lambda_functions:
        table_html += "<tr>"
        table_html += f"<td>{function['Name']}</td>"
        table_html += f"<td>{function['Runtime']}</td>"
        table_html += f"<td>{function['CompatibleUpgradableVersion']}</td>"
        table_html += f"<td>{function['Description']}</td>"
        table_html += "</tr>"
    table_html += "</table>"
    table_html += "</body></html>"
    return table_html

def send_mail_with_attach_ses(sender, recipient, aws_region, subject, html_content):
    ses = boto3.client('ses', region_name=aws_region)
    
    # Send email using SES
    try:
        response = ses.send_email(
            Source=sender,
            Destination={'ToAddresses': [recipient]},
            Message={
                'Subject': {'Data': subject},
                'Body': {'Html': {'Data': html_content}}
            }
        )
        logger.info("Email sent successfully: %s", response)
    except Exception as e:
        logger.error("Failed to send email: %s", e)

def lambda_handler(event, context):
    # Create Lambda client
    lambda_client = boto3.client('lambda', region_name=os.environ['AWS_REGION'])
    
    # Get Lambda functions
    lambda_functions = get_lambda_functions(lambda_client)
    
    # Generate HTML table
    html_content = generate_html_table(lambda_functions)
    
    # Send email with the HTML content
    sender = 'anilsoni181@gmail.com'  # Replace with your sender email address
    recipient = 'anilsoni181@gmail.com'  # Replace with recipient email address
    aws_region = os.environ['AWS_REGION']  # Get AWS region from Lambda environment
    subject = 'List of Available Lambda Functions'
    send_mail_with_attach_ses(sender, recipient, aws_region, subject, html_content)
    
    return {
        'statusCode': 200,
        'body': 'Email sent successfully'
    }

