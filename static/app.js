import * as SIP from "/vendor/sip.js/lib/index.js";

let userAgent = null;
let registerer = null;
let currentSession = null;
let remoteMediaStream = null;
let sipConfig = null;

const logEl = document.getElementById("event-log");
const transportEl = document.getElementById("transport-status");
const registrationEl = document.getElementById("registration-status");
const callStatusEl = document.getElementById("call-status");
const destinationEl = document.getElementById("destination");
const remoteAudioEl = document.getElementById("remote-audio");

function log(message) {
  const line = `[${new Date().toLocaleTimeString()}] ${message}`;
  logEl.textContent = `${line}\n${logEl.textContent}`.trim();
}

function setStatus(element, value) {
  element.textContent = value;
}

async function loadConfig() {
  const response = await fetch("/api/config/public");
  if (!response.ok) {
    throw new Error("Unable to load SIP configuration");
  }
  sipConfig = await response.json();
  log(`Loaded SIP config for ${sipConfig.uri}`);
}

async function requestMicrophone() {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
  stream.getTracks().forEach((track) => track.stop());
  log("Microphone permission granted");
}

function ensureSipJsAvailable() {
  if (!SIP || !SIP.UserAgent) {
    throw new Error("SIP.js failed to load");
  }
}

function buildUserAgent() {
  ensureSipJsAvailable();
  const uri = SIP.UserAgent.makeURI(sipConfig.uri);
  userAgent = new SIP.UserAgent({
    uri,
    transportOptions: {
      server: sipConfig.websocket_url,
    },
    authorizationUsername: sipConfig.authorization_username,
    authorizationPassword: sipConfig.password,
    displayName: sipConfig.display_name,
    sessionDescriptionHandlerFactoryOptions: {
      constraints: {
        audio: true,
        video: false,
      },
      peerConnectionConfiguration: {
        iceServers: [{ urls: ["stun:stun.l.google.com:19302"] }],
      },
    },
    delegate: {
      onInvite(invitation) {
        currentSession = invitation;
        wireSession(invitation);
        setStatus(callStatusEl, "Incoming");
        log("Incoming call received");
      },
      onConnect() {
        setStatus(transportEl, "Connected");
        log("WebSocket transport connected");
      },
      onDisconnect() {
        setStatus(transportEl, "Disconnected");
        setStatus(registrationEl, "Offline");
        log("WebSocket transport disconnected");
      },
    },
  });
}

function wireRemoteAudio(session) {
  const sdh = session.sessionDescriptionHandler;
  if (!sdh || !sdh.peerConnection) {
    return;
  }
  const pc = sdh.peerConnection;
  remoteMediaStream = new MediaStream();
  pc.getReceivers().forEach((receiver) => {
    if (receiver.track) {
      remoteMediaStream.addTrack(receiver.track);
    }
  });
  remoteAudioEl.srcObject = remoteMediaStream;
}

function wireSession(session) {
  session.stateChange.addListener((state) => {
    setStatus(callStatusEl, state);
    log(`Session state changed to ${state}`);
    if (state === SIP.SessionState.Established) {
      wireRemoteAudio(session);
    }
    if (state === SIP.SessionState.Terminated) {
      currentSession = null;
    }
  });
}

async function registerBrowser() {
  if (!sipConfig) {
    await loadConfig();
  }
  if (!userAgent) {
    buildUserAgent();
  }
  await userAgent.start();
  if (!registerer) {
    registerer = new SIP.Registerer(userAgent);
  }
  await registerer.register();
  setStatus(registrationEl, "Registered");
  log("Browser SIP endpoint registered");
}

async function placeBrowserCall() {
  const destination = destinationEl.value.trim();
  if (!destination) {
    log("Enter a destination number first");
    return;
  }
  if (!userAgent || !registerer) {
    await registerBrowser();
  }
  const target = SIP.UserAgent.makeURI(`sip:${destination}@${sipConfig.uri.split("@")[1]}`);
  const inviter = new SIP.Inviter(userAgent, target, {
    sessionDescriptionHandlerOptions: {
      constraints: { audio: true, video: false },
    },
  });
  currentSession = inviter;
  wireSession(inviter);
  await inviter.invite();
  log(`Outbound browser call started to ${destination}`);
}

async function answerCall() {
  if (!currentSession || !(currentSession instanceof SIP.Invitation)) {
    log("No incoming call to answer");
    return;
  }
  await currentSession.accept({
    sessionDescriptionHandlerOptions: {
      constraints: { audio: true, video: false },
    },
  });
  log("Incoming call answered");
}

async function hangupCall() {
  if (!currentSession) {
    log("No active call to hang up");
    return;
  }
  const state = currentSession.state;
  if (state === SIP.SessionState.Initial || state === SIP.SessionState.Establishing) {
    await currentSession.cancel();
  } else if (state === SIP.SessionState.Established) {
    await currentSession.bye();
  } else if (currentSession.reject) {
    await currentSession.reject();
  }
  log("Call hangup requested");
}

async function originateFromBackend() {
  const destination = destinationEl.value.trim();
  if (!destination) {
    log("Enter a destination number first");
    return;
  }
  const response = await fetch("/api/calls/initiate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ destination }),
  });
  const payload = await response.json();
  if (!response.ok) {
    log(`FastAPI originate failed: ${payload.detail || "Unknown error"}`);
    return;
  }
  log(`FastAPI originate queued with id ${payload.call.id}`);
}

document.getElementById("register-btn").addEventListener("click", async () => {
  try {
    await requestMicrophone();
    await registerBrowser();
  } catch (error) {
    log(`Register failed: ${error.message}`);
  }
});

document.getElementById("call-btn").addEventListener("click", async () => {
  try {
    await requestMicrophone();
    await placeBrowserCall();
  } catch (error) {
    log(`Call failed: ${error.message}`);
  }
});

document.getElementById("answer-btn").addEventListener("click", async () => {
  try {
    await answerCall();
  } catch (error) {
    log(`Answer failed: ${error.message}`);
  }
});

document.getElementById("hangup-btn").addEventListener("click", async () => {
  try {
    await hangupCall();
  } catch (error) {
    log(`Hangup failed: ${error.message}`);
  }
});

document.getElementById("mic-btn").addEventListener("click", async () => {
  try {
    await requestMicrophone();
  } catch (error) {
    log(`Microphone check failed: ${error.message}`);
  }
});

document.getElementById("backend-call-btn").addEventListener("click", async () => {
  try {
    await originateFromBackend();
  } catch (error) {
    log(`Backend originate failed: ${error.message}`);
  }
});

loadConfig().catch((error) => {
  log(`Startup failed: ${error.message}`);
});
