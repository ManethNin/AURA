import pytest
from pathlib import Path
import tempfile
import os

from masterthesis.agent.aider.AdvancedDiffAgent import UnifiedDiffCoder


@pytest.fixture
def temp_repo():
    with tempfile.TemporaryDirectory() as tmpdirname:
        yield tmpdirname


@pytest.fixture
def temp_file(temp_repo):
    file_path = Path(temp_repo) / "test_file.py"
    with open(file_path, "w", encoding="utf-8") as f:
        f.write("line1\nline2\nline3\n")
    return str(file_path)


def test_abs_root_path(temp_repo):
    coder = UnifiedDiffCoder(repo_dir=temp_repo)
    relative_path = "test_file.py"
    expected_path = str(Path(temp_repo).resolve() / relative_path)
    assert coder.abs_root_path(relative_path) == expected_path


def test_get_edits():
    diff_content = """```diff
--- a/test_file.py
+++ b/test_file.py
@@ -1,3 +1,3 @@
-line1
+line1_modified
 line2
 line3
```
"""
    coder = UnifiedDiffCoder(repo_dir="")
    edits = coder.get_edits(diff_content)
    assert len(edits) == 1
    assert edits[0][0] == "test_file.py"
    assert edits[0][1] == [
        "-line1\n",
        "+line1_modified\n",
        " line2\n",
        " line3\n",
    ]


def test_get_edits_java():
    diff = """```diff
--- a/src/main/java/com/feedzai/commons/sql/abstraction/engine/impl/mysql/MySqlQueryExceptionHandler.java
+++ b/src/main/java/com/feedzai/commons/sql/abstraction/engine/impl/mysql/MySqlQueryExceptionHandler.java
@@ -18,7 +18,7 @@ package com.feedzai.commons.sql.abstraction.engine.impl.mysql;

 import com.feedzai.commons.sql.abstraction.engine.handler.QueryExceptionHandler;

-import com.mysql.jdbc.exceptions.MySQLTimeoutException;
+import com.mysql.cj.jdbc.exceptions.MySQLTimeoutException;

 import java.sql.SQLException;
```
"""

    coder = UnifiedDiffCoder(repo_dir="")
    edits = coder.get_paths(diff)
    print(edits)
    assert len(edits) == 1
    assert (
        "src/main/java/com/feedzai/commons/sql/abstraction/engine/impl/mysql/MySqlQueryExceptionHandler.java"
        in edits
    )


import shutil


def test_get_paths_v2():
    def _assert_file(diff, path):
        with tempfile.TemporaryDirectory() as tmpdirname:
            file_path = Path(tmpdirname) / path
            os.makedirs(file_path.parent, exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(
                    'package uk.gov.pay.adminusers.queue.event;\n\nimport ch.qos.logback.classic.Level;\nimport ch.qos.logback.classic.Logger;\nimport ch.qos.logback.classic.spi.ILoggingEvent;\nimport ch.qos.logback.core.Appender;\nimport com.fasterxml.jackson.databind.ObjectMapper;\nimport com.google.gson.GsonBuilder;\nimport org.hamcrest.core.Is;\nimport org.junit.jupiter.api.BeforeEach;\nimport org.junit.jupiter.api.Test;\nimport org.junit.jupiter.api.extension.ExtendWith;\nimport org.mockito.ArgumentCaptor;\nimport org.mockito.Captor;\nimport org.mockito.Mock;\nimport org.mockito.junit.jupiter.MockitoExtension;\nimport org.slf4j.LoggerFactory;\nimport uk.gov.pay.adminusers.client.ledger.model.LedgerTransaction;\nimport uk.gov.pay.adminusers.client.ledger.service.LedgerService;\nimport uk.gov.pay.adminusers.model.MerchantDetails;\nimport uk.gov.pay.adminusers.model.Service;\nimport uk.gov.pay.adminusers.model.ServiceName;\nimport uk.gov.pay.adminusers.persistence.entity.UserEntity;\nimport uk.gov.pay.adminusers.queue.model.Event;\nimport uk.gov.pay.adminusers.queue.model.EventMessage;\nimport uk.gov.pay.adminusers.queue.model.EventType;\nimport uk.gov.pay.adminusers.service.NotificationService;\nimport uk.gov.pay.adminusers.service.ServiceFinder;\nimport uk.gov.pay.adminusers.service.UserServices;\nimport uk.gov.service.payments.commons.queue.exception.QueueException;\nimport uk.gov.service.payments.commons.queue.model.QueueMessage;\n\nimport java.time.Instant;\nimport java.util.Arrays;\nimport java.util.Collections;\nimport java.util.List;\nimport java.util.Map;\nimport java.util.Optional;\nimport java.util.Set;\n\nimport static org.hamcrest.MatcherAssert.assertThat;\nimport static org.hamcrest.Matchers.hasItems;\nimport static org.hamcrest.Matchers.is;\nimport static org.hamcrest.Matchers.nullValue;\nimport static org.mockito.ArgumentMatchers.anyMap;\nimport static org.mockito.ArgumentMatchers.anySet;\nimport static org.mockito.Mockito.atMostOnce;\nimport static org.mockito.Mockito.mock;\nimport static org.mockito.Mockito.never;\nimport static org.mockito.Mockito.times;\nimport static org.mockito.Mockito.verify;\nimport static org.mockito.Mockito.when;\nimport static uk.gov.pay.adminusers.app.util.RandomIdGenerator.randomInt;\nimport static uk.gov.pay.adminusers.app.util.RandomIdGenerator.randomUuid;\nimport static uk.gov.pay.adminusers.fixtures.EventFixture.anEventFixture;\nimport static uk.gov.pay.adminusers.fixtures.LedgerTransactionFixture.aLedgerTransactionFixture;\nimport static uk.gov.pay.adminusers.model.Service.DEFAULT_NAME_VALUE;\nimport static uk.gov.pay.adminusers.service.UserServicesTest.aUserEntityWithRoleForService;\n\n@ExtendWith(MockitoExtension.class)\nclass EventMessageHandlerTest {\n\n    @Mock\n    private EventSubscriberQueue mockEventSubscriberQueue;\n\n    @Mock\n    private NotificationService mockNotificationService;\n\n    @Mock\n    private ServiceFinder mockServiceFinder;\n\n    @Mock\n    private UserServices mockUserServices;\n\n    @Mock\n    private LedgerService mockLedgerService;\n\n    @Captor\n    ArgumentCaptor<Set<String>> adminEmailsCaptor;\n\n    @Captor\n    ArgumentCaptor<Map<String, String>> personalisationCaptor;\n    @Mock\n    private Appender<ILoggingEvent> mockLogAppender;\n    @Captor\n    ArgumentCaptor<ILoggingEvent> loggingEventArgumentCaptor;\n\n    private final ObjectMapper objectMapper = new ObjectMapper();\n    private final String gatewayAccountId = "123";\n\n    private EventMessageHandler eventMessageHandler;\n    private Service service;\n    private LedgerTransaction transaction;\n    private List<UserEntity> users;\n    private Event disputeEvent;\n\n    @BeforeEach\n    void setUp() {\n        eventMessageHandler = new EventMessageHandler(mockEventSubscriberQueue, mockLedgerService, mockNotificationService, mockServiceFinder, mockUserServices, objectMapper);\n        service = Service.from(randomInt(), randomUuid(), new ServiceName(DEFAULT_NAME_VALUE));\n        service.setMerchantDetails(new MerchantDetails("Organisation Name", null, null, null, null, null, null, null, null));\n        transaction = aLedgerTransactionFixture()\n                .withTransactionId("456")\n                .withReference("tx ref")\n                .build();\n        users = Arrays.asList(\n                aUserEntityWithRoleForService(service, true, "admin1"),\n                aUserEntityWithRoleForService(service, true, "admin2")\n        );\n\n        Logger logger = (Logger) LoggerFactory.getLogger(EventMessageHandler.class);\n        logger.setLevel(Level.INFO);\n        logger.addAppender(mockLogAppender);\n    }\n\n    @Test\n    void shouldMarkMessageAsProcessed() throws Exception {\n        disputeEvent = anEventFixture()\n                .withEventType(EventType.DISPUTE_CREATED.name())\n                .withEventDetails(objectMapper.valueToTree(Map.of("amount", 21000L, "evidence_due_date", "2022-03-07T13:00:00.001Z", "gateway_account_id", gatewayAccountId)))\n                .withParentResourceExternalId("456")\n                .build();\n        when(mockServiceFinder.byGatewayAccountId(gatewayAccountId)).thenReturn(Optional.of(service));\n        when(mockLedgerService.getTransaction(transaction.getTransactionId())).thenReturn(Optional.of(transaction));\n        when(mockUserServices.getAdminUsersForService(service.getId())).thenReturn(users);\n\n        var mockQueueMessage = mock(QueueMessage.class);\n        var eventMessage = EventMessage.of(disputeEvent, mockQueueMessage);\n        when(mockEventSubscriberQueue.retrieveEvents()).thenReturn(List.of(eventMessage));\n\n        eventMessageHandler.processMessages();\n\n        verify(mockEventSubscriberQueue).markMessageAsProcessed(mockQueueMessage);\n    }\n\n    @Test\n    void shouldHandleDisputeCreatedEvent() throws QueueException {\n        var mockQueueMessage = mock(QueueMessage.class);\n        disputeEvent = anEventFixture()\n                .withEventType(EventType.DISPUTE_CREATED.name())\n                .withEventDetails(objectMapper.valueToTree(Map.of("amount", 21000L, "evidence_due_date", "2022-03-07T13:00:00.001Z", "gateway_account_id", gatewayAccountId, "reason", "fraudulent")))\n                .withParentResourceExternalId("456")\n                .build();\n        var eventMessage = EventMessage.of(disputeEvent, mockQueueMessage);\n        when(mockQueueMessage.getMessageId()).thenReturn("queue-message-id");\n        when(mockEventSubscriberQueue.retrieveEvents()).thenReturn(List.of(eventMessage));\n\n        when(mockServiceFinder.byGatewayAccountId(gatewayAccountId)).thenReturn(Optional.of(service));\n        when(mockLedgerService.getTransaction(transaction.getTransactionId())).thenReturn(Optional.of(transaction));\n        when(mockUserServices.getAdminUsersForService(service.getId())).thenReturn(users);\n\n        eventMessageHandler.processMessages();\n\n        verify(mockNotificationService, atMostOnce()).sendStripeDisputeCreatedEmail(adminEmailsCaptor.capture(), personalisationCaptor.capture());\n\n        var emails = adminEmailsCaptor.getValue();\n        var personalisation = personalisationCaptor.getValue();\n\n        assertThat(emails.size(), is(2));\n        assertThat(emails, hasItems("admin1@service.gov.uk", "admin2@service.gov.uk"));\n        assertThat(personalisation.get("serviceName"), is(service.getName()));\n        assertThat(personalisation.get("paymentExternalId"), is("456"));\n        assertThat(personalisation.get("serviceReference"), is("tx ref"));\n        assertThat(personalisation.get("sendEvidenceToPayDueDate"), is("4 March 2022"));\n        assertThat(personalisation.get("disputedAmount"), is("210.00"));\n\n        assertThat(personalisation.get("fraudulent"), is("yes"));\n        assertThat(personalisation.get("duplicate"), is("no"));\n        assertThat(personalisation.get("credit_not_processed"), is("no"));\n        assertThat(personalisation.get("product_not_received"), is("no"));\n        assertThat(personalisation.get("product_unacceptable"), is("no"));\n        assertThat(personalisation.get("subscription_canceled"), is("no"));\n        assertThat(personalisation.get("unrecognized"), is("no"));\n        assertThat(personalisation.get("paymentAmount"), is(nullValue()));\n        assertThat(personalisation.get("disputeEvidenceDueDate"), is(nullValue()));\n\n        verify(mockLogAppender, times(2)).doAppend(loggingEventArgumentCaptor.capture());\n\n        List<ILoggingEvent> logStatement = loggingEventArgumentCaptor.getAllValues();\n        assertThat(logStatement.get(0).getFormattedMessage(), Is.is("Retrieved event queue message with id [queue-message-id] for resource external id [a-resource-external-id]"));\n        assertThat(logStatement.get(1).getFormattedMessage(), Is.is("Processed notification email for disputed transaction"));\n    }\n\n    @Test\n    void shouldHandleDisputeLostEvent() throws QueueException {\n        var mockQueueMessage = mock(QueueMessage.class);\n        disputeEvent = anEventFixture()\n                .withEventType(EventType.DISPUTE_LOST.name())\n                .withEventDetails(objectMapper.valueToTree(Map.of("net_amount", -4000L, "fee", 1500L, "amount", 2500L, "gateway_account_id", gatewayAccountId)))\n                .withParentResourceExternalId("456")\n                .withServiceId(service.getExternalId())\n                .withLive(true)\n                .build();\n        var eventMessage = EventMessage.of(disputeEvent, mockQueueMessage);\n        when(mockQueueMessage.getMessageId()).thenReturn("queue-message-id");\n        when(mockEventSubscriberQueue.retrieveEvents()).thenReturn(List.of(eventMessage));\n        when(mockServiceFinder.byGatewayAccountId(gatewayAccountId)).thenReturn(Optional.of(service));\n        when(mockLedgerService.getTransaction(transaction.getTransactionId())).thenReturn(Optional.of(transaction));\n        when(mockUserServices.getAdminUsersForService(service.getId())).thenReturn(users);\n\n        eventMessageHandler.processMessages();\n\n        verify(mockNotificationService, atMostOnce()).sendStripeDisputeLostEmail(adminEmailsCaptor.capture(), personalisationCaptor.capture());\n\n        var emails = adminEmailsCaptor.getValue();\n        var personalisation = personalisationCaptor.getValue();\n\n        assertThat(emails.size(), is(2));\n        assertThat(emails, hasItems("admin1@service.gov.uk", "admin2@service.gov.uk"));\n        assertThat(personalisation.get("serviceName"), is(service.getName()));\n        assertThat(personalisation.get("serviceReference"), is("tx ref"));\n        assertThat(personalisation.get("organisationName"), is(service.getMerchantDetails().getName()));\n\n        verify(mockLogAppender, times(2)).doAppend(loggingEventArgumentCaptor.capture());\n\n        List<ILoggingEvent> logStatement = loggingEventArgumentCaptor.getAllValues();\n        assertThat(logStatement.get(0).getFormattedMessage(), Is.is("Retrieved event queue message with id [queue-message-id] for resource external id [a-resource-external-id]"));\n        assertThat(logStatement.get(1).getFormattedMessage(), Is.is("Processed notification email for disputed transaction"));\n    }\n\n    @Test\n    void shouldHandleDisputeWonEvent() throws QueueException {\n        var mockQueueMessage = mock(QueueMessage.class);\n        disputeEvent = anEventFixture()\n                .withEventType(EventType.DISPUTE_WON.name())\n                .withEventDetails(objectMapper.valueToTree(Map.of("gateway_account_id", gatewayAccountId)))\n                .withParentResourceExternalId("456")\n                .withServiceId(service.getExternalId())\n                .withLive(true)\n                .build();\n        var eventMessage = EventMessage.of(disputeEvent, mockQueueMessage);\n        when(mockQueueMessage.getMessageId()).thenReturn("queue-message-id");\n        when(mockEventSubscriberQueue.retrieveEvents()).thenReturn(List.of(eventMessage));\n        when(mockServiceFinder.byGatewayAccountId(gatewayAccountId)).thenReturn(Optional.of(service));\n        when(mockLedgerService.getTransaction(transaction.getTransactionId())).thenReturn(Optional.of(transaction));\n        when(mockUserServices.getAdminUsersForService(service.getId())).thenReturn(users);\n\n        eventMessageHandler.processMessages();\n\n        verify(mockNotificationService, atMostOnce()).sendStripeDisputeWonEmail(adminEmailsCaptor.capture(), personalisationCaptor.capture());\n\n        var emails = adminEmailsCaptor.getValue();\n        var personalisation = personalisationCaptor.getValue();\n\n        assertThat(emails.size(), is(2));\n        assertThat(emails, hasItems("admin1@service.gov.uk", "admin2@service.gov.uk"));\n        assertThat(personalisation.get("serviceName"), is(service.getName()));\n        assertThat(personalisation.get("serviceReference"), is("tx ref"));\n        assertThat(personalisation.get("organisationName"), is(service.getMerchantDetails().getName()));\n\n        verify(mockLogAppender, times(2)).doAppend(loggingEventArgumentCaptor.capture());\n\n        List<ILoggingEvent> logStatement = loggingEventArgumentCaptor.getAllValues();\n        assertThat(logStatement.get(0).getFormattedMessage(), Is.is("Retrieved event queue message with id [queue-message-id] for resource external id [a-resource-external-id]"));\n        assertThat(logStatement.get(1).getFormattedMessage(), Is.is("Processed notification email for disputed transaction"));\n    }\n\n    @Test\n    void shouldHandleDisputeEvidenceSubmittedEvent() throws QueueException {\n        var mockQueueMessage = mock(QueueMessage.class);\n        disputeEvent = anEventFixture()\n                .withEventType(EventType.DISPUTE_EVIDENCE_SUBMITTED.name())\n                .withEventDetails(objectMapper.valueToTree(Map.of("gateway_account_id", gatewayAccountId)))\n                .withParentResourceExternalId("456")\n                .withServiceId(service.getExternalId())\n                .withLive(true)\n                .build();\n        var eventMessage = EventMessage.of(disputeEvent, mockQueueMessage);\n        when(mockQueueMessage.getMessageId()).thenReturn("queue-message-id");\n        when(mockEventSubscriberQueue.retrieveEvents()).thenReturn(List.of(eventMessage));\n        when(mockServiceFinder.byGatewayAccountId(gatewayAccountId)).thenReturn(Optional.of(service));\n        when(mockLedgerService.getTransaction(transaction.getTransactionId())).thenReturn(Optional.of(transaction));\n        when(mockUserServices.getAdminUsersForService(service.getId())).thenReturn(users);\n\n        eventMessageHandler.processMessages();\n\n        verify(mockNotificationService, atMostOnce()).sendStripeDisputeEvidenceSubmittedEmail(adminEmailsCaptor.capture(), personalisationCaptor.capture());\n\n        var emails = adminEmailsCaptor.getValue();\n        var personalisation = personalisationCaptor.getValue();\n\n        assertThat(emails.size(), is(2));\n        assertThat(emails, hasItems("admin1@service.gov.uk", "admin2@service.gov.uk"));\n        assertThat(personalisation.get("serviceName"), is(service.getName()));\n        assertThat(personalisation.get("serviceReference"), is("tx ref"));\n        assertThat(personalisation.get("organisationName"), is(service.getMerchantDetails().getName()));\n\n        verify(mockLogAppender, times(2)).doAppend(loggingEventArgumentCaptor.capture());\n\n        List<ILoggingEvent> logStatement = loggingEventArgumentCaptor.getAllValues();\n        assertThat(logStatement.get(0).getFormattedMessage(), Is.is("Retrieved event queue message with id [queue-message-id] for resource external id [a-resource-external-id]"));\n        assertThat(logStatement.get(1).getFormattedMessage(), Is.is("Processed notification email for disputed transaction"));\n    }\n\n    @Test\n    void shouldNotCallNotificationServiceWhenServiceDoesNotExist() throws QueueException {\n        var mockQueueMessage = mock(QueueMessage.class);\n        disputeEvent = anEventFixture()\n                .withEventType(EventType.DISPUTE_CREATED.name())\n                .withEventDetails(objectMapper.valueToTree(Map.of("amount", 21000L, "fee", 1500L, "evidence_due_date", "2022-03-07T13:00:00Z", "gateway_account_id", gatewayAccountId)))\n                .withParentResourceExternalId("456")\n                .build();\n        var eventMessage = EventMessage.of(disputeEvent, mockQueueMessage);\n        when(mockEventSubscriberQueue.retrieveEvents()).thenReturn(List.of(eventMessage));\n        when(mockServiceFinder.byGatewayAccountId(gatewayAccountId)).thenReturn(Optional.empty());\n\n        eventMessageHandler.processMessages();\n\n        verify(mockNotificationService, never()).sendStripeDisputeCreatedEmail(anySet(), anyMap());\n    }\n\n    @Test\n    void shouldNotCallNotificationServiceWhenTransactionDoesNotExist() throws QueueException {\n        var mockQueueMessage = mock(QueueMessage.class);\n        disputeEvent = anEventFixture()\n                .withEventType(EventType.DISPUTE_CREATED.name())\n                .withEventDetails(objectMapper.valueToTree(Map.of("amount", 21000L, "fee", 1500L, "evidence_due_date", "2022-03-07T13:00:00.001Z", "gateway_account_id", gatewayAccountId)))\n                .withParentResourceExternalId("456")\n                .build();\n        var eventMessage = EventMessage.of(disputeEvent, mockQueueMessage);\n        when(mockEventSubscriberQueue.retrieveEvents()).thenReturn(List.of(eventMessage));\n        when(mockServiceFinder.byGatewayAccountId(gatewayAccountId)).thenReturn(Optional.of(service));\n        when(mockLedgerService.getTransaction(transaction.getTransactionId())).thenReturn(Optional.empty());\n\n        eventMessageHandler.processMessages();\n\n        verify(mockNotificationService, never()).sendStripeDisputeCreatedEmail(anySet(), anyMap());\n    }\n\n    @Test\n    void shouldNotCallNotificationServiceWhenNoAdminUsersExist() throws QueueException {\n        var mockQueueMessage = mock(QueueMessage.class);\n        disputeEvent = anEventFixture()\n                .withEventType(EventType.DISPUTE_CREATED.name())\n                .withEventDetails(objectMapper.valueToTree(Map.of("amount", 21000L, "fee", 1500L, "evidence_due_date", "2022-03-07T13:00:00.001Z", "gateway_account_id", gatewayAccountId)))\n                .withParentResourceExternalId("456")\n                .build();\n        var eventMessage = EventMessage.of(disputeEvent, mockQueueMessage);\n        when(mockEventSubscriberQueue.retrieveEvents()).thenReturn(List.of(eventMessage));\n\n        when(mockServiceFinder.byGatewayAccountId(gatewayAccountId)).thenReturn(Optional.of(service));\n        when(mockLedgerService.getTransaction(transaction.getTransactionId())).thenReturn(Optional.of(transaction));\n        when(mockUserServices.getAdminUsersForService(service.getId())).thenReturn(Collections.emptyList());\n\n        eventMessageHandler.processMessages();\n\n        verify(mockNotificationService, never()).sendStripeDisputeCreatedEmail(anySet(), anyMap());\n    }\n}\n'
                )
            coder = UnifiedDiffCoder(repo_dir=tmpdirname)
            edits = coder.get_edits(diff)
            print(edits)
            assert len(edits) >= 1
            for edit in edits:
                print(edit)
                assert path in edit
            success, err = coder.apply_edits(diff)
            assert success, err

    # diff = "```diff\n--- a/src/test/java/uk/gov/pay/adminusers/queue/event/EventMessageHandlerTest.java\n+++ b/src/test/java/uk/gov/pay/adminusers/queue/event/EventMessageHandlerTest.java\n@@ -17,7 +17,7 @@ import ch.qos.logback.classic.spi.ILoggingEvent;\n import com.fasterxml.jackson.databind.ObjectMapper;\n import com.google.gson.GsonBuilder;\n -import org.slf4j.spi.LoggingEventAware;\n +import org.slf4j.event.LoggingEvent;\n import org.junit.jupiter.api.BeforeEach;\n import org.junit.jupiter.api.Test;\n import org.junit.jupiter.api.extension.ExtendWith;\n```"
    # diff_2 = "```diff\n--- a/src/test/java/uk/gov/pay/adminusers/queue/event/EventMessageHandlerTest.java\n+++ b/src/test/java/uk/gov/pay/adminusers/queue/event/EventMessageHandlerTest.java\n@@ -17,7 +17,7 @@ import ch.qos.logback.classic.spi.ILoggingEvent;\n import com.fasterxml.jackson.databind.ObjectMapper;\n import com.google.gson.GsonBuilder;\n --import org.slf4j.spi.LoggingEventAware;\n +import org.slf4j.event.LoggingEvent;\n import org.junit.jupiter.api.BeforeEach;\n import org.junit.jupiter.api.Test;\n import org.junit.jupiter.api.extension.ExtendWith;\n```"
    # diff_3 = "```diff\n--- a/src/main/java/de/gwdg/metadataqa/marc/dao/MarcRecord.java\n+++ b/src/main/java/de/gwdg/metadataqa/marc/dao/MarcRecord.java\n@@ -7,7 +7,7 @@\n import de.gwdg.metadataqa.marc.Extractable;\n import de.gwdg.metadataqa.marc.MarcFactory;\n -import de.gwdg.metadataqa.marc.MarcSubfield;\n +import de.gwdg.metadataqa.marc.model.MarcSubfield;\n import de.gwdg.metadataqa.marc.Validatable;\n import de.gwdg.metadataqa.marc.cli.utils.IgnorableFields;\n import de.gwdg.metadataqa.marc.definition.*;\n@@ -254,7 +254,7 @@\n public class MarcRecord implements Extractable, Validatable, Serializable {\n     * @param tag\n     * @param subfield\n     -public List<String> extract(String tag, String subfield, RESOLVE doResolve) {\n     +public List<String> extract(String tag, String subfield, MarcSubfield.Resolve doResolve) {\n         List<String> values = new ArrayList<>();\n         List<DataField> fields = getDatafield(tag);\n         if (fields != null && !fields.isEmpty()) {\n```"
    # diff_4 = "```diff\n--- src/test/java/uk/gov/pay/adminusers/queue/event/EventMessageHandlerTest.java\n+++ src/test/java/uk/gov/pay/adminusers/queue/event/EventMessageHandlerTest.java\n@@ -1,5 +1,5 @@\n package uk.gov.pay.adminusers.queue.event; \n import ch.qos.logback.classic.Level; \n import ch.qos.logback.classic.Logger; \n-import ch.qos.logback.classic.spi.ILoggingEvent; \n+import org.slf4j.spi.LoggingEventAware; \n import ch.qos.logback.core.Appender; \n import com.fasterxml.jackson.databind.ObjectMapper; \n import com.google.gson.GsonBuilder; \n```"

    diff_5 = "```diff\n--- a/src/test/java/uk/gov/pay/adminusers/queue/event/EventMessageHandlerTest.java\n+++ b/src/test/java/uk/gov/pay/adminusers/queue/event/EventMessageHandlerTest.java\n@@ -1,11 +1,11 @@\n-package uk.gov.pay.adminusers.queue.event;\n+import org.slf4j.Logger;\n+import org.slf4j.LoggerFactory;\n import ch.qos.logback.classic.Level;\n-import ch.qos.logback.classic.Logger;\n-import ch.qos.logback.classic.spi.ILoggingEvent;\n-import ch.qos.logback.core.Appender;\n+import org.slf4j.MDC;\n import com.fasterxml.jackson.databind.ObjectMapper;\n import com.google.gson.GsonBuilder;\n import org.hamcrest.core.Is;\n@@ -13,7 +13,7 @@\n-import ch.qos.logback.classic.spi.ILoggingEvent;\n-import ch.qos.logback.core.Appender;\n+import uk.gov.service.payments.commons.queue.model.EventType;\n import uk.gov.pay.adminusers.service.UserServices;\n@@ -22,7 +22,7 @@\n-import static org.mockito.Mockito.anySet;\n+import static org.mockito.Mockito.any;\n import static org.mockito.Mockito.atMostOnce;\n import static org.mockito.Mockito.mock;\n import static org.mockito.Mockito.never;\n@@ -30,7 +30,7 @@\n-import static uk.gov.pay.adminusers.app.util.RandomIdGenerator.randomUuid;\n+import static java.util.UUID.randomUUID;\n import static uk.gov.pay.adminusers.fixtures.EventFixture.anEventFixture;\n import static uk.gov.pay.adminusers.fixtures.LedgerTransactionFixture.aLedgerTransactionFixture;\n import static uk.gov.pay.adminusers.model.Service.DEFAULT_NAME_VALUE;\n@@ -40,7 +40,7 @@\n-@Mock private EventSubscriberQueue mockEventSubscriberQueue;\n+private EventSubscriberQueue mockEventSubscriberQueue = mock(EventSubscriberQueue.class);\n```"
    # _assert_file(diff, "src/test/java/uk/gov/pay/adminusers/queue/event/EventMessageHandlerTest.java")
    # _assert_file(diff_2, "src/test/java/uk/gov/pay/adminusers/queue/event/EventMessageHandlerTest.java")
    # _assert_file(diff_3, "src/main/java/de/gwdg/metadataqa/marc/dao/MarcRecord.java")
    # _assert_file(diff_4, "src/test/java/uk/gov/pay/adminusers/queue/event/EventMessageHandlerTest.java")

    _assert_file(
        diff_5,
        "src/test/java/uk/gov/pay/adminusers/queue/event/EventMessageHandlerTest.java",
    )
    print("All tests passed")


# llama8b is doing some fun stuff....
def test_get_edits_with_comments():
    initial_content = """package com.feedzai.commons.sql.abstraction.engine.impl.mysql;

import com.feedzai.commons.sql.abstraction.engine.handler.QueryExceptionHandler;

import com.mysql.jdbc.exceptions.MySQLTimeoutException;

import java.sql.SQLException;

public class MySqlQueryExceptionHandler extends QueryExceptionHandler {

    private static final int UNIQUE_CONSTRAINT_VIOLATION_ERROR_CODE = 1062;

    @Override
    public boolean isTimeoutException(final SQLException exception) {
        return exception instanceof MySQLTimeoutException || super.isTimeoutException(exception);
    }

    @Override
    public boolean isUniqueConstraintViolationException(final SQLException exception) {
        return UNIQUE_CONSTRAINT_VIOLATION_ERROR_CODE == exception.getErrorCode()
                || super.isUniqueConstraintViolationException(exception);
    }
}"""
    diff_content = "Here is the diff to fix the changes in the API:\n\n```diff\n--- src/main/java/com/feedzai/commons/sql/abstraction/engine/impl/mysql/MySqlQueryExceptionHandler.java\n+++ src/main/java/com/feedzai/commons/sql/abstraction/engine/impl/mysql/MySqlQueryExceptionHandler.java\n@@ \npackage com.feedzai.commons.sql.abstraction.engine.impl.mysql;\nimport com.feedzai.commons.sql.abstraction.engine.handler.QueryExceptionHandler;\n+import org.mariadb.jdbc.exceptions.MariaDBTimeoutException;\n+import java.sql.SQLException;\n\npublic class MySqlQueryExceptionHandler extends QueryExceptionHandler {\n    private static final int UNIQUE_CONSTRAINT_VIOLATION_ERROR_CODE = 1062;\n```"

    with tempfile.TemporaryDirectory() as tmpdirname:
        file_path = (
            Path(tmpdirname)
            / "src/main/java/com/feedzai/commons/sql/abstraction/engine/impl/mysql/MySqlQueryExceptionHandler.java"
        )
        os.makedirs(file_path.parent, exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(initial_content)
        coder = UnifiedDiffCoder(repo_dir=tmpdirname)
        edits = coder.apply_edits(diff_content)
        print(edits)

        assert len(edits) == 2


def test_apply_edits_success(temp_file):
    coder = UnifiedDiffCoder(repo_dir=str(Path(temp_file).parent))
    diff_content = """```diff diff --git a/test_file.py b/test_file.py
--- a/test_file.py
+++ b/test_file.py
@@ @@
-line1
+line1_modified
```
"""
    success, content = coder.apply_edits(diff_content)
    assert success
    assert content == "line1_modified\nline2\nline3\n"


def test_apply_edits_no_match_error(temp_file):
    coder = UnifiedDiffCoder(repo_dir=str(Path(temp_file).parent))
    diff_content = """```diff diff --git a/test_file.py b/test_file.py
--- a/test_file.py
+++ b/test_file.py
@@ @@
-line_nonexistent
+line1_modified
```
"""
    success, error = coder.apply_edits(diff_content)
    assert not success
    assert isinstance(error, ValueError)
    assert "UnifiedDiffNoMatch" in str(error)


def test_apply_edits_not_unique_error(temp_file):
    with open(temp_file, "a", encoding="utf-8") as f:
        f.write("line1\nline2\nline3\n")

    coder = UnifiedDiffCoder(repo_dir=str(Path(temp_file).parent))
    diff_content = """```diff diff --git a/test_file.py b/test_file.py
--- a/test_file.py
+++ b/test_file.py
@@ @@
-line1
+line1_modified
```
"""
    success, error = coder.apply_edits(diff_content)
    assert not success
    assert isinstance(error, ValueError)
    assert "UnifiedDiffNoMatch" in str(error)


def test_apply_edits_no_edits_error(temp_file):
    coder = UnifiedDiffCoder(repo_dir=str(Path(temp_file).parent))
    diff_content = "```diff diff --git a/test_file.py b/test_file.py\n--- a/test_file.py\n+++ b/test_file.py\n```"
    success, error = coder.apply_edits(diff_content)
    assert not success
    assert isinstance(error, ValueError)
    assert "UnifiedDiffNoEdits" in str(error)


def test_apply_weird_llama_format(temp_file):
    coder = UnifiedDiffCoder(repo_dir=str(Path(temp_file).parent))
    diff_content = """```diff -U0 
test_file.py 
test_file.py
@@ -108,5 +108,5 -line1
+line1_modified```
```"""
    print(coder.get_edits(diff_content))
    success, error = coder.apply_edits(diff_content)
    assert not success
    assert isinstance(error, ValueError)
    assert "UnifiedDiffNoEdits" in str(error)
