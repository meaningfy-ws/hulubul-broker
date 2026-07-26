Feature: Telegram message relay to LangFlow
  As a Sender messaging Hulubul on Telegram
  I want my message routed to the request-intake flow
  So that I can start a delivery request by chatting normally

  Scenario Outline: A first message from a new Telegram channel reaches LangFlow
    Given a Telegram chat with system_id "<system_id>" that has never messaged Hulubul before
    When the sender sends the message "<message_text>"
    Then LangFlow receives session_id "<expected_session_id>"
    And LangFlow receives the channel identity medium "Telegram" and system_id "<system_id>"

    Examples:
      | system_id   | message_text                  | expected_session_id |
      | 111111111   | I need to send a parcel       | Telegram:111111111  |
      | 222222222   | Hi, can you help me ship this | Telegram:222222222  |

  Scenario: A reply from LangFlow is sent back to the originating chat
    Given a Telegram chat with system_id "333333333"
    And LangFlow will reply with "Sure, where is it going?"
    When the sender sends the message "I need to send a parcel"
    Then the sender receives the message "Sure, where is it going?"

  # Trace: langflow-message-relay spec, "A LangFlow error does not crash the gateway process".
  Scenario: The sender gets silence, not a crash, when LangFlow is unreachable
    Given a Telegram chat with system_id "666666666"
    And LangFlow is unreachable
    When the sender sends the message "I need to send a parcel"
    Then the sender receives no message

  # Trace: langflow-message-relay spec, "A channel-send failure does not crash the gateway
  # process" — one Sender's delivery failure must not stop the next Sender being served.
  Scenario: A blocked Sender's delivery failure does not stop the next Sender being served
    Given a Telegram chat with system_id "777777777" and a Telegram chat with system_id "888888888"
    And LangFlow will reply "Sorry you're having trouble" to system_id "777777777"
    And LangFlow will reply "Sure, where is it going?" to system_id "888888888"
    And sending to system_id "777777777" fails because the Sender blocked the bot
    When the sender on system_id "777777777" sends the message "I need to send a parcel"
    And the sender on system_id "888888888" sends the message "I need to send a parcel too"
    Then the sender on system_id "888888888" receives the message "Sure, where is it going?"
