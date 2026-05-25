from fastapi import APIRouter, Depends, HTTPException

from app.config import Settings, get_settings
from app.models import CallRequest, CallStatusResponse, PublicSipConfig
from app.services.asterisk import AsteriskAmiClient, AsteriskAmiError, InMemoryCallStore

router = APIRouter(prefix="/api")
call_store = InMemoryCallStore()


def get_ami_client(settings: Settings = Depends(get_settings)) -> AsteriskAmiClient:
    return AsteriskAmiClient(settings)


@router.get("/health")
async def healthcheck(settings: Settings = Depends(get_settings)) -> dict:
    return {
        "status": "ok",
        "app": settings.app_name,
        "environment": settings.app_env,
        "ami_enabled": settings.asterisk_ami_enabled,
    }


@router.get("/config/public", response_model=PublicSipConfig)
async def public_config(settings: Settings = Depends(get_settings)) -> PublicSipConfig:
    ws_url = settings.sip_wss_url if settings.sip_wss_url else settings.sip_ws_url
    return PublicSipConfig(
        websocket_url=ws_url,
        uri=f"sip:{settings.sip_extension}@{settings.sip_domain}",
        authorization_username=settings.sip_auth_username,
        password=settings.sip_auth_password,
        display_name=settings.sip_display_name,
    )


@router.get("/calls")
async def list_calls() -> dict:
    return {"calls": call_store.list()}


@router.get("/calls/{call_id}", response_model=CallStatusResponse)
async def get_call(call_id: str) -> CallStatusResponse:
    record = call_store.get(call_id)
    if not record:
        raise HTTPException(status_code=404, detail="Call not found")
    return CallStatusResponse(call=record)


@router.post("/calls/initiate", response_model=CallStatusResponse)
async def initiate_call(
    payload: CallRequest,
    settings: Settings = Depends(get_settings),
    ami_client: AsteriskAmiClient = Depends(get_ami_client),
) -> CallStatusResponse:
    destination = f"{settings.public_dial_prefix}{payload.destination}"
    record = call_store.create(payload.model_copy(update={"destination": destination}))
    call_store.update(record.id, state="ringing")
    try:
        provider_reference = await ami_client.originate(record)
        record = call_store.update(record.id, provider_reference=provider_reference)
    except AsteriskAmiError as exc:
        record = call_store.update(record.id, state="failed", error=str(exc))
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return CallStatusResponse(call=record)


@router.post("/calls/{call_id}/hangup", response_model=CallStatusResponse)
async def hangup_call(call_id: str) -> CallStatusResponse:
    record = call_store.get(call_id)
    if not record:
        raise HTTPException(status_code=404, detail="Call not found")
    record = call_store.update(call_id, state="hangup")
    return CallStatusResponse(call=record)



