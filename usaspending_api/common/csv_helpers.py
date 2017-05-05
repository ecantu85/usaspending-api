from django.core.urlresolvers import resolve
from django.utils.six.moves.urllib.parse import urlparse

from django.conf import settings

import boto3
import botocore
import json


def s3_get_url(path, checksum):
    '''
    Returns a pre-signed S3 URL for the CSV file, or None if the file does not exist
    '''
    s3 = boto3.client('s3')
    filename = create_filename_from_options(path, checksum)

    try:
        s3.Object(settings.CSV_S3_BUCKET, filename).load()
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == "404":
            return None
        else:
            raise
    else:
        url = s3.generate_presigned_url(
            ClientMethod='get_object',
            Params={
                'Bucket': settings.CSV_S3_BUCKET,
                'Key': filename
            }
        )

        return url


def s3_empty_bucket():
    '''
    Deletes all keys in the S3 bucket
    '''
    s3 = boto3.client('s3')
    bucket = s3.Bucket(settings.CSV_S3_BUCKET)
    s3.meta.client.head_bucket(Bucket=settings.CSV_S3_BUCKET)
    for key in bucket.objects.all():
        key.delete()
    return True


def sqs_add_to_queue(path, checksum):
    '''
    Adds a request to generate a CSV file to the SQS queue
    '''
    sqs = boto3.client('sqs')

    queue = sqs.get_queue_by_name(QueueName=settings.SQS_QUEUE_NAME)

    queue.send_message(MessageBody=json.dumps({
        "request_checksum": checksum,
        "request_path": format_path(path),
    }))


def format_path(path):
    # Do some cleanup on the path
    # Add a starting slash if we don't have it
    if path[0] != "/":
        path = "/{}".format(path)

    # Add a trailing slash if we don't have get parameters and there is no trailing slash
    if '?' not in path and path[-1] != "/":
        path = "{}/".format(path)

    # Prepend with /api/v1 if it's not there
    if path[:7] != "/api/v1":
        path = "/api/v1{}".format(path)

    return path


def create_filename_from_options(path, checksum):
    path = format_path(path)
    split_path = [x for x in path.split("/") if len(x) > 0 and x != "api"]
    split_path.append(checksum)

    filename = "{}.csv".format("_".join(split_path))

    return filename


def resolve_path_to_view(request_path):
    '''
    Returns a viewset if the path resolves to a view and if that view supports
    the get queryset function. In any other case, it returns None
    '''
    # Resolve the path to a view
    view, args, kwargs = resolve(urlparse(request_path)[2])

    if not view:
        return None

    # Instantiate the view and pass the request in
    view = view.cls()

    if not hasattr(view, "get_queryset"):
        return None

    return view
