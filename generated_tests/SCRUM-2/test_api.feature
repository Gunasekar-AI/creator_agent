Feature: Login API with valid credentials

Background:
  * def baseUrl = java.lang.System.getenv('BASE_URL') != null ? java.lang.System.getenv('BASE_URL') : 'http://127.0.0.1:8001'
  * def username = java.lang.System.getenv('TEST_USERNAME')
  * def password = java.lang.System.getenv('TEST_PASSWORD')
  * def loginEndpoint = '/api/login'

Scenario: TC-004 Login API with valid credentials
  Given url baseUrl + loginEndpoint
  And request { username: '#(username)', password: '#(password)' }
  When method post
  Then status 200
  # Expected authentication information fields are not specified in the requirements
