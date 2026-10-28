Feature: Login API with valid credentials

Scenario: Successful login with valid credentials
    Given url 'http://127.0.0.1:8001/api/login'
    And request { username: 'testuser', password: 'Password123' }
    When method post
    Then status 200
    And match response.success == true
    And match response.message == 'Login successful'
    And match response.username == 'testuser'
