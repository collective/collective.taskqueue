*** Settings ***

Resource  plone/app/robotframework/selenium.robot
Resource  plone/app/robotframework/keywords.robot

Library  Remote  ${PLONE_URL}/RobotRemote

Test Setup  Open test browser
Test Teardown  Close all browsers


*** Test Cases ***

Scenario: As an manager I can queue publication of a document
    Given a site owner
      and a new document
     When I queue publication of the document
     Then a visitor can view the document


*** Keywords ***

# Given

A site owner
  Log in  ${SITE_OWNER_NAME}  ${SITE_OWNER_PASSWORD}

A new document
  Enable autologin as  Manager
  Set autologin username  ${SITE_OWNER_NAME}
  Create content  type=Document
  ...  id=a-document  title=A New Document
  Disable autologin

# When

I queue publication of the document
  Go to  ${PLONE_URL}/queue-task-form
  Page should contain element  form-widgets-url
  Input text  form-widgets-url
  ...  ${PLONE_SITE_ID}/a-document/content_status_modify?workflow_action=publish
  Click button  Queue
  Page should contain  Queued a new request

# Then

A visitor can view the document
  Log out
  Go to  ${PLONE_URL}/a-document
  Page should contain  A New Document
