# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: kv_store.proto
# Protobuf Python Version: 5.26.0
"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder


# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()


DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(
    b"\n\x0ekv_store.proto\x12\x1b\x61\x65\x61.dvilela.kv_store.v0_1_0\"\xe6\x07\n\x0eKvStoreMessage\x12u\n\x18\x63reate_or_update_request\x18\x05 \x01(\x0b\x32Q.aea.dvilela.kv_store.v0_1_0.KvStoreMessage.Create_Or_Update_Request_PerformativeH\x00\x12O\n\x05\x65rror\x18\x06 \x01(\x0b\x32>.aea.dvilela.kv_store.v0_1_0.KvStoreMessage.Error_PerformativeH\x00\x12]\n\x0cread_request\x18\x07 \x01(\x0b\x32\x45.aea.dvilela.kv_store.v0_1_0.KvStoreMessage.Read_Request_PerformativeH\x00\x12_\n\rread_response\x18\x08 \x01(\x0b\x32\x46.aea.dvilela.kv_store.v0_1_0.KvStoreMessage.Read_Response_PerformativeH\x00\x12S\n\x07success\x18\t \x01(\x0b\x32@.aea.dvilela.kv_store.v0_1_0.KvStoreMessage.Success_PerformativeH\x00\x1a)\n\x19Read_Request_Performative\x12\x0c\n\x04keys\x18\x01 \x03(\t\x1a\xa9\x01\n\x1aRead_Response_Performative\x12^\n\x04\x64\x61ta\x18\x01 \x03(\x0b\x32P.aea.dvilela.kv_store.v0_1_0.KvStoreMessage.Read_Response_Performative.DataEntry\x1a+\n\tDataEntry\x12\x0b\n\x03key\x18\x01 \x01(\t\x12\r\n\x05value\x18\x02 \x01(\t:\x02\x38\x01\x1a\xbf\x01\n%Create_Or_Update_Request_Performative\x12i\n\x04\x64\x61ta\x18\x01 \x03(\x0b\x32[.aea.dvilela.kv_store.v0_1_0.KvStoreMessage.Create_Or_Update_Request_Performative.DataEntry\x1a+\n\tDataEntry\x12\x0b\n\x03key\x18\x01 \x01(\t\x12\r\n\x05value\x18\x02 \x01(\t:\x02\x38\x01\x1a'\n\x14Success_Performative\x12\x0f\n\x07message\x18\x01 \x01(\t\x1a%\n\x12\x45rror_Performative\x12\x0f\n\x07message\x18\x01 \x01(\tB\x0e\n\x0cperformativeb\x06proto3"
)

_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, "kv_store_pb2", _globals)
if not _descriptor._USE_C_DESCRIPTORS:
    DESCRIPTOR._loaded_options = None
    _globals[
        "_KVSTOREMESSAGE_READ_RESPONSE_PERFORMATIVE_DATAENTRY"
    ]._loaded_options = None
    _globals[
        "_KVSTOREMESSAGE_READ_RESPONSE_PERFORMATIVE_DATAENTRY"
    ]._serialized_options = b"8\001"
    _globals[
        "_KVSTOREMESSAGE_CREATE_OR_UPDATE_REQUEST_PERFORMATIVE_DATAENTRY"
    ]._loaded_options = None
    _globals[
        "_KVSTOREMESSAGE_CREATE_OR_UPDATE_REQUEST_PERFORMATIVE_DATAENTRY"
    ]._serialized_options = b"8\001"
    _globals["_KVSTOREMESSAGE"]._serialized_start = 48
    _globals["_KVSTOREMESSAGE"]._serialized_end = 1046
    _globals["_KVSTOREMESSAGE_READ_REQUEST_PERFORMATIVE"]._serialized_start = 543
    _globals["_KVSTOREMESSAGE_READ_REQUEST_PERFORMATIVE"]._serialized_end = 584
    _globals["_KVSTOREMESSAGE_READ_RESPONSE_PERFORMATIVE"]._serialized_start = 587
    _globals["_KVSTOREMESSAGE_READ_RESPONSE_PERFORMATIVE"]._serialized_end = 756
    _globals[
        "_KVSTOREMESSAGE_READ_RESPONSE_PERFORMATIVE_DATAENTRY"
    ]._serialized_start = 713
    _globals[
        "_KVSTOREMESSAGE_READ_RESPONSE_PERFORMATIVE_DATAENTRY"
    ]._serialized_end = 756
    _globals[
        "_KVSTOREMESSAGE_CREATE_OR_UPDATE_REQUEST_PERFORMATIVE"
    ]._serialized_start = 759
    _globals[
        "_KVSTOREMESSAGE_CREATE_OR_UPDATE_REQUEST_PERFORMATIVE"
    ]._serialized_end = 950
    _globals[
        "_KVSTOREMESSAGE_CREATE_OR_UPDATE_REQUEST_PERFORMATIVE_DATAENTRY"
    ]._serialized_start = 713
    _globals[
        "_KVSTOREMESSAGE_CREATE_OR_UPDATE_REQUEST_PERFORMATIVE_DATAENTRY"
    ]._serialized_end = 756
    _globals["_KVSTOREMESSAGE_SUCCESS_PERFORMATIVE"]._serialized_start = 952
    _globals["_KVSTOREMESSAGE_SUCCESS_PERFORMATIVE"]._serialized_end = 991
    _globals["_KVSTOREMESSAGE_ERROR_PERFORMATIVE"]._serialized_start = 993
    _globals["_KVSTOREMESSAGE_ERROR_PERFORMATIVE"]._serialized_end = 1030
# @@protoc_insertion_point(module_scope)
