import logging

import boto3
from tenacity import retry, stop_after_attempt, wait_exponential

from rest_framework import status
from rest_framework.response import Response

from .config import AWS_AUTH, AWS_S3_REGION_NAME

logger = logging.getLogger("sparta_games")


def std_response(
    data=None,
    message=None,
    status="error",
    pagination=None,
    error_code=None,
    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
):
    response = {
        "status": status,
        "message": message,
        "data": data,
        "pagination": pagination,
        "error_code": error_code
    }
    return Response(response, status=status_code)


# ==================== S3 헬퍼 ====================

def get_s3_client():
    """S3 클라이언트 생성 (호출부에서 재사용)"""
    return boto3.client(
        "s3",
        aws_access_key_id=AWS_AUTH["aws_access_key_id"],
        aws_secret_access_key=AWS_AUTH["aws_secret_access_key"],
        region_name=AWS_S3_REGION_NAME,
    )


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def safe_s3_delete(s3_client, bucket, keys):
    """
    S3 오브젝트 삭제 (최대 3회 재시도, 2s/4s/8s 백오프)

    Args:
        s3_client: boto3 S3 클라이언트
        bucket: S3 버킷명
        keys: 삭제할 키 리스트

    Raises:
        Exception: 3회 재시도 후에도 실패하면 예외 발생
    """
    if not keys:
        return

    try:
        s3_client.delete_objects(
            Bucket=bucket,
            Delete={"Objects": [{"Key": k} for k in keys]},
        )
        logger.debug(f"S3 delete success: {len(keys)} objects deleted")
    except Exception as e:
        logger.warning(f"S3 delete attempt failed: {e}, retrying...")
        raise


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def safe_s3_tag(s3_client, bucket, key, tags):
    """
    S3 오브젝트 태깅 (최대 3회 재시도, 2s/4s/8s 백오프)

    Args:
        s3_client: boto3 S3 클라이언트
        bucket: S3 버킷명
        key: S3 키
        tags: 태그 딕셔너리 {Key: Value}

    Raises:
        Exception: 3회 재시도 후에도 실패하면 예외 발생
    """
    try:
        tag_set = [{"Key": k, "Value": v} for k, v in tags.items()]
        s3_client.put_object_tagging(
            Bucket=bucket,
            Key=key,
            Tagging={"TagSet": tag_set},
        )
        logger.debug(f"S3 tag success: {key}")
    except Exception as e:
        logger.warning(f"S3 tag attempt failed for {key}: {e}, retrying...")
        raise
