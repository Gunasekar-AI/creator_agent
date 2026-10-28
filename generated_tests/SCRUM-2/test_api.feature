Feature: Login API with valid credentials

Background:
    * url "http://127.0.0.1:8001/api/login"
    * configure method = 'post'
    * def validPayload =
    """
    {
        "username": "testuser",
        "password": "Password123"
    }
    """

Scenario: TC-004 Login API with valid credentials
    Given request validPayload
    When method post
    Then status 200
    And match response.success == true
    And match response.message == 'Login successful'
    And match response.username == 'testuser'
