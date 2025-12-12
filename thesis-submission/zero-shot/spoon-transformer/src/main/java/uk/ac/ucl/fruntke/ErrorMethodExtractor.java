package org.coderepair;
import spoon.Launcher;
import spoon.reflect.CtModel;
import spoon.reflect.code.CtFieldAccess;
import spoon.reflect.code.CtInvocation;
import spoon.reflect.declaration.*;
import spoon.reflect.cu.SourcePosition;
import spoon.reflect.reference.CtFieldReference;
import spoon.reflect.reference.CtExecutableReference;
import spoon.reflect.reference.CtTypeReference;
import spoon.reflect.visitor.filter.TypeFilter;
import spoon.support.compiler.VirtualFile;

import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.*;
import java.util.stream.Collectors;

import spoon.Launcher;
import spoon.reflect.CtModel;
import spoon.reflect.code.CtFieldAccess;
import spoon.reflect.code.CtInvocation;
import spoon.reflect.declaration.*;
import spoon.reflect.cu.SourcePosition;
import spoon.reflect.reference.CtFieldReference;
import spoon.reflect.reference.CtExecutableReference;
import spoon.reflect.reference.CtTypeReference;
import spoon.reflect.visitor.filter.TypeFilter;
import spoon.support.compiler.VirtualFile;

import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.*;
import java.util.stream.Collectors;

public class ErrorMethodExtractor {
    private static final String END_OF_INPUT_MARKER = "##END_OF_INPUT##";

    public static void main(String[] args) {
        boolean includeComments = !Arrays.asList(args).contains("--no-comments");
        Map<String, List<CompilationError>> errors = readErrors();
        
        for (String filePath : errors.keySet()) {
            String result = extractRelevantCode(includeComments, filePath, errors.get(filePath));
            System.out.println("FILE_START:" + filePath);
            System.out.println(result);
            System.out.println("FILE_END");
        }
    }

    private static Map<String, List<CompilationError>> readErrors() {
        Map<String, List<CompilationError>> errors = new HashMap<>();
        try (Scanner scanner = new Scanner(System.in)) {
            while (scanner.hasNextLine()) {
                String errorLine = scanner.nextLine();
                if (errorLine.equals(END_OF_INPUT_MARKER)) {
                    break;
                }
                String[] errorParts = errorLine.split(":");
                if (errorParts.length == 3) {
                    String fileName = errorParts[0];
                    int line = Integer.parseInt(errorParts[1]);
                    int column = Integer.parseInt(errorParts[2]);
                    errors.computeIfAbsent(fileName, k -> new ArrayList<>())
                            .add(new CompilationError(fileName, line, column));
                } else {
                    System.err.println("Invalid error format: " + errorLine);
                }
            }
        }
        return errors;
    }

    public static String extractRelevantCode(boolean includeComments, String filePath, List<CompilationError> fileErrors) {
        try {
            String fileContent = new String(Files.readAllBytes(Paths.get(filePath)));
            Launcher spoon = new Launcher();
            spoon.addInputResource(new VirtualFile(fileContent));
            spoon.getEnvironment().setNoClasspath(true);
            spoon.getEnvironment().setCommentEnabled(includeComments);
            spoon.buildModel();
            CtModel model = spoon.getModel();

            List<CtType<?>> types = model.getElements(new TypeFilter<>(CtType.class));
            if (types.isEmpty()) {
                throw new RuntimeException("No types found in the model for file: " + filePath);
            }

            StringBuilder resultBuilder = new StringBuilder();
            boolean addedImports = false;

            for (CtType<?> type : types) {
                if (type.isTopLevel()) {
                    if (!addedImports) {
                        addPackageAndImportsInOriginalOrder(resultBuilder, type, fileContent);
                        addedImports = true;
                    }
                    processType(resultBuilder, type, fileContent, includeComments, fileErrors);
                }
            }

            return resultBuilder.toString().trim();
        } catch (Exception e) {
            e.printStackTrace();
            return "Error processing file: " + e.getMessage();
        }
    }

    private static void addPackageAndImportsInOriginalOrder(StringBuilder builder, CtType<?> type, String fileContent) {
        String[] lines = fileContent.split("\n");
        boolean inPackageOrImports = false;
        boolean addedNewLineAfterPackage = false;

        for (String line : lines) {
            String trimmedLine = line.trim();
            if (trimmedLine.startsWith("package ") || trimmedLine.startsWith("import ")) {
                inPackageOrImports = true;
                builder.append(line).append("\n");
                if (trimmedLine.startsWith("package ") && !addedNewLineAfterPackage) {
                    builder.append("\n");
                    addedNewLineAfterPackage = true;
                }
            } else if (inPackageOrImports && !trimmedLine.isEmpty()) {
                // We've reached the end of imports
                break;
            }
        }
        builder.append("\n");
    }

    private static void processType(StringBuilder builder, CtType<?> type, String fileContent, boolean includeComments, List<CompilationError> fileErrors) {
        boolean retainEntireClass = shouldRetainEntireClass(type, fileErrors);
        if (retainEntireClass) {
            addEntireClass(builder, type, fileContent, includeComments);
        } else {
            Set<CtTypeMember> relevantMembers = new LinkedHashSet<>();
            for (CtTypeMember member : type.getTypeMembers()) {
                if (member instanceof CtMethod && isMethodRelevant((CtMethod<?>) member, fileErrors)) {
                    relevantMembers.add(member);
                    relevantMembers.addAll(findReferencedMembers((CtMethod<?>) member, type));
                } else if (member instanceof CtType) {
                    if (hasRelevantNestedContent((CtType<?>) member, fileErrors)) {
                        relevantMembers.add(member);
                    }
                }
            }

            if (!relevantMembers.isEmpty()) {
                addClassDeclarationWithExactContent(builder, type, fileContent, includeComments);
                for (CtTypeMember member : type.getTypeMembers()) {
                    if (relevantMembers.contains(member)) {
                        if (member instanceof CtType) {
                            processType(builder, (CtType<?>) member, fileContent, includeComments, fileErrors);
                        } else {
                            addMemberWithExactContent(builder, member, fileContent, includeComments);
                        }
                    }
                }
                builder.append("}\n");
            }
        }
    }

    private static boolean hasRelevantNestedContent(CtType<?> nestedType, List<CompilationError> fileErrors) {
        for (CtTypeMember member : nestedType.getTypeMembers()) {
            if (member instanceof CtMethod && isMethodRelevant((CtMethod<?>) member, fileErrors)) {
                return true;
            } else if (member instanceof CtType && hasRelevantNestedContent((CtType<?>) member, fileErrors)) {
                return true;
            }
        }
        return false;
    }


    private static void addClassDeclarationWithExactContent(StringBuilder builder, CtType<?> type, String fileContent, boolean includeComments) {
        SourcePosition position = type.getPosition();
        int startLine = findAnnotationStartLine(position.getLine(), fileContent);
        if (includeComments) {
            startLine = findCommentStartLine(startLine, fileContent);
        }
        int endLine = getClassDeclarationEndLine(type, fileContent);
        
        String[] lines = fileContent.split("\n");
        for (int i = startLine - 1; i <= endLine; i++) {
            builder.append(lines[i]).append("\n");
        }
    }

    private static int getClassDeclarationEndLine(CtType<?> type, String fileContent) {
        String[] lines = fileContent.split("\n");
        int startLine = type.getPosition().getLine() - 1;
        int braceCount = 0;
        boolean foundOpeningBrace = false;

        for (int i = startLine; i < lines.length; i++) {
            if (!foundOpeningBrace && lines[i].contains("{")) {
                foundOpeningBrace = true;
            }
            if (foundOpeningBrace) {
                braceCount += lines[i].chars().filter(ch -> ch == '{').count();
                braceCount -= lines[i].chars().filter(ch -> ch == '}').count();
                if (braceCount == 1) {
                    return i;
                }
            }
        }
        return startLine;
    }

    private static boolean isMethodRelevant(CtMethod<?> method, List<CompilationError> errors) {
        SourcePosition position = method.getPosition();
        return position.isValidPosition() && errors.stream().anyMatch(error -> 
            error.getLine() >= position.getLine() && error.getLine() <= position.getEndLine()
        );
    }

    private static int findAnnotationStartLine(int elementStartLine, String fileContent) {
        String[] lines = fileContent.split("\n");
        int startLine = elementStartLine - 1;
        while (startLine > 0 && lines[startLine - 1].trim().startsWith("@")) {
            startLine--;
        }
        return startLine + 1;
    }


    private static void addMemberWithExactContent(StringBuilder builder, CtTypeMember member, String fileContent, boolean includeComments) {
        SourcePosition position = member.getPosition();
        int startLine = findAnnotationStartLine(position.getLine(), fileContent);
        if (includeComments) {
            startLine = findCommentStartLine(startLine, fileContent);
        }
        int endLine = position.getEndLine();
        
        String[] lines = fileContent.split("\n");
        for (int i = startLine - 1; i < endLine; i++) {
            builder.append(lines[i]).append("\n");
        }
        builder.append("\n");
    }

    private static int findCommentStartLine(int elementStartLine, String fileContent) {
        String[] lines = fileContent.split("\n");
        int commentStartLine = elementStartLine - 1;
        while (commentStartLine > 0 && (lines[commentStartLine - 1].trim().startsWith("//") || 
                                        lines[commentStartLine - 1].trim().startsWith("/*") || 
                                        lines[commentStartLine - 1].trim().startsWith("*") ||
                                        lines[commentStartLine - 1].trim().startsWith("@"))) {
            commentStartLine--;
        }
        return commentStartLine + 1;
    }

    private static Set<CtTypeMember> findReferencedMembers(CtMethod<?> method, CtType<?> type) {
        Set<CtTypeMember> referencedMembers = new HashSet<>();
        
        // Find field accesses
        method.getElements(new TypeFilter<>(CtFieldAccess.class)).forEach(fieldAccess -> {
            CtFieldReference<?> fieldRef = fieldAccess.getVariable();
            if (fieldRef.getDeclaringType() != null && fieldRef.getDeclaringType().equals(type.getReference())) {
                CtField<?> field = type.getField(fieldRef.getSimpleName());
                if (field != null) {
                    referencedMembers.add(field);
                }
            }
        });

        // Find method invocations
        method.getElements(new TypeFilter<>(CtInvocation.class)).forEach(invocation -> {
            CtExecutableReference<?> execRef = invocation.getExecutable();
            if (execRef.getDeclaringType() != null && execRef.getDeclaringType().equals(type.getReference())) {
                CtMethod<?> invokedMethod = type.getMethod(execRef.getSimpleName(), execRef.getParameters().toArray(new CtTypeReference[0]));
                if (invokedMethod != null) {
                    referencedMembers.add(invokedMethod);
                }
            }
        });

        return referencedMembers;
    }

    private static boolean shouldRetainEntireClass(CtType<?> type, List<CompilationError> errors) {
        SourcePosition position = type.getPosition();
        return errors.stream().anyMatch(error -> 
            error.getLine() < position.getLine() || error.getLine() > position.getEndLine()
        );
    }

    private static void addEntireClass(StringBuilder builder, CtType<?> type, String fileContent, boolean includeComments) {
        SourcePosition position = type.getPosition();
        int startLine = findAnnotationStartLine(position.getLine(), fileContent);
        if (includeComments) {
            startLine = findCommentStartLine(startLine, fileContent);
        }
        int endLine = position.getEndLine();
        
        String[] lines = fileContent.split("\n");
        for (int i = startLine - 1; i < endLine; i++) {
            builder.append(lines[i]).append("\n");
        }
    }

    public static class CompilationError {
        private final String fileName;
        private final int line;
        private final int col;

        public CompilationError(String fileName, int line, int col) {
            this.fileName = fileName;
            this.line = line;
            this.col = col;
        }

        public int getLine() {
            return line;
        }
    }
}