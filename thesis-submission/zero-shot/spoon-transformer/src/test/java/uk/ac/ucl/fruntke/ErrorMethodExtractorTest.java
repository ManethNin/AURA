package org.coderepair;

import org.assertj.core.api.SoftAssertions;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.io.ObjectInputFilter.Config;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Arrays;
import java.util.List;
import java.util.logging.Logger;
import java.util.logging.Level;

class ErrorMethodExtractorTest {
    private static final Logger LOGGER = Logger.getLogger(ErrorMethodExtractorTest.class.getName());
    private SoftAssertions softly;

    @TempDir
    Path tempDir;

    @BeforeEach
    void setUp() {
        LOGGER.setLevel(Level.ALL);
        softly = new SoftAssertions();
    }

    @Test
    void testSingleClassWithSingleError() throws Exception {
        LOGGER.info("Starting testSingleClassWithSingleError");
        String input =
            "package de.test;\n" +
            "public class TestClass {\n" +
            "    public void method1() {\n" +
            "        int x = 5;\n" +
            "    }\n" +
            "    public void method2() {\n" +
            "        String s = null;\n" +
            "        s.length(); // NullPointerException\n" +
            "    }\n" +
            "}";

        Path sourceFile = tempDir.resolve("TestClass.java");
        Files.writeString(sourceFile, input);

        List<ErrorMethodExtractor.CompilationError> errors = Arrays.asList(
            new ErrorMethodExtractor.CompilationError("TestClass.java", 7, 10)
        );

        String result = ErrorMethodExtractor.extractRelevantCode(true, sourceFile.toString(), errors);
        LOGGER.info("Extraction result:\n" + result);

        softly.assertThat(result).contains("public class TestClass");
        softly.assertThat(result).contains("public void method2()");
        softly.assertThat(result).contains("s.length();");
        softly.assertThat(result).contains("NullPointerException");
        // softly.assertThat(result).doesNotContain("public void method1()");
        // softly.assertThat(result).doesNotContain("int x = 5;");
        softly.assertThat(result).doesNotContain("unnamed package");
        softly.assertThat(result).contains("package de.test;");

        String expected = SnapshotUtils.getOrUpdateSnapshot("testSingleClassWithSingleError", result);
        softly.assertThat(result).isEqualTo(expected);
        softly.assertAll();
    }

    @Test
    void testMultipleClassesWithErrors() throws Exception {
        LOGGER.info("Starting testMultipleClassesWithErrors");
        String input =
            "public class Class1 {\n" +
            "    public void methodA() {\n" +
            "        int x = 5 / 0; // ArithmeticException\n" +
            "    }\n" +
            "}\n" +
            "class Class2 {\n" +
            "    public void methodB() {\n" +
            "        String s = null;\n" +
            "        s.length(); // NullPointerException\n" +
            "    }\n" +
            "}";

        Path sourceFile = tempDir.resolve("MultiClass.java");
        Files.writeString(sourceFile, input);

        List<ErrorMethodExtractor.CompilationError> errors = Arrays.asList(
            new ErrorMethodExtractor.CompilationError("MultiClass.java", 3, 15),
            new ErrorMethodExtractor.CompilationError("MultiClass.java", 9, 10)
        );

        String result = ErrorMethodExtractor.extractRelevantCode(true, sourceFile.toString(), errors);
        LOGGER.info("Extraction result:\n" + result);

        softly.assertThat(result).contains("public class Class1");
        softly.assertThat(result).contains("class Class2");
        softly.assertThat(result).contains("public void methodA()");
        softly.assertThat(result).contains("public void methodB()");
        softly.assertThat(result).contains("int x = 5 / 0;");
        softly.assertThat(result).contains("s.length();");
        softly.assertThat(result).contains("ArithmeticException");
        softly.assertThat(result).contains("NullPointerException");

        String expected = SnapshotUtils.getOrUpdateSnapshot("testMultipleClassesWithErrors", result);
        softly.assertThat(result).isEqualTo(expected);
        softly.assertAll();
    }

    @Test
    void testClassWithImportsAndComments() throws Exception {
        LOGGER.info("Starting testClassWithImportsAndComments");
        String input =
            "package com.example;\n" +
            "import java.util.List;\n" +
            "import java.util.ArrayList;\n" +
            "\n" +
            "/**\n" +
            " * This is a test class\n" +
            " */\n" +
            "public class TestClass {\n" +
            "    // This method has an error\n" +
            "    public void errorMethod() {\n" +
            "        List<String> list = null;\n" +
            "        list.add(\"Hello\"); // NullPointerException\n" +
            "    }\n" +
            "\n" +
            "    // This method is fine\n" +
            "    public void okMethod() {\n" +
            "        System.out.println(\"OK\");\n" +
            "    }\n" +
            "}";

        Path sourceFile = tempDir.resolve("TestClass.java");
        Files.writeString(sourceFile, input);

        List<ErrorMethodExtractor.CompilationError> errors = Arrays.asList(
            new ErrorMethodExtractor.CompilationError("TestClass.java", 11, 10)
        );

        String result = ErrorMethodExtractor.extractRelevantCode(true, sourceFile.toString(), errors);
        LOGGER.info("Extraction result:\n" + result);

        softly.assertThat(result).contains("import java.util.List;");
        softly.assertThat(result).contains("import java.util.ArrayList;");
        softly.assertThat(result).contains("* This is a test class");
        softly.assertThat(result).contains("public class TestClass");
        softly.assertThat(result).contains("// This method has an error");
        softly.assertThat(result).contains("public void errorMethod()");
        softly.assertThat(result).contains("list.add(\"Hello\");");
        softly.assertThat(result).contains("NullPointerException");
        // softly.assertThat(result).doesNotContain("public void okMethod()");
        // softly.assertThat(result).doesNotContain("System.out.println(\"OK\");");
        softly.assertThat(result).contains("package com.example;");

        String expected = SnapshotUtils.getOrUpdateSnapshot("testClassWithImportsAndComments", result);
        softly.assertThat(result).isEqualTo(expected);
        softly.assertAll();
    }

    @Test
    void testRealWorld() throws Exception {
        LOGGER.info("Starting testRealWorld");
        Path inputFile = tempDir.resolve("RealWorld.java");
        Files.copy(Path.of("src/test/java/org/coderepair/test_real"), inputFile);

        List<ErrorMethodExtractor.CompilationError> errors = Arrays.asList(
            new ErrorMethodExtractor.CompilationError("TestClass.java", 41, 36),
            new ErrorMethodExtractor.CompilationError("TestClass.java", 300, 1043)
        );

        String result = ErrorMethodExtractor.extractRelevantCode(true, inputFile.toString(), errors);
        LOGGER.info("Extraction result:\n" + result);

        String expected = SnapshotUtils.getOrUpdateSnapshot("testRealWorld", result);
        softly.assertThat(result).isEqualTo(expected);
        softly.assertAll();
    }

    @Test
    void testRealWorldServer() throws Exception {
        LOGGER.info("Starting testRealWorld");
        Path inputFile = tempDir.resolve("Server.java");
        Files.copy(Path.of("src/test/java/org/coderepair/test_server"), inputFile);

        List<ErrorMethodExtractor.CompilationError> errors = Arrays.asList(
            new ErrorMethodExtractor.CompilationError("TestClass.java", 160, 16),
            new ErrorMethodExtractor.CompilationError("TestClass.java", 285, 18),
            new ErrorMethodExtractor.CompilationError("TestClass.java", 269, 49),
            new ErrorMethodExtractor.CompilationError("TestClass.java", 87, 50),
            new ErrorMethodExtractor.CompilationError("TestClass.java", 118, 29),
            new ErrorMethodExtractor.CompilationError("TestClass.java", 113, 1)
        );

        String result = ErrorMethodExtractor.extractRelevantCode(true,inputFile.toString(), errors);
        LOGGER.info("Extraction result:\n" + result);

        String unwanted_weird_shit = "public abstract class Server<Config extends Configuration> extends Application<Config> {\n"+
        "        bootstrap.addBundle(new SwaggerBundle<>() {";
        
        softly.assertThat(result).doesNotContain(unwanted_weird_shit);


        String expected = SnapshotUtils.getOrUpdateSnapshot("testRealWorldServer", result);
        softly.assertThat(result).isEqualTo(expected);
        softly.assertAll();

        String noComments = ErrorMethodExtractor.extractRelevantCode(false,inputFile.toString(), errors);
        LOGGER.info("Extraction result:\n" + result);

        String expectedNoComments = SnapshotUtils.getOrUpdateSnapshot("testRealWorldServerNoComments", noComments);
        softly.assertThat(noComments).isEqualTo(expectedNoComments);
        softly.assertAll();
    }

    @Test
    void testRealWorldNoComments() throws Exception {
        LOGGER.info("Starting testRealWorldNoComments");
        Path inputFile = tempDir.resolve("RealWorld.java");
        Files.copy(Path.of("src/test/java/org/coderepair/test_real"), inputFile);

        List<ErrorMethodExtractor.CompilationError> errors = Arrays.asList(
            new ErrorMethodExtractor.CompilationError("TestClass.java", 41, 36),
            new ErrorMethodExtractor.CompilationError("TestClass.java", 300, 1043)
        );

        String result = ErrorMethodExtractor.extractRelevantCode(false, inputFile.toString(), errors);
        LOGGER.info("Extraction result:\n" + result);

        String expected = SnapshotUtils.getOrUpdateSnapshot("testRealWorldNoComments", result);
        softly.assertThat(result).isEqualTo(expected);
        softly.assertAll();
    }
}
