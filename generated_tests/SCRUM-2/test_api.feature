Feature: Login API with valid credentials

Scenario: Login with valid credentials
    Given url 'TODO_ENDPOINT_URL'
    And request { TODO_REQUEST_BODY }
    When method TODO_HTTP_METHOD
    Then status 200
    # TODO: Add response schema validation

