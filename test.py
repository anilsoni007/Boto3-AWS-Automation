
import boto3
from datetime import datetime, timedelta, timezone

def get_updated_runtime_functions(client):
    # Get a list of all Lambda functions
    functions = client.list_functions()['Functions']
    
    # Get the cutoff time for last 48 hours in UTC timezone
    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=48)
    
    # Filter functions updated in the last 48 hours and with updated runtime
    updated_runtime_functions = []
    for function in functions:
        last_modified = function['LastModified']
        last_modified_time = datetime.strptime(last_modified, '%Y-%m-%dT%H:%M:%S.%f%z').astimezone(timezone.utc)
        runtime = function['Runtime']
        
        if last_modified_time > cutoff_time and runtime != 'python3.8':
            updated_runtime_functions.append(function)
    
    # Sort the updated runtime functions by their last modified time
    sorted_updated_runtime_functions = sorted(updated_runtime_functions, key=lambda x: x['LastModified'])
    
    return sorted_updated_runtime_functions

def lambda_handler(event, context):
    # Initialize the Lambda client
    lambda_client = boto3.client('lambda')
    
    # Get list of updated runtime functions
    updated_runtime_functions = get_updated_runtime_functions(lambda_client)
    
    # Prepare the tabular format
    table = "Function Name\tLast Modified\tRuntime\tMemory Size\tTimeout\n"
    for function in updated_runtime_functions:
        function_name = function['FunctionName']
        last_modified = function['LastModified']
        runtime = function['Runtime']
        memory = function['MemorySize']
        timeout = function['Timeout']
        
        # Append function details to the table
        table += f"{function_name}\t{last_modified}\t{runtime}\t{memory}\t{timeout}\n"
    
    # Send email with tabular format if there are updated runtime functions
    if updated_runtime_functions:
        sender_email = "anilsoni181@gmail.com"
        recipient_email = "anilsoni181@gmail.com"
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
            'body': 'No updated runtime functions found.'
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
