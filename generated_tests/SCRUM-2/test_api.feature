Feature: Login API with valid credentials

Background:
  * def baseUrl = java.lang.System.getenv('BASE_URL')
  * def username = java.lang.System.getenv('TEST_USERNAME')
  * def password = java.lang.System.getenv('TEST_PASSWORD')

Scenario: TC-004 Login API with valid credentials
  Given url baseUrl + '/api/login'
  And request { username: '#(username)', password: '#(password)' }
  When method post
  Then status 200
