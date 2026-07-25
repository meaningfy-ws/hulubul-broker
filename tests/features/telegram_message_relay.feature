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
