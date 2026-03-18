from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, Optional

import boto3


@dataclass
class S3Storage:
    endpoint_url: str
    access_key: str
    secret_key: str
    region: str
    bucket: str
    sse_kms_key_id: str = ""

    def _client(self):
        return boto3.client(
            "s3",
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            region_name=self.region,
        )

    def _extra_args(self) -> Dict[str, Any]:
        if not self.sse_kms_key_id:
            return {}
        return {
            "ServerSideEncryption": "aws:kms",
            "SSEKMSKeyId": self.sse_kms_key_id,
        }

    def upload_bytes(self, key: str, data: bytes, content_type: Optional[str] = None) -> None:
        extra_args = self._extra_args()
        if content_type:
            extra_args["ContentType"] = content_type
        self._client().put_object(Bucket=self.bucket, Key=key, Body=data, **extra_args)

    def upload_json(self, key: str, payload: Dict[str, Any]) -> None:
        data = json.dumps(payload, ensure_ascii=True, indent=2).encode("utf-8")
        self.upload_bytes(key, data, content_type="application/json")

    def upload_file(self, key: str, filename: str, content_type: Optional[str] = None) -> None:
        extra_args = self._extra_args()
        if content_type:
            extra_args["ContentType"] = content_type
        self._client().upload_file(filename, self.bucket, key, ExtraArgs=extra_args)
