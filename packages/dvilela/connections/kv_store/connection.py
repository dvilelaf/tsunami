#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Scaffold connection and channel."""
from pathlib import Path
from typing import Any, Callable, cast

from aea.configurations.base import PublicId
from aea.connections.base import BaseSyncConnection
from aea.mail.base import Envelope
from aea.protocols.base import Address, Message
from aea.protocols.dialogue.base import Dialogue
from peewee import CharField, Model, SqliteDatabase

from packages.dvilela.protocols.kv_storage.dialogues import KvStorageDialogue
from packages.dvilela.protocols.kv_storage.dialogues import (
    KvStorageDialogues as BaseKvStorageDialogues,
)
from packages.dvilela.protocols.kv_storage.message import KvStorageMessage


PUBLIC_ID = PublicId.from_str("valory/kv_store:0.1.0")


db = SqliteDatabase(None)


class BaseModel(Model):
    """Database base model"""

    class Meta:  # noqa pylint: disable=too-few-public-methods
        """Database meta model, as required per peewee"""

        database = db  # noqa: F841


class Store(BaseModel):
    """Database Store table"""

    key = CharField()
    value = CharField()


class KvStorageDialogues(BaseKvStorageDialogues):
    """A class to keep track of KvStorage dialogues."""

    def __init__(self, **kwargs: Any) -> None:
        """
        Initialize dialogues.

        :param kwargs: keyword arguments
        """

        def role_from_first_message(  # pylint: disable=unused-argument
            message: Message, receiver_address: Address
        ) -> Dialogue.Role:
            """Infer the role of the agent from an incoming/outgoing first message

            :param message: an incoming/outgoing first message
            :param receiver_address: the address of the receiving agent
            :return: The role of the agent
            """
            return KvStorageDialogue.Role.CONNECTION

        BaseKvStorageDialogues.__init__(
            self,
            self_address=str(kwargs.pop("connection_id")),
            role_from_first_message=role_from_first_message,
            **kwargs,
        )


class KvStoreConnection(BaseSyncConnection):
    """Proxy to the functionality of the SDK or API."""

    MAX_WORKER_THREADS = 5

    connection_id = PUBLIC_ID

    def __init__(self, *args: Any, **kwargs: Any) -> None:  # pragma: no cover
        """
        Initialize the connection.

        The configuration must be specified if and only if the following
        parameters are None: connection_id, excluded_protocols or restricted_to_protocols.

        Possible arguments:
        - configuration: the connection configuration.
        - data_dir: directory where to put local files.
        - identity: the identity object held by the agent.
        - crypto_store: the crypto store for encrypted communication.
        - restricted_to_protocols: the set of protocols ids of the only supported protocols for this connection.
        - excluded_protocols: the set of protocols ids that we want to exclude for this connection.

        :param args: arguments passed to component base
        :param kwargs: keyword arguments passed to component base
        """
        super().__init__(*args, **kwargs)
        self.dialogues = KvStorageDialogues(connection_id=PUBLIC_ID)
        self.db_path = self.configuration.config.get("db_path")

    def main(self) -> None:
        """
        Run synchronous code in background.

        SyncConnection `main()` usage:
        The idea of the `main` method in the sync connection
        is to provide for a way to actively generate messages by the connection via the `put_envelope` method.

        A simple example is the generation of a message every second:
        ```
        while self.is_connected:
            envelope = make_envelope_for_current_time()
            self.put_enevelope(envelope)
            time.sleep(1)
        ```
        In this case, the connection will generate a message every second
        regardless of envelopes sent to the connection by the agent.
        For instance, this way one can implement periodically polling some internet resources
        and generate envelopes for the agent if some updates are available.
        Another example is the case where there is some framework that runs blocking
        code and provides a callback on some internal event.
        This blocking code can be executed in the main function and new envelops
        can be created in the event callback.
        """

    def on_send(self, envelope: Envelope) -> None:
        """
        Send an envelope.

        :param envelope: the envelope to send.
        """
        kv_storage_message = cast(KvStorageMessage, envelope.message)
        dialogue = self.dialogues.update(kv_storage_message)

        if kv_storage_message.performative not in [
            KvStorageMessage.Performative.READ_REQUEST,
            KvStorageMessage.Performative.CREATE_OR_UPDATE_REQUEST,
        ]:
            self.logger.error(
                f"Performative `{kv_storage_message.performative.value}` is not supported."
            )
            return

        handler: Callable[
            [KvStorageMessage, KvStorageDialogue], KvStorageMessage
        ] = getattr(self, kv_storage_message.performative.value)
        response = handler(kv_storage_message, dialogue)
        response_envelope = Envelope(
            to=envelope.sender,
            sender=envelope.to,
            message=response,
            context=envelope.context,
        )
        self.put_envelope(response_envelope)

    def read_request(
        self,
        message: KvStorageMessage,
        dialogue: KvStorageDialogue,
    ) -> KvStorageMessage:
        """Read several keys."""

        data = Store.select().where(Store.key in message.keys)

        return cast(
            KvStorageMessage,
            dialogue.reply(
                performative=KvStorageMessage.Performative.READ_RESPONSE,
                target_message=message,
                data=data,
            ),
        )

    def create_or_update_request(
        self,
        message: KvStorageMessage,
        dialogue: KvStorageDialogue,
    ) -> KvStorageMessage:
        """Write several key-value pairs."""

        with db.atomic():
            Store.insert_many(
                message.data.items(), fields=[Store.key, Store.value]
            ).execute()

        return cast(
            KvStorageMessage,
            dialogue.reply(
                performative=KvStorageMessage.Performative.SUCCESS,
                target_message=message,
            ),
        )

    def on_connect(self) -> None:
        """Set up the connection"""
        db.init(self.db_path)
        db.connect()
        db.create_tables([Store])

    def on_disconnect(self) -> None:
        """
        Tear down the connection.

        Connection status set automatically.
        """
