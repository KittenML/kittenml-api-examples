# Python realtime file streaming

These examples use either the official OpenAI client or a standard WebSocket
client. Both stream the included audio in paced 200 ms chunks through the
canonical `/v1/realtime` route.

## Run

```bash
cd stt/realtime/python
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
# Put your KittenML API key in .env.
python transcribe_file.py
# Or use the official OpenAI client's realtime connection:
python openai_sdk.py
# Or transcribe live microphone turns using server VAD:
python microphone.py
```

Expected output has this shape:

```text
connected: <session-id>
enriched partial: [low][slow]A (cold), [pause_short] (lucid)...[/slow][/low]
clean partial: A cold lucid indifference...
enriched final: [low][slow]A (cold), [pause_short] (lucid)...[/slow][/low]
clean final: A cold lucid indifference reigned in his soul.
```

Enriched output is printed first. Its markup carries emotion, tone, pause, and
stress information; clean output removes that markup. The wording and tags can
vary slightly because this is model output.

Realtime errors include both `error.code` and `request_id` for correlation. A
socket close before the final transcript is treated as a failed request even
when the WebSocket closes cleanly.

`openai_sdk.py` configures `base_url=https://api.kittenml.com/v1`; the SDK then
constructs `wss://api.kittenml.com/v1/realtime`. It uses the SDK connection and
KittenML's transcription events. OpenAI speech-to-speech, tool calling, and
response-generation events are outside this transcription-only API.

## Use your own audio

Convert it to 24 kHz mono PCM16, then pass the resulting file:

```bash
ffmpeg -y -i input.wav -ac 1 -ar 24000 -f s16le input.pcm
python transcribe_file.py input.pcm
```

Pass `--language es` or another supported language code when a language hint
is useful. Omit `--language` for automatic detection.

## Multi-turn and VAD

Keep one WebSocket open and explicitly commit one prerecorded file per turn:

```bash
python manual_turns.py ../assets/sample.pcm
# For multiple turns, provide one different PCM file per turn:
python manual_turns.py turn-1.pcm turn-2.pcm
```

Each final event has a different `item_id`. At least one file is required; the
script never repeats a sample implicitly. This is useful for push-to-talk or
other applications that decide where each turn ends.

Two-hundred-millisecond client chunks are the recommended default. This command is useful
when validating an existing integration with a different append size:

```bash
python manual_turns.py --chunk-ms 500 turn-1.pcm turn-2.pcm
```

For a genuine ongoing microphone conversation, let server VAD create turns:

```bash
python microphone.py
```

Speak normally and pause for about 700 ms at the end of each turn. The client
continues listening and prints partial and final transcripts until you press
Ctrl+C. To choose a microphone:

```bash
python microphone.py --list-devices
python microphone.py --device 2
```

The microphone client uses the cross-platform `sounddevice` package:

- **Linux:** Install PortAudio first if your distribution does not provide it.
  On Ubuntu/Debian, run `sudo apt install libportaudio2` before installing the
  Python requirements.
- **macOS:** Installing the Python requirements also installs PortAudio. Allow
  Terminal or your IDE under **System Settings → Privacy & Security →
  Microphone** when prompted.
- **Windows:** Installing the Python requirements also installs PortAudio.
  Enable microphone access for desktop apps under **Settings → Privacy &
  security → Microphone** if capture is blocked.

Omit `--device` to use the operating system's default input. Device indexes can
change when hardware is connected or removed, so run `--list-devices` again if
a saved index stops working.
