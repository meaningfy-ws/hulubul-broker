Feature: Resume a parcel request intake conversation
  As a Sender
  I want Hulubul to continue my recorded parcel request across interactions
  So that I can complete the request without repeating information or creating another request

  @UC-1 @UC-1-EXT-4a
  @CAP-conversation-request-resumption--human-transparent-session-continuity
  Scenario Outline: Sender answers a focused clarification naturally
    Given the Sender's original request needs clarification about the <missing item>
    And Hulubul has asked for the <missing item>
    When the Sender replies with "<answer>"
    Then the answer is added to the original request
    And the Sender is not asked for a tracking or continuity reference

    Examples:
      | missing item     | answer                       |
      | receiver name    | Ana Popescu                  |
      | pickup location  | Central Market in Chisinau  |
      | destination      | Stefan cel Mare 12, Balti   |
      | parcel contents  | Two boxes of children's books |

  @UC-1 @UC-1-MINIMAL-GUARANTEE @UC-1-EXT-4a
  @CAP-conversation-request-resumption--same-request-across-clarification-turns
  Scenario: Facts supplied over several turns remain on one request
    Given the Sender's first parcel details are recorded as a draft with a request reference
    When the Sender supplies the remaining required details over two more turns
    Then every supplied detail is recorded against the original request reference
    And exactly one request exists for that conversation

  @CAP-conversation-request-resumption--langflow-restart-resumption
  @NFR-REL-001 @NFR-REL-002
  Scenario: Clarification continues after a retained-state service restart
    Given the Sender's request needs clarification
    And Hulubul has asked the Sender for the destination
    When the intake service is restarted while its recorded conversation and request state are retained
    And the Sender replies "Balti" in the same conversation
    Then "Balti" is added to the request recorded before the restart
    And the request keeps its original request reference

  @CAP-conversation-request-resumption--langflow-restart-resumption @NFR-REL-001
  Scenario: Resuming after a retained-state service restart creates no additional request
    Given the Sender's request needs clarification before an intake service restart
    And the recorded conversation and request state are retained during the restart
    When the Sender continues the same conversation after the restart
    Then Hulubul resumes the request recorded before the restart
    And no additional request is created for that conversation

  @CAP-conversation-request-resumption--unique-session-binding
  @CAP-conversation-request-resumption--atomic-request-and-binding-creation
  @NFR-DAT-004 @NFR-CON-001
  Scenario: Concurrent first interactions register one request without an extra draft
    Given no parcel request is recorded for the Sender's conversation
    When two first parcel intentions from that conversation are handled at the same time
    Then exactly one request is registered for the conversation
    And the registered request has a request reference
    And no additional draft remains

  @CAP-conversation-request-resumption--optimistic-concurrency-for-mutations
  @NFR-DAT-005
  Scenario Outline: A concurrent clarification loser does not overwrite the accepted answer
    Given the original request needs clarification about the <missing item>
    And two replies are based on the same earlier request state
    When "<first answer>" and "<second answer>" are handled at the same time
    Then at most one reply changes the original request
    And the other reply does not overwrite the accepted answer
    And Hulubul reports that the request changed before the other reply could be applied
    And no additional request is created

    Examples:
      | missing item    | first answer                 | second answer                    |
      | destination     | Balti                        | Orhei                            |
      | pickup location | Central Market in Chisinau  | Chisinau railway station         |

  @CAP-domain-state-routing--change-1-no-mutation-routing-results @NFR-CTL-001
  Scenario: A completed intake remains unchanged
    Given the Sender's request has completed intake
    When another message arrives in the same conversation
    Then Hulubul reports that intake is already complete
    And the completed request remains unchanged
    And no post-intake coordination is started

  @CAP-domain-state-routing--inconsistent-context-fails-closed
  @NFR-CON-001 @NFR-CON-002
  Scenario Outline: Inconsistent continuity fails closed without changing a request
    Given the recorded conversation cannot be resumed consistently because <condition>
    When the Sender sends another message in that conversation
    Then Hulubul reports that the request cannot be resumed safely
    And Hulubul does not guess which request to continue
    And no request is created or changed

    Examples:
      | condition                                             |
      | no current request can be found                       |
      | more than one current request is associated with it   |
      | more than one continuity record exists                |
      | the request state is not recognized                   |
      | the recorded continuity details contradict each other |
