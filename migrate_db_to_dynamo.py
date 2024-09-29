import json
import time
from pathlib import Path

import boto3
import streamlit as st
from tqdm import tqdm


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


def create_table(table_name, key_schema, attribute_definitions, provisioned_throughput):
    """Create a DynamoDB table with the given specifications."""
    try:
        table = dynamodb.Table(table_name)
        table.load()  # Check if the table exists
        print(f"Table {table_name} already exists.")
        print(f"Number of items in table {table_name}: {table.item_count}")
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


def insert_data_to_table(table, data_of_table):
    """Insert data into the specified table using batch_writer."""
    with table.batch_writer() as batch:
        for entry in tqdm(data_of_table):
            try:
                batch.put_item(Item=entry)
                time.sleep(0.5)  # Adjust sleep duration to prevent throttling
            except Exception as e:
                print(f"Error inserting item: {entry}")
                print(f"Exception: {e}")

    response = table.scan()
    print(
        f"Number of items in table {table.name} after insertion: {len(response['Items'])}"
    )


def process_table(table_name, table_data):
    """Handles the logic for creating and populating each specific table."""

    if table_name == "performances":
        # Handling the "performances" table
        key_schema = [{"AttributeName": "key", "KeyType": "HASH"}]
        attribute_definitions = [{"AttributeName": "key", "AttributeType": "S"}]
        provisioned_throughput = {"ReadCapacityUnits": 5, "WriteCapacityUnits": 5}

        table = create_table(
            table_name, key_schema, attribute_definitions, provisioned_throughput
        )

        # Formatting the data for insertion
        formatted_data = [
            {
                "key": entry["key"],
                "name": entry.get("name", ""),
                "date": entry.get("date", ""),
                "composer": entry.get("composer", ""),
                "stage": entry.get("stage", ""),
                "production": entry.get("production", ""),
                "comments": entry.get("comments", ""),
                "is_concertante": entry.get("is_concertante", False),
                "cast": entry.get("cast", {}),
                "leading_team": entry.get("leading_team", {}),
            }
            for entry in table_data
        ]

        insert_data_to_table(table, formatted_data)

    elif table_name == "works_dates":
        # Handling the "works_dates" table
        key_schema = [{"AttributeName": "key", "KeyType": "HASH"}]
        attribute_definitions = [{"AttributeName": "key", "AttributeType": "S"}]
        provisioned_throughput = {"ReadCapacityUnits": 5, "WriteCapacityUnits": 5}

        table = create_table(
            table_name, key_schema, attribute_definitions, provisioned_throughput
        )

        # Formatting the data for insertion
        formatted_data = [
            {
                "key": entry["key"],
                "composer": entry.get("composer", ""),
                "title": entry.get("title", ""),
                "year": entry.get("year", ""),
            }
            for entry in table_data
        ]

        insert_data_to_table(table, formatted_data)
    elif table_name == "venues":
        # Handling the "venues" table
        key_schema = [{"AttributeName": "key", "KeyType": "HASH"}]
        attribute_definitions = [{"AttributeName": "key", "AttributeType": "S"}]
        provisioned_throughput = {"ReadCapacityUnits": 5, "WriteCapacityUnits": 5}

        table = create_table(
            table_name, key_schema, attribute_definitions, provisioned_throughput
        )

        # Formatting the data for insertion
        formatted_data = [
            {
                "key": entry.key,
                "name": entry.name,
                "short_name": entry.short_name,
            }
            for entry in table_data
        ]

        insert_data_to_table(table, formatted_data)

    # Add more `elif` blocks if you have additional tables with different schemas


from pyopera.common import SHORT_STAGE_NAME_TO_FULL, VenueModel


def main():
    # # Load your JSON data file
    # path_to_json = Path("/mnt/c/Users/papal/Downloads/database (13).json")
    # data = json.loads(path_to_json.read_text())

    # # Process each table in the JSON data
    # for table_name, table_data in data.items():
    #     process_table(table_name, table_data)
    venues = [
        VenueModel(name=value, short_name=key)
        for key, value in SHORT_STAGE_NAME_TO_FULL.items()
    ]

    process_table("venues", venues)


if __name__ == "__main__":
    main()
