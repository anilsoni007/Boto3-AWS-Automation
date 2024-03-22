import boto3
from datetime import datetime, timedelta, timezone

def get_updated_functions(client):
    updated_functions = []
    # Get a list of all Lambda functions
    functions = client.list_functions()['Functions']
    
    # Get the cutoff time for last 48 hours in UTC timezone
    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=48)
    
    # Iterate through each function
    for function in functions:
        # Get the last modified time of the function
        last_modified = function['LastModified']
        
        # Convert last modified time string to datetime object
        last_modified_time = datetime.fromisoformat(last_modified.replace('Z', '+00:00'))
        
        # Check if the function has been updated in the last 48 hours
        if last_modified_time > cutoff_time:
            updated_functions.append(function)
    
    return updated_functions

def lambda_handler(event, context):
    # Initialize the Lambda client
    lambda_client = boto3.client('lambda')
    
    # Get list of updated functions
    updated_functions = get_updated_functions(lambda_client)
    
    # Prepare the tabular format
    table = "Function Name\tLast Modified\tRuntime\tMemory Size\tTimeout\n"
    for function in updated_functions:
        function_name = function['FunctionName']
        last_modified = function['LastModified']
        runtime = function['Runtime']
        memory = function['MemorySize']
        timeout = function['Timeout']
        
        # Append function details to the table
        table += f"{function_name}\t{last_modified}\t{runtime}\t{memory}\t{timeout}\n"
    
    # Send email with tabular format if there are updated functions
    if updated_functions:
        sender_email = "your_sender_email@example.com"
        recipient_email = "your_recipient_email@example.com"
        subject = "Updated Lambda Functions Report"
        body = table
        
        send_email(sender_email, recipient_email, subject, body)

        return {
            'statusCode': 200,
            'body': 'Email sent successfully!'
        }
    else:
        return {
            'statusCode': 200,
            'body': 'No updated functions found.'
        }

def send_email(sender, recipient, subject, body):
    # Create a new SES client
    ses_client = boto3.client('ses')

    # Try to send the email
    try:
        response = ses_client.send_email(
            Source=sender,
            Destination={'ToAddresses': [recipient]},
            Message={
                'Subject': {'Data': subject},
                'Body': {'Text': {'Data': body}}
            }
        )
    except ClientError as e:
        print(e.response['Error']['Message'])
        return False
    else:
        print("Email sent! Message ID:", response['MessageId'])
        return True
