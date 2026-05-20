import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict

from app.config import Settings
from app.models import CallRecord, CallRequest

logger = logging.getLogger(__name__)


class AsteriskAmiError(RuntimeError):
    pass


class InMemoryCallStore:
    def __init__(self) -> None:
        self._calls: Dict[str, CallRecord] = {}

    def create(self, payload: CallRequest) -> CallRecord:
        record = CallRecord(
            destination=payload.destination,
            caller_id=payload.caller_id,
            metadata=payload.metadata,
        )
        self._calls[record.id] = record
        return record

    def get(self, call_id: str) -> CallRecord | None:
        return self._calls.get(call_id)

    def list(self) -> list[CallRecord]:
        return sorted(self._calls.values(), key=lambda item: item.created_at, reverse=True)

    def update(self, call_id: str, **changes: object) -> CallRecord:
        record = self._calls[call_id]
        for key, value in changes.items():
            setattr(record, key, value)
        record.updated_at = datetime.now(timezone.utc)
        self._calls[call_id] = record
        return record


class AsteriskAmiClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def originate(self, record: CallRecord) -> str:
        if not self.settings.asterisk_ami_enabled:
            logger.info("AMI disabled, simulating originate for call %s", record.id)
            return f"mock-{record.id}"

        reader, writer = await asyncio.open_connection(
            self.settings.asterisk_ami_host,
            self.settings.asterisk_ami_port,
        )
        try:
            await self._consume_banner(reader)
            await self._send_action(
                writer,
                {
                    "Action": "Login",
                    "Username": self.settings.asterisk_ami_username,
                    "Secret": self.settings.asterisk_ami_secret,
                    "Events": "off",
                },
            )
            login_response = await self._read_until_response(reader)
            if login_response.get("Response") != "Success":
                raise AsteriskAmiError(login_response.get("Message", "AMI login failed"))

            channel = (
                f"{self.settings.asterisk_ami_channel_prefix}/"
                f"{record.destination}@{self.settings.asterisk_ami_originate_context}"
            )
            action_id = record.id
            await self._send_action(
                writer,
                {
                    "Action": "Originate",
                    "ActionID": action_id,
                    "Channel": channel,
                    "Context": self.settings.asterisk_ami_originate_context,
                    "Exten": record.destination,
                    "Priority": str(self.settings.asterisk_ami_originate_priority),
                    "CallerID": record.caller_id or "",
                    "Async": "true",
                    "Timeout": str(self.settings.asterisk_ami_originate_timeout_ms),
                    "Variable": f"APP_CALL_ID={record.id}",
                },
            )
            originate_response = await self._read_until_response(reader)
            if originate_response.get("Response") != "Success":
                raise AsteriskAmiError(originate_response.get("Message", "AMI originate failed"))
            return originate_response.get("ActionID", action_id)
        except TimeoutError as exc:
            raise AsteriskAmiError("AMI request timed out") from exc
        finally:
            try:
                await self._send_action(writer, {"Action": "Logoff"})
            except Exception:
                logger.debug("AMI logoff skipped due to prior connection issue", exc_info=True)
            writer.close()
            await writer.wait_closed()

    async def _send_action(self, writer: asyncio.StreamWriter, fields: dict[str, str]) -> None:
        payload = "".join(f"{key}: {value}\r\n" for key, value in fields.items()) + "\r\n"
        writer.write(payload.encode("utf-8"))
        await writer.drain()

    async def _read_message(self, reader: asyncio.StreamReader) -> dict[str, str]:
        message: dict[str, str] = {}
        while True:
            line = await reader.readline()
            if not line:
                break
            decoded = line.decode("utf-8", errors="ignore").strip()
            if not decoded:
                break
            if ":" in decoded:
                key, value = decoded.split(":", 1)
                message[key.strip()] = value.strip()
        return message

    async def _read_until_response(self, reader: asyncio.StreamReader) -> dict[str, str]:
        while True:
            message = await asyncio.wait_for(self._read_message(reader), timeout=5)
            if not message:
                continue
            if "Response" in message or "Event" in message:
                return message

    async def _consume_banner(self, reader: asyncio.StreamReader) -> None:
        await asyncio.wait_for(reader.readline(), timeout=5)
        try:
            await asyncio.wait_for(reader.readline(), timeout=1)
        except TimeoutError:
            pass
