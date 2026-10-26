Feature: Login API with valid credentials

Background:
  # TODO: Set base URL if needed
  * url "TODO_BASE_URL"

Scenario: TC-004 Login API with valid credentials
  Given path "TODO_LOGIN_ENDPOINT"
  And request
    """
    {
      "username": "TODO_VALID_USERNAME",
      "password": "TODO_VALID_PASSWORD"
    }
    """
  When method post
  Then status 200
  # TODO: Validate response contains authentication information
  And match response == { authToken: '#notnull' }