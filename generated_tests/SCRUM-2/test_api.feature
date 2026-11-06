Feature: Login API with valid credentials

Background:
  * def baseUrl = karate.properties['BASE_URL']
  * def username = karate.properties['TEST_USERNAME']
  * def password = karate.properties['TEST_PASSWORD']

Scenario: TC-004 Login API with valid credentials
  Given url baseUrl + '/api/login'
  And request { username: '#(username)', password: '#(password)' }
  When method post
  Then status 200
