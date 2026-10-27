Feature: Login API with valid credentials

Scenario: Login with valid credentials
    Given url "TODO_API_ENDPOINT_URL"
    And request { TODO_REQUEST_PAYLOAD_FORMAT }
    When method post
    Then status 200
    # TODO: verify authentication information fields in response
