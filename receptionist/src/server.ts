import express from "express";
import { createServer } from "http";
import { WebSocketServer, WebSocket } from "ws";
import dotenv from "dotenv";

dotenv.config({ path: "/home/ai/.openclaw/.env" });

const {
  ELEVENLABS_API_KEY,
  ELEVENLABS_AGENT_ID,
  TWILIO_ACCOUNT_SID,
  TWILIO_AUTH_TOKEN,
  GOOGLE_REFRESH_TOKEN,
  GOOGLE_CLIENT_ID,
  GOOGLE_CLIENT_SECRET,
  PORT = "8080",
  SHEET_ID = "1zujOUa1EpRPo1qqtt7wAnLTUh5pnSFjUMZOz0Ko5aR4",
  SHEET_TAB = "PestGuard Demo",
} = process.env;

if (!ELEVENLABS_API_KEY || !ELEVENLABS_AGENT_ID || !TWILIO_ACCOUNT_SID || !TWILIO_AUTH_TOKEN) {
  console.error("Missing required keys in .env");
  process.exit(1);
}

const app = express();
app.use(express.urlencoded({ extended: true }));
app.use(express.json());

// ─────────────────────────────────────────────
// Google OAuth helpers
// ─────────────────────────────────────────────
async function getGoogleToken(): Promise<string> {
  const resp = await fetch("https://oauth2.googleapis.com/token", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      client_id: GOOGLE_CLIENT_ID!,
      client_secret: GOOGLE_CLIENT_SECRET!,
      refresh_token: GOOGLE_REFRESH_TOKEN!,
      grant_type: "refresh_token",
    }),
  });
  const data = await resp.json() as { access_token: string };
  return data.access_token;
}

// ─────────────────────────────────────────────
// Google Sheets helpers
// ─────────────────────────────────────────────
async function sheetFindRowByPhone(phone: string): Promise<{ row: number; data: Record<string, string> } | null> {
  const token = await getGoogleToken();
  const phoneNormalized = phone.replace(/\D/g, "").slice(-10);

  // Fetch columns A through L (enough to include the Phone column at C / index 2)
  const resp = await fetch(
    `https://sheets.googleapis.com/v4/spreadsheets/${SHEET_ID}/values/${encodeURIComponent(SHEET_TAB)}!A:L`,
    { headers: { Authorization: `Bearer ${token}` } }
  );
  const json = await resp.json() as { values: string[][] };
  const rows = json.values ?? [];

  for (let i = 1; i < rows.length; i++) {
    const rowPhone = (rows[i][2] ?? "").replace(/\D/g, "").slice(-10);
    if (rowPhone === phoneNormalized) {
      // Fetch full row
      const fullRow = await fetch(
        `https://sheets.googleapis.com/v4/spreadsheets/${SHEET_ID}/values/${encodeURIComponent(SHEET_TAB)}!${i + 1}:${i + 1}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      const fullData = await fullRow.json() as { values: string[][] };
      const rowData: Record<string, string> = {};
      const headers = rows[0];
      (fullData.values?.[0] ?? []).forEach((val, idx) => {
        rowData[headers[idx] ?? `col${idx}`] = val;
      });
      return { row: i + 1, data: rowData };
    }
  }
  return null;
}

async function sheetUpdateRow(row: number, data: Record<string, string>): Promise<void> {
  const token = await getGoogleToken();
  const headersResp = await fetch(
    `https://sheets.googleapis.com/v4/spreadsheets/${SHEET_ID}/values/${encodeURIComponent(SHEET_TAB)}!1:1`,
    { headers: { Authorization: `Bearer ${token}` } }
  );
  const headersJson = await headersResp.json() as { values: string[][] };
  const headers = headersJson.values?.[0] ?? [];

  const rowData: string[] = headers.map((h, i) => data[h] ?? "");
  const range = `${SHEET_TAB}!${row}:${row}`;

  await fetch(
    `https://sheets.googleapis.com/v4/spreadsheets/${SHEET_ID}/values/${encodeURIComponent(range)}?valueInputOption=RAW`,
    {
      method: "PUT",
      headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
      body: JSON.stringify({ values: [rowData] }),
    }
  );
}

async function sheetAppendRow(data: Record<string, string>): Promise<number> {
  const token = await getGoogleToken();
  const headersResp = await fetch(
    `https://sheets.googleapis.com/v4/spreadsheets/${SHEET_ID}/values/${encodeURIComponent(SHEET_TAB)}!1:1`,
    { headers: { Authorization: `Bearer ${token}` } }
  );
  const headersJson = await headersResp.json() as { values: string[][] };
  const headers = headersJson.values?.[0] ?? [];

  const rowData: string[] = headers.map((h) => data[h] ?? "");
  const range = `${SHEET_TAB}!A:A`;

  const resp = await fetch(
    `https://sheets.googleapis.com/v4/spreadsheets/${SHEET_ID}/values/${encodeURIComponent(range)}:append?valueInputOption=RAW`,
    {
      method: "POST",
      headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
      body: JSON.stringify({ values: [rowData] }),
    }
  );
  const json = await resp.json() as { updates: { updatedRows: number } };
  return json.updates.updatedRows;
}

// ─────────────────────────────────────────────
// Google Calendar helpers
// ─────────────────────────────────────────────
async function calendarGetAvailableSlots(date: string): Promise<string[]> {
  // date format: YYYY-MM-DD
  const token = await getGoogleToken();
  const [year, month, day] = date.split("-").map(Number);
  // Business hours 8am–6pm EST = 13:00–24:00 UTC (UTC-5 offset)
  const startOfDay = new Date(Date.UTC(year, month - 1, day, 13, 0, 0));
  const endOfDay = new Date(Date.UTC(year, month - 1, day, 24, 0, 0));

  const resp = await fetch(
    `https://www.googleapis.com/calendar/v3/calendars/primary/events?timeMin=${startOfDay.toISOString()}&timeMax=${endOfDay.toISOString()}&singleEvents=true&orderBy=startTime&timeZone=America%2FNew_York`,
    { headers: { Authorization: `Bearer ${token}` } }
  );
  const json = await resp.json() as { items: { start: { dateTime: string }; end: { dateTime: string }; summary?: string }[] };

  const busySlots: { start: number; end: number }[] = (json.items ?? []).map((ev) => ({
    start: new Date(ev.start.dateTime).getTime(),
    end: new Date(ev.end.dateTime).getTime(),
  }));

  // Construct slot times in New York timezone directly
  const dateStrNY = `${year}-${String(month).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
  const available: string[] = [];
  const slotDurationMs = 60 * 60 * 1000;

  // Business hours 8 AM – 6 PM NY (EDT = UTC-4 on April 25, 2026)
  const nyOffsetHours = 4;
  for (let h = 8; h <= 18; h++) {
    // Convert NY hour to UTC: NY +4 = UTC
    const utcH = h + nyOffsetHours;
    const slotStartNY = new Date(`${dateStrNY}T${String(utcH).padStart(2, "0")}:00:00`);
    const slotStartMs = slotStartNY.getTime();
    const slotEndMs = slotStartMs + slotDurationMs;
    const isBusy = busySlots.some((b) => b.start < slotEndMs && b.end > slotStartMs);
    if (!isBusy) {
      const estTime = slotStartNY.toLocaleTimeString("en-US", {
        hour: "numeric",
        minute: "2-digit",
        hour12: true,
        timeZone: "America/New_York",
      });
      available.push(estTime);
    }
  }
  return available;
}

// Helper: parse time string to hour (0-23) in New York timezone
  // (used by calendarCreateEvent)

async function calendarCreateEvent(title: string, date: string, time: string, contactName: string, phone: string): Promise<string> {
  const token = await getGoogleToken();

  // Parse "8:00 AM" → hour in 24h NY time
  const [timePart, ampm] = time.split(" ");
  let [hours, mins] = timePart.split(":").map(Number);
  if (ampm === "PM" && hours !== 12) hours += 12;
  if (ampm === "AM" && hours === 12) hours = 0;

  // Convert NY local time to UTC for the Google Calendar API
  // NY is UTC-4 (EDT) on April 25, 2026
  const [year, month, day] = date.split("-").map(Number);
  const nyOffset = -4 * 60; // minutes
  const utcHour = hours - nyOffset / 60;
  const startDateTime = new Date(Date.UTC(year, month - 1, day, utcHour, mins, 0));
  const endDateTime = new Date(startDateTime.getTime() + 60 * 60 * 1000);

  const resp = await fetch("https://www.googleapis.com/calendar/v3/calendars/primary/events?sendUpdates=all", {
    method: "POST",
    headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
    body: JSON.stringify({
      summary: title,
      description: `Contact: ${contactName}\nPhone: ${phone}\nSource: PestGuard AI Receptionist`,
      start: { dateTime: startDateTime.toISOString(), timeZone: "America/New_York" },
      end: { dateTime: endDateTime.toISOString(), timeZone: "America/New_York" },
      reminders: { useDefault: false, overrides: [{ method: "popup", minutes: 30 }] },
    }),
  });
  const json = await resp.json() as { id: string; htmlLink: string };
  return json.htmlLink ?? "created";
}

// ─────────────────────────────────────────────
// REST API routes (called by ElevenLabs agent)
// ─────────────────────────────────────────────
const api = express.Router();
app.use("/api", api);

// GET /api/lookup?phone=+19733068922
api.get("/lookup", async (req, res) => {
  try {
    const phone = (req.query.phone as string) ?? "";
    const result = await sheetFindRowByPhone(phone);
    if (!result) {
      res.json({ found: false, phone });
    } else {
      res.json({ found: true, ...result });
    }
  } catch (err) {
    console.error("[sheets] lookup error:", err);
    res.status(500).json({ error: "Lookup failed" });
  }
});

// POST /api/update-row
// Body: { row: number, data: { "Contact Name": "...", "Notes / Last Conversation": "...", ... } }
api.post("/update-row", async (req, res) => {
  try {
    const { row, data } = req.body as { row: number; data: Record<string, string> };
    await sheetUpdateRow(row, data);
    res.json({ success: true });
  } catch (err) {
    console.error("[sheets] update error:", err);
    res.status(500).json({ error: "Update failed" });
  }
});

// POST /api/create-lead
// Body: { "Contact Name": "...", "Phone": "...", ... }
api.post("/create-lead", async (req, res) => {
  try {
    const data = req.body as Record<string, string>;
    const row = await sheetAppendRow(data);
    res.json({ success: true, row });
  } catch (err) {
    console.error("[sheets] create error:", err);
    res.status(500).json({ error: "Create lead failed" });
  }
});

// GET /api/availability?date=2026-04-25
api.get("/availability", async (req, res) => {
  try {
    const date = (req.query.date as string) ?? "";
    if (!/^\d{4}-\d{2}-\d{2}$/.test(date)) {
      res.status(400).json({ error: "Invalid date format. Use YYYY-MM-DD" });
      return;
    }
    const slots = await calendarGetAvailableSlots(date);
    res.json({ date, slots });
  } catch (err) {
    console.error("[calendar] availability error:", err);
    res.status(500).json({ error: "Availability check failed" });
  }
});

// POST /api/book-appointment
// Body: { title, date, time, contactName, phone }
api.post("/book-appointment", async (req, res) => {
  try {
    const { title, date, time, contactName, phone } = req.body as {
      title: string; date: string; time: string; contactName: string; phone: string;
    };
    const link = await calendarCreateEvent(title, date, time, contactName, phone);
    res.json({ success: true, calendarLink: link });
  } catch (err) {
    console.error("[calendar] booking error:", err);
    res.status(500).json({ error: "Booking failed" });
  }
});

// Health check
api.get("/health", (_req, res) => res.json({ ok: true }));

// ─────────────────────────────────────────────
// Twilio webhook & media stream
// ─────────────────────────────────────────────
app.get("/", (_req, res) => {
  res.send("OpenClaw Receptionist is running.");
});

app.post("/incoming-call", (req, res) => {
  const host = req.headers.host;
  const twiml = `<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Connect>
    <Stream url="wss://${host}/media-stream">
      <Parameter name="auth_token" value="${TWILIO_AUTH_TOKEN}" />
    </Stream>
  </Connect>
</Response>`;
  res.type("text/xml").send(twiml);
});

app.post("/call-status", (req, res) => {
  const { CallStatus, CallSid, Duration } = req.body;
  console.log(`[status] ${CallSid} → ${CallStatus} (${Duration}s)`);
  res.sendStatus(200);
});

const server = createServer(app);
const wss = new WebSocketServer({ server, path: "/media-stream" });

wss.on("connection", (twilioWs) => {
  console.log("[call] Twilio connected. Waiting for start event payload...");
  let streamSid: string | null = null;
  let elevenLabsWs: WebSocket | null = null;

  twilioWs.on("message", (data) => {
    let msg: Record<string, any>;
    try { msg = JSON.parse(data.toString()); } catch { return; }

    switch (msg.event) {
      case "start": {
        const authToken = msg.start?.customParameters?.auth_token;
        if (authToken !== TWILIO_AUTH_TOKEN) {
          console.error("[call] Unauthorized!");
          twilioWs.close();
          return;
        }

        const start = msg.start as { streamSid: string; callSid: string };
        streamSid = start.streamSid;
        console.log(`[call] Authenticated | stream: ${streamSid} | call: ${start.callSid}`);

        elevenLabsWs = new WebSocket(
          `wss://api.elevenlabs.io/v1/convai/conversation?agent_id=${ELEVENLABS_AGENT_ID}`,
          { headers: { "xi-api-key": ELEVENLABS_API_KEY! } }
        );

        elevenLabsWs.on("open", () => console.log("[elevenlabs] connected"));
        elevenLabsWs.on("close", () => {
          console.log("[elevenlabs] disconnected");
          if (twilioWs.readyState === WebSocket.OPEN) twilioWs.close();
        });
        elevenLabsWs.on("error", (err) => console.error("[elevenlabs] error:", err.message));

        elevenLabsWs.on("message", (elData) => {
          let elMsg: Record<string, any>;
          try { elMsg = JSON.parse(elData.toString()); } catch { return; }

          switch (elMsg.type) {
            case "conversation_initiation_metadata":
              console.log("[elevenlabs] session:", elMsg.conversation_initiation_metadata_event?.conversation_id);
              break;
            case "audio": {
              if (streamSid && twilioWs.readyState === WebSocket.OPEN) {
                const audio64 = elMsg.audio_event?.audio_base_64;
                if (audio64) {
                  twilioWs.send(JSON.stringify({ event: "media", streamSid, media: { payload: audio64 } }));
                }
              }
              break;
            }
            case "interruption":
              if (streamSid && twilioWs.readyState === WebSocket.OPEN) {
                twilioWs.send(JSON.stringify({ event: "clear", streamSid }));
              }
              break;
            case "ping": {
              const pingEventId = elMsg.ping_event?.event_id;
              if (elevenLabsWs?.readyState === WebSocket.OPEN) {
                elevenLabsWs.send(JSON.stringify({ type: "pong", event_id: pingEventId }));
              }
              break;
            }
            case "agent_response":
              console.log("[agent]", elMsg.agent_response_event?.agent_response);
              break;
            case "user_transcript":
              console.log("[caller]", elMsg.user_transcription_event?.user_transcript);
              break;
          }
        });
        break;
      }
      case "media": {
        const media = msg.media as { track: string; payload: string };
        if (elevenLabsWs && elevenLabsWs.readyState === WebSocket.OPEN && media.track === "inbound") {
          elevenLabsWs.send(JSON.stringify({ user_audio_chunk: media.payload }));
        }
        break;
      }
      case "stop":
        console.log("[call] stopped");
        if (elevenLabsWs) elevenLabsWs.close();
        break;
    }
  });

  twilioWs.on("close", () => {
    console.log("[call] Twilio disconnected");
    if (elevenLabsWs && elevenLabsWs.readyState === WebSocket.OPEN) elevenLabsWs.close();
  });
  twilioWs.on("error", (err) => console.error("[twilio] ws error:", err.message));
});

server.listen(Number(PORT), () => {
  console.log(`OpenClaw Receptionist listening on :${PORT}`);
  console.log(`  Webhook:   POST /incoming-call`);
  console.log(`  Stream WS: wss://<host>/media-stream`);
  console.log(`  REST API:  GET  /api/lookup?phone=...`);
  console.log(`             POST /api/update-row`);
  console.log(`             POST /api/create-lead`);
  console.log(`             GET  /api/availability?date=YYYY-MM-DD`);
  console.log(`             POST /api/book-appointment`);
});