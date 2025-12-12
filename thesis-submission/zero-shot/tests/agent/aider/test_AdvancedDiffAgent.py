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
        coder = UnifiedDiffCoder(repo_dir="")
        edits = coder.get_edits(diff)
        print(edits)
        assert len(edits) >= 1
        for edit in edits:
            print(edit)
            assert path in edit
    diff = "```diff\n--- a/src/test/java/uk/gov/pay/adminusers/queue/event/EventMessageHandlerTest.java\n+++ b/src/test/java/uk/gov/pay/adminusers/queue/event/EventMessageHandlerTest.java\n@@ -17,7 +17,7 @@ import ch.qos.logback.classic.spi.ILoggingEvent;\n import com.fasterxml.jackson.databind.ObjectMapper;\n import com.google.gson.GsonBuilder;\n -import org.slf4j.spi.LoggingEventAware;\n +import org.slf4j.event.LoggingEvent;\n import org.junit.jupiter.api.BeforeEach;\n import org.junit.jupiter.api.Test;\n import org.junit.jupiter.api.extension.ExtendWith;\n```"
    diff_2 = "```diff\n--- a/src/test/java/uk/gov/pay/adminusers/queue/event/EventMessageHandlerTest.java\n+++ b/src/test/java/uk/gov/pay/adminusers/queue/event/EventMessageHandlerTest.java\n@@ -17,7 +17,7 @@ import ch.qos.logback.classic.spi.ILoggingEvent;\n import com.fasterxml.jackson.databind.ObjectMapper;\n import com.google.gson.GsonBuilder;\n --import org.slf4j.spi.LoggingEventAware;\n +import org.slf4j.event.LoggingEvent;\n import org.junit.jupiter.api.BeforeEach;\n import org.junit.jupiter.api.Test;\n import org.junit.jupiter.api.extension.ExtendWith;\n```"
    diff_3 = "```diff\n--- a/src/main/java/de/gwdg/metadataqa/marc/dao/MarcRecord.java\n+++ b/src/main/java/de/gwdg/metadataqa/marc/dao/MarcRecord.java\n@@ -7,7 +7,7 @@\n import de.gwdg.metadataqa.marc.Extractable;\n import de.gwdg.metadataqa.marc.MarcFactory;\n -import de.gwdg.metadataqa.marc.MarcSubfield;\n +import de.gwdg.metadataqa.marc.model.MarcSubfield;\n import de.gwdg.metadataqa.marc.Validatable;\n import de.gwdg.metadataqa.marc.cli.utils.IgnorableFields;\n import de.gwdg.metadataqa.marc.definition.*;\n@@ -254,7 +254,7 @@\n public class MarcRecord implements Extractable, Validatable, Serializable {\n     * @param tag\n     * @param subfield\n     -public List<String> extract(String tag, String subfield, RESOLVE doResolve) {\n     +public List<String> extract(String tag, String subfield, MarcSubfield.Resolve doResolve) {\n         List<String> values = new ArrayList<>();\n         List<DataField> fields = getDatafield(tag);\n         if (fields != null && !fields.isEmpty()) {\n```"
    diff_4 = "```diff\n--- src/test/java/uk/gov/pay/adminusers/queue/event/EventMessageHandlerTest.java\n+++ src/test/java/uk/gov/pay/adminusers/queue/event/EventMessageHandlerTest.java\n@@ -1,5 +1,5 @@\n package uk.gov.pay.adminusers.queue.event; \n import ch.qos.logback.classic.Level; \n import ch.qos.logback.classic.Logger; \n-import ch.qos.logback.classic.spi.ILoggingEvent; \n+import org.slf4j.spi.LoggingEventAware; \n import ch.qos.logback.core.Appender; \n import com.fasterxml.jackson.databind.ObjectMapper; \n import com.google.gson.GsonBuilder; \n```"
    
    _assert_file(diff, "src/test/java/uk/gov/pay/adminusers/queue/event/EventMessageHandlerTest.java")
    _assert_file(diff_2, "src/test/java/uk/gov/pay/adminusers/queue/event/EventMessageHandlerTest.java")
    _assert_file(diff_3, "src/main/java/de/gwdg/metadataqa/marc/dao/MarcRecord.java")
    _assert_file(diff_4, "src/test/java/uk/gov/pay/adminusers/queue/event/EventMessageHandlerTest.java")
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
