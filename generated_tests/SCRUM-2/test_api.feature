Feature: Login API with valid credentials

Background:
    * def username = karate.properties['test.username']
    * def password = karate.properties['test.password']
    * url 'http://127.0.0.1:8001/api/login'

Scenario: Successful login
    Given request { username: '#(username)', password: '#(password)' }
    When method post
    Then status 200
    And match response.success == true
    And match response.message == 'Login successful'
    And match response.username == username
