import psycopg2
import logging
from os import environ

from usaspending_api.data_load.field_mappings_fpds import (
    transaction_fpds_columns,
    transaction_normalized_columns,
    transaction_normalized_functions,
    legal_entity_columns,
    legal_entity_boolean_columns,
    legal_entity_functions,
    recipient_location_columns,
    recipient_location_functions,
    place_of_performance_columns,
    place_of_performance_functions,
    award_functions,
    transaction_fpds_boolean_columns,
    transaction_fpds_functions,
)
from usaspending_api.data_load.data_load_helpers import (
    capitalize_if_string,
    false_if_null,
    get_deleted_fpds_data_from_s3,
)
from usaspending_api.data_load.generic_loaders import (
    update_transaction_fpds,
    update_transaction_normalized,
    insert_transaction_normalized,
    insert_transaction_fpds,
    insert_recipient_locations,
    insert_recipients,
    insert_place_of_performance,
    insert_award,
)
from usaspending_api.common.helpers.timing_helpers import Timer
from usaspending_api.common.helpers.sql_helpers import get_database_dsn_string


USASPENDING_CONNECTION_STRING = get_database_dsn_string()
BROKER_CONNECTION_STRING = environ.get("DATA_BROKER_DATABASE_URL", None)

DESTROY_ORPHANS_LEGAL_ENTITY_SQL = (
    "DELETE FROM legal_entity legal WHERE legal.legal_entity_id in "
    "(SELECT l.legal_entity_id FROM legal_entity l "
    "LEFT JOIN transaction_normalized t ON t.recipient_id = l.legal_entity_id "
    "LEFT JOIN awards a ON a.recipient_id = l.legal_entity_id "
    "WHERE t is null and a.id is null); "
)
DESTROY_ORPHANS_REFERENCES_LOCATION_SQL = (
    "DELETE FROM references_location location WHERE location.location_id in "
    "(SELECT l.location_id FROM references_location l "
    "LEFT JOIN transaction_normalized t ON t.place_of_performance_id = l.location_id "
    "LEFT JOIN legal_entity e ON e.location_id = l.location_id "
    "LEFT JOIN awards a ON a.place_of_performance_id = l.location_id "
    "WHERE t.id is null and a.id is null and e.legal_entity_id is null)"
)

CHUNK_SIZE = 5000

logger = logging.getLogger("console")


def destroy_orphans():
    """cleans up tables after run_fpds_load is called"""
    with psycopg2.connect(dsn=USASPENDING_CONNECTION_STRING) as connection:
        with connection.cursor() as cursor:
            cursor.execute(DESTROY_ORPHANS_LEGAL_ENTITY_SQL)
            cursor.execute(DESTROY_ORPHANS_REFERENCES_LOCATION_SQL)


def delete_stale_fpds(date):
    """
    Removed transaction_fpds and transaction_normalized records matching any of the
    provided detached_award_procurement_id list
    Returns list of awards touched
    """
    if not date:
        return []

    detached_award_procurement_ids = get_deleted_fpds_data_from_s3(date)

    if detached_award_procurement_ids:
        with psycopg2.connect(dsn=USASPENDING_CONNECTION_STRING) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "select transaction_id from transaction_fpds where detached_award_procurement_id in ({})".format(
                        ",".join([str(id) for id in detached_award_procurement_ids])
                    )
                )
                # assumes, possibly dangerously, that this won't be too many for the job to handle
                transaction_normalized_ids = cursor.fetchall()

                # Set backreferences from Awards to Transaction Normalized to null. These pointers will be correctly updated
                # in the update awards stage later on
                cursor.execute(
                    "update awards set latest_transaction_id = null, earliest_transaction_id = null "
                    "where latest_transaction_id in ({}) returning id".format(
                        ",".join([str(row[0]) for row in transaction_normalized_ids])
                    )
                )
                awards_touched = cursor.fetchall()

                # Remove Trasaction FPDS rows
                cursor.execute(
                    "delete from transaction_fpds where detached_award_procurement_id in ({})".format(
                        ",".join([str(id) for id in detached_award_procurement_ids])
                    )
                )

                # Remove Transaction Normalized rows
                cursor.execute(
                    "delete from transaction_normalized where id in ({})".format(
                        ",".join([str(row[0]) for row in transaction_normalized_ids])
                    )
                )

                return awards_touched
    else:
        return []


def run_fpds_load(id_list):
    """
    Run transaction load for the provided ids. This will create any new rows in other tables to support the transaction
    data, but does NOT update "secondary" award values like total obligations or C -> D linkages. If transactions are
    being reloaded, this will also leave behind rows in supporting tables that won't be removed unless destory_orphans
    is called.
    returns ids for each award touched
    """
    chunks = [id_list[x : x + CHUNK_SIZE] for x in range(0, len(id_list), CHUNK_SIZE)]

    modified_awards = []
    for chunk in chunks:
        logger.info("> loading {} ids (ids {}-{})".format(len(chunk), chunk[0], chunk[-1]))
        modified_awards.extend(_load_chunk(chunk))
    return modified_awards


def _load_chunk(chunk):
    with Timer() as timer:
        broker_transactions = _extract_broker_objects(chunk)

        load_objects = _transform_objects(broker_transactions)

        retval = _load_transactions(load_objects)
    logger.info("batch completed in {}".format(timer.as_string(timer.elapsed)))
    return retval


def _extract_broker_objects(id_list):
    formatted_id_list = "({})".format(",".join(map(str, id_list)))

    with psycopg2.connect(dsn=BROKER_CONNECTION_STRING) as connection:
        with connection.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
            sql = "SELECT * from detached_award_procurement where detached_award_procurement_id in {}".format(
                formatted_id_list
            )

            cursor.execute(sql)
            results = cursor.fetchall()

    return results


def _create_load_object(broker_object, non_boolean_column_map, boolean_column_map, function_map):
    retval = {}
    if non_boolean_column_map:
        retval.update(
            {non_boolean_column_map[key]: capitalize_if_string(broker_object[key]) for key in non_boolean_column_map}
        )

    if boolean_column_map:
        retval.update({boolean_column_map[key]: false_if_null(broker_object[key]) for key in boolean_column_map})

    if function_map:
        retval.update({key: func(broker_object) for key, func in function_map.items()})

    return retval


def _transform_objects(broker_objects):
    retval = []

    for broker_object in broker_objects:
        connected_objects = {}

        connected_objects["recipient_location"] = _create_load_object(
            broker_object, recipient_location_columns, None, recipient_location_functions
        )

        connected_objects["legal_entity"] = _create_load_object(
            broker_object, legal_entity_columns, legal_entity_boolean_columns, legal_entity_functions
        )

        connected_objects["place_of_performance_location"] = _create_load_object(
            broker_object, place_of_performance_columns, None, place_of_performance_functions
        )

        # matching award. NOT a real db object, but needs to be stored when making the link in load_transactions
        connected_objects["generated_unique_award_id"] = broker_object["unique_award_key"]

        # award. NOT used if a matching award is found later
        connected_objects["award"] = _create_load_object(broker_object, None, None, award_functions)

        connected_objects["transaction_normalized"] = _create_load_object(
            broker_object, transaction_normalized_columns, None, transaction_normalized_functions
        )

        connected_objects["transaction_fpds"] = _create_load_object(
            broker_object, transaction_fpds_columns, transaction_fpds_boolean_columns, transaction_fpds_functions
        )

        retval.append(connected_objects)
    return retval


def _load_transactions(load_objects):
    """returns ids for each award touched"""
    ids_of_awards_created_or_updated = set()
    with psycopg2.connect(dsn=USASPENDING_CONNECTION_STRING) as connection:
        with connection.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:

            # Insert always, even if duplicative
            # First create the records that don't have a foreign key out to anything else in one transaction per type
            inserted_recipient_locations = insert_recipient_locations(cursor, load_objects)
            for index, elem in enumerate(inserted_recipient_locations):
                load_objects[index]["legal_entity"]["location_id"] = inserted_recipient_locations[index]

            inserted_recipients = insert_recipients(cursor, load_objects)
            for index, elem in enumerate(inserted_recipients):
                load_objects[index]["transaction_normalized"]["recipient_id"] = inserted_recipients[index]
                load_objects[index]["award"]["recipient_id"] = inserted_recipients[index]

            inserted_place_of_performance = insert_place_of_performance(cursor, load_objects)
            for index, elem in enumerate(inserted_place_of_performance):
                load_objects[index]["transaction_normalized"][
                    "place_of_performance_id"
                ] = inserted_place_of_performance[index]
                load_objects[index]["award"]["place_of_performance_id"] = inserted_place_of_performance[index]

            # Handle transaction-to-award relationship for each transaction to be loaded
            for load_object in load_objects:

                # AWARD GET OR CREATE
                award_id = _lookup_award_by_transaction(cursor, load_object)
                if not award_id:
                    # If there is no award, we need to create one
                    award_id = insert_award(cursor, load_object)

                load_object["transaction_normalized"]["award_id"] = award_id
                ids_of_awards_created_or_updated.add(award_id)

                # TRANSACTION UPSERT
                transaction_id = _lookup_existing_transaction(cursor, load_object)
                if transaction_id:
                    # Inject the Primary Key of transaction_normalized+transaction_fpds that was found, so that the
                    # following updates can find it to update
                    load_object["transaction_fpds"]["transaction_id"] = transaction_id
                    _update_fpds_transaction(cursor, load_object, transaction_id)
                else:
                    # If there is no transaction we create a new one.
                    transaction_id = _insert_fpds_transaction(cursor, load_object)

                load_object["transaction_fpds"]["transaction_id"] = transaction_id
                load_object["award"]["latest_transaction_id"] = transaction_id

    return list(ids_of_awards_created_or_updated)


def _lookup_award_by_transaction(cursor, load_object):
    # Try to find an award for this transaction to belong to
    find_matching_award_sql = "select id from awards where generated_unique_award_id = '{}'".format(
        load_object["generated_unique_award_id"]
    )
    results = cursor.execute(find_matching_award_sql)
    return results[0][0] if results else None


def _lookup_existing_transaction(cursor, load_object):
    # Determine if we are making a new transaction, or updating an old one
    find_matching_transaction_sql = (
        "select transaction_id from transaction_fpds "
        "where detached_award_proc_unique = '{}'".format(load_object["transaction_fpds"]["detached_award_proc_unique"])
    )
    cursor.execute(find_matching_transaction_sql)
    results = cursor.fetchall()
    return results[0][0] if results else None


def _update_fpds_transaction(cursor, load_object, transaction_id):
    # If there is a transaction (transaction_normalized and transaction_fpds should be one-to-one)
    # we update all values
    update_transaction_fpds(cursor, load_object)
    update_transaction_normalized(cursor, load_object)
    logger.debug("updated fpds transaction {}".format(transaction_id))


def _insert_fpds_transaction(cursor, load_object):
    # transaction_normalized and transaction_fpds should be one-to-one
    transaction_normalized_id = insert_transaction_normalized(cursor, load_object)

    # Inject the Primary Key of transaction_normalized row that this record is mapped to in the one-to-one relationship
    load_object["transaction_fpds"]["transaction_id"] = transaction_normalized_id

    transaction_fpds_id = insert_transaction_fpds(cursor, load_object)
    logger.debug("created fpds transaction {}".format(transaction_fpds_id))
    return transaction_fpds_id
