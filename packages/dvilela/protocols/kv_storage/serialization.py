# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------
#
#   Copyright 2024 dvilela
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
# ------------------------------------------------------------------------------

"""Serialization module for kv_storage protocol."""

# pylint: disable=too-many-statements,too-many-locals,no-member,too-few-public-methods,redefined-builtin
from typing import Any, Dict, cast

from aea.mail.base_pb2 import DialogueMessage  # type: ignore
from aea.mail.base_pb2 import Message as ProtobufMessage  # type: ignore
from aea.protocols.base import Message  # type: ignore
from aea.protocols.base import Serializer  # type: ignore

from packages.dvilela.protocols.kv_storage import kv_storage_pb2  # type: ignore
from packages.dvilela.protocols.kv_storage.message import (  # type: ignore
    KvStorageMessage,
)


class KvStorageSerializer(Serializer):
    """Serialization for the 'kv_storage' protocol."""

    @staticmethod
    def encode(msg: Message) -> bytes:
        """
        Encode a 'KvStorage' message into bytes.

        :param msg: the message object.
        :return: the bytes.
        """
        msg = cast(KvStorageMessage, msg)
        message_pb = ProtobufMessage()
        dialogue_message_pb = DialogueMessage()
        kv_storage_msg = kv_storage_pb2.KvStorageMessage()  # type: ignore

        dialogue_message_pb.message_id = msg.message_id
        dialogue_reference = msg.dialogue_reference
        dialogue_message_pb.dialogue_starter_reference = dialogue_reference[0]
        dialogue_message_pb.dialogue_responder_reference = dialogue_reference[1]
        dialogue_message_pb.target = msg.target

        performative_id = msg.performative
        if performative_id == KvStorageMessage.Performative.READ_REQUEST:
            performative = kv_storage_pb2.KvStorageMessage.Read_Request_Performative()  # type: ignore
            keys = msg.keys
            performative.keys.extend(keys)
            kv_storage_msg.read_request.CopyFrom(performative)
        elif performative_id == KvStorageMessage.Performative.READ_RESPONSE:
            performative = kv_storage_pb2.KvStorageMessage.Read_Response_Performative()  # type: ignore
            data = msg.data
            performative.data.update(data)
            kv_storage_msg.read_response.CopyFrom(performative)
        elif performative_id == KvStorageMessage.Performative.CREATE_OR_UPDATE_REQUEST:
            performative = kv_storage_pb2.KvStorageMessage.Create_Or_Update_Request_Performative()  # type: ignore
            data = msg.data
            performative.data.update(data)
            kv_storage_msg.create_or_update_request.CopyFrom(performative)
        elif performative_id == KvStorageMessage.Performative.SUCCESS:
            performative = kv_storage_pb2.KvStorageMessage.Success_Performative()  # type: ignore
            message = msg.message
            performative.message = message
            kv_storage_msg.success.CopyFrom(performative)
        elif performative_id == KvStorageMessage.Performative.ERROR:
            performative = kv_storage_pb2.KvStorageMessage.Error_Performative()  # type: ignore
            message = msg.message
            performative.message = message
            kv_storage_msg.error.CopyFrom(performative)
        else:
            raise ValueError("Performative not valid: {}".format(performative_id))

        dialogue_message_pb.content = kv_storage_msg.SerializeToString()

        message_pb.dialogue_message.CopyFrom(dialogue_message_pb)
        message_bytes = message_pb.SerializeToString()
        return message_bytes

    @staticmethod
    def decode(obj: bytes) -> Message:
        """
        Decode bytes into a 'KvStorage' message.

        :param obj: the bytes object.
        :return: the 'KvStorage' message.
        """
        message_pb = ProtobufMessage()
        kv_storage_pb = kv_storage_pb2.KvStorageMessage()  # type: ignore
        message_pb.ParseFromString(obj)
        message_id = message_pb.dialogue_message.message_id
        dialogue_reference = (
            message_pb.dialogue_message.dialogue_starter_reference,
            message_pb.dialogue_message.dialogue_responder_reference,
        )
        target = message_pb.dialogue_message.target

        kv_storage_pb.ParseFromString(message_pb.dialogue_message.content)
        performative = kv_storage_pb.WhichOneof("performative")
        performative_id = KvStorageMessage.Performative(str(performative))
        performative_content = dict()  # type: Dict[str, Any]
        if performative_id == KvStorageMessage.Performative.READ_REQUEST:
            keys = kv_storage_pb.read_request.keys
            keys_tuple = tuple(keys)
            performative_content["keys"] = keys_tuple
        elif performative_id == KvStorageMessage.Performative.READ_RESPONSE:
            data = kv_storage_pb.read_response.data
            data_dict = dict(data)
            performative_content["data"] = data_dict
        elif performative_id == KvStorageMessage.Performative.CREATE_OR_UPDATE_REQUEST:
            data = kv_storage_pb.create_or_update_request.data
            data_dict = dict(data)
            performative_content["data"] = data_dict
        elif performative_id == KvStorageMessage.Performative.SUCCESS:
            message = kv_storage_pb.success.message
            performative_content["message"] = message
        elif performative_id == KvStorageMessage.Performative.ERROR:
            message = kv_storage_pb.error.message
            performative_content["message"] = message
        else:
            raise ValueError("Performative not valid: {}.".format(performative_id))

        return KvStorageMessage(
            message_id=message_id,
            dialogue_reference=dialogue_reference,
            target=target,
            performative=performative,
            **performative_content
        )
