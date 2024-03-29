
aws rds describe-db-instances --query 'DBInstances[?Engine==`aurora`].[DBInstanceIdentifier]' --output text
