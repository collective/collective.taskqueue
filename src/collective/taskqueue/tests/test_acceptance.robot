*** Settings ***

Resource  plone/app/robotframework/selenium.robot
Resource  plone/app/robotframework/keywords.robot

Library  Remote  ${PLONE_URL}/RobotRemote

Test Setup  Open test browser
Test Teardown  Close all browsers


*** Test Cases ***

Scenario: As a manager I can queue publication of a document
    Given a site owner
      and a new document
     When I queue publication of the document
     Then a visitor can view the document

Scenario: As a manager I cannot see view registered for the task layer
    Given a site owner
     When I open a view registered for the task layer
     Then I see page not found error

Scenario: As a manager I can queue an email to be sent
    Given a site owner
      and an email queuing form
     When I queue a new email
     Then my email is being sent

Scenario: As a manager I can queue 1000 emails to be sent
    Given a site owner
      and an email queuing form
     When I queue 1000 new emails
     Then exactly 1000 emails are being sent

*** Keywords ***

# Given

A site owner
  Log in  ${SITE_OWNER_NAME}  ${SITE_OWNER_PASSWORD}
  Page should contain  You are now logged in

A new document
  Enable autologin as  Manager
  Set autologin username  ${SITE_OWNER_NAME}
  Create content  type=Document
  ...  id=a-document  title=A New Document
  Disable autologin

An email queuing form
  Go to  ${PLONE_URL}/queue-task-email-form
  Page should contain element  form-widgets-message
  Page should contain element  form-widgets-amount

# When

I queue publication of the document
  Go to  ${PLONE_URL}/queue-task-form
  Page should contain element  form-widgets-url
  Input text  form-widgets-url
  ...  ${PLONE_SITE_ID}/a-document/content_status_modify?workflow_action=publish
  Click button  Queue
  Page should contain  Queued a new request
  Go to  ${PLONE_URL}/a-document

I open a view registered for the task layer
  Go to  ${PLONE_URL}/send-email-view

I queue a new email
  Page should contain element  form-widgets-message
  Page should contain element  form-widgets-amount
  Input text  form-widgets-message  This is my message
  Input text  form-widgets-amount  1
  Click button  Queue
  Page should contain  Queued 1 new email(s)

I queue 1000 new emails
  Page should contain element  form-widgets-message
  Page should contain element  form-widgets-amount
  Input text  form-widgets-message  This is my message
  Input text  form-widgets-amount  1000
  Click button  Queue
  Page should contain  Queued 1000 new email(s)

# Then

A visitor can view the document
  Log out
  Go to  ${PLONE_URL}/a-document
  Page should contain  A New Document

I see page not found error
  Page should contain  This page does not seem to exist

My email is being sent
  ${message} =  Get the last sent email
  ${amount} =  Get the total amount of sent emails
  Should contain  ${message}  This is my message
  Should be equal  '${amount}'  '1'

Exactly 1000 emails are being sent
  Wait until keyword succeeds  1 min  5 sec  '1000' emails should have been sent

'${n}' emails should have been sent
  ${amount} =  Get the total amount of sent emails
  Should be equal  '${amount}'  '${n}'
