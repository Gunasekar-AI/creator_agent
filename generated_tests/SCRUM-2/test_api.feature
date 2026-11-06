Feature: Login API with valid credentials

Background:
  * url baseUrl
  * def username = java.lang.System.getenv('TEST_USERNAME')
  * def password = java.lang.System.getenv('TEST_PASSWORD')
  * def loginPayload = { username: username, password: password }

Scenario: TC-004 Login API with valid credentials
  Given path '/api/login'
  And request loginPayload
  When method post
  Then status 200
