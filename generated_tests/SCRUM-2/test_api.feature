Feature: Login API with valid credentials

  Scenario: Successful login
    Given url 'TODO_API_ENDPOINT'
    And request { username: 'TODO_VALID_USERNAME', password: 'TODO_VALID_PASSWORD' }
    When method post
    Then status 200
    # TODO: add response schema validation
    And match response == { TODO_RESPONSE_FIELDS }
