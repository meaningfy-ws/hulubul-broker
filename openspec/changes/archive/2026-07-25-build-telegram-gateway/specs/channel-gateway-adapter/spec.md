## ADDED Requirements

### Requirement: ChannelPort interface
The system SHALL define a `ChannelPort` interface with a `receive()` operation returning an
`InboundMessage` and a `send()` operation accepting a `TextMessage` or `MediaMessage`, that
every channel adapter MUST implement, so the gateway core and LangFlow-relay logic never
depend on a specific channel's SDK or wire format.

#### Scenario: A new adapter can be added without changing the gateway core
- **WHEN** a new class implements `ChannelPort`'s `receive()` and `send()` operations
- **THEN** the gateway's relay/orchestration logic accepts it without any code change to
  `services/relay_message.py` or the `langflow-message-relay` capability

### Requirement: Telegram inbound message reception
The `TelegramAdapter` SHALL receive inbound Telegram messages via aiogram, in either polling
mode or webhook mode selected by the `GATEWAY_MODE` configuration value, and SHALL normalize
each inbound update into an `InboundMessage` value object before it leaves the adapter layer.

#### Scenario: Polling mode receives a text message
- **WHEN** `GATEWAY_MODE=polling` and a user sends a text message to the configured Telegram
  bot
- **THEN** the adapter produces an `InboundMessage` carrying the message text, the sender's
  `chat_id`, and the medium `Telegram`, with no raw Telegram/aiogram objects leaking past the
  adapter boundary

#### Scenario: Webhook mode receives a text message
- **WHEN** `GATEWAY_MODE=webhook` and Telegram POSTs an update to the registered webhook URL
  with a valid `secret_token`
- **THEN** the adapter produces the same `InboundMessage` shape as polling mode for equivalent
  input, and rejects the request if the `secret_token` does not match configuration

### Requirement: Telegram outbound message sending
The `TelegramAdapter` SHALL send a `TextMessage` back to Telegram via an explicit
`sendMessage` API call, since Telegram does not treat a webhook's HTTP response body as the
bot's reply.

#### Scenario: A relayed reply is delivered as an explicit sendMessage call
- **WHEN** the relay orchestration calls `TelegramAdapter.send()` with a `TextMessage` and the
  `chat_id` the originating `InboundMessage` arrived on
- **THEN** the adapter issues a `POST` to Telegram's `sendMessage` endpoint for that `chat_id`,
  independent of whether the inbound message was received via polling or webhook

### Requirement: WhatsApp adapter stub proves interface fit without live integration
The system SHALL provide a `WhatsAppAdapter` class that implements `ChannelPort` and whose
`receive()`/`send()` bodies raise `NotImplementedError`, structured so its method signatures
and any WhatsApp-shaped value objects it references reflect 360dialog's real payload shape,
without performing any live WhatsApp API call.

#### Scenario: The stub type-checks against the shared interface
- **WHEN** `WhatsAppAdapter` is instantiated and assigned to a variable typed as `ChannelPort`
- **THEN** static type checking (mypy) passes, confirming the interface generalizes to a
  second channel without gateway-core changes

#### Scenario: Calling the stub fails loudly, not silently
- **WHEN** `WhatsAppAdapter.receive()` or `.send()` is invoked
- **THEN** it raises `NotImplementedError`, so accidental use in the gateway's channel
  selection logic fails immediately rather than silently no-op-ing
