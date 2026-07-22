Feature: Register a parcel delivery request
  As a Sender
  I want to describe a parcel delivery once and add missing details over time
  So that Hulubul records one truthful request with as little repetition as possible

  # Trace: UC-1 Main Success Scenario, steps 1-5.
  @UC-1 @UC-1-MSS
  Scenario Outline: Complete a request from one message with or without a preferred period
    Given <sender> is known through a trusted identity
    When the Sender's first message is "<request message>"
    Then exactly one delivery request is recorded
    And the request is Complete
    And the Sender receives its confirmed request identifier
    And no clarification question is asked
    And the preferred period is recorded as <recorded preferred period>

    Examples:
      | sender        | request message                                                                                                                                            | recorded preferred period    |
      | Mara Ionescu  | Please send a box of children's books from 14 Oak Street, Bristol to Alex Morgan at 8 King Road, Bath.                                                    | not supplied                 |
      | Daniel Popa   | Please send two winter coats from 25 Lake Avenue, Cardiff to Elena Marin at 17 Hill Lane, Swansea, preferably between 12 and 14 August 2026.               | 12 to 14 August 2026         |

  # Trace: UC-1 Extension 4a and its minimal guarantee.
  @UC-1 @UC-1-MINIMAL-GUARANTEE @UC-1-EXT-4a
  Scenario Outline: Record a truthful sparse draft from an incomplete first message
    Given <sender> is known through a trusted identity
    When the Sender's first message is "<request message>"
    Then exactly one draft request is recorded with a request identifier
    And the request Needs clarification
    And only <available facts> are recorded on the request
    And no missing Receiver, parcel contents, pickup location, or drop-off location is invented

    Examples:
      | sender        | request message                                                               | available facts                                                        |
      | Mara Ionescu  | Please collect three boxes of books from 14 Oak Street, Bristol.              | pickup at 14 Oak Street, Bristol and three boxes of books              |
      | Daniel Popa   | I want to send a parcel.                                                      | none of the Receiver, parcel contents, pickup, or drop-off facts       |

  # Trace: UC-1 Main Success Scenario step 2 and truthful sparse draft creation;
  # this does not implement UC-13.
  @UC-1 @UC-1-MSS @CAP-delivery-request-intake--truthful-sparse-draft-creation
  Scenario: Create only the intake identity needed for a first-time trusted Sender
    Given a first-time Sender is known through a trusted simulated identity
    When the Sender's first message is "I want to send a parcel."
    Then exactly one draft request is recorded with a request identifier
    And one enduring Sender identity is recorded for that request
    And no broader party profile or profile-maintenance process is created

  # Trace: UC-1 Extension 4a.
  @UC-1 @UC-1-EXT-4a
  Scenario Outline: Report every missing fact while asking one focused question
    Given <sender> is known through a trusted identity
    When the Sender's first message is "<request message>"
    Then the complete missing set is <missing facts>
    And exactly one clarification question is asked
    And that question asks for <clarification fact>

    Examples:
      | sender        | request message                                                  | missing facts                                             | clarification fact |
      | Mara Ionescu  | Send three books from 14 Oak Street, Bristol to 8 King Road, Bath. | Receiver identity                                         | Receiver identity  |
      | Daniel Popa   | I need to send something from 25 Lake Avenue, Cardiff.             | Receiver identity, drop-off location, and parcel contents | Receiver identity  |

  # Trace: Delivery intake validation and place-boundary capabilities;
  # not a UC-1 behavior branch.
  @CAP-delivery-request-intake--phase-1-intake-profile
  @CAP-delivery-request-intake--immediate-fact-validation
  @CAP-delivery-request-intake--free-text-place-boundary
  Scenario Outline: Reject text outside the 1-to-4,000 character boundary during the same interaction
    Given a trusted Sender has a delivery request in progress
    When the Sender supplies <supplied text> as the <fact>
    Then the <fact> is rejected during that interaction
    And the supplied text is not retained as a valid fact
    And the response identifies the <fact> for correction before pursuing another missing fact

    Examples:
      | supplied text                                                   | fact                    |
      | surrounding spaces that leave 0 characters                     | drop-off location       |
      | a Receiver name containing 4,001 characters                    | Receiver name           |
      | a pickup description containing 4,001 characters               | pickup location         |
      | a drop-off description containing 4,001 characters             | drop-off location       |
      | a parcel-content description containing 4,001 characters       | parcel contents         |
      | a preferred-period description containing 4,001 characters     | preferred period        |

  # Trace: UC-1 Extension 4a, resuming at completeness check step 4.
  @UC-1 @UC-1-EXT-4a
  Scenario: Accumulate valid facts over several turns on the same request
    Given Mara Ionescu is known through a trusted identity
    And her first message is "Please collect a parcel at 14 Oak Street, Bristol."
    And Hulubul records a draft request and gives her its request identifier
    When she next says "Deliver it to 8 King Road, Bath."
    And then says "It contains three children's books."
    And then says "The Receiver is Alex Morgan."
    Then each valid fact is retained after the turn in which it was supplied
    And every turn refers to the original request identifier
    And no already valid fact has to be repeated
    And the request becomes Complete after Alex Morgan is supplied

  # Trace: Delivery intake domain graph mapping; not a UC-1 behavior branch.
  @CAP-delivery-request-intake--domain-graph-mapping
  Scenario Outline: Keep same-name Receivers distinct when no shared stable identity is supplied
    Given <first sender> and <second sender> each start a separate delivery request
    When both Senders name <receiver name> as their Receiver without a shared stable identity
    Then each request records a distinct Receiver identity scoped to that request
    And neither Receiver is reused solely because the names match

    Examples:
      | first sender   | second sender  | receiver name  |
      | Mara Ionescu   | Daniel Popa    | Alex Morgan    |
      | Sofia Marin    | Victor Radu    | Sam Lee        |

  # Trace: UC-1 Extension 1a.
  @UC-1 @UC-1-EXT-1a
  Scenario Outline: Reuse a returning Sender deterministically across separate requests
    Given <sender> is known through the same trusted identity in separate conversations
    When the Sender registers "<first request>"
    And later registers "<second request>" in another conversation
    Then two distinct delivery request identifiers are recorded
    And both requests belong to the same enduring Sender identity
    And each later use of that trusted identity selects that same Sender

    Examples:
      | sender        | first request                                                                                                      | second request                                                                                                     |
      | Mara Ionescu  | Send books from 14 Oak Street, Bristol to Alex Morgan at 8 King Road, Bath.                                        | Send a lamp from 14 Oak Street, Bristol to Sofia Marin at 5 River Walk, Exeter.                                    |
      | Daniel Popa   | Send two coats from 25 Lake Avenue, Cardiff to Elena Marin at 17 Hill Lane, Swansea.                               | Send a bicycle helmet from 25 Lake Avenue, Cardiff to Victor Radu at 3 Market Square, Newport.                     |
