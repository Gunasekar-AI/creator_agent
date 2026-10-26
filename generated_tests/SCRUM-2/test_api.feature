Feature: Login API with valid credentials

  Scenario: Successful login
    # TODO: set the API endpoint URL
    Given url "TODO_API_ENDPOINT_URL"
    And request
    """
    TODO_REQUEST_PAYLOAD_FORMAT
    """
    When method post
    Then status 200
    # TODO: validate response structure and authentication information
    # Example: assert response contains token
    # * match response == { token: '#string' }
