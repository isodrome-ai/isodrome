from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class Role(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    ROLE_UNSPECIFIED: _ClassVar[Role]
    ROLE_ADMIN: _ClassVar[Role]
    ROLE_WRITER: _ClassVar[Role]
    ROLE_READER: _ClassVar[Role]

class CredentialKind(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    CREDENTIAL_KIND_UNSPECIFIED: _ClassVar[CredentialKind]
    CREDENTIAL_KIND_API_KEY: _ClassVar[CredentialKind]
    CREDENTIAL_KIND_SESSION: _ClassVar[CredentialKind]

class TimeUnit(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    TIME_UNIT_UNSPECIFIED: _ClassVar[TimeUnit]
    TIME_UNIT_SECONDS: _ClassVar[TimeUnit]
    TIME_UNIT_MILLISECONDS: _ClassVar[TimeUnit]
    TIME_UNIT_MICROSECONDS: _ClassVar[TimeUnit]
    TIME_UNIT_NANOSECONDS: _ClassVar[TimeUnit]

class AckMode(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    ACK_MODE_UNSPECIFIED: _ClassVar[AckMode]
    ACK_MODE_REPLICATED: _ClassVar[AckMode]
    ACK_MODE_NONE: _ClassVar[AckMode]

class ColumnType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    COLUMN_TYPE_UNSPECIFIED: _ClassVar[ColumnType]
    COLUMN_TYPE_BOOL: _ClassVar[ColumnType]
    COLUMN_TYPE_INT64: _ClassVar[ColumnType]
    COLUMN_TYPE_FLOAT64: _ClassVar[ColumnType]
    COLUMN_TYPE_STRING: _ClassVar[ColumnType]
    COLUMN_TYPE_JSON: _ClassVar[ColumnType]

class RejectionReason(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    REJECTION_REASON_UNSPECIFIED: _ClassVar[RejectionReason]
    REJECTION_REASON_INVALID_JSON: _ClassVar[RejectionReason]
    REJECTION_REASON_NOT_AN_OBJECT: _ClassVar[RejectionReason]
    REJECTION_REASON_MISSING_EVENT_TIME: _ClassVar[RejectionReason]
    REJECTION_REASON_INVALID_EVENT_TIME: _ClassVar[RejectionReason]
    REJECTION_REASON_MISSING_KEY: _ClassVar[RejectionReason]
    REJECTION_REASON_INVALID_KEY: _ClassVar[RejectionReason]
    REJECTION_REASON_PAYLOAD_TOO_LARGE: _ClassVar[RejectionReason]
    REJECTION_REASON_MISSING_MESSAGE_ID: _ClassVar[RejectionReason]
    REJECTION_REASON_MESSAGE_ID_REUSED: _ClassVar[RejectionReason]

class FilterOp(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    FILTER_OP_UNSPECIFIED: _ClassVar[FilterOp]
    FILTER_OP_EQ: _ClassVar[FilterOp]
    FILTER_OP_NE: _ClassVar[FilterOp]
    FILTER_OP_LT: _ClassVar[FilterOp]
    FILTER_OP_LTE: _ClassVar[FilterOp]
    FILTER_OP_GT: _ClassVar[FilterOp]
    FILTER_OP_GTE: _ClassVar[FilterOp]
    FILTER_OP_IN: _ClassVar[FilterOp]
    FILTER_OP_IS_NULL: _ClassVar[FilterOp]
    FILTER_OP_IS_NOT_NULL: _ClassVar[FilterOp]

class AsOfBasis(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    AS_OF_BASIS_UNSPECIFIED: _ClassVar[AsOfBasis]
    AS_OF_BASIS_RECEIVED: _ClassVar[AsOfBasis]
    AS_OF_BASIS_PUBLISHED: _ClassVar[AsOfBasis]

class DedupeKeep(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    DEDUPE_KEEP_UNSPECIFIED: _ClassVar[DedupeKeep]
    DEDUPE_KEEP_FIRST: _ClassVar[DedupeKeep]
    DEDUPE_KEEP_LAST: _ClassVar[DedupeKeep]

class DedupeOrder(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    DEDUPE_ORDER_UNSPECIFIED: _ClassVar[DedupeOrder]
    DEDUPE_ORDER_ARRIVAL: _ClassVar[DedupeOrder]
    DEDUPE_ORDER_PUBLICATION: _ClassVar[DedupeOrder]

class Delivery(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    DELIVERY_UNSPECIFIED: _ClassVar[Delivery]
    DELIVERY_CONFIRMED: _ClassVar[Delivery]
    DELIVERY_FAST: _ClassVar[Delivery]

class UsageBucket(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    USAGE_BUCKET_UNSPECIFIED: _ClassVar[UsageBucket]
    USAGE_BUCKET_MINUTE: _ClassVar[UsageBucket]
    USAGE_BUCKET_HOUR: _ClassVar[UsageBucket]
    USAGE_BUCKET_DAY: _ClassVar[UsageBucket]
ROLE_UNSPECIFIED: Role
ROLE_ADMIN: Role
ROLE_WRITER: Role
ROLE_READER: Role
CREDENTIAL_KIND_UNSPECIFIED: CredentialKind
CREDENTIAL_KIND_API_KEY: CredentialKind
CREDENTIAL_KIND_SESSION: CredentialKind
TIME_UNIT_UNSPECIFIED: TimeUnit
TIME_UNIT_SECONDS: TimeUnit
TIME_UNIT_MILLISECONDS: TimeUnit
TIME_UNIT_MICROSECONDS: TimeUnit
TIME_UNIT_NANOSECONDS: TimeUnit
ACK_MODE_UNSPECIFIED: AckMode
ACK_MODE_REPLICATED: AckMode
ACK_MODE_NONE: AckMode
COLUMN_TYPE_UNSPECIFIED: ColumnType
COLUMN_TYPE_BOOL: ColumnType
COLUMN_TYPE_INT64: ColumnType
COLUMN_TYPE_FLOAT64: ColumnType
COLUMN_TYPE_STRING: ColumnType
COLUMN_TYPE_JSON: ColumnType
REJECTION_REASON_UNSPECIFIED: RejectionReason
REJECTION_REASON_INVALID_JSON: RejectionReason
REJECTION_REASON_NOT_AN_OBJECT: RejectionReason
REJECTION_REASON_MISSING_EVENT_TIME: RejectionReason
REJECTION_REASON_INVALID_EVENT_TIME: RejectionReason
REJECTION_REASON_MISSING_KEY: RejectionReason
REJECTION_REASON_INVALID_KEY: RejectionReason
REJECTION_REASON_PAYLOAD_TOO_LARGE: RejectionReason
REJECTION_REASON_MISSING_MESSAGE_ID: RejectionReason
REJECTION_REASON_MESSAGE_ID_REUSED: RejectionReason
FILTER_OP_UNSPECIFIED: FilterOp
FILTER_OP_EQ: FilterOp
FILTER_OP_NE: FilterOp
FILTER_OP_LT: FilterOp
FILTER_OP_LTE: FilterOp
FILTER_OP_GT: FilterOp
FILTER_OP_GTE: FilterOp
FILTER_OP_IN: FilterOp
FILTER_OP_IS_NULL: FilterOp
FILTER_OP_IS_NOT_NULL: FilterOp
AS_OF_BASIS_UNSPECIFIED: AsOfBasis
AS_OF_BASIS_RECEIVED: AsOfBasis
AS_OF_BASIS_PUBLISHED: AsOfBasis
DEDUPE_KEEP_UNSPECIFIED: DedupeKeep
DEDUPE_KEEP_FIRST: DedupeKeep
DEDUPE_KEEP_LAST: DedupeKeep
DEDUPE_ORDER_UNSPECIFIED: DedupeOrder
DEDUPE_ORDER_ARRIVAL: DedupeOrder
DEDUPE_ORDER_PUBLICATION: DedupeOrder
DELIVERY_UNSPECIFIED: Delivery
DELIVERY_CONFIRMED: Delivery
DELIVERY_FAST: Delivery
USAGE_BUCKET_UNSPECIFIED: UsageBucket
USAGE_BUCKET_MINUTE: UsageBucket
USAGE_BUCKET_HOUR: UsageBucket
USAGE_BUCKET_DAY: UsageBucket

class GetServerInfoRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class ServerInfo(_message.Message):
    __slots__ = ("version", "revision", "api_version", "public_url", "max_payload_bytes", "dedupe_window_ns", "capabilities")
    VERSION_FIELD_NUMBER: _ClassVar[int]
    REVISION_FIELD_NUMBER: _ClassVar[int]
    API_VERSION_FIELD_NUMBER: _ClassVar[int]
    PUBLIC_URL_FIELD_NUMBER: _ClassVar[int]
    MAX_PAYLOAD_BYTES_FIELD_NUMBER: _ClassVar[int]
    DEDUPE_WINDOW_NS_FIELD_NUMBER: _ClassVar[int]
    CAPABILITIES_FIELD_NUMBER: _ClassVar[int]
    version: str
    revision: str
    api_version: str
    public_url: str
    max_payload_bytes: int
    dedupe_window_ns: int
    capabilities: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, version: _Optional[str] = ..., revision: _Optional[str] = ..., api_version: _Optional[str] = ..., public_url: _Optional[str] = ..., max_payload_bytes: _Optional[int] = ..., dedupe_window_ns: _Optional[int] = ..., capabilities: _Optional[_Iterable[str]] = ...) -> None: ...

class WhoAmIRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class WhoAmIResponse(_message.Message):
    __slots__ = ("organization", "default_namespace", "role", "key_id", "email", "kind", "expires_at_ns", "service_account")
    ORGANIZATION_FIELD_NUMBER: _ClassVar[int]
    DEFAULT_NAMESPACE_FIELD_NUMBER: _ClassVar[int]
    ROLE_FIELD_NUMBER: _ClassVar[int]
    KEY_ID_FIELD_NUMBER: _ClassVar[int]
    EMAIL_FIELD_NUMBER: _ClassVar[int]
    KIND_FIELD_NUMBER: _ClassVar[int]
    EXPIRES_AT_NS_FIELD_NUMBER: _ClassVar[int]
    SERVICE_ACCOUNT_FIELD_NUMBER: _ClassVar[int]
    organization: str
    default_namespace: str
    role: Role
    key_id: str
    email: str
    kind: CredentialKind
    expires_at_ns: int
    service_account: str
    def __init__(self, organization: _Optional[str] = ..., default_namespace: _Optional[str] = ..., role: _Optional[_Union[Role, str]] = ..., key_id: _Optional[str] = ..., email: _Optional[str] = ..., kind: _Optional[_Union[CredentialKind, str]] = ..., expires_at_ns: _Optional[int] = ..., service_account: _Optional[str] = ...) -> None: ...

class Namespace(_message.Message):
    __slots__ = ("id", "organization", "name", "created_at_ns", "public", "owner")
    ID_FIELD_NUMBER: _ClassVar[int]
    ORGANIZATION_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_NS_FIELD_NUMBER: _ClassVar[int]
    PUBLIC_FIELD_NUMBER: _ClassVar[int]
    OWNER_FIELD_NUMBER: _ClassVar[int]
    id: str
    organization: str
    name: str
    created_at_ns: int
    public: bool
    owner: str
    def __init__(self, id: _Optional[str] = ..., organization: _Optional[str] = ..., name: _Optional[str] = ..., created_at_ns: _Optional[int] = ..., public: bool = ..., owner: _Optional[str] = ...) -> None: ...

class CreateNamespaceRequest(_message.Message):
    __slots__ = ("name", "public")
    NAME_FIELD_NUMBER: _ClassVar[int]
    PUBLIC_FIELD_NUMBER: _ClassVar[int]
    name: str
    public: bool
    def __init__(self, name: _Optional[str] = ..., public: bool = ...) -> None: ...

class UpdateNamespaceRequest(_message.Message):
    __slots__ = ("name", "public")
    NAME_FIELD_NUMBER: _ClassVar[int]
    PUBLIC_FIELD_NUMBER: _ClassVar[int]
    name: str
    public: bool
    def __init__(self, name: _Optional[str] = ..., public: bool = ...) -> None: ...

class ListNamespacesRequest(_message.Message):
    __slots__ = ("public",)
    PUBLIC_FIELD_NUMBER: _ClassVar[int]
    public: bool
    def __init__(self, public: bool = ...) -> None: ...

class ListNamespacesResponse(_message.Message):
    __slots__ = ("namespaces",)
    NAMESPACES_FIELD_NUMBER: _ClassVar[int]
    namespaces: _containers.RepeatedCompositeFieldContainer[Namespace]
    def __init__(self, namespaces: _Optional[_Iterable[_Union[Namespace, _Mapping]]] = ...) -> None: ...

class DeleteNamespaceRequest(_message.Message):
    __slots__ = ("name",)
    NAME_FIELD_NUMBER: _ClassVar[int]
    name: str
    def __init__(self, name: _Optional[str] = ...) -> None: ...

class DeleteNamespaceResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class ApiKey(_message.Message):
    __slots__ = ("key_id", "role", "default_namespace", "name", "created_at_ns", "revoked", "kind", "owner", "created_by", "expires_at_ns")
    KEY_ID_FIELD_NUMBER: _ClassVar[int]
    ROLE_FIELD_NUMBER: _ClassVar[int]
    DEFAULT_NAMESPACE_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_NS_FIELD_NUMBER: _ClassVar[int]
    REVOKED_FIELD_NUMBER: _ClassVar[int]
    KIND_FIELD_NUMBER: _ClassVar[int]
    OWNER_FIELD_NUMBER: _ClassVar[int]
    CREATED_BY_FIELD_NUMBER: _ClassVar[int]
    EXPIRES_AT_NS_FIELD_NUMBER: _ClassVar[int]
    key_id: str
    role: Role
    default_namespace: str
    name: str
    created_at_ns: int
    revoked: bool
    kind: CredentialKind
    owner: str
    created_by: str
    expires_at_ns: int
    def __init__(self, key_id: _Optional[str] = ..., role: _Optional[_Union[Role, str]] = ..., default_namespace: _Optional[str] = ..., name: _Optional[str] = ..., created_at_ns: _Optional[int] = ..., revoked: bool = ..., kind: _Optional[_Union[CredentialKind, str]] = ..., owner: _Optional[str] = ..., created_by: _Optional[str] = ..., expires_at_ns: _Optional[int] = ...) -> None: ...

class CreateApiKeyRequest(_message.Message):
    __slots__ = ("role", "default_namespace", "name", "personal", "service_account")
    ROLE_FIELD_NUMBER: _ClassVar[int]
    DEFAULT_NAMESPACE_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    PERSONAL_FIELD_NUMBER: _ClassVar[int]
    SERVICE_ACCOUNT_FIELD_NUMBER: _ClassVar[int]
    role: Role
    default_namespace: str
    name: str
    personal: bool
    service_account: str
    def __init__(self, role: _Optional[_Union[Role, str]] = ..., default_namespace: _Optional[str] = ..., name: _Optional[str] = ..., personal: bool = ..., service_account: _Optional[str] = ...) -> None: ...

class ServiceAccount(_message.Message):
    __slots__ = ("id", "name", "role", "created_at_ns")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    ROLE_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_NS_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    role: Role
    created_at_ns: int
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., role: _Optional[_Union[Role, str]] = ..., created_at_ns: _Optional[int] = ...) -> None: ...

class CreateServiceAccountRequest(_message.Message):
    __slots__ = ("name", "role")
    NAME_FIELD_NUMBER: _ClassVar[int]
    ROLE_FIELD_NUMBER: _ClassVar[int]
    name: str
    role: Role
    def __init__(self, name: _Optional[str] = ..., role: _Optional[_Union[Role, str]] = ...) -> None: ...

class ListServiceAccountsRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class ListServiceAccountsResponse(_message.Message):
    __slots__ = ("service_accounts",)
    SERVICE_ACCOUNTS_FIELD_NUMBER: _ClassVar[int]
    service_accounts: _containers.RepeatedCompositeFieldContainer[ServiceAccount]
    def __init__(self, service_accounts: _Optional[_Iterable[_Union[ServiceAccount, _Mapping]]] = ...) -> None: ...

class DeleteServiceAccountRequest(_message.Message):
    __slots__ = ("name",)
    NAME_FIELD_NUMBER: _ClassVar[int]
    name: str
    def __init__(self, name: _Optional[str] = ...) -> None: ...

class DeleteServiceAccountResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class CreateApiKeyResponse(_message.Message):
    __slots__ = ("key", "api_key")
    KEY_FIELD_NUMBER: _ClassVar[int]
    API_KEY_FIELD_NUMBER: _ClassVar[int]
    key: ApiKey
    api_key: str
    def __init__(self, key: _Optional[_Union[ApiKey, _Mapping]] = ..., api_key: _Optional[str] = ...) -> None: ...

class ListApiKeysRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class ListApiKeysResponse(_message.Message):
    __slots__ = ("keys",)
    KEYS_FIELD_NUMBER: _ClassVar[int]
    keys: _containers.RepeatedCompositeFieldContainer[ApiKey]
    def __init__(self, keys: _Optional[_Iterable[_Union[ApiKey, _Mapping]]] = ...) -> None: ...

class RevokeApiKeyRequest(_message.Message):
    __slots__ = ("key_id",)
    KEY_ID_FIELD_NUMBER: _ClassVar[int]
    key_id: str
    def __init__(self, key_id: _Optional[str] = ...) -> None: ...

class FeedRef(_message.Message):
    __slots__ = ("namespace", "name", "organization", "version", "tag")
    NAMESPACE_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    ORGANIZATION_FIELD_NUMBER: _ClassVar[int]
    VERSION_FIELD_NUMBER: _ClassVar[int]
    TAG_FIELD_NUMBER: _ClassVar[int]
    namespace: str
    name: str
    organization: str
    version: int
    tag: str
    def __init__(self, namespace: _Optional[str] = ..., name: _Optional[str] = ..., organization: _Optional[str] = ..., version: _Optional[int] = ..., tag: _Optional[str] = ...) -> None: ...

class Column(_message.Message):
    __slots__ = ("name", "type", "first_seen_ns")
    NAME_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    FIRST_SEEN_NS_FIELD_NUMBER: _ClassVar[int]
    name: str
    type: ColumnType
    first_seen_ns: int
    def __init__(self, name: _Optional[str] = ..., type: _Optional[_Union[ColumnType, str]] = ..., first_seen_ns: _Optional[int] = ...) -> None: ...

class FeedStats(_message.Message):
    __slots__ = ("events_flushed", "events_pending_flush", "flush_lag_ms", "file_count", "schema_conflicts", "rejections", "last_event_time_ns", "last_receive_time_ns", "last_published_time_ns", "events_ingested_total", "bytes_ingested_total", "bytes_read_total", "bytes_stored")
    EVENTS_FLUSHED_FIELD_NUMBER: _ClassVar[int]
    EVENTS_PENDING_FLUSH_FIELD_NUMBER: _ClassVar[int]
    FLUSH_LAG_MS_FIELD_NUMBER: _ClassVar[int]
    FILE_COUNT_FIELD_NUMBER: _ClassVar[int]
    SCHEMA_CONFLICTS_FIELD_NUMBER: _ClassVar[int]
    REJECTIONS_FIELD_NUMBER: _ClassVar[int]
    LAST_EVENT_TIME_NS_FIELD_NUMBER: _ClassVar[int]
    LAST_RECEIVE_TIME_NS_FIELD_NUMBER: _ClassVar[int]
    LAST_PUBLISHED_TIME_NS_FIELD_NUMBER: _ClassVar[int]
    EVENTS_INGESTED_TOTAL_FIELD_NUMBER: _ClassVar[int]
    BYTES_INGESTED_TOTAL_FIELD_NUMBER: _ClassVar[int]
    BYTES_READ_TOTAL_FIELD_NUMBER: _ClassVar[int]
    BYTES_STORED_FIELD_NUMBER: _ClassVar[int]
    events_flushed: int
    events_pending_flush: int
    flush_lag_ms: int
    file_count: int
    schema_conflicts: int
    rejections: RejectionStats
    last_event_time_ns: int
    last_receive_time_ns: int
    last_published_time_ns: int
    events_ingested_total: int
    bytes_ingested_total: int
    bytes_read_total: int
    bytes_stored: int
    def __init__(self, events_flushed: _Optional[int] = ..., events_pending_flush: _Optional[int] = ..., flush_lag_ms: _Optional[int] = ..., file_count: _Optional[int] = ..., schema_conflicts: _Optional[int] = ..., rejections: _Optional[_Union[RejectionStats, _Mapping]] = ..., last_event_time_ns: _Optional[int] = ..., last_receive_time_ns: _Optional[int] = ..., last_published_time_ns: _Optional[int] = ..., events_ingested_total: _Optional[int] = ..., bytes_ingested_total: _Optional[int] = ..., bytes_read_total: _Optional[int] = ..., bytes_stored: _Optional[int] = ...) -> None: ...

class RejectionStats(_message.Message):
    __slots__ = ("total", "last_hour", "last_hour_by_reason", "latest")
    class LastHourByReasonEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: int
        def __init__(self, key: _Optional[str] = ..., value: _Optional[int] = ...) -> None: ...
    TOTAL_FIELD_NUMBER: _ClassVar[int]
    LAST_HOUR_FIELD_NUMBER: _ClassVar[int]
    LAST_HOUR_BY_REASON_FIELD_NUMBER: _ClassVar[int]
    LATEST_FIELD_NUMBER: _ClassVar[int]
    total: int
    last_hour: int
    last_hour_by_reason: _containers.ScalarMap[str, int]
    latest: Rejected
    def __init__(self, total: _Optional[int] = ..., last_hour: _Optional[int] = ..., last_hour_by_reason: _Optional[_Mapping[str, int]] = ..., latest: _Optional[_Union[Rejected, _Mapping]] = ...) -> None: ...

class Rejected(_message.Message):
    __slots__ = ("message_id", "reason", "detail", "rejected_at_ns", "payload", "original_payload_bytes")
    MESSAGE_ID_FIELD_NUMBER: _ClassVar[int]
    REASON_FIELD_NUMBER: _ClassVar[int]
    DETAIL_FIELD_NUMBER: _ClassVar[int]
    REJECTED_AT_NS_FIELD_NUMBER: _ClassVar[int]
    PAYLOAD_FIELD_NUMBER: _ClassVar[int]
    ORIGINAL_PAYLOAD_BYTES_FIELD_NUMBER: _ClassVar[int]
    message_id: str
    reason: RejectionReason
    detail: str
    rejected_at_ns: int
    payload: bytes
    original_payload_bytes: int
    def __init__(self, message_id: _Optional[str] = ..., reason: _Optional[_Union[RejectionReason, str]] = ..., detail: _Optional[str] = ..., rejected_at_ns: _Optional[int] = ..., payload: _Optional[bytes] = ..., original_payload_bytes: _Optional[int] = ...) -> None: ...

class ListRejectionsRequest(_message.Message):
    __slots__ = ("feed", "limit")
    FEED_FIELD_NUMBER: _ClassVar[int]
    LIMIT_FIELD_NUMBER: _ClassVar[int]
    feed: FeedRef
    limit: int
    def __init__(self, feed: _Optional[_Union[FeedRef, _Mapping]] = ..., limit: _Optional[int] = ...) -> None: ...

class ListRejectionsResponse(_message.Message):
    __slots__ = ("rejections",)
    REJECTIONS_FIELD_NUMBER: _ClassVar[int]
    rejections: _containers.RepeatedCompositeFieldContainer[Rejected]
    def __init__(self, rejections: _Optional[_Iterable[_Union[Rejected, _Mapping]]] = ...) -> None: ...

class CreateFeedRequest(_message.Message):
    __slots__ = ("feed", "key_field", "time_field", "time_unit", "ack_mode", "partitions", "arrival_time", "publication_time_field", "description", "licence", "attribution", "source_url")
    FEED_FIELD_NUMBER: _ClassVar[int]
    KEY_FIELD_FIELD_NUMBER: _ClassVar[int]
    TIME_FIELD_FIELD_NUMBER: _ClassVar[int]
    TIME_UNIT_FIELD_NUMBER: _ClassVar[int]
    ACK_MODE_FIELD_NUMBER: _ClassVar[int]
    PARTITIONS_FIELD_NUMBER: _ClassVar[int]
    ARRIVAL_TIME_FIELD_NUMBER: _ClassVar[int]
    PUBLICATION_TIME_FIELD_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    LICENCE_FIELD_NUMBER: _ClassVar[int]
    ATTRIBUTION_FIELD_NUMBER: _ClassVar[int]
    SOURCE_URL_FIELD_NUMBER: _ClassVar[int]
    feed: FeedRef
    key_field: str
    time_field: str
    time_unit: TimeUnit
    ack_mode: AckMode
    partitions: int
    arrival_time: bool
    publication_time_field: str
    description: str
    licence: str
    attribution: str
    source_url: str
    def __init__(self, feed: _Optional[_Union[FeedRef, _Mapping]] = ..., key_field: _Optional[str] = ..., time_field: _Optional[str] = ..., time_unit: _Optional[_Union[TimeUnit, str]] = ..., ack_mode: _Optional[_Union[AckMode, str]] = ..., partitions: _Optional[int] = ..., arrival_time: bool = ..., publication_time_field: _Optional[str] = ..., description: _Optional[str] = ..., licence: _Optional[str] = ..., attribution: _Optional[str] = ..., source_url: _Optional[str] = ...) -> None: ...

class UpdateFeedRequest(_message.Message):
    __slots__ = ("feed", "time_field", "arrival_time", "time_unit", "ack_mode", "key_field", "publication_time_field", "description", "licence", "attribution", "source_url")
    FEED_FIELD_NUMBER: _ClassVar[int]
    TIME_FIELD_FIELD_NUMBER: _ClassVar[int]
    ARRIVAL_TIME_FIELD_NUMBER: _ClassVar[int]
    TIME_UNIT_FIELD_NUMBER: _ClassVar[int]
    ACK_MODE_FIELD_NUMBER: _ClassVar[int]
    KEY_FIELD_FIELD_NUMBER: _ClassVar[int]
    PUBLICATION_TIME_FIELD_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    LICENCE_FIELD_NUMBER: _ClassVar[int]
    ATTRIBUTION_FIELD_NUMBER: _ClassVar[int]
    SOURCE_URL_FIELD_NUMBER: _ClassVar[int]
    feed: FeedRef
    time_field: str
    arrival_time: bool
    time_unit: TimeUnit
    ack_mode: AckMode
    key_field: str
    publication_time_field: str
    description: str
    licence: str
    attribution: str
    source_url: str
    def __init__(self, feed: _Optional[_Union[FeedRef, _Mapping]] = ..., time_field: _Optional[str] = ..., arrival_time: bool = ..., time_unit: _Optional[_Union[TimeUnit, str]] = ..., ack_mode: _Optional[_Union[AckMode, str]] = ..., key_field: _Optional[str] = ..., publication_time_field: _Optional[str] = ..., description: _Optional[str] = ..., licence: _Optional[str] = ..., attribution: _Optional[str] = ..., source_url: _Optional[str] = ...) -> None: ...

class Feed(_message.Message):
    __slots__ = ("id", "organization", "namespace", "name", "key_field", "time_field", "time_unit", "ack_mode", "partitions", "created_at_ns", "columns", "stats", "arrival_time", "deleted_at_ns", "purge_at_ns", "publication_time_field", "description", "licence", "attribution", "source_url", "public", "version", "tags", "latest_version")
    ID_FIELD_NUMBER: _ClassVar[int]
    ORGANIZATION_FIELD_NUMBER: _ClassVar[int]
    NAMESPACE_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    KEY_FIELD_FIELD_NUMBER: _ClassVar[int]
    TIME_FIELD_FIELD_NUMBER: _ClassVar[int]
    TIME_UNIT_FIELD_NUMBER: _ClassVar[int]
    ACK_MODE_FIELD_NUMBER: _ClassVar[int]
    PARTITIONS_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_NS_FIELD_NUMBER: _ClassVar[int]
    COLUMNS_FIELD_NUMBER: _ClassVar[int]
    STATS_FIELD_NUMBER: _ClassVar[int]
    ARRIVAL_TIME_FIELD_NUMBER: _ClassVar[int]
    DELETED_AT_NS_FIELD_NUMBER: _ClassVar[int]
    PURGE_AT_NS_FIELD_NUMBER: _ClassVar[int]
    PUBLICATION_TIME_FIELD_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    LICENCE_FIELD_NUMBER: _ClassVar[int]
    ATTRIBUTION_FIELD_NUMBER: _ClassVar[int]
    SOURCE_URL_FIELD_NUMBER: _ClassVar[int]
    PUBLIC_FIELD_NUMBER: _ClassVar[int]
    VERSION_FIELD_NUMBER: _ClassVar[int]
    TAGS_FIELD_NUMBER: _ClassVar[int]
    LATEST_VERSION_FIELD_NUMBER: _ClassVar[int]
    id: str
    organization: str
    namespace: str
    name: str
    key_field: str
    time_field: str
    time_unit: TimeUnit
    ack_mode: AckMode
    partitions: int
    created_at_ns: int
    columns: _containers.RepeatedCompositeFieldContainer[Column]
    stats: FeedStats
    arrival_time: bool
    deleted_at_ns: int
    purge_at_ns: int
    publication_time_field: str
    description: str
    licence: str
    attribution: str
    source_url: str
    public: bool
    version: int
    tags: _containers.RepeatedScalarFieldContainer[str]
    latest_version: int
    def __init__(self, id: _Optional[str] = ..., organization: _Optional[str] = ..., namespace: _Optional[str] = ..., name: _Optional[str] = ..., key_field: _Optional[str] = ..., time_field: _Optional[str] = ..., time_unit: _Optional[_Union[TimeUnit, str]] = ..., ack_mode: _Optional[_Union[AckMode, str]] = ..., partitions: _Optional[int] = ..., created_at_ns: _Optional[int] = ..., columns: _Optional[_Iterable[_Union[Column, _Mapping]]] = ..., stats: _Optional[_Union[FeedStats, _Mapping]] = ..., arrival_time: bool = ..., deleted_at_ns: _Optional[int] = ..., purge_at_ns: _Optional[int] = ..., publication_time_field: _Optional[str] = ..., description: _Optional[str] = ..., licence: _Optional[str] = ..., attribution: _Optional[str] = ..., source_url: _Optional[str] = ..., public: bool = ..., version: _Optional[int] = ..., tags: _Optional[_Iterable[str]] = ..., latest_version: _Optional[int] = ...) -> None: ...

class DeleteFeedRequest(_message.Message):
    __slots__ = ("feed",)
    FEED_FIELD_NUMBER: _ClassVar[int]
    feed: FeedRef
    def __init__(self, feed: _Optional[_Union[FeedRef, _Mapping]] = ...) -> None: ...

class DeclareFeedRequest(_message.Message):
    __slots__ = ("definition", "allow_new_version")
    DEFINITION_FIELD_NUMBER: _ClassVar[int]
    ALLOW_NEW_VERSION_FIELD_NUMBER: _ClassVar[int]
    definition: CreateFeedRequest
    allow_new_version: bool
    def __init__(self, definition: _Optional[_Union[CreateFeedRequest, _Mapping]] = ..., allow_new_version: bool = ...) -> None: ...

class DeclareFeedResponse(_message.Message):
    __slots__ = ("feed", "outcome")
    FEED_FIELD_NUMBER: _ClassVar[int]
    OUTCOME_FIELD_NUMBER: _ClassVar[int]
    feed: Feed
    outcome: str
    def __init__(self, feed: _Optional[_Union[Feed, _Mapping]] = ..., outcome: _Optional[str] = ...) -> None: ...

class SetFeedTagRequest(_message.Message):
    __slots__ = ("feed", "tag")
    FEED_FIELD_NUMBER: _ClassVar[int]
    TAG_FIELD_NUMBER: _ClassVar[int]
    feed: FeedRef
    tag: str
    def __init__(self, feed: _Optional[_Union[FeedRef, _Mapping]] = ..., tag: _Optional[str] = ...) -> None: ...

class DeleteFeedTagRequest(_message.Message):
    __slots__ = ("feed", "tag")
    FEED_FIELD_NUMBER: _ClassVar[int]
    TAG_FIELD_NUMBER: _ClassVar[int]
    feed: FeedRef
    tag: str
    def __init__(self, feed: _Optional[_Union[FeedRef, _Mapping]] = ..., tag: _Optional[str] = ...) -> None: ...

class DeleteFeedTagResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class UndeleteFeedRequest(_message.Message):
    __slots__ = ("feed", "id")
    FEED_FIELD_NUMBER: _ClassVar[int]
    ID_FIELD_NUMBER: _ClassVar[int]
    feed: FeedRef
    id: str
    def __init__(self, feed: _Optional[_Union[FeedRef, _Mapping]] = ..., id: _Optional[str] = ...) -> None: ...

class GetFeedRequest(_message.Message):
    __slots__ = ("feed",)
    FEED_FIELD_NUMBER: _ClassVar[int]
    feed: FeedRef
    def __init__(self, feed: _Optional[_Union[FeedRef, _Mapping]] = ...) -> None: ...

class ListFeedsRequest(_message.Message):
    __slots__ = ("namespace", "deleted", "organization", "all_versions")
    NAMESPACE_FIELD_NUMBER: _ClassVar[int]
    DELETED_FIELD_NUMBER: _ClassVar[int]
    ORGANIZATION_FIELD_NUMBER: _ClassVar[int]
    ALL_VERSIONS_FIELD_NUMBER: _ClassVar[int]
    namespace: str
    deleted: bool
    organization: str
    all_versions: bool
    def __init__(self, namespace: _Optional[str] = ..., deleted: bool = ..., organization: _Optional[str] = ..., all_versions: bool = ...) -> None: ...

class ListFeedsResponse(_message.Message):
    __slots__ = ("feeds",)
    FEEDS_FIELD_NUMBER: _ClassVar[int]
    feeds: _containers.RepeatedCompositeFieldContainer[Feed]
    def __init__(self, feeds: _Optional[_Iterable[_Union[Feed, _Mapping]]] = ...) -> None: ...

class Event(_message.Message):
    __slots__ = ("payload", "event_time_ns", "message_id", "published_time_ns")
    PAYLOAD_FIELD_NUMBER: _ClassVar[int]
    EVENT_TIME_NS_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_ID_FIELD_NUMBER: _ClassVar[int]
    PUBLISHED_TIME_NS_FIELD_NUMBER: _ClassVar[int]
    payload: bytes
    event_time_ns: int
    message_id: str
    published_time_ns: int
    def __init__(self, payload: _Optional[bytes] = ..., event_time_ns: _Optional[int] = ..., message_id: _Optional[str] = ..., published_time_ns: _Optional[int] = ...) -> None: ...

class SendRequest(_message.Message):
    __slots__ = ("feed", "events")
    FEED_FIELD_NUMBER: _ClassVar[int]
    EVENTS_FIELD_NUMBER: _ClassVar[int]
    feed: FeedRef
    events: _containers.RepeatedCompositeFieldContainer[Event]
    def __init__(self, feed: _Optional[_Union[FeedRef, _Mapping]] = ..., events: _Optional[_Iterable[_Union[Event, _Mapping]]] = ...) -> None: ...

class Accepted(_message.Message):
    __slots__ = ("message_id", "receive_time_ns", "partition", "offset", "duplicate")
    MESSAGE_ID_FIELD_NUMBER: _ClassVar[int]
    RECEIVE_TIME_NS_FIELD_NUMBER: _ClassVar[int]
    PARTITION_FIELD_NUMBER: _ClassVar[int]
    OFFSET_FIELD_NUMBER: _ClassVar[int]
    DUPLICATE_FIELD_NUMBER: _ClassVar[int]
    message_id: str
    receive_time_ns: int
    partition: int
    offset: int
    duplicate: bool
    def __init__(self, message_id: _Optional[str] = ..., receive_time_ns: _Optional[int] = ..., partition: _Optional[int] = ..., offset: _Optional[int] = ..., duplicate: bool = ...) -> None: ...

class Rejection(_message.Message):
    __slots__ = ("message_id", "reason", "detail")
    MESSAGE_ID_FIELD_NUMBER: _ClassVar[int]
    REASON_FIELD_NUMBER: _ClassVar[int]
    DETAIL_FIELD_NUMBER: _ClassVar[int]
    message_id: str
    reason: RejectionReason
    detail: str
    def __init__(self, message_id: _Optional[str] = ..., reason: _Optional[_Union[RejectionReason, str]] = ..., detail: _Optional[str] = ...) -> None: ...

class SendResponse(_message.Message):
    __slots__ = ("accepted", "rejected", "server_ns")
    ACCEPTED_FIELD_NUMBER: _ClassVar[int]
    REJECTED_FIELD_NUMBER: _ClassVar[int]
    SERVER_NS_FIELD_NUMBER: _ClassVar[int]
    accepted: _containers.RepeatedCompositeFieldContainer[Accepted]
    rejected: _containers.RepeatedCompositeFieldContainer[Rejection]
    server_ns: int
    def __init__(self, accepted: _Optional[_Iterable[_Union[Accepted, _Mapping]]] = ..., rejected: _Optional[_Iterable[_Union[Rejection, _Mapping]]] = ..., server_ns: _Optional[int] = ...) -> None: ...

class Value(_message.Message):
    __slots__ = ("bool_value", "int_value", "float_value", "string_value")
    BOOL_VALUE_FIELD_NUMBER: _ClassVar[int]
    INT_VALUE_FIELD_NUMBER: _ClassVar[int]
    FLOAT_VALUE_FIELD_NUMBER: _ClassVar[int]
    STRING_VALUE_FIELD_NUMBER: _ClassVar[int]
    bool_value: bool
    int_value: int
    float_value: float
    string_value: str
    def __init__(self, bool_value: bool = ..., int_value: _Optional[int] = ..., float_value: _Optional[float] = ..., string_value: _Optional[str] = ...) -> None: ...

class Filter(_message.Message):
    __slots__ = ("column", "op", "values")
    COLUMN_FIELD_NUMBER: _ClassVar[int]
    OP_FIELD_NUMBER: _ClassVar[int]
    VALUES_FIELD_NUMBER: _ClassVar[int]
    column: str
    op: FilterOp
    values: _containers.RepeatedCompositeFieldContainer[Value]
    def __init__(self, column: _Optional[str] = ..., op: _Optional[_Union[FilterOp, str]] = ..., values: _Optional[_Iterable[_Union[Value, _Mapping]]] = ...) -> None: ...

class ArrowBatch(_message.Message):
    __slots__ = ("ipc",)
    IPC_FIELD_NUMBER: _ClassVar[int]
    ipc: bytes
    def __init__(self, ipc: _Optional[bytes] = ...) -> None: ...

class LatestRequest(_message.Message):
    __slots__ = ("feed", "keys", "columns")
    FEED_FIELD_NUMBER: _ClassVar[int]
    KEYS_FIELD_NUMBER: _ClassVar[int]
    COLUMNS_FIELD_NUMBER: _ClassVar[int]
    feed: FeedRef
    keys: _containers.RepeatedScalarFieldContainer[str]
    columns: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, feed: _Optional[_Union[FeedRef, _Mapping]] = ..., keys: _Optional[_Iterable[str]] = ..., columns: _Optional[_Iterable[str]] = ...) -> None: ...

class LatestResponse(_message.Message):
    __slots__ = ("batch", "server_ns")
    BATCH_FIELD_NUMBER: _ClassVar[int]
    SERVER_NS_FIELD_NUMBER: _ClassVar[int]
    batch: ArrowBatch
    server_ns: int
    def __init__(self, batch: _Optional[_Union[ArrowBatch, _Mapping]] = ..., server_ns: _Optional[int] = ...) -> None: ...

class ReadRequest(_message.Message):
    __slots__ = ("feed", "start_event_time_ns", "end_event_time_ns", "as_of_ns", "filters", "columns", "limit", "include_payload", "at_position", "dedupe", "as_of_basis", "as_of_lag_ns", "estimate_only")
    FEED_FIELD_NUMBER: _ClassVar[int]
    START_EVENT_TIME_NS_FIELD_NUMBER: _ClassVar[int]
    END_EVENT_TIME_NS_FIELD_NUMBER: _ClassVar[int]
    AS_OF_NS_FIELD_NUMBER: _ClassVar[int]
    FILTERS_FIELD_NUMBER: _ClassVar[int]
    COLUMNS_FIELD_NUMBER: _ClassVar[int]
    LIMIT_FIELD_NUMBER: _ClassVar[int]
    INCLUDE_PAYLOAD_FIELD_NUMBER: _ClassVar[int]
    AT_POSITION_FIELD_NUMBER: _ClassVar[int]
    DEDUPE_FIELD_NUMBER: _ClassVar[int]
    AS_OF_BASIS_FIELD_NUMBER: _ClassVar[int]
    AS_OF_LAG_NS_FIELD_NUMBER: _ClassVar[int]
    ESTIMATE_ONLY_FIELD_NUMBER: _ClassVar[int]
    feed: FeedRef
    start_event_time_ns: int
    end_event_time_ns: int
    as_of_ns: int
    filters: _containers.RepeatedCompositeFieldContainer[Filter]
    columns: _containers.RepeatedScalarFieldContainer[str]
    limit: int
    include_payload: bool
    at_position: Position
    dedupe: Dedupe
    as_of_basis: AsOfBasis
    as_of_lag_ns: int
    estimate_only: bool
    def __init__(self, feed: _Optional[_Union[FeedRef, _Mapping]] = ..., start_event_time_ns: _Optional[int] = ..., end_event_time_ns: _Optional[int] = ..., as_of_ns: _Optional[int] = ..., filters: _Optional[_Iterable[_Union[Filter, _Mapping]]] = ..., columns: _Optional[_Iterable[str]] = ..., limit: _Optional[int] = ..., include_payload: bool = ..., at_position: _Optional[_Union[Position, _Mapping]] = ..., dedupe: _Optional[_Union[Dedupe, _Mapping]] = ..., as_of_basis: _Optional[_Union[AsOfBasis, str]] = ..., as_of_lag_ns: _Optional[int] = ..., estimate_only: bool = ...) -> None: ...

class ReadResponse(_message.Message):
    __slots__ = ("batch", "position", "server_ns", "estimated_rows", "estimated_bytes")
    BATCH_FIELD_NUMBER: _ClassVar[int]
    POSITION_FIELD_NUMBER: _ClassVar[int]
    SERVER_NS_FIELD_NUMBER: _ClassVar[int]
    ESTIMATED_ROWS_FIELD_NUMBER: _ClassVar[int]
    ESTIMATED_BYTES_FIELD_NUMBER: _ClassVar[int]
    batch: ArrowBatch
    position: Position
    server_ns: int
    estimated_rows: int
    estimated_bytes: int
    def __init__(self, batch: _Optional[_Union[ArrowBatch, _Mapping]] = ..., position: _Optional[_Union[Position, _Mapping]] = ..., server_ns: _Optional[int] = ..., estimated_rows: _Optional[int] = ..., estimated_bytes: _Optional[int] = ...) -> None: ...

class Position(_message.Message):
    __slots__ = ("next_offsets",)
    NEXT_OFFSETS_FIELD_NUMBER: _ClassVar[int]
    next_offsets: _containers.RepeatedScalarFieldContainer[int]
    def __init__(self, next_offsets: _Optional[_Iterable[int]] = ...) -> None: ...

class Dedupe(_message.Message):
    __slots__ = ("columns", "keep", "order")
    COLUMNS_FIELD_NUMBER: _ClassVar[int]
    KEEP_FIELD_NUMBER: _ClassVar[int]
    ORDER_FIELD_NUMBER: _ClassVar[int]
    columns: _containers.RepeatedScalarFieldContainer[str]
    keep: DedupeKeep
    order: DedupeOrder
    def __init__(self, columns: _Optional[_Iterable[str]] = ..., keep: _Optional[_Union[DedupeKeep, str]] = ..., order: _Optional[_Union[DedupeOrder, str]] = ...) -> None: ...

class SubscribeRequest(_message.Message):
    __slots__ = ("feed", "from_beginning", "from_event_time_ns", "from_now", "from_last", "from_position", "speed", "filters", "columns", "delivery", "include_payload", "dedupe")
    FEED_FIELD_NUMBER: _ClassVar[int]
    FROM_BEGINNING_FIELD_NUMBER: _ClassVar[int]
    FROM_EVENT_TIME_NS_FIELD_NUMBER: _ClassVar[int]
    FROM_NOW_FIELD_NUMBER: _ClassVar[int]
    FROM_LAST_FIELD_NUMBER: _ClassVar[int]
    FROM_POSITION_FIELD_NUMBER: _ClassVar[int]
    SPEED_FIELD_NUMBER: _ClassVar[int]
    FILTERS_FIELD_NUMBER: _ClassVar[int]
    COLUMNS_FIELD_NUMBER: _ClassVar[int]
    DELIVERY_FIELD_NUMBER: _ClassVar[int]
    INCLUDE_PAYLOAD_FIELD_NUMBER: _ClassVar[int]
    DEDUPE_FIELD_NUMBER: _ClassVar[int]
    feed: FeedRef
    from_beginning: bool
    from_event_time_ns: int
    from_now: bool
    from_last: int
    from_position: Position
    speed: float
    filters: _containers.RepeatedCompositeFieldContainer[Filter]
    columns: _containers.RepeatedScalarFieldContainer[str]
    delivery: Delivery
    include_payload: bool
    dedupe: Dedupe
    def __init__(self, feed: _Optional[_Union[FeedRef, _Mapping]] = ..., from_beginning: bool = ..., from_event_time_ns: _Optional[int] = ..., from_now: bool = ..., from_last: _Optional[int] = ..., from_position: _Optional[_Union[Position, _Mapping]] = ..., speed: _Optional[float] = ..., filters: _Optional[_Iterable[_Union[Filter, _Mapping]]] = ..., columns: _Optional[_Iterable[str]] = ..., delivery: _Optional[_Union[Delivery, str]] = ..., include_payload: bool = ..., dedupe: _Optional[_Union[Dedupe, _Mapping]] = ...) -> None: ...

class CaughtUp(_message.Message):
    __slots__ = ("history_events", "position")
    HISTORY_EVENTS_FIELD_NUMBER: _ClassVar[int]
    POSITION_FIELD_NUMBER: _ClassVar[int]
    history_events: int
    position: Position
    def __init__(self, history_events: _Optional[int] = ..., position: _Optional[_Union[Position, _Mapping]] = ...) -> None: ...

class Heartbeat(_message.Message):
    __slots__ = ("server_time_ns",)
    SERVER_TIME_NS_FIELD_NUMBER: _ClassVar[int]
    server_time_ns: int
    def __init__(self, server_time_ns: _Optional[int] = ...) -> None: ...

class SubscribeResponse(_message.Message):
    __slots__ = ("batch", "caught_up", "heartbeat")
    BATCH_FIELD_NUMBER: _ClassVar[int]
    CAUGHT_UP_FIELD_NUMBER: _ClassVar[int]
    HEARTBEAT_FIELD_NUMBER: _ClassVar[int]
    batch: ArrowBatch
    caught_up: CaughtUp
    heartbeat: Heartbeat
    def __init__(self, batch: _Optional[_Union[ArrowBatch, _Mapping]] = ..., caught_up: _Optional[_Union[CaughtUp, _Mapping]] = ..., heartbeat: _Optional[_Union[Heartbeat, _Mapping]] = ...) -> None: ...

class ConnectorTemplate(_message.Message):
    __slots__ = ("name", "version", "description", "options_example", "feeds", "poll_interval_ms", "credentials")
    NAME_FIELD_NUMBER: _ClassVar[int]
    VERSION_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    OPTIONS_EXAMPLE_FIELD_NUMBER: _ClassVar[int]
    FEEDS_FIELD_NUMBER: _ClassVar[int]
    POLL_INTERVAL_MS_FIELD_NUMBER: _ClassVar[int]
    CREDENTIALS_FIELD_NUMBER: _ClassVar[int]
    name: str
    version: int
    description: str
    options_example: str
    feeds: _containers.RepeatedCompositeFieldContainer[ConnectorFeed]
    poll_interval_ms: int
    credentials: _containers.RepeatedCompositeFieldContainer[ConnectorCredential]
    def __init__(self, name: _Optional[str] = ..., version: _Optional[int] = ..., description: _Optional[str] = ..., options_example: _Optional[str] = ..., feeds: _Optional[_Iterable[_Union[ConnectorFeed, _Mapping]]] = ..., poll_interval_ms: _Optional[int] = ..., credentials: _Optional[_Iterable[_Union[ConnectorCredential, _Mapping]]] = ...) -> None: ...

class ConnectorCredential(_message.Message):
    __slots__ = ("name", "description")
    NAME_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    name: str
    description: str
    def __init__(self, name: _Optional[str] = ..., description: _Optional[str] = ...) -> None: ...

class ConnectorFeed(_message.Message):
    __slots__ = ("name", "key_field", "time_field", "publication_time_field", "description", "licence", "attribution", "source_url")
    NAME_FIELD_NUMBER: _ClassVar[int]
    KEY_FIELD_FIELD_NUMBER: _ClassVar[int]
    TIME_FIELD_FIELD_NUMBER: _ClassVar[int]
    PUBLICATION_TIME_FIELD_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    LICENCE_FIELD_NUMBER: _ClassVar[int]
    ATTRIBUTION_FIELD_NUMBER: _ClassVar[int]
    SOURCE_URL_FIELD_NUMBER: _ClassVar[int]
    name: str
    key_field: str
    time_field: str
    publication_time_field: str
    description: str
    licence: str
    attribution: str
    source_url: str
    def __init__(self, name: _Optional[str] = ..., key_field: _Optional[str] = ..., time_field: _Optional[str] = ..., publication_time_field: _Optional[str] = ..., description: _Optional[str] = ..., licence: _Optional[str] = ..., attribution: _Optional[str] = ..., source_url: _Optional[str] = ...) -> None: ...

class ListConnectorTemplatesRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class ListConnectorTemplatesResponse(_message.Message):
    __slots__ = ("templates",)
    TEMPLATES_FIELD_NUMBER: _ClassVar[int]
    templates: _containers.RepeatedCompositeFieldContainer[ConnectorTemplate]
    def __init__(self, templates: _Optional[_Iterable[_Union[ConnectorTemplate, _Mapping]]] = ...) -> None: ...

class Connection(_message.Message):
    __slots__ = ("id", "name", "template", "namespace", "options_json", "service_account", "paused", "status", "status_detail", "cursor_json", "worker", "last_heartbeat_at_ns", "last_event_at_ns", "events_sent", "created_at_ns", "feeds", "credential_fields", "credentials_set_at_ns")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    TEMPLATE_FIELD_NUMBER: _ClassVar[int]
    NAMESPACE_FIELD_NUMBER: _ClassVar[int]
    OPTIONS_JSON_FIELD_NUMBER: _ClassVar[int]
    SERVICE_ACCOUNT_FIELD_NUMBER: _ClassVar[int]
    PAUSED_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    STATUS_DETAIL_FIELD_NUMBER: _ClassVar[int]
    CURSOR_JSON_FIELD_NUMBER: _ClassVar[int]
    WORKER_FIELD_NUMBER: _ClassVar[int]
    LAST_HEARTBEAT_AT_NS_FIELD_NUMBER: _ClassVar[int]
    LAST_EVENT_AT_NS_FIELD_NUMBER: _ClassVar[int]
    EVENTS_SENT_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_NS_FIELD_NUMBER: _ClassVar[int]
    FEEDS_FIELD_NUMBER: _ClassVar[int]
    CREDENTIAL_FIELDS_FIELD_NUMBER: _ClassVar[int]
    CREDENTIALS_SET_AT_NS_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    template: str
    namespace: str
    options_json: str
    service_account: str
    paused: bool
    status: str
    status_detail: str
    cursor_json: str
    worker: str
    last_heartbeat_at_ns: int
    last_event_at_ns: int
    events_sent: int
    created_at_ns: int
    feeds: _containers.RepeatedScalarFieldContainer[str]
    credential_fields: _containers.RepeatedScalarFieldContainer[str]
    credentials_set_at_ns: int
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., template: _Optional[str] = ..., namespace: _Optional[str] = ..., options_json: _Optional[str] = ..., service_account: _Optional[str] = ..., paused: bool = ..., status: _Optional[str] = ..., status_detail: _Optional[str] = ..., cursor_json: _Optional[str] = ..., worker: _Optional[str] = ..., last_heartbeat_at_ns: _Optional[int] = ..., last_event_at_ns: _Optional[int] = ..., events_sent: _Optional[int] = ..., created_at_ns: _Optional[int] = ..., feeds: _Optional[_Iterable[str]] = ..., credential_fields: _Optional[_Iterable[str]] = ..., credentials_set_at_ns: _Optional[int] = ...) -> None: ...

class CreateConnectionRequest(_message.Message):
    __slots__ = ("name", "template", "namespace", "options_json", "paused", "credentials_json")
    NAME_FIELD_NUMBER: _ClassVar[int]
    TEMPLATE_FIELD_NUMBER: _ClassVar[int]
    NAMESPACE_FIELD_NUMBER: _ClassVar[int]
    OPTIONS_JSON_FIELD_NUMBER: _ClassVar[int]
    PAUSED_FIELD_NUMBER: _ClassVar[int]
    CREDENTIALS_JSON_FIELD_NUMBER: _ClassVar[int]
    name: str
    template: str
    namespace: str
    options_json: str
    paused: bool
    credentials_json: str
    def __init__(self, name: _Optional[str] = ..., template: _Optional[str] = ..., namespace: _Optional[str] = ..., options_json: _Optional[str] = ..., paused: bool = ..., credentials_json: _Optional[str] = ...) -> None: ...

class SetConnectionCredentialsRequest(_message.Message):
    __slots__ = ("name", "credentials_json")
    NAME_FIELD_NUMBER: _ClassVar[int]
    CREDENTIALS_JSON_FIELD_NUMBER: _ClassVar[int]
    name: str
    credentials_json: str
    def __init__(self, name: _Optional[str] = ..., credentials_json: _Optional[str] = ...) -> None: ...

class ListConnectionsRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class ListConnectionsResponse(_message.Message):
    __slots__ = ("connections",)
    CONNECTIONS_FIELD_NUMBER: _ClassVar[int]
    connections: _containers.RepeatedCompositeFieldContainer[Connection]
    def __init__(self, connections: _Optional[_Iterable[_Union[Connection, _Mapping]]] = ...) -> None: ...

class GetConnectionRequest(_message.Message):
    __slots__ = ("name",)
    NAME_FIELD_NUMBER: _ClassVar[int]
    name: str
    def __init__(self, name: _Optional[str] = ...) -> None: ...

class PauseConnectionRequest(_message.Message):
    __slots__ = ("name",)
    NAME_FIELD_NUMBER: _ClassVar[int]
    name: str
    def __init__(self, name: _Optional[str] = ...) -> None: ...

class ResumeConnectionRequest(_message.Message):
    __slots__ = ("name",)
    NAME_FIELD_NUMBER: _ClassVar[int]
    name: str
    def __init__(self, name: _Optional[str] = ...) -> None: ...

class DeleteConnectionRequest(_message.Message):
    __slots__ = ("name",)
    NAME_FIELD_NUMBER: _ClassVar[int]
    name: str
    def __init__(self, name: _Optional[str] = ...) -> None: ...

class DeleteConnectionResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class LookupRequest(_message.Message):
    __slots__ = ("feed", "probes", "probe_batch", "as_of_basis", "columns", "filters", "include_payload")
    FEED_FIELD_NUMBER: _ClassVar[int]
    PROBES_FIELD_NUMBER: _ClassVar[int]
    PROBE_BATCH_FIELD_NUMBER: _ClassVar[int]
    AS_OF_BASIS_FIELD_NUMBER: _ClassVar[int]
    COLUMNS_FIELD_NUMBER: _ClassVar[int]
    FILTERS_FIELD_NUMBER: _ClassVar[int]
    INCLUDE_PAYLOAD_FIELD_NUMBER: _ClassVar[int]
    feed: FeedRef
    probes: _containers.RepeatedCompositeFieldContainer[LookupProbe]
    probe_batch: ArrowBatch
    as_of_basis: AsOfBasis
    columns: _containers.RepeatedScalarFieldContainer[str]
    filters: _containers.RepeatedCompositeFieldContainer[Filter]
    include_payload: bool
    def __init__(self, feed: _Optional[_Union[FeedRef, _Mapping]] = ..., probes: _Optional[_Iterable[_Union[LookupProbe, _Mapping]]] = ..., probe_batch: _Optional[_Union[ArrowBatch, _Mapping]] = ..., as_of_basis: _Optional[_Union[AsOfBasis, str]] = ..., columns: _Optional[_Iterable[str]] = ..., filters: _Optional[_Iterable[_Union[Filter, _Mapping]]] = ..., include_payload: bool = ...) -> None: ...

class LookupProbe(_message.Message):
    __slots__ = ("key", "at_ns")
    KEY_FIELD_NUMBER: _ClassVar[int]
    AT_NS_FIELD_NUMBER: _ClassVar[int]
    key: str
    at_ns: int
    def __init__(self, key: _Optional[str] = ..., at_ns: _Optional[int] = ...) -> None: ...

class LookupResponse(_message.Message):
    __slots__ = ("batch", "server_ns")
    BATCH_FIELD_NUMBER: _ClassVar[int]
    SERVER_NS_FIELD_NUMBER: _ClassVar[int]
    batch: ArrowBatch
    server_ns: int
    def __init__(self, batch: _Optional[_Union[ArrowBatch, _Mapping]] = ..., server_ns: _Optional[int] = ...) -> None: ...

class GetUsageRequest(_message.Message):
    __slots__ = ("start_ns", "end_ns", "bucket", "by_feed")
    START_NS_FIELD_NUMBER: _ClassVar[int]
    END_NS_FIELD_NUMBER: _ClassVar[int]
    BUCKET_FIELD_NUMBER: _ClassVar[int]
    BY_FEED_FIELD_NUMBER: _ClassVar[int]
    start_ns: int
    end_ns: int
    bucket: UsageBucket
    by_feed: bool
    def __init__(self, start_ns: _Optional[int] = ..., end_ns: _Optional[int] = ..., bucket: _Optional[_Union[UsageBucket, str]] = ..., by_feed: bool = ...) -> None: ...

class UsageRow(_message.Message):
    __slots__ = ("start_ns", "feed", "feed_id", "metric", "value")
    START_NS_FIELD_NUMBER: _ClassVar[int]
    FEED_FIELD_NUMBER: _ClassVar[int]
    FEED_ID_FIELD_NUMBER: _ClassVar[int]
    METRIC_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    start_ns: int
    feed: FeedRef
    feed_id: str
    metric: str
    value: float
    def __init__(self, start_ns: _Optional[int] = ..., feed: _Optional[_Union[FeedRef, _Mapping]] = ..., feed_id: _Optional[str] = ..., metric: _Optional[str] = ..., value: _Optional[float] = ...) -> None: ...

class GetUsageResponse(_message.Message):
    __slots__ = ("rows",)
    ROWS_FIELD_NUMBER: _ClassVar[int]
    rows: _containers.RepeatedCompositeFieldContainer[UsageRow]
    def __init__(self, rows: _Optional[_Iterable[_Union[UsageRow, _Mapping]]] = ...) -> None: ...

class TransformerRef(_message.Message):
    __slots__ = ("namespace", "name")
    NAMESPACE_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    namespace: str
    name: str
    def __init__(self, namespace: _Optional[str] = ..., name: _Optional[str] = ...) -> None: ...

class TransformerInput(_message.Message):
    __slots__ = ("name", "feed", "pinned", "window", "horizon_ns")
    NAME_FIELD_NUMBER: _ClassVar[int]
    FEED_FIELD_NUMBER: _ClassVar[int]
    PINNED_FIELD_NUMBER: _ClassVar[int]
    WINDOW_FIELD_NUMBER: _ClassVar[int]
    HORIZON_NS_FIELD_NUMBER: _ClassVar[int]
    name: str
    feed: str
    pinned: FeedRef
    window: TransformerWindow
    horizon_ns: int
    def __init__(self, name: _Optional[str] = ..., feed: _Optional[str] = ..., pinned: _Optional[_Union[FeedRef, _Mapping]] = ..., window: _Optional[_Union[TransformerWindow, _Mapping]] = ..., horizon_ns: _Optional[int] = ...) -> None: ...

class SyncFeedRequest(_message.Message):
    __slots__ = ("feed",)
    FEED_FIELD_NUMBER: _ClassVar[int]
    feed: FeedRef
    def __init__(self, feed: _Optional[_Union[FeedRef, _Mapping]] = ...) -> None: ...

class SyncFeedResponse(_message.Message):
    __slots__ = ("server_ns", "next_offsets", "last_accepted")
    SERVER_NS_FIELD_NUMBER: _ClassVar[int]
    NEXT_OFFSETS_FIELD_NUMBER: _ClassVar[int]
    LAST_ACCEPTED_FIELD_NUMBER: _ClassVar[int]
    server_ns: int
    next_offsets: _containers.RepeatedScalarFieldContainer[int]
    last_accepted: _containers.RepeatedScalarFieldContainer[int]
    def __init__(self, server_ns: _Optional[int] = ..., next_offsets: _Optional[_Iterable[int]] = ..., last_accepted: _Optional[_Iterable[int]] = ...) -> None: ...

class TransformerWindow(_message.Message):
    __slots__ = ("count", "duration_ns", "tumbling", "all_keys")
    COUNT_FIELD_NUMBER: _ClassVar[int]
    DURATION_NS_FIELD_NUMBER: _ClassVar[int]
    TUMBLING_FIELD_NUMBER: _ClassVar[int]
    ALL_KEYS_FIELD_NUMBER: _ClassVar[int]
    count: int
    duration_ns: int
    tumbling: bool
    all_keys: bool
    def __init__(self, count: _Optional[int] = ..., duration_ns: _Optional[int] = ..., tumbling: bool = ..., all_keys: bool = ...) -> None: ...

class TransformerOutput(_message.Message):
    __slots__ = ("feed", "key_field", "time_field", "publication_time_field", "description", "pinned")
    FEED_FIELD_NUMBER: _ClassVar[int]
    KEY_FIELD_FIELD_NUMBER: _ClassVar[int]
    TIME_FIELD_FIELD_NUMBER: _ClassVar[int]
    PUBLICATION_TIME_FIELD_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    PINNED_FIELD_NUMBER: _ClassVar[int]
    feed: str
    key_field: str
    time_field: str
    publication_time_field: str
    description: str
    pinned: FeedRef
    def __init__(self, feed: _Optional[str] = ..., key_field: _Optional[str] = ..., time_field: _Optional[str] = ..., publication_time_field: _Optional[str] = ..., description: _Optional[str] = ..., pinned: _Optional[_Union[FeedRef, _Mapping]] = ...) -> None: ...

class DeployTransformerRequest(_message.Message):
    __slots__ = ("transformer", "triggers", "dependencies", "output", "code", "entrypoint", "paused", "on_restart", "as_of_basis", "bundle_sha256", "python_version", "validate_only", "max_error_rate", "sample_events", "allow_unverified", "stateful")
    TRANSFORMER_FIELD_NUMBER: _ClassVar[int]
    TRIGGERS_FIELD_NUMBER: _ClassVar[int]
    DEPENDENCIES_FIELD_NUMBER: _ClassVar[int]
    OUTPUT_FIELD_NUMBER: _ClassVar[int]
    CODE_FIELD_NUMBER: _ClassVar[int]
    ENTRYPOINT_FIELD_NUMBER: _ClassVar[int]
    PAUSED_FIELD_NUMBER: _ClassVar[int]
    ON_RESTART_FIELD_NUMBER: _ClassVar[int]
    AS_OF_BASIS_FIELD_NUMBER: _ClassVar[int]
    BUNDLE_SHA256_FIELD_NUMBER: _ClassVar[int]
    PYTHON_VERSION_FIELD_NUMBER: _ClassVar[int]
    VALIDATE_ONLY_FIELD_NUMBER: _ClassVar[int]
    MAX_ERROR_RATE_FIELD_NUMBER: _ClassVar[int]
    SAMPLE_EVENTS_FIELD_NUMBER: _ClassVar[int]
    ALLOW_UNVERIFIED_FIELD_NUMBER: _ClassVar[int]
    STATEFUL_FIELD_NUMBER: _ClassVar[int]
    transformer: TransformerRef
    triggers: _containers.RepeatedCompositeFieldContainer[TransformerInput]
    dependencies: _containers.RepeatedCompositeFieldContainer[TransformerInput]
    output: TransformerOutput
    code: str
    entrypoint: str
    paused: bool
    on_restart: str
    as_of_basis: AsOfBasis
    bundle_sha256: str
    python_version: str
    validate_only: bool
    max_error_rate: float
    sample_events: int
    allow_unverified: bool
    stateful: bool
    def __init__(self, transformer: _Optional[_Union[TransformerRef, _Mapping]] = ..., triggers: _Optional[_Iterable[_Union[TransformerInput, _Mapping]]] = ..., dependencies: _Optional[_Iterable[_Union[TransformerInput, _Mapping]]] = ..., output: _Optional[_Union[TransformerOutput, _Mapping]] = ..., code: _Optional[str] = ..., entrypoint: _Optional[str] = ..., paused: bool = ..., on_restart: _Optional[str] = ..., as_of_basis: _Optional[_Union[AsOfBasis, str]] = ..., bundle_sha256: _Optional[str] = ..., python_version: _Optional[str] = ..., validate_only: bool = ..., max_error_rate: _Optional[float] = ..., sample_events: _Optional[int] = ..., allow_unverified: bool = ..., stateful: bool = ...) -> None: ...

class UploadBundleRequest(_message.Message):
    __slots__ = ("chunk",)
    CHUNK_FIELD_NUMBER: _ClassVar[int]
    chunk: bytes
    def __init__(self, chunk: _Optional[bytes] = ...) -> None: ...

class UploadBundleResponse(_message.Message):
    __slots__ = ("sha256", "size_bytes")
    SHA256_FIELD_NUMBER: _ClassVar[int]
    SIZE_BYTES_FIELD_NUMBER: _ClassVar[int]
    sha256: str
    size_bytes: int
    def __init__(self, sha256: _Optional[str] = ..., size_bytes: _Optional[int] = ...) -> None: ...

class TransformerBuild(_message.Message):
    __slots__ = ("id", "namespace", "transformer", "status", "status_detail", "bundle_sha256", "python_version", "validate_only", "lockfile", "environment_bytes", "manifest_json", "report_json", "log", "created_at_ns", "started_at_ns", "finished_at_ns", "transformer_version", "runtime_json")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAMESPACE_FIELD_NUMBER: _ClassVar[int]
    TRANSFORMER_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    STATUS_DETAIL_FIELD_NUMBER: _ClassVar[int]
    BUNDLE_SHA256_FIELD_NUMBER: _ClassVar[int]
    PYTHON_VERSION_FIELD_NUMBER: _ClassVar[int]
    VALIDATE_ONLY_FIELD_NUMBER: _ClassVar[int]
    LOCKFILE_FIELD_NUMBER: _ClassVar[int]
    ENVIRONMENT_BYTES_FIELD_NUMBER: _ClassVar[int]
    MANIFEST_JSON_FIELD_NUMBER: _ClassVar[int]
    REPORT_JSON_FIELD_NUMBER: _ClassVar[int]
    LOG_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_NS_FIELD_NUMBER: _ClassVar[int]
    STARTED_AT_NS_FIELD_NUMBER: _ClassVar[int]
    FINISHED_AT_NS_FIELD_NUMBER: _ClassVar[int]
    TRANSFORMER_VERSION_FIELD_NUMBER: _ClassVar[int]
    RUNTIME_JSON_FIELD_NUMBER: _ClassVar[int]
    id: str
    namespace: str
    transformer: str
    status: str
    status_detail: str
    bundle_sha256: str
    python_version: str
    validate_only: bool
    lockfile: str
    environment_bytes: int
    manifest_json: str
    report_json: str
    log: str
    created_at_ns: int
    started_at_ns: int
    finished_at_ns: int
    transformer_version: int
    runtime_json: str
    def __init__(self, id: _Optional[str] = ..., namespace: _Optional[str] = ..., transformer: _Optional[str] = ..., status: _Optional[str] = ..., status_detail: _Optional[str] = ..., bundle_sha256: _Optional[str] = ..., python_version: _Optional[str] = ..., validate_only: bool = ..., lockfile: _Optional[str] = ..., environment_bytes: _Optional[int] = ..., manifest_json: _Optional[str] = ..., report_json: _Optional[str] = ..., log: _Optional[str] = ..., created_at_ns: _Optional[int] = ..., started_at_ns: _Optional[int] = ..., finished_at_ns: _Optional[int] = ..., transformer_version: _Optional[int] = ..., runtime_json: _Optional[str] = ...) -> None: ...

class GetTransformerBuildRequest(_message.Message):
    __slots__ = ("id",)
    ID_FIELD_NUMBER: _ClassVar[int]
    id: str
    def __init__(self, id: _Optional[str] = ...) -> None: ...

class ListTransformerBuildsRequest(_message.Message):
    __slots__ = ("transformer",)
    TRANSFORMER_FIELD_NUMBER: _ClassVar[int]
    transformer: TransformerRef
    def __init__(self, transformer: _Optional[_Union[TransformerRef, _Mapping]] = ...) -> None: ...

class ListTransformerBuildsResponse(_message.Message):
    __slots__ = ("builds",)
    BUILDS_FIELD_NUMBER: _ClassVar[int]
    builds: _containers.RepeatedCompositeFieldContainer[TransformerBuild]
    def __init__(self, builds: _Optional[_Iterable[_Union[TransformerBuild, _Mapping]]] = ...) -> None: ...

class CancelTransformerBuildRequest(_message.Message):
    __slots__ = ("id",)
    ID_FIELD_NUMBER: _ClassVar[int]
    id: str
    def __init__(self, id: _Optional[str] = ...) -> None: ...

class PackageIndex(_message.Message):
    __slots__ = ("name", "url", "credential_fields", "replaces_pypi", "created_at_ns", "updated_at_ns")
    NAME_FIELD_NUMBER: _ClassVar[int]
    URL_FIELD_NUMBER: _ClassVar[int]
    CREDENTIAL_FIELDS_FIELD_NUMBER: _ClassVar[int]
    REPLACES_PYPI_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_NS_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_NS_FIELD_NUMBER: _ClassVar[int]
    name: str
    url: str
    credential_fields: _containers.RepeatedScalarFieldContainer[str]
    replaces_pypi: bool
    created_at_ns: int
    updated_at_ns: int
    def __init__(self, name: _Optional[str] = ..., url: _Optional[str] = ..., credential_fields: _Optional[_Iterable[str]] = ..., replaces_pypi: bool = ..., created_at_ns: _Optional[int] = ..., updated_at_ns: _Optional[int] = ...) -> None: ...

class CreatePackageIndexRequest(_message.Message):
    __slots__ = ("name", "url", "replaces_pypi", "credentials_json")
    NAME_FIELD_NUMBER: _ClassVar[int]
    URL_FIELD_NUMBER: _ClassVar[int]
    REPLACES_PYPI_FIELD_NUMBER: _ClassVar[int]
    CREDENTIALS_JSON_FIELD_NUMBER: _ClassVar[int]
    name: str
    url: str
    replaces_pypi: bool
    credentials_json: str
    def __init__(self, name: _Optional[str] = ..., url: _Optional[str] = ..., replaces_pypi: bool = ..., credentials_json: _Optional[str] = ...) -> None: ...

class ListPackageIndexesRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class ListPackageIndexesResponse(_message.Message):
    __slots__ = ("indexes",)
    INDEXES_FIELD_NUMBER: _ClassVar[int]
    indexes: _containers.RepeatedCompositeFieldContainer[PackageIndex]
    def __init__(self, indexes: _Optional[_Iterable[_Union[PackageIndex, _Mapping]]] = ...) -> None: ...

class SetPackageIndexCredentialsRequest(_message.Message):
    __slots__ = ("name", "credentials_json")
    NAME_FIELD_NUMBER: _ClassVar[int]
    CREDENTIALS_JSON_FIELD_NUMBER: _ClassVar[int]
    name: str
    credentials_json: str
    def __init__(self, name: _Optional[str] = ..., credentials_json: _Optional[str] = ...) -> None: ...

class DeletePackageIndexRequest(_message.Message):
    __slots__ = ("name",)
    NAME_FIELD_NUMBER: _ClassVar[int]
    name: str
    def __init__(self, name: _Optional[str] = ...) -> None: ...

class DeletePackageIndexResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class TransformerStats(_message.Message):
    __slots__ = ("latency_p50_ms", "latency_p95_ms", "latency_max_ms", "delivery_p50_ms", "python_ms_per_event", "dependency_ms_per_call", "send_ms_per_batch", "events_per_second", "cpu_seconds", "memory_bytes", "batches", "dependency_calls", "last_error", "lag_ms", "state_versions", "state_bytes", "syncs", "sync_ms_mean", "worker_memory_bytes", "run_seconds", "code_state_bytes", "backfill_remaining")
    LATENCY_P50_MS_FIELD_NUMBER: _ClassVar[int]
    LATENCY_P95_MS_FIELD_NUMBER: _ClassVar[int]
    LATENCY_MAX_MS_FIELD_NUMBER: _ClassVar[int]
    DELIVERY_P50_MS_FIELD_NUMBER: _ClassVar[int]
    PYTHON_MS_PER_EVENT_FIELD_NUMBER: _ClassVar[int]
    DEPENDENCY_MS_PER_CALL_FIELD_NUMBER: _ClassVar[int]
    SEND_MS_PER_BATCH_FIELD_NUMBER: _ClassVar[int]
    EVENTS_PER_SECOND_FIELD_NUMBER: _ClassVar[int]
    CPU_SECONDS_FIELD_NUMBER: _ClassVar[int]
    MEMORY_BYTES_FIELD_NUMBER: _ClassVar[int]
    BATCHES_FIELD_NUMBER: _ClassVar[int]
    DEPENDENCY_CALLS_FIELD_NUMBER: _ClassVar[int]
    LAST_ERROR_FIELD_NUMBER: _ClassVar[int]
    LAG_MS_FIELD_NUMBER: _ClassVar[int]
    STATE_VERSIONS_FIELD_NUMBER: _ClassVar[int]
    STATE_BYTES_FIELD_NUMBER: _ClassVar[int]
    SYNCS_FIELD_NUMBER: _ClassVar[int]
    SYNC_MS_MEAN_FIELD_NUMBER: _ClassVar[int]
    WORKER_MEMORY_BYTES_FIELD_NUMBER: _ClassVar[int]
    RUN_SECONDS_FIELD_NUMBER: _ClassVar[int]
    CODE_STATE_BYTES_FIELD_NUMBER: _ClassVar[int]
    BACKFILL_REMAINING_FIELD_NUMBER: _ClassVar[int]
    latency_p50_ms: float
    latency_p95_ms: float
    latency_max_ms: float
    delivery_p50_ms: float
    python_ms_per_event: float
    dependency_ms_per_call: float
    send_ms_per_batch: float
    events_per_second: float
    cpu_seconds: float
    memory_bytes: int
    batches: int
    dependency_calls: int
    last_error: str
    lag_ms: int
    state_versions: int
    state_bytes: int
    syncs: int
    sync_ms_mean: float
    worker_memory_bytes: int
    run_seconds: float
    code_state_bytes: int
    backfill_remaining: int
    def __init__(self, latency_p50_ms: _Optional[float] = ..., latency_p95_ms: _Optional[float] = ..., latency_max_ms: _Optional[float] = ..., delivery_p50_ms: _Optional[float] = ..., python_ms_per_event: _Optional[float] = ..., dependency_ms_per_call: _Optional[float] = ..., send_ms_per_batch: _Optional[float] = ..., events_per_second: _Optional[float] = ..., cpu_seconds: _Optional[float] = ..., memory_bytes: _Optional[int] = ..., batches: _Optional[int] = ..., dependency_calls: _Optional[int] = ..., last_error: _Optional[str] = ..., lag_ms: _Optional[int] = ..., state_versions: _Optional[int] = ..., state_bytes: _Optional[int] = ..., syncs: _Optional[int] = ..., sync_ms_mean: _Optional[float] = ..., worker_memory_bytes: _Optional[int] = ..., run_seconds: _Optional[float] = ..., code_state_bytes: _Optional[int] = ..., backfill_remaining: _Optional[int] = ...) -> None: ...

class Transformer(_message.Message):
    __slots__ = ("id", "namespace", "name", "version", "triggers", "dependencies", "output", "entrypoint", "code_sha256", "paused", "status", "status_detail", "worker", "last_heartbeat_at_ns", "last_event_at_ns", "events_in", "events_out", "errors", "stats", "created_at_ns", "updated_at_ns", "service_account", "code", "on_restart", "as_of_basis", "python_version", "bundle_sha256", "manifest_json", "build", "stateful")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAMESPACE_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    VERSION_FIELD_NUMBER: _ClassVar[int]
    TRIGGERS_FIELD_NUMBER: _ClassVar[int]
    DEPENDENCIES_FIELD_NUMBER: _ClassVar[int]
    OUTPUT_FIELD_NUMBER: _ClassVar[int]
    ENTRYPOINT_FIELD_NUMBER: _ClassVar[int]
    CODE_SHA256_FIELD_NUMBER: _ClassVar[int]
    PAUSED_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    STATUS_DETAIL_FIELD_NUMBER: _ClassVar[int]
    WORKER_FIELD_NUMBER: _ClassVar[int]
    LAST_HEARTBEAT_AT_NS_FIELD_NUMBER: _ClassVar[int]
    LAST_EVENT_AT_NS_FIELD_NUMBER: _ClassVar[int]
    EVENTS_IN_FIELD_NUMBER: _ClassVar[int]
    EVENTS_OUT_FIELD_NUMBER: _ClassVar[int]
    ERRORS_FIELD_NUMBER: _ClassVar[int]
    STATS_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_NS_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_NS_FIELD_NUMBER: _ClassVar[int]
    SERVICE_ACCOUNT_FIELD_NUMBER: _ClassVar[int]
    CODE_FIELD_NUMBER: _ClassVar[int]
    ON_RESTART_FIELD_NUMBER: _ClassVar[int]
    AS_OF_BASIS_FIELD_NUMBER: _ClassVar[int]
    PYTHON_VERSION_FIELD_NUMBER: _ClassVar[int]
    BUNDLE_SHA256_FIELD_NUMBER: _ClassVar[int]
    MANIFEST_JSON_FIELD_NUMBER: _ClassVar[int]
    BUILD_FIELD_NUMBER: _ClassVar[int]
    STATEFUL_FIELD_NUMBER: _ClassVar[int]
    id: str
    namespace: str
    name: str
    version: int
    triggers: _containers.RepeatedCompositeFieldContainer[TransformerInput]
    dependencies: _containers.RepeatedCompositeFieldContainer[TransformerInput]
    output: TransformerOutput
    entrypoint: str
    code_sha256: str
    paused: bool
    status: str
    status_detail: str
    worker: str
    last_heartbeat_at_ns: int
    last_event_at_ns: int
    events_in: int
    events_out: int
    errors: int
    stats: TransformerStats
    created_at_ns: int
    updated_at_ns: int
    service_account: str
    code: str
    on_restart: str
    as_of_basis: AsOfBasis
    python_version: str
    bundle_sha256: str
    manifest_json: str
    build: TransformerBuild
    stateful: bool
    def __init__(self, id: _Optional[str] = ..., namespace: _Optional[str] = ..., name: _Optional[str] = ..., version: _Optional[int] = ..., triggers: _Optional[_Iterable[_Union[TransformerInput, _Mapping]]] = ..., dependencies: _Optional[_Iterable[_Union[TransformerInput, _Mapping]]] = ..., output: _Optional[_Union[TransformerOutput, _Mapping]] = ..., entrypoint: _Optional[str] = ..., code_sha256: _Optional[str] = ..., paused: bool = ..., status: _Optional[str] = ..., status_detail: _Optional[str] = ..., worker: _Optional[str] = ..., last_heartbeat_at_ns: _Optional[int] = ..., last_event_at_ns: _Optional[int] = ..., events_in: _Optional[int] = ..., events_out: _Optional[int] = ..., errors: _Optional[int] = ..., stats: _Optional[_Union[TransformerStats, _Mapping]] = ..., created_at_ns: _Optional[int] = ..., updated_at_ns: _Optional[int] = ..., service_account: _Optional[str] = ..., code: _Optional[str] = ..., on_restart: _Optional[str] = ..., as_of_basis: _Optional[_Union[AsOfBasis, str]] = ..., python_version: _Optional[str] = ..., bundle_sha256: _Optional[str] = ..., manifest_json: _Optional[str] = ..., build: _Optional[_Union[TransformerBuild, _Mapping]] = ..., stateful: bool = ...) -> None: ...

class ListTransformersRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class ListTransformersResponse(_message.Message):
    __slots__ = ("transformers",)
    TRANSFORMERS_FIELD_NUMBER: _ClassVar[int]
    transformers: _containers.RepeatedCompositeFieldContainer[Transformer]
    def __init__(self, transformers: _Optional[_Iterable[_Union[Transformer, _Mapping]]] = ...) -> None: ...

class GetTransformerRequest(_message.Message):
    __slots__ = ("transformer",)
    TRANSFORMER_FIELD_NUMBER: _ClassVar[int]
    transformer: TransformerRef
    def __init__(self, transformer: _Optional[_Union[TransformerRef, _Mapping]] = ...) -> None: ...

class PauseTransformerRequest(_message.Message):
    __slots__ = ("transformer",)
    TRANSFORMER_FIELD_NUMBER: _ClassVar[int]
    transformer: TransformerRef
    def __init__(self, transformer: _Optional[_Union[TransformerRef, _Mapping]] = ...) -> None: ...

class ResumeTransformerRequest(_message.Message):
    __slots__ = ("transformer",)
    TRANSFORMER_FIELD_NUMBER: _ClassVar[int]
    transformer: TransformerRef
    def __init__(self, transformer: _Optional[_Union[TransformerRef, _Mapping]] = ...) -> None: ...

class DeleteTransformerRequest(_message.Message):
    __slots__ = ("transformer",)
    TRANSFORMER_FIELD_NUMBER: _ClassVar[int]
    transformer: TransformerRef
    def __init__(self, transformer: _Optional[_Union[TransformerRef, _Mapping]] = ...) -> None: ...

class DeleteTransformerResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class StartTransformerRunRequest(_message.Message):
    __slots__ = ("transformer", "start_ns", "end_ns", "into")
    TRANSFORMER_FIELD_NUMBER: _ClassVar[int]
    START_NS_FIELD_NUMBER: _ClassVar[int]
    END_NS_FIELD_NUMBER: _ClassVar[int]
    INTO_FIELD_NUMBER: _ClassVar[int]
    transformer: TransformerRef
    start_ns: int
    end_ns: int
    into: str
    def __init__(self, transformer: _Optional[_Union[TransformerRef, _Mapping]] = ..., start_ns: _Optional[int] = ..., end_ns: _Optional[int] = ..., into: _Optional[str] = ...) -> None: ...

class TransformerRun(_message.Message):
    __slots__ = ("id", "transformer", "version", "start_ns", "end_ns", "output", "status", "status_detail", "progress", "events_in", "events_out", "errors", "stats", "created_at_ns", "finished_at_ns")
    ID_FIELD_NUMBER: _ClassVar[int]
    TRANSFORMER_FIELD_NUMBER: _ClassVar[int]
    VERSION_FIELD_NUMBER: _ClassVar[int]
    START_NS_FIELD_NUMBER: _ClassVar[int]
    END_NS_FIELD_NUMBER: _ClassVar[int]
    OUTPUT_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    STATUS_DETAIL_FIELD_NUMBER: _ClassVar[int]
    PROGRESS_FIELD_NUMBER: _ClassVar[int]
    EVENTS_IN_FIELD_NUMBER: _ClassVar[int]
    EVENTS_OUT_FIELD_NUMBER: _ClassVar[int]
    ERRORS_FIELD_NUMBER: _ClassVar[int]
    STATS_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_NS_FIELD_NUMBER: _ClassVar[int]
    FINISHED_AT_NS_FIELD_NUMBER: _ClassVar[int]
    id: str
    transformer: str
    version: int
    start_ns: int
    end_ns: int
    output: FeedRef
    status: str
    status_detail: str
    progress: float
    events_in: int
    events_out: int
    errors: int
    stats: TransformerStats
    created_at_ns: int
    finished_at_ns: int
    def __init__(self, id: _Optional[str] = ..., transformer: _Optional[str] = ..., version: _Optional[int] = ..., start_ns: _Optional[int] = ..., end_ns: _Optional[int] = ..., output: _Optional[_Union[FeedRef, _Mapping]] = ..., status: _Optional[str] = ..., status_detail: _Optional[str] = ..., progress: _Optional[float] = ..., events_in: _Optional[int] = ..., events_out: _Optional[int] = ..., errors: _Optional[int] = ..., stats: _Optional[_Union[TransformerStats, _Mapping]] = ..., created_at_ns: _Optional[int] = ..., finished_at_ns: _Optional[int] = ...) -> None: ...

class ListTransformerRunsRequest(_message.Message):
    __slots__ = ("transformer",)
    TRANSFORMER_FIELD_NUMBER: _ClassVar[int]
    transformer: TransformerRef
    def __init__(self, transformer: _Optional[_Union[TransformerRef, _Mapping]] = ...) -> None: ...

class ListTransformerRunsResponse(_message.Message):
    __slots__ = ("runs",)
    RUNS_FIELD_NUMBER: _ClassVar[int]
    runs: _containers.RepeatedCompositeFieldContainer[TransformerRun]
    def __init__(self, runs: _Optional[_Iterable[_Union[TransformerRun, _Mapping]]] = ...) -> None: ...

class GetTransformerRunRequest(_message.Message):
    __slots__ = ("id",)
    ID_FIELD_NUMBER: _ClassVar[int]
    id: str
    def __init__(self, id: _Optional[str] = ...) -> None: ...

class CancelTransformerRunRequest(_message.Message):
    __slots__ = ("id",)
    ID_FIELD_NUMBER: _ClassVar[int]
    id: str
    def __init__(self, id: _Optional[str] = ...) -> None: ...
