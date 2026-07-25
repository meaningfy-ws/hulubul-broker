# langflow-message-relay Specification

## Purpose
TBD - created by archiving change build-telegram-gateway. Update Purpose after archive.
## Requirements
### Requirement: Deterministic session_id derivation
The system SHALL derive `session_id` as a pure, deterministic function of the channel's
medium and `systemID` (`f(medium, systemID)`), computed locally from data already present in
the inbound message, without any network call or lookup.

#### Scenario: The same channel always produces the same session_id
- **WHEN** two separate inbound messages arrive from the same Telegram `chat_id`, at any two
  points in time
- **THEN** both produce an identical `session_id`, so `OperationalConversationBinding` lookups
  in LangFlow/Neo4j resolve to the same binding across messages

#### Scenario: Different channels never collide
- **WHEN** a Telegram `chat_id` and a WhatsApp phone number happen to share the same digits
- **THEN** their derived `session_id`s differ, because the medium is part of the derivation

### Requirement: Trusted channel identity attached to every relay call
The system SHALL attach the trusted `(medium, systemID)` channel identity to every LangFlow
Run API call, since the gateway is the trust boundary holding the authenticated channel
credential and LangFlow cannot independently verify the message's origin.

#### Scenario: LangFlow receives the channel identity alongside the message
- **WHEN** the relay orchestration calls the LangFlow Run API for an inbound message
- **THEN** the call includes the `session_id`, the `medium`, and the `systemID`, so
  `resolve_channel_actor(medium, systemID)` inside LangFlow can resolve or create the
  corresponding `Channel`/`Agent`

### Requirement: LangFlow Run API client isolates the HTTP integration
The system SHALL provide a `LangflowClient` adapter that wraps calls to LangFlow's Run API
(`/api/v1/run/{flow_id}`), so no other layer constructs LangFlow HTTP requests directly.

#### Scenario: A relay call goes through the client, not raw HTTP
- **WHEN** `services/relay_message.py` needs to invoke LangFlow
- **THEN** it calls `LangflowClient`'s method rather than issuing `requests`/`httpx` calls
  itself, keeping the HTTP integration confined to the adapters layer

### Requirement: Reply relay back to the originating channel
The system SHALL take LangFlow's structured reply and relay it back through the same
`ChannelPort` adapter and identity (`chat_id`/`systemID`) the inbound message arrived on,
never a different or default channel.

#### Scenario: A reply is sent to the message's origin channel
- **WHEN** LangFlow returns a structured reply for a message that arrived via Telegram
  `chat_id` X
- **THEN** the relay orchestration calls `TelegramAdapter.send()` targeting `chat_id` X, not
  any other stored contact point for the resolved Agent

#### Scenario: A LangFlow error does not crash the gateway process
- **WHEN** the LangFlow Run API call fails or returns an unexpected shape
- **THEN** the relay orchestration logs the failure and does not propagate an unhandled
  exception that would crash the long-running gateway process

#### Scenario: A channel-send failure does not crash the gateway process
- **WHEN** `ChannelPort.send()` raises (e.g. the Telegram API rejects delivery because the
  bot was blocked by the user)
- **THEN** the relay orchestration logs the failure and does not propagate an unhandled
  exception — one message's delivery failure must not stop subsequent messages from being
  processed

