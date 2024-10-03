import boto3
import streamlit as st


def create_dynamodb_resource():
    """Create a DynamoDB resource using credentials stored in Streamlit secrets."""
    aws_access_key_id = st.secrets["aws"]["aws_access_key_id"]
    aws_secret_access_key = st.secrets["aws"]["aws_secret_access_key"]
    aws_region = st.secrets["aws"]["aws_region"]

    session = boto3.Session(
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        region_name=aws_region,
    )

    dynamodb = session.resource("dynamodb")
    return dynamodb


dynamodb = create_dynamodb_resource()


def make_deta_style_table(table_name: str):
    """
    Create a DynamoDB in the style of deta where the primary key is a string called "key".
    """
    if len(table_name) < 3:
        raise ValueError("Table name must be at least 3 characters long.")

    key_schema = [{"AttributeName": "key", "KeyType": "HASH"}]
    attribute_definitions = [{"AttributeName": "key", "AttributeType": "S"}]
    provisioned_throughput = {"ReadCapacityUnits": 5, "WriteCapacityUnits": 5}

    try:
        table = dynamodb.Table(table_name)
        table.load()  # Check if the table exists
    except dynamodb.meta.client.exceptions.ResourceNotFoundException:
        table = dynamodb.create_table(
            TableName=table_name,
            KeySchema=key_schema,
            AttributeDefinitions=attribute_definitions,
            ProvisionedThroughput=provisioned_throughput,
        )
        table.meta.client.get_waiter("table_exists").wait(TableName=table_name)
        print(f"Table {table_name} created successfully.")
    return table
